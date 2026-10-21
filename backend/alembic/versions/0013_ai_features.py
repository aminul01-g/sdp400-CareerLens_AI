"""Revision 13 — the AI layer's two user artefacts, and the language preference.

The AI layer is an *enhancement*: it explains, sequences and drafts, but it
does not decide anything the engine already decides. What it does produce is
worth keeping, and this revision is where it is kept.

* ``learning_roadmap`` and ``learning_roadmap_task`` — a generated plan and
  the learner's progress through it. The plan is stored as a snapshot so a
  plan somebody is halfway through cannot change underneath them; the
  progress lives in columns rather than inside the snapshot, because "which
  tasks have I finished" is a question for a query and not for JSON scanning.
* ``interview_session`` and ``interview_exchange`` — a mock interview and the
  feedback given for each answer. The rubric is stored with the session, so a
  score stays explicable months later.
* ``profile.preferred_language`` — the language the generated explanations are
  written in. It changes the language of an answer and nothing else: skill
  names, role titles and every calculated score stay as the engine produced
  them.

Nothing here is destructive. The migration only adds a column and four
tables, and every foreign key cascades from its owner, so deleting a user
removes their plans and interviews in the same statement as the rest of their
data.

Revision ID: 0013_ai_features
Revises: 0012_achievements
Create Date: 2026-10-21
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013_ai_features"
down_revision: str | None = "0012_achievements"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "profile",
        sa.Column(
            "preferred_language",
            sa.String(length=2),
            nullable=False,
            server_default="en",
        ),
    )
    op.create_check_constraint(
        op.f("ck_profile_preferred_language_allowed"),
        "profile",
        "preferred_language IN ('en', 'bn')",
    )

    op.create_table(
        "learning_roadmap",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("job_role_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("duration_weeks", sa.Integer(), nullable=False),
        sa.Column("language", sa.String(length=2), nullable=False, server_default="en"),
        sa.Column(
            "plan",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("generated_by", sa.String(length=80), nullable=False),
        sa.Column(
            "gap_skills",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("duration_weeks IN (4, 6)", name=op.f("ck_learning_roadmap_duration_weeks_allowed")),
        sa.CheckConstraint("language IN ('en', 'bn')", name=op.f("ck_learning_roadmap_language_allowed")),
        sa.CheckConstraint("length(trim(title)) > 0", name=op.f("ck_learning_roadmap_title_not_blank")),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name=op.f("fk_learning_roadmap_user_id_user"),
            ondelete="CASCADE",
        ),
        # SET NULL rather than RESTRICT: a saved plan belongs to the learner,
        # not to the role. Retiring a role from the knowledge base must not
        # destroy somebody's plan.
        sa.ForeignKeyConstraint(
            ["job_role_id"],
            ["job_role.id"],
            name=op.f("fk_learning_roadmap_job_role_id_job_role"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learning_roadmap")),
    )
    op.create_index(
        "ix_roadmap_user", "learning_roadmap", ["user_id", "created_at"]
    )

    op.create_table(
        "learning_roadmap_task",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("roadmap_id", sa.Integer(), nullable=False),
        sa.Column("task_key", sa.String(length=24), nullable=False),
        sa.Column("week", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("is_complete", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("portfolio_url", sa.String(length=600), nullable=False, server_default=""),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("week >= 1", name=op.f("ck_learning_roadmap_task_week_positive")),
        sa.CheckConstraint("position >= 1", name=op.f("ck_learning_roadmap_task_position_positive")),
        sa.CheckConstraint(
            "length(trim(title)) > 0", name=op.f("ck_learning_roadmap_task_title_not_blank")
        ),
        sa.ForeignKeyConstraint(
            ["roadmap_id"],
            ["learning_roadmap.id"],
            name=op.f("fk_learning_roadmap_task_roadmap_id_learning_roadmap"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_learning_roadmap_task")),
    )
    op.create_index(
        "uq_roadmap_task_key",
        "learning_roadmap_task",
        ["roadmap_id", "task_key"],
        unique=True,
    )
    op.create_index(
        "ix_roadmap_task_roadmap",
        "learning_roadmap_task",
        ["roadmap_id", "position"],
    )

    op.create_table(
        "interview_session",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("job_role_id", sa.Integer(), nullable=True),
        sa.Column("job_label", sa.String(length=200), nullable=False),
        sa.Column("language", sa.String(length=2), nullable=False, server_default="en"),
        sa.Column(
            "rubric",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("language IN ('en', 'bn')", name=op.f("ck_interview_session_language_allowed")),
        sa.CheckConstraint(
            "length(trim(job_label)) > 0", name=op.f("ck_interview_session_job_label_not_blank")
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name=op.f("fk_interview_session_user_id_user"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["job_role_id"],
            ["job_role.id"],
            name=op.f("fk_interview_session_job_role_id_job_role"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_interview_session")),
    )
    op.create_index(
        "ix_interview_session_user", "interview_session", ["user_id", "created_at"]
    )

    op.create_table(
        "interview_exchange",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "question",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("answer", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "feedback",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("position >= 1", name=op.f("ck_interview_exchange_position_positive")),
        sa.ForeignKeyConstraint(
            ["session_id"],
            ["interview_session.id"],
            name=op.f("fk_interview_exchange_session_id_interview_session"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_interview_exchange")),
    )
    op.create_index(
        "uq_exchange_position",
        "interview_exchange",
        ["session_id", "position"],
        unique=True,
    )
    op.create_index(
        "ix_exchange_session", "interview_exchange", ["session_id", "position"]
    )


def downgrade() -> None:
    op.drop_index("ix_exchange_session", table_name="interview_exchange")
    op.drop_index("uq_exchange_position", table_name="interview_exchange")
    op.drop_table("interview_exchange")

    op.drop_index("ix_interview_session_user", table_name="interview_session")
    op.drop_table("interview_session")

    op.drop_index("ix_roadmap_task_roadmap", table_name="learning_roadmap_task")
    op.drop_index("uq_roadmap_task_key", table_name="learning_roadmap_task")
    op.drop_table("learning_roadmap_task")

    op.drop_index("ix_roadmap_user", table_name="learning_roadmap")
    op.drop_table("learning_roadmap")

    op.drop_constraint("ck_profile_preferred_language_allowed", "profile")
    op.drop_column("profile", "preferred_language")
