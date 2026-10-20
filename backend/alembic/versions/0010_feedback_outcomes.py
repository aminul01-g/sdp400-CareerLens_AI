"""Revision 10 — outcomes in the community prior.

``docs/limitations.md`` used to say of the community prior:

    **It measures interest, not outcomes.** A dismissal says "not this role".
    It does not say whether the person found a job, or whether the role was a
    good match for somebody else.

The prior could only count opinions, so a role that lots of people saved and
a role that lots of people got an interview for looked identical to it.

This revision adds the two outcome actions -- ``interview`` and ``offer`` --
alongside the ``applied`` that the model already accepted but nothing
collected, and widens the check constraint to allow them.

The weighting itself is a formula in
``app/services/feedback_service.py``; there is no model file and nothing is
fitted, so proposal section 18.9 still holds.

The constraint is dropped and recreated with raw SQL rather than through
``op.drop_constraint`` and ``op.create_check_constraint``, for two reasons.
The name in the database is not the one the model declares -- the earlier
migrations passed an already-prefixed name into ``sa.CheckConstraint``, and
Alembic's naming convention prefixed it a second time, so the live schema and
``Base.metadata`` disagree. And the exact name has to be the one the model
declares, or the disagreement gets worse rather than better. The lookup
below therefore asks the catalogue what the constraint is actually called
instead of assuming.

Revision ID: 0010_feedback_outcomes
Revises: 0009_rate_limit_event
Create Date: 2026-10-19
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_feedback_outcomes"
down_revision: str | None = "0009_rate_limit_event"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: The constraint before this revision.
OLD_ACTIONS = "action IN ('saved','dismissed','interested','applied')"

#: The constraint after it.
NEW_ACTIONS = "action IN ('saved','dismissed','interested','applied','interview','offer')"

#: The name ``Base.metadata`` declares, once the naming convention in
#: ``app/db/base.py`` has been applied to ``action_valid``.
CONSTRAINT_NAME = "ck_recommendation_feedback_action_valid"

_TABLE = "recommendation_feedback"


def _find_action_constraint(connection) -> str | None:
    """The name of the check constraint that governs ``action``, if there is one.

    The definition is matched rather than the name, because the name in the
    database and the name in the model have not always agreed.
    """
    row = connection.execute(
        sa.text(
            """
            SELECT conname
            FROM pg_constraint
            WHERE conrelid = to_regclass(:table)
              AND contype = 'c'
              AND pg_get_constraintdef(oid) LIKE '%dismissed%'
            ORDER BY conname
            """
        ),
        {"table": _TABLE},
    ).first()
    return str(row[0]) if row else None


def upgrade() -> None:
    connection = op.get_bind()
    existing = _find_action_constraint(connection)
    if existing is not None:
        op.execute(sa.text(f'ALTER TABLE {_TABLE} DROP CONSTRAINT "{existing}"'))
    op.execute(
        sa.text(
            f'ALTER TABLE {_TABLE} ADD CONSTRAINT "{CONSTRAINT_NAME}" '
            f"CHECK ({NEW_ACTIONS})"
        )
    )


def downgrade() -> None:
    connection = op.get_bind()
    existing = _find_action_constraint(connection)
    if existing is not None:
        op.execute(sa.text(f'ALTER TABLE {_TABLE} DROP CONSTRAINT "{existing}"'))
    op.execute(
        sa.text(
            f'ALTER TABLE {_TABLE} ADD CONSTRAINT "{CONSTRAINT_NAME}" '
            f"CHECK ({OLD_ACTIONS})"
        )
    )
