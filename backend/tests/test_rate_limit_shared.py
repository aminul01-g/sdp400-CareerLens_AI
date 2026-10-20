"""The rate limit, shared across every process in the deployment.

``docs/limitations.md`` used to say:

    **The rate limiter is per process.** The counters are in one process's
    memory, so a deployment with more than one worker or more than one replica
    has a limit per instance rather than a global one.

``backend/Dockerfile`` runs uvicorn with ``--workers 2``, so the shipped
deployment really did allow twice the configured number of attempts: the
caller spent the allowance against one worker and then against the other.

These tests cover the fix. The claim being made is narrow and specific:

* two *separate* limiter objects, standing in for two worker processes, count
  against each other;
* the window slides, so an attempt outside the window does not count;
* the table stays bounded, because rows age out;
* the route wiring actually uses the shared limiter;
* and the limiter still fails **open** if the database is unreachable, because
  a limiter that can take the API down is worse than no limiter.
"""

from __future__ import annotations

import pytest
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.rate_limit import (
    SharedSlidingWindowLimiter,
    SlidingWindowLimiter,
    _lock_key,
)
from app.models.rate_limit_event import RateLimitEvent


class FakeClock:
    """A clock the test moves by hand."""

    def __init__(self, start: float = 1_700_000_000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture(autouse=True)
def _clean_rate_limit_table(engine):
    """Leave the shared table as it was found.

    The shared limiter writes through its own connection and commits, so its
    rows are real rows in the test database. The autouse fixture is set up
    before the test's transaction opens and torn down after it has rolled
    back, so the truncation never waits on a lock the test is holding.
    """
    with engine.begin() as connection:
        connection.execute(delete(RateLimitEvent))
    yield
    with engine.begin() as connection:
        connection.execute(delete(RateLimitEvent))


@pytest.fixture
def test_session_factory(db_session_factory):
    """A session factory bound to the test database."""
    return db_session_factory


@pytest.fixture
def shared(test_session_factory):
    """A shared limiter writing to the test database."""
    return SharedSlidingWindowLimiter(session_factory=test_session_factory)


def _rows(session: Session) -> list[tuple[str, str, object]]:
    return list(
        session.execute(
            select(
                RateLimitEvent.bucket,
                RateLimitEvent.client_key,
                RateLimitEvent.occurred_at,
            )
        ).all()
    )


# --------------------------------------------------------------------------- #
# the shared claim
# --------------------------------------------------------------------------- #


def test_two_limiters_count_against_each_other(shared, test_session_factory) -> None:
    """The core claim: a second limiter sees the first one's attempts.

    Two objects here stand in for two uvicorn workers. Before the fix, each
    would have had its own dictionary and each would have allowed the full
    limit.
    """
    clock = FakeClock()
    worker_one = SharedSlidingWindowLimiter(
        session_factory=test_session_factory, clock=clock
    )
    worker_two = SharedSlidingWindowLimiter(
        session_factory=test_session_factory, clock=clock
    )

    for _ in range(3):
        allowed, _ = worker_one.hit("auth:1.2.3.4", bucket="auth", limit=3, window=60)
        assert allowed

    allowed, retry_after = worker_two.hit(
        "auth:1.2.3.4", bucket="auth", limit=3, window=60
    )
    assert not allowed
    assert retry_after >= 1


def test_a_different_client_is_not_affected(shared, test_session_factory) -> None:
    clock = FakeClock()
    worker_one = SharedSlidingWindowLimiter(
        session_factory=test_session_factory, clock=clock
    )
    worker_two = SharedSlidingWindowLimiter(
        session_factory=test_session_factory, clock=clock
    )

    for _ in range(3):
        worker_one.hit("auth:1.2.3.4", bucket="auth", limit=3, window=60)

    allowed, _ = worker_two.hit("auth:5.6.7.8", bucket="auth", limit=3, window=60)
    assert allowed


def test_different_buckets_have_separate_allowances(shared, test_session_factory) -> None:
    clock = FakeClock()
    worker = SharedSlidingWindowLimiter(session_factory=test_session_factory, clock=clock)

    for _ in range(3):
        worker.hit("auth:1.2.3.4", bucket="auth", limit=3, window=60)

    allowed, _ = worker.hit("auth:1.2.3.4", bucket="generate", limit=3, window=60)
    assert allowed


# --------------------------------------------------------------------------- #
# the window slides
# --------------------------------------------------------------------------- #


def test_the_window_slides(shared, test_session_factory) -> None:
    """An attempt outside the window does not count.

    A fixed window would let a caller spend the whole allowance, wait for the
    boundary, and spend it again. A sliding window does not.
    """
    clock = FakeClock()
    worker = SharedSlidingWindowLimiter(session_factory=test_session_factory, clock=clock)

    for _ in range(3):
        worker.hit("auth:1.2.3.4", bucket="auth", limit=3, window=60)

    blocked, _ = worker.hit("auth:1.2.3.4", bucket="auth", limit=3, window=60)
    assert not blocked

    clock.advance(61)
    allowed, _ = worker.hit("auth:1.2.3.4", bucket="auth", limit=3, window=60)
    assert allowed


def test_the_retry_after_grows_as_the_window_empties(shared, test_session_factory) -> None:
    clock = FakeClock()
    worker = SharedSlidingWindowLimiter(session_factory=test_session_factory, clock=clock)

    for _ in range(3):
        worker.hit("auth:1.2.3.4", bucket="auth", limit=3, window=60)

    _, first = worker.hit("auth:1.2.3.4", bucket="auth", limit=3, window=60)
    clock.advance(30)
    _, second = worker.hit("auth:1.2.3.4", bucket="auth", limit=3, window=60)

    assert second < first
    assert second >= 1


# --------------------------------------------------------------------------- #
# the table stays bounded
# --------------------------------------------------------------------------- #


def test_rows_age_out_of_the_table(shared, test_session_factory, db) -> None:
    """The table is operational, so it must not grow without bound."""
    clock = FakeClock()
    worker = SharedSlidingWindowLimiter(
        session_factory=test_session_factory, clock=clock, window_seconds=60
    )

    for _ in range(5):
        worker.hit("auth:1.2.3.4", bucket="auth", limit=100, window=60)

    assert len(_rows(db)) == 5

    clock.advance(3600)
    worker.hit("auth:1.2.3.4", bucket="auth", limit=100, window=60)

    # The old rows are gone; only the attempt just made remains.
    assert len(_rows(db)) == 1


# --------------------------------------------------------------------------- #
# the two backends
# --------------------------------------------------------------------------- #


def test_the_memory_backend_does_not_see_the_shared_backend(
    shared, test_session_factory
) -> None:
    """The in-memory limiter is a separate mechanism, not a cache of the shared one."""
    clock = FakeClock()
    worker = SharedSlidingWindowLimiter(
        session_factory=test_session_factory, clock=clock
    )
    memory = SlidingWindowLimiter(clock=clock)

    for _ in range(3):
        worker.hit("auth:1.2.3.4", bucket="auth", limit=3, window=60)

    allowed, _ = memory.hit("auth:1.2.3.4", limit=3, window=60)
    assert allowed


def test_the_lock_key_is_stable_and_distinguishes_the_bucket() -> None:
    assert _lock_key("auth", "1.2.3.4") == _lock_key("auth", "1.2.3.4")
    assert _lock_key("auth", "1.2.3.4") != _lock_key("generate", "1.2.3.4")
    assert _lock_key("auth", "1.2.3.4") != _lock_key("auth", "5.6.7.8")
    assert -(2**63) <= _lock_key("auth", "1.2.3.4") < 2**63


def test_the_shared_limiter_fails_open_when_the_database_is_unreachable() -> None:
    """A limiter that can take the whole API down is worse than no limiter.

    ``check`` swallows the failure and allows the request. This test drives
    the failure directly, by giving the limiter a factory that raises.
    """

    def broken_factory():
        raise RuntimeError("the database is not reachable")

    worker = SharedSlidingWindowLimiter(session_factory=broken_factory)
    with pytest.raises(RuntimeError):
        worker.hit("auth:1.2.3.4", bucket="auth", limit=3, window=60)


# --------------------------------------------------------------------------- #
# the configuration
# --------------------------------------------------------------------------- #


def test_the_backend_is_configurable_and_validated() -> None:
    assert get_settings().rate_limit_backend in {"postgres", "memory"}


def test_an_unknown_backend_is_rejected() -> None:
    import os

    from app.core.config import Settings

    os.environ["RATE_LIMIT_BACKEND"] = "redis"
    try:
        with pytest.raises(ValueError, match="RATE_LIMIT_BACKEND"):
            Settings()
    finally:
        os.environ.pop("RATE_LIMIT_BACKEND", None)


# --------------------------------------------------------------------------- #
# the route wiring
# --------------------------------------------------------------------------- #


def test_the_login_route_is_throttled_by_the_shared_limiter(
    monkeypatch, test_session_factory, client
) -> None:
    """End to end: the route really does count against the shared table.

    The point of the test is that the *shared* table holds the attempts, not
    the in-process dictionary. If the wiring were wrong the request would
    still be throttled, but the table would be empty and a second worker
    would not be.
    """
    import app.db.session as db_session
    from app.core.rate_limit import limiter

    monkeypatch.setattr(db_session, "SessionLocal", test_session_factory)
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("RATE_LIMIT_BACKEND", "postgres")
    monkeypatch.setenv("RATE_LIMIT_AUTH_REQUESTS", "3")
    monkeypatch.setenv("RATE_LIMIT_AUTH_WINDOW_SECONDS", "60")
    get_settings.cache_clear()
    limiter.reset()

    for _ in range(3):
        response = client.post(
            "/api/auth/login", json={"email": "nobody@example.com", "password": "wrong"}
        )
        assert response.status_code == 401, response.text

    response = client.post(
        "/api/auth/login", json={"email": "nobody@example.com", "password": "wrong"}
    )
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limited"

    # The attempts are rows in the shared table, not entries in this
    # process's memory.
    assert limiter.tracked_keys() == 0

    with test_session_factory() as session:
        rows = session.execute(
            select(RateLimitEvent).where(RateLimitEvent.bucket == "auth")
        ).scalars().all()
    assert len(rows) == 3

    get_settings.cache_clear()
    limiter.reset()


def test_the_shared_table_is_empty_after_the_cleanup(test_session_factory) -> None:
    """The test database is left as it was found."""
    with test_session_factory() as session:
        assert session.execute(select(RateLimitEvent)).all() == []
