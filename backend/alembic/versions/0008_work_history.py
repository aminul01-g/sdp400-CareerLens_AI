"""Revision 8 — the work history, and section-aware CV extraction.

``docs/limitations.md`` used to say the CV pipeline produced "a bag of skill
mentions and some text. Nothing else is extracted, so nothing else influences
the score."

This revision adds the two things that make that less true:

* ``work_history`` — where somebody has worked, and for how long. It makes
  "years of experience" something the document supports rather than a number
  the user typed, which is the difference between a claim and an observation.
  The rows mirror ``user_skill``: a ``source``, a ``confirmed`` flag, and the
  upload a proposed row came from.
* ``resume_detected_skill.section`` — the section a detection was found in.
  A skill under **Skills** is a claim about the person; the same word inside a
  project description is a mention that may describe somebody else's work.
  The two are now distinguishable, and the confirmation screen can say which
  is which.

Revision ID: 0008_work_history
Revises: 0007_recommendation_feedback
Create Date: 2026-10-19
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_work_history"
down_revision: str | None = "0007_recommendation_feedback"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "work_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("employer", sa.String(length=160), nullable=False),
        sa.Column("title", sa.String(length=160), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column(
            "source",
            sa.String(length=20),
            server_default="manual",
            nullable=False,
        ),
        sa.Column(
            "confirmed",
            sa.Boolean(),
            server_default=sa.true(),
            nullable=False,
        ),
        sa.Column("resume_upload_id", sa.Integer(), nullable=True),
        sa.Column("raw_text", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "source IN ('manual','cv_extracted')",
            name="ck_work_history_source_valid",
        ),
        sa.CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR end_date >= start_date",
            name="ck_work_history_end_date_after_start",
        ),
        sa.CheckConstraint(
            "length(trim(employer)) > 0", name="ck_work_history_employer_not_blank"
        ),
        sa.ForeignKeyConstraint(
            ["resume_upload_id"],
            ["resume_upload.id"],
            name="fk_work_history_resume_upload_id_resume_upload",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name="fk_work_history_user_id_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_work_history"),
    )
    op.create_index(
        "ix_work_history_user", "work_history", ["user_id", "start_date"], unique=False
    )

    # The section a detection was found in.
    op.add_column(
        "resume_detected_skill",
        sa.Column("section", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "resume_detected_skill",
        sa.Column(
            "is_declared",
            sa.Boolean(),
            server_default=sa.false(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("resume_detected_skill", "is_declared")
    op.drop_column("resume_detected_skill", "section")

    op.drop_index("ix_work_history_user", table_name="work_history")
    op.drop_table("work_history")
