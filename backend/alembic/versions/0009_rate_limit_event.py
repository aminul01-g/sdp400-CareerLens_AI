"""Revision 9 — the shared rate limit.

``docs/limitations.md`` used to say the rate limiter was per process:

    **The rate limiter is per process.** The counters are in one process's
    memory, so a deployment with more than one worker or more than one replica
    has a limit per instance rather than a global one.

``backend/Dockerfile`` runs uvicorn with ``--workers 2``, so the shipped
deployment really did have twice the configured allowance. This revision adds
the table that makes the limit deployment-wide: one row per attempt, and the
window is the set of rows for a ``(bucket, client)`` pair inside the last N
seconds.

The table is operational. Nothing in the product reads it, and rows age out
of their window and are deleted.

Revision ID: 0009_rate_limit_event
Revises: 0008_work_history
Create Date: 2026-10-19
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_rate_limit_event"
down_revision: str | None = "0008_work_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "rate_limit_event",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("bucket", sa.String(length=64), nullable=False),
        sa.Column("client_key", sa.String(length=255), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_rate_limit_event")),
    )
    op.create_index(
        "ix_rate_limit_event_window",
        "rate_limit_event",
        ["bucket", "client_key", "occurred_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_rate_limit_event_window", table_name="rate_limit_event")
    op.drop_table("rate_limit_event")
