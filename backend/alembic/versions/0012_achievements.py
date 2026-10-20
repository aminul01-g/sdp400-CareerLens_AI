"""Revision 12 — the achievements a document claims.

``docs/limitations.md`` used to say of the CV extractor:

    **No achievement quantification.** The extractor knows which technologies a
    sentence mentions. It does not know that "cut query time by 80%" is more
    impressive than "worked on query performance".

    **No understanding of who did what.** "We migrated the Python service" is
    read as a mention, which is right, but the system cannot tell whether "we"
    was the candidate.

This revision adds the column the extracted claims are stored in. The claims
themselves are produced by ``app/ml/achievements.py``; they are stored as JSON
because the shape is a list of small records that is only ever read whole.

The column is ``NOT NULL`` with an empty-list default, so an upload made
before this revision reads as "no achievements found" rather than as a null
that every reader has to special-case.

Revision ID: 0012_achievements
Revises: 0011_constraint_names
Create Date: 2026-10-20
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012_achievements"
down_revision: str | None = "0011_constraint_names"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "resume_upload",
        sa.Column(
            "achievements",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default="[]",
        ),
    )


def downgrade() -> None:
    op.drop_column("resume_upload", "achievements")
