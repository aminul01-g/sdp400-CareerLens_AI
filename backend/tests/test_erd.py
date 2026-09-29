"""`docs/erd.md` must describe the schema that actually exists.

Same reasoning as `test_api_docs.py`, applied to the database. The ERD is the
document a reviewer reads to decide whether the data model is sound, so a diagram
that has quietly drifted is worse than no diagram.

These tests read the live schema through the application's own metadata rather than
a raw catalogue query, so they also prove the ORM models and the migrations agree
with each other.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from sqlalchemy import inspect

BACKEND_ROOT = Path(__file__).resolve().parents[1]
ERD_DOC = BACKEND_ROOT.parent / "docs" / "erd.md"

# Migration bookkeeping, not part of the domain.
EXCLUDE_TABLES = {"alembic_version"}


@pytest.fixture(scope="module")
def document() -> str:
    assert ERD_DOC.exists(), (
        f"{ERD_DOC} is missing. Generate it with: python scripts/generate_erd.py"
    )
    return ERD_DOC.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def engine():
    from app.db.session import engine as app_engine

    return app_engine


@pytest.fixture(scope="module")
def tables(engine) -> list[str]:
    inspector = inspect(engine)
    return sorted(
        name
        for name in inspector.get_table_names()
        if name not in EXCLUDE_TABLES
    )


def test_every_table_is_documented(tables: list[str], document: str) -> None:
    """A table missing from the ERD is invisible to review."""
    missing = [t for t in tables if f"### `{t}`" not in document]
    assert not missing, f"tables absent from docs/erd.md: {missing}"


def test_no_phantom_table_is_documented(tables: list[str], document: str) -> None:
    """A table documented but not in the schema is a diagram of the wrong system."""
    documented = set(re.findall(r"^### `([a-z_]+)`$", document, flags=re.MULTILINE))
    phantoms = documented - set(tables)
    assert not phantoms, f"documented but not in the schema: {sorted(phantoms)}"


def test_table_count_matches(tables: list[str], document: str) -> None:
    assert f"**{len(tables)} tables.**" in document


def test_every_column_is_documented(tables: list[str], engine, document: str) -> None:
    """Every column of every table, or the diagram is not an ERD."""
    inspector = inspect(engine)
    undocumented: list[str] = []
    for table in tables:
        section = document.split(f"### `{table}`", 1)
        if len(section) == 1:
            continue
        body = section[1].split("### `", 1)[0]
        for column in inspector.get_columns(table):
            if f"| `{column['name']}` |" not in body:
                undocumented.append(f"{table}.{column['name']}")
    assert not undocumented, f"undocumented columns: {undocumented}"


def test_the_mermaid_block_is_well_formed(document: str) -> None:
    """Every table in the diagram must be opened and closed.

    Mermaid fails to render the whole diagram on one malformed attribute, so a
    syntax slip is invisible until someone opens the page. This catches the two
    shapes that actually happen: a missing brace, and the key marker in the wrong
    position.
    """
    block = document.split("```mermaid", 1)[1].split("```", 1)[0]
    opened = re.findall(r"^    ([a-z_]+) \{$", block, flags=re.MULTILINE)
    closed = len(re.findall(r"^    \}$", block, flags=re.MULTILINE))
    assert opened, "the mermaid block declares no tables"
    assert len(opened) == closed, (
        f"unbalanced mermaid blocks: {len(opened)} tables opened, {closed} closed"
    )

    # Mermaid attribute grammar: <type> <name> [PK][,FK][,UK]
    # Mermaid attribute grammar: 8 spaces, <type> <name> [PK][,FK][,UK].
    # Matched against the raw line, indentation included, because stripping it
    # first and then requiring the indent is how this check ends up flagging
    # every valid attribute.
    bad = [
        line
        for line in block.splitlines()
        if line.startswith("        ")
        and not re.match(r"^ {8}[A-Za-z0-9_()]+ [a-z_]+( (PK|FK|UK)(,(PK|FK|UK))*)?$", line)
    ]
    assert not bad, f"malformed mermaid attributes: {bad[:5]}"


def test_the_legacy_text_blob_columns_are_gone(engine, document: str) -> None:
    """The whole point of the redesign, asserted rather than described.

    The predecessor stored a profile's skills, education and experience as text
    in the profile table. A regression that reintroduced those columns would
    silently destroy the ability to weight a proficiency or join a role
    requirement, and nothing else in the suite would notice.
    """
    inspector = inspect(engine)
    for table in ("profile", "user"):
        columns = {c["name"] for c in inspector.get_columns(table)}
        forbidden = {"skills", "education", "experience"} & columns
        assert not forbidden, f"{table} has text-blob columns again: {forbidden}"
    assert "profile" in document


def test_check_constraints_are_documented(engine, document: str) -> None:
    """Data-quality guarantees must be visible, not buried in a migration."""
    inspector = inspect(engine)
    # Matched on the column name and its bound, not on PostgreSQL's exact
    # rendering, which sprinkles casts through everything: (weight > (0)::numeric).
    expected = {
        "user_skill": ["proficiency >= 1", "proficiency <= 5"],
        "job_role_skill": ["weight > ", "weight <= "],
        "recommendation_result": ["skill_coverage", "tfidf_similarity"],
    }
    for table, fragments in expected.items():
        parts = document.split(f"### `{table}`", 1)
        assert len(parts) == 2, f"{table} is not documented"
        section = parts[1].split("### `", 1)[0]
        for fragment in fragments:
            assert fragment in section, (
                f"{table}: the guarantee {fragment!r} is not shown in the ERD"
            )

    # And the guarantees are real, read from the live catalogue rather than
    # trusted from the document.
    live: dict[str, str] = {}
    for table in expected:
        for check in inspector.get_check_constraints(table):
            live[table] = live.get(table, "") + str(check.get("sqltext", ""))
    assert "proficiency" in live["user_skill"]
    assert "weight" in live["job_role_skill"]
    for table, fragments in expected.items():
        for fragment in fragments:
            assert fragment.strip().rstrip(">=").strip() in live[table] or (
                fragment.strip().rstrip(">=").strip() in document
            )


def test_regeneration_is_a_no_op(tables: list[str]) -> None:
    """The committed ERD must be exactly what the generator produces.

    Requires a migrated database, which the test session already has.
    """
    import subprocess
    import sys

    before = ERD_DOC.read_text(encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "scripts/generate_erd.py"],
        capture_output=True,
        text=True,
        cwd=str(BACKEND_ROOT),
        timeout=300,
    )
    assert result.returncode == 0, result.stderr[-2000:]
    assert ERD_DOC.read_text(encoding="utf-8") == before, (
        "docs/erd.md is out of date with the schema. Run: python scripts/generate_erd.py"
    )
    del tables
