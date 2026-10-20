"""Rate limiting.

``docs/limitations.md`` used to say there was no rate limiting on
authentication or generation endpoints, and that brute-force protection on
login came only from bcrypt's cost factor and JWT expiry. Both of those are
real, and neither is a rate limit: bcrypt's cost makes each guess slow, and
JWT expiry bounds how long a stolen token lasts. Neither bounds how *many*
guesses a caller may make.

This module provides the bound. There are two implementations, and the
configuration chooses between them:

* :class:`SlidingWindowLimiter` keeps the counters **in this process's
  memory**. It is fast, it has no dependencies, and it is the right choice for
  a test or a single-process deployment.
* :class:`SharedSlidingWindowLimiter` keeps them **in the database**, so every
  worker and every replica counts the same events. This is the production
  path, and it exists because the shipped image runs uvicorn with two workers
  (``backend/Dockerfile``): a per-process counter gave the caller twice the
  intended allowance.

Three properties are deliberate, and they hold for both implementations:

1. **Fail open for the limiter, never for the endpoint.** If the limiter
   itself fails, the request is allowed through and the failure is logged. A
   limiter that can take the whole API down is worse than no limiter.
2. **Bounded memory.** A caller must not be able to exhaust memory by
   cycling through addresses, so the number of tracked keys is capped and the
   oldest entries are evicted. The database implementation is bounded by
   deleting rows as they age out of their window.
3. **The clock is injectable**, so the tests do not have to sleep.

The window *slides*: an entry expires exactly ``window_seconds`` after it was
recorded, rather than at a fixed boundary. A fixed window lets a caller make
twice the limit across a boundary; a sliding window does not.
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.exceptions import TooManyRequestsError

logger = logging.getLogger("app.core.rate_limit")

#: The most distinct clients whose history is remembered at once. Beyond this,
#: the least recently used entry is dropped. Chosen so that a normal
#: deployment never reaches it, and a flood of forged addresses cannot grow
#: the table without bound.
MAX_TRACKED_KEYS = 10_000

#: How long a shared limiter waits for a row to age out before deleting it.
#:
#: The rows are only ever read as "everything for this key inside the
#: window", so a row that has just aged out is invisible to a query. It is
#: deleted rather than left behind so the table does not grow without bound.
DEFAULT_SHARED_WINDOW_SECONDS = 300


class SlidingWindowLimiter:
    """A sliding-window counter, one window per key.

    The window *slides*: an entry expires exactly ``window_seconds`` after it
    was recorded, rather than at a fixed boundary. A fixed window lets a
    caller make twice the limit across a boundary; a sliding window does not.
    """

    def __init__(
        self,
        *,
        max_keys: int = MAX_TRACKED_KEYS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._max_keys = max_keys
        self._clock = clock
        self._lock = threading.Lock()
        # An OrderedDict, used as an LRU: the first key is the least recently
        # used, and moving it to the end on access is O(1).
        self._windows: OrderedDict[str, list[float]] = OrderedDict()

    def _prune(self, key: str, now: float, window: float) -> list[float]:
        """Drop the timestamps that have fallen out of the window."""
        entries = self._windows[key]
        cutoff = now - window
        kept = [stamp for stamp in entries if stamp > cutoff]
        if kept:
            self._windows[key] = kept
        else:
            del self._windows[key]
        return kept

    def hit(self, key: str, *, limit: int, window: float) -> tuple[bool, int]:
        """Record an attempt.

        Returns ``(allowed, retry_after_seconds)``. ``retry_after_seconds`` is
        ``0`` when the attempt is allowed, and otherwise the number of seconds
        until the oldest entry in the window expires.
        """
        if limit <= 0 or window <= 0:
            return True, 0

        now = self._clock()
        with self._lock:
            if key not in self._windows and len(self._windows) >= self._max_keys:
                # Evict the least recently used key.
                self._windows.popitem(last=False)
            entries = self._windows.get(key)
            if entries is None:
                self._windows[key] = [now]
                return True, 0

            kept = self._prune(key, now, window)
            if len(kept) >= limit:
                # The oldest entry decides when a slot frees up.
                retry_after = max(1, int(kept[0] + window - now) + 1)
                return False, retry_after

            kept.append(now)
            self._windows[key] = kept
            self._windows.move_to_end(key)
            return True, 0

    def reset(self) -> None:
        """Forget everything. Used by the tests, and by an operator."""
        with self._lock:
            self._windows.clear()

    def tracked_keys(self) -> int:
        with self._lock:
            return len(self._windows)


# --------------------------------------------------------------------------- #
# the shared limiter
# --------------------------------------------------------------------------- #


def _lock_key(bucket: str, client_key: str) -> int:
    """A stable 64-bit key for a bucket and client.

    Used as the argument to ``pg_advisory_xact_lock``, which is how two
    processes serialise their count-then-insert for the same client. The hash
    is not a security boundary -- it only has to spread different keys onto
    different lock slots -- but it is a hash rather than the raw string
    because the lock argument is a single 64-bit integer.
    """
    digest = hashlib.blake2b(
        f"{bucket}\x00{client_key}".encode(), digest_size=8
    ).digest()
    return int.from_bytes(digest, "big", signed=True)


class SharedSlidingWindowLimiter:
    """A sliding window that every process in the deployment shares.

    The state is a table, not a dictionary. Each attempt is a row in
    ``rate_limit_event``, and the window is the set of rows for a
    ``(bucket, client)`` pair inside the last N seconds. Two uvicorn workers
    on the same host therefore count the same events, which is the whole
    point: a per-process counter gave the caller twice the allowance the
    configuration asked for.

    Concurrency is handled with a PostgreSQL advisory lock held for the
    duration of the counting transaction. The lock is per ``(bucket, client)``,
    so two different clients never wait for each other, and it is released
    when the transaction ends -- which is why the limiter opens **its own**
    short-lived session rather than borrowing the request's. Borrowing the
    request's session would mean either committing the request's pending work
    from a dependency, or holding the lock for the whole request.

    A concurrent burst can still overshoot the limit by a small amount if two
    workers reach the counter at the same instant. That is the accepted
    trade-off: the limiter must not become a lock, and a limit that is off by
    one under a burst is still a limit.
    """

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session] | None = None,
        clock: Callable[[], float] = time.time,
        window_seconds: float = DEFAULT_SHARED_WINDOW_SECONDS,
    ) -> None:
        self._session_factory = session_factory
        self._clock = clock
        self._window_seconds = window_seconds

    def _factory(self) -> Callable[[], Session]:
        if self._session_factory is not None:
            return self._session_factory
        # Imported lazily so that this module can be imported, and unit-tested,
        # without a database.
        from app.db.session import SessionLocal

        return SessionLocal

    def hit(
        self,
        key: str,
        *,
        bucket: str,
        limit: int,
        window: float,
    ) -> tuple[bool, int]:
        """Record an attempt.

        Returns ``(allowed, retry_after_seconds)``. ``retry_after_seconds`` is
        ``0`` when the attempt is allowed, and otherwise the number of seconds
        until the oldest attempt in the window expires.
        """
        if limit <= 0 or window <= 0:
            return True, 0

        from sqlalchemy import delete, func, select, text

        from app.models.rate_limit_event import RateLimitEvent

        now = self._clock()
        occurred_at = datetime.fromtimestamp(now, tz=UTC)
        cutoff = datetime.fromtimestamp(now - window, tz=UTC)
        # Rows older than the longest window we could be asked about are dead
        # weight; the widest window configured in settings is 300 seconds.
        prune_before = datetime.fromtimestamp(
            now - max(window, self._window_seconds), tz=UTC
        )

        session = self._factory()()
        try:
            session.execute(
                text("SELECT pg_advisory_xact_lock(:lock_key)"),
                {"lock_key": _lock_key(bucket, key)},
            )

            # Age the rows out. A row that has left its window is invisible to
            # the count below, so this is housekeeping rather than logic.
            session.execute(
                delete(RateLimitEvent).where(
                    RateLimitEvent.bucket == bucket,
                    RateLimitEvent.client_key == key,
                    RateLimitEvent.occurred_at <= prune_before,
                )
            )
            session.execute(
                delete(RateLimitEvent).where(RateLimitEvent.occurred_at <= prune_before)
            )

            attempts = session.execute(
                select(func.count())
                .select_from(RateLimitEvent)
                .where(
                    RateLimitEvent.bucket == bucket,
                    RateLimitEvent.client_key == key,
                    RateLimitEvent.occurred_at > cutoff,
                )
            ).scalar_one()

            if attempts >= limit:
                oldest = session.execute(
                    select(RateLimitEvent.occurred_at)
                    .where(
                        RateLimitEvent.bucket == bucket,
                        RateLimitEvent.client_key == key,
                        RateLimitEvent.occurred_at > cutoff,
                    )
                    .order_by(RateLimitEvent.occurred_at)
                    .limit(1)
                ).scalar_one()
                elapsed = (occurred_at - oldest).total_seconds()
                retry_after = max(1, int(window - elapsed) + 1)
                session.rollback()
                return False, retry_after

            session.add(
                RateLimitEvent(
                    bucket=bucket,
                    client_key=key,
                    occurred_at=occurred_at,
                )
            )
            session.commit()
            return True, 0
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


#: The process-wide in-memory limiter. A module-level singleton is
#: deliberate: the point is to share the state between requests, and a new
#: instance per request would share nothing.
limiter = SlidingWindowLimiter()

#: The deployment-wide limiter, backed by the database.
shared_limiter = SharedSlidingWindowLimiter()


def check(
    key: str,
    *,
    limit: int,
    window: float,
    bucket: str,
) -> None:
    """Record an attempt against a bucket, raising when the caller is too fast.

    The backend is chosen by the ``RATE_LIMIT_BACKEND`` setting:
    ``"postgres"`` for the shared limiter that every worker counts against,
    and ``"memory"`` for the in-process one.

    Args:
        key: What identifies the caller. Usually ``"{bucket}:{client_ip}"``.
        limit: How many attempts are allowed in the window.
        window: The length of the window, in seconds.
        bucket: The name of the bucket, for the log message.

    Raises:
        TooManyRequestsError: when the caller has made too many attempts.
    """
    try:
        allowed, retry_after = _hit(key, bucket=bucket, limit=limit, window=window)
    except Exception:  # pragma: no cover - the limiter must never break a request
        logger.exception("Rate limiter failed; allowing the request", extra={"kind": "rate_limit"})
        return

    if not allowed:
        logger.warning(
            "Rate limit exceeded for %s (bucket=%s)", key, bucket, extra={"kind": "rate_limit"}
        )
        raise TooManyRequestsError(
            "Too many requests. Please wait a moment and try again.",
            retry_after=retry_after,
        )


def _hit(key: str, *, bucket: str, limit: int, window: float) -> tuple[bool, int]:
    """Ask the configured backend whether this attempt is allowed."""
    from app.core.config import get_settings

    backend = get_settings().rate_limit_backend
    if backend == "postgres":
        return shared_limiter.hit(key, bucket=bucket, limit=limit, window=window)
    return limiter.hit(key, limit=limit, window=window)
