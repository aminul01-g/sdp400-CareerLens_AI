"""``rate_limit_event`` — the shared record of one rate-limited attempt.

``docs/limitations.md`` used to say the rate limiter was per process:

    **The rate limiter is per process.** The counters are in one process's
    memory, so a deployment with more than one worker or more than one replica
    has a limit per instance rather than a global one.

That was true, and it was not academic. ``backend/Dockerfile`` runs uvicorn
with ``--workers 2``, so the shipped deployment had a limit of *twice* the
configured one: a caller could make the full allowance against each worker and
get double the intended budget.

This table is the fix. Each attempt is a row, and the window is the set of
rows for a ``(bucket, client)`` pair inside the last N seconds. Because the
rows live in the database, every worker and every replica counts the same
events.

Three properties matter:

1. **The table is operational, not domain.** It is deleted from on a rolling
   basis as rows age out of their window, so it stays small. Nothing in the
   product reads it.
2. **It is append-only within a window.** There is no update and no
   aggregate row to keep in step. A concurrent burst can overshoot the limit
   by a small amount, which is the accepted trade-off for a limiter that must
   not become a lock.
3. **The client key is the caller's address**, hashed into the bucket that
   applies to it. A forwarded address is the client's problem to solve; the
   limiter's job is to bound the volume.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RateLimitEvent(Base):
    """One attempt against one bucket by one client."""

    __tablename__ = "rate_limit_event"
    __table_args__ = (
        # The lookup is always "the events for this bucket and client inside
        # the window", so the index leads with the two equality columns and
        # ends with the range column.
        Index("ix_rate_limit_event_window", "bucket", "client_key", "occurred_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bucket: Mapped[str] = mapped_column(String(64), nullable=False)
    client_key: Mapped[str] = mapped_column(String(255), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<RateLimitEvent id={self.id} bucket={self.bucket!r} "
            f"client={self.client_key!r} at={self.occurred_at!r}>"
        )
