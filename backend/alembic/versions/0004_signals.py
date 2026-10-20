"""Revision 4 — the context signals: recency, depth, level and industry.

``docs/limitations.md`` said the engine read nothing but skills: a skill last
used in 2004 counted the same as one used last week, a skill listed at
proficiency 5 counted the same whether the user had written one line of it or
a decade of it, and a junior and a principal engineer with identical declared
skills were indistinguishable.

This revision gives the engine somewhere to read those signals from. Nothing
here is a new concept — every column is a fact the product already had a field
for, or a fact the user can now state:

* ``user_skill.last_used_at`` — the recency signal, per skill.
* ``user_skill.years_used`` already existed but was never read by the engine.
  It is the depth signal, and it needs no migration.
* ``profile.seniority`` — the level the user is at.
* ``profile.years_experience`` already existed and was never read either. It is
  the fallback source for the user's level.
* ``profile.industry`` — the sector, which is topical and so joins the text the
  TF-IDF similarity is computed over.
* ``job_role.min_years_experience`` — what a role typically expects, so the
  role's own definition carries the same context the user's does.
* ``recommendation_result.declared_coverage`` / ``signal_coverage`` /
  ``level_fit`` — the intermediate numbers, persisted so a stored run can be
  explained months later without re-running the engine.

Every one of these is **optional**. A row with no value is neutral, not a zero:
the engine applies no penalty to a user who has not filled a field in. That is
the property that keeps this change from being a regression for existing users.

Revision ID: 0004_signals
Revises: 0003_feedback
Create Date: 2026-10-19
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_signals"
down_revision: str | None = "0003_feedback"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # -- user_skill: the recency signal -------------------------------------
    op.add_column(
        "user_skill",
        sa.Column("last_used_at", sa.Date(), nullable=True),
    )

    # -- profile: the level and the sector -----------------------------------
    op.add_column(
        "profile",
        sa.Column("seniority", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "profile",
        sa.Column("industry", sa.String(length=120), nullable=True),
    )

    # -- job_role: what the role itself expects ------------------------------
    op.add_column(
        "job_role",
        sa.Column("min_years_experience", sa.SmallInteger(), nullable=True),
    )
    op.create_check_constraint(
        "ck_job_role_min_years_experience_range",
        "job_role",
        "min_years_experience IS NULL OR min_years_experience BETWEEN 0 AND 60",
    )

    # -- recommendation_result: the intermediate numbers ----------------------
    op.add_column(
        "recommendation_result",
        sa.Column(
            "declared_coverage",
            sa.Numeric(precision=6, scale=5),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "recommendation_result",
        sa.Column(
            "signal_coverage",
            sa.Numeric(precision=6, scale=5),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "recommendation_result",
        sa.Column(
            "level_fit",
            sa.Numeric(precision=4, scale=3),
            nullable=False,
            server_default="1",
        ),
    )
    op.create_check_constraint(
        "ck_recommendation_result_declared_coverage_range",
        "recommendation_result",
        "declared_coverage BETWEEN 0 AND 1",
    )
    op.create_check_constraint(
        "ck_recommendation_result_signal_coverage_range",
        "recommendation_result",
        "signal_coverage BETWEEN 0 AND 1",
    )
    op.create_check_constraint(
        "ck_recommendation_result_level_fit_range",
        "recommendation_result",
        "level_fit BETWEEN 0 AND 1",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_recommendation_result_level_fit_range",
        "recommendation_result",
        type_="check",
    )
    op.drop_constraint(
        "ck_recommendation_result_signal_coverage_range",
        "recommendation_result",
        type_="check",
    )
    op.drop_constraint(
        "ck_recommendation_result_declared_coverage_range",
        "recommendation_result",
        type_="check",
    )
    op.drop_column("recommendation_result", "level_fit")
    op.drop_column("recommendation_result", "signal_coverage")
    op.drop_column("recommendation_result", "declared_coverage")

    op.drop_constraint(
        "ck_job_role_min_years_experience_range", "job_role", type_="check"
    )
    op.drop_column("job_role", "min_years_experience")

    op.drop_column("profile", "industry")
    op.drop_column("profile", "seniority")

    op.drop_column("user_skill", "last_used_at")
