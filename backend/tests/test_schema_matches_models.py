"""The schema and the models must agree.

``app/db/base.py`` declares a naming convention so that every constraint has a
deterministic name, and says what it is for:

    Without it PostgreSQL auto-names check constraints ``user_skill_proficiency_check``,
    ``user_skill_proficiency_check1``, ... and the third Alembic autogenerate run
    starts producing spurious diffs. Fixing the names at the metadata level makes
    every autogenerate and every ``downgrade()`` deterministic.

That promise was broken for a while, and the break was invisible. Several
migrations passed an already-prefixed name into ``sa.CheckConstraint``; the
naming convention applied itself a second time, and the constraint landed in
the database under a name the models did not have. Fifteen constraints were
affected, across eight tables.

The consequences were concrete: ``alembic revision --autogenerate`` wanted to
rename constraints that were already right in substance; ``docs/erd.md``,
which is generated from the live catalogue, documented names the code did not
have; and a migration that wanted to *alter* one of those constraints could
not drop it by name.

Revision 0011 fixed the names, and this file is what stops it happening
again. The check is deliberately blunt: every constraint the models declare
must exist in the live database under exactly that name, and every
constraint in the database must be one the models declare.

The check runs against the *test* database, which the suite builds by running
the real Alembic chain, so it also proves that a fresh deployment lands on
the same schema the models describe.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.base import Base


def _declared_constraints() -> dict[str, set[str]]:
    """``table -> {constraint names}`` as the models declare them."""
    import app.models  # noqa: F401 - importing registers every mapper

    declared: dict[str, set[str]] = {}
    for table_name, table in Base.metadata.tables.items():
        declared[table_name] = {
            constraint.name for constraint in table.constraints if constraint.name
        }
    return declared


def _live_constraints(session: Session) -> dict[str, set[str]]:
    """``table -> {constraint names}`` as the database has them.

    Only the kinds the models declare are included. PostgreSQL also reports
    the implicit ``NOT NULL`` of every column as a constraint, and those are
    a property of the column rather than something the model declares.
    """
    rows = session.execute(
        text(
            """
            SELECT rel.relname, con.conname
            FROM pg_constraint con
            JOIN pg_class rel ON rel.oid = con.conrelid
            JOIN pg_namespace ns ON ns.oid = rel.relnamespace
            WHERE ns.nspname = current_schema()
              AND con.contype IN ('c', 'f', 'u', 'p')
            """
        )
    ).all()
    live: dict[str, set[str]] = {}
    for table_name, name in rows:
        live.setdefault(str(table_name), set()).add(str(name))
    return live


def test_the_models_describe_every_table() -> None:
    import app.models  # noqa: F401

    assert len(Base.metadata.tables) == 24, (
        "the schema has grown; the table count in "
        "app/models/__init__.py and in docs/erd.md has to follow"
    )


def test_every_declared_constraint_exists_in_the_database(db: Session) -> None:
    declared = _declared_constraints()
    live = _live_constraints(db)
    missing: dict[str, list[str]] = {}
    for table_name, names in declared.items():
        absent = names - live.get(table_name, set())
        if absent:
            missing[table_name] = sorted(absent)
    assert not missing, (
        "the database is missing constraints the models declare "
        f"(a migration has not been run, or it used a different name): {missing}"
    )


def test_the_database_has_no_constraint_the_models_do_not_declare(db: Session) -> None:
    declared = _declared_constraints()
    live = _live_constraints(db)
    extra: dict[str, list[str]] = {}
    for table_name, names in live.items():
        if table_name not in declared:
            continue
        unexpected = names - declared[table_name]
        if unexpected:
            extra[table_name] = sorted(unexpected)
    assert not extra, (
        "the database has constraints the models do not declare, so "
        "Base.metadata does not describe the live schema: " f"{extra}"
    )


def test_no_constraint_name_is_double_prefixed(db: Session) -> None:
    """The specific failure this file exists to catch.

    A name like ``ck_user_ck_user_email_not_blank`` is the naming convention
    applied twice, which is what the migrations used to do.
    """
    live = _live_constraints(db)
    doubled = [
        f"{table}.{name}"
        for table, names in live.items()
        for name in names
        if name.startswith(f"ck_{table}_ck_{table}_")
        or name.startswith(f"fk_{table}_fk_{table}_")
        or name.startswith(f"uq_{table}_uq_{table}_")
    ]
    assert not doubled, f"double-prefixed constraint names: {doubled}"


@pytest.mark.parametrize("table", ["user", "job_role", "recommendation_feedback"])
def test_the_important_constraints_are_named_as_declared(db: Session, table: str) -> None:
    live = _live_constraints(db)
    declared = _declared_constraints()[table]
    assert live.get(table, set()) == declared
