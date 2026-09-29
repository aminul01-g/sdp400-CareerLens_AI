"""Revision 3 — the feedback table.

Feedback is a thin in-app feature the proposal does not list among its nine
modules, so it lives in its own revision rather than inflating the 14-table core
schema. ``docs/erd.md`` covers the core; this one is documented in the
architecture ADR.

The legacy ``Event`` analytics table is deliberately **not** recreated: it has no
proposal justification and the client-side export that wrote it had no caller.

Revision ID: 0003_feedback
Revises: 0002_domain_schema
Create Date: 2026-09-30
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_feedback"
down_revision: str | None = "0002_domain_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "feedback",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        # NOT NULL. The legacy upload/feedback routes used
        # @jwt_required(optional=True), so anonymous callers wrote rows with
        # user_id = NULL that were permanently unattributable (finding S4).
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(length=60), server_default="general", nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("rating", sa.SmallInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "category IN ('general','bug','feature','ui','data','other')",
            name="ck_feedback_category_valid",
        ),
        sa.CheckConstraint(
            "rating IS NULL OR rating BETWEEN 1 AND 5", name="ck_feedback_rating_range"
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name="fk_feedback_user_id_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_feedback"),
    )
    op.create_index("ix_feedback_user", "feedback", ["user_id", "created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_feedback_user", table_name="feedback")
    op.drop_table("feedback")
