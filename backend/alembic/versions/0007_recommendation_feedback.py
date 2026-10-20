"""Revision 7 — the feedback loop.

``docs/limitations.md`` used to say there was no feedback loop: a user who
dismissed a recommendation "leaves no trace that affects a future result". The
free-text ``feedback`` table existed and was read by an admin, and that was all
it did.

This revision adds the structured half:

* ``recommendation_feedback`` — what a user did with a role in a run. One row
  per ``(run, role)``, so a user who changes their mind updates the row rather
  than voting twice.
* ``recommendation_result.role_prior`` and ``.feedback_samples`` — the prior
  that was applied to that row, and the number of observations behind it. A
  stored run therefore explains itself: "this role was ranked third, with a
  community prior of -0.08 from 12 observations".

The prior is a **formula**, not a model: a net favourability in ``[-1, 1]``
applied as a bounded multiplier of at most 10%. Proposal §18.9 forbids a
trained ranking model, and nothing here is one — there is no fitting, no
learned coefficients, and the result is reproducible by hand.

Revision ID: 0007_recommendation_feedback
Revises: 0006_auth_tokens
Create Date: 2026-10-19
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_recommendation_feedback"
down_revision: str | None = "0006_auth_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "recommendation_feedback",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("run_id", sa.Integer(), nullable=False),
        sa.Column("job_role_id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "action IN ('saved','dismissed','interested','applied')",
            name="ck_recommendation_feedback_action_valid",
        ),
        sa.ForeignKeyConstraint(
            ["job_role_id"],
            ["job_role.id"],
            name="fk_recommendation_feedback_job_role_id_job_role",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["recommendation_run.id"],
            name="fk_recommendation_feedback_run_id_recommendation_run",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name="fk_recommendation_feedback_user_id_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_recommendation_feedback"),
        sa.UniqueConstraint(
            "run_id", "job_role_id", name="uq_feedback_run_role"
        ),
    )
    op.create_index(
        "ix_recommendation_feedback_role",
        "recommendation_feedback",
        ["job_role_id", "action"],
        unique=False,
    )
    op.create_index(
        "ix_recommendation_feedback_user",
        "recommendation_feedback",
        ["user_id", "created_at"],
        unique=False,
    )

    # The prior and the number of observations behind it, so a stored run can
    # explain the rank it was given.
    op.add_column(
        "recommendation_result",
        sa.Column(
            "role_prior",
            sa.Numeric(precision=4, scale=3),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "recommendation_result",
        sa.Column(
            "feedback_samples",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.create_check_constraint(
        "ck_recommendation_result_role_prior_range",
        "recommendation_result",
        "role_prior BETWEEN -1 AND 1",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_recommendation_result_role_prior_range",
        "recommendation_result",
        type_="check",
    )
    op.drop_column("recommendation_result", "feedback_samples")
    op.drop_column("recommendation_result", "role_prior")

    op.drop_index(
        "ix_recommendation_feedback_user", table_name="recommendation_feedback"
    )
    op.drop_index(
        "ix_recommendation_feedback_role", table_name="recommendation_feedback"
    )
    op.drop_table("recommendation_feedback")
