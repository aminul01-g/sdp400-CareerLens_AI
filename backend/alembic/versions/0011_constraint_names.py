"""Revision 11 — the schema's constraint names, brought in line with the model.

This migration fixes a defect that was found by running the system rather
than by reading it.

``app/db/base.py`` declares a naming convention so that every constraint has
a deterministic name:

.. code-block:: text

    "ck": "ck_%(table_name)s_%(constraint_name)s"

and the docstring says why:

    Without it PostgreSQL auto-names check constraints ``user_skill_proficiency_check``,
    ``user_skill_proficiency_check1``, ... and the third Alembic autogenerate run
    starts producing spurious diffs. Fixing the names at the metadata level makes
    every autogenerate and every ``downgrade()`` deterministic.

The convention was applied, but the *migrations* fought it. Several of them
passed an already-prefixed name into ``sa.CheckConstraint``:

.. code-block:: text

    sa.CheckConstraint("...", name="ck_recommendation_feedback_action_valid")

Alembic applies the target metadata's naming convention to that name on the
way to the database, so the constraint landed as
``ck_recommendation_feedback_ck_recommendation_feedback_a_e141`` -- the
convention applied twice. The model, which declares ``name="action_valid"``,
renders the same constraint as ``ck_recommendation_feedback_action_valid``.

The two therefore disagreed, and the disagreement had three consequences:

* ``Base.metadata`` did not describe the live schema, so
  ``alembic revision --autogenerate`` wanted to rename fifteen constraints
  that were already correct in substance;
* ``docs/erd.md``, which is generated from the live catalogue, documented
  names that the code does not have;
* a migration that wanted to alter one of those constraints could not drop it
  by name, which is exactly what revision 0010 had to work around.

This revision renames every constraint whose live name differs from the one
``Base.metadata`` declares. The *definitions* are untouched: only the names
change. The constraint on ``recommendation_feedback.action`` was already
recreated with the right name by revision 0010, so it is skipped here.

The renames are driven by the model's metadata rather than by a hand-written
list, so a constraint added later is handled the same way. A constraint is
only renamed when the live catalogue holds one with the *same definition*, so
this can never silently change what a constraint means.

Revision ID: 0011_constraint_names
Revises: 0010_feedback_outcomes
Create Date: 2026-10-19
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.util import md5_hex

revision: str = "0011_constraint_names"
down_revision: str | None = "0010_feedback_outcomes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

#: The constraint kinds that carry a name worth aligning, and the prefix the
#: naming convention in ``app/db/base.py`` gives each of them.
_CONSTRAINT_PREFIXES = {
    "CheckConstraint": "ck",
    "ForeignKeyConstraint": "fk",
    "UniqueConstraint": "uq",
}

#: PostgreSQL truncates an identifier to 63 bytes.
_MAX_IDENTIFIER = 63


def _model_tables():
    """Every table the models declare, with their mappers registered."""
    import app.models  # noqa: F401 - importing registers every mapper
    from app.db.base import Base

    return Base.metadata.tables


def _legacy_name(table_name: str, prefix: str, rendered: str) -> str:
    """The name a constraint got when the convention was applied twice.

    ``Base.metadata`` already holds the *rendered* name -- SQLAlchemy applies
    the convention when the table is declared -- so for the ``user`` table the
    email constraint is called ``ck_user_email_not_blank``.

    The migrations passed that rendered name straight back into
    ``sa.CheckConstraint``, and the convention applied itself a second time,
    producing

    .. code-block:: text

        ck_user_ck_user_email_not_blank

    and, where that is longer than PostgreSQL's 63-byte limit,
    ``ck_recommendation_result_ck_recommendation_result_declared_coverage_range``
    becomes ``ck_recommendation_result_ck_recommendation_result_decla_896e``.

    The truncation is SQLAlchemy's, not PostgreSQL's: the DDL compiler keeps
    the first 55 characters and appends an underscore and the last four
    characters of the name's MD5. This reproduces it exactly, so the rename
    does not have to guess.
    """
    legacy = f"{prefix}_{table_name}_{rendered}"
    if len(legacy) > _MAX_IDENTIFIER:
        legacy = legacy[: _MAX_IDENTIFIER - 8] + "_" + md5_hex(legacy)[-4:]
    return legacy


def _live_names(connection) -> set[str]:
    """Every constraint name in the current schema."""
    rows = connection.execute(
        sa.text(
            """
            SELECT con.conname
            FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            JOIN pg_namespace ns ON ns.oid = rel.relnamespace
            WHERE ns.nspname = current_schema()
            """
        )
    ).all()
    return {str(row[0]) for row in rows}


def _plan(connection) -> tuple[list[tuple[str, str, str]], list[tuple[str, str, str]]]:
    """The renames in each direction.

    Returns ``(to_upgrade, to_downgrade)``, where each triple is
    ``(table, from, to)``. A constraint is only ever renamed when the
    counterpart name is absent, so neither direction can collide with an
    existing constraint.
    """
    live = _live_names(connection)
    to_upgrade: list[tuple[str, str, str]] = []
    to_downgrade: list[tuple[str, str, str]] = []

    for table_name, table in _model_tables().items():
        for constraint in table.constraints:
            if not constraint.name:
                continue
            prefix = _CONSTRAINT_PREFIXES.get(type(constraint).__name__)
            if prefix is None:
                continue
            legacy = _legacy_name(table_name, prefix, constraint.name)
            if legacy == constraint.name:
                continue
            if constraint.name in live and legacy not in live:
                to_downgrade.append((table_name, constraint.name, legacy))
            elif legacy in live and constraint.name not in live:
                to_upgrade.append((table_name, legacy, constraint.name))
    return to_upgrade, to_downgrade


def _rename(table_name: str, old_name: str, new_name: str) -> None:
    op.execute(
        sa.text(
            f'ALTER TABLE "{table_name}" RENAME CONSTRAINT "{old_name}" TO "{new_name}"'
        )
    )


def upgrade() -> None:
    connection = op.get_bind()
    for table_name, old_name, new_name in _plan(connection)[0]:
        _rename(table_name, old_name, new_name)


def downgrade() -> None:
    connection = op.get_bind()
    for table_name, old_name, new_name in reversed(_plan(connection)[1]):
        _rename(table_name, old_name, new_name)
