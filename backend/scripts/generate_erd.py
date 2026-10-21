"""Generate `docs/erd.md` by introspecting the live database.

An ERD that a human maintains drifts from the schema within a week. This reads
the actual tables, columns, keys, constraints and indexes from PostgreSQL and emits
the document from them, so a migration that changes the shape of the database
cannot leave the diagram quietly wrong.

It needs a migrated database. Set ``DATABASE_URL`` (or run it inside the compose
stack) and then:

    python scripts/generate_erd.py
"""

from __future__ import annotations

import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))

OUTPUT = BACKEND_ROOT.parent / "docs" / "erd.md"

# Tables that exist in the schema but are migration bookkeeping.
EXCLUDE_TABLES = {"alembic_version"}

# What each table is for, in the reviewer's terms rather than the ORM's. A diagram
# with no annotation makes the reader reverse-engineer intent from column names.
TABLE_PURPOSE: dict[str, str] = {
    "user": "Account and role. One row per person.",
    "profile": "The user's professional summary: headline, goal, bio.",
    "skill": "The curated skill taxonomy. Seeded from data/skills_taxonomy.json.",
    "skill_alias": "Every surface form that resolves to a skill, e.g. 'k8s' -> Kubernetes.",
    "user_skill": "A skill the user has declared, with a self-reported proficiency of 1-5.",
    "project": "A project on the profile. Free text plus a tech stack of skill slugs.",
    "education_record": "One education entry.",
    "certification": "One certification.",
    "resume_upload": "A stored CV file and its extracted text.",
    "resume_detected_skill": "A skill the extractor found. A proposal, never a declaration.",
    "job_role": "The role knowledge base. Seeded from data/job_roles.json.",
    "job_role_skill": "A role's requirements, each weighted in (0, 1].",
    "recommendation_run": "One generated shortlist, persisted so it can be re-read.",
    "recommendation_result": "One role's score within a run, with both components stored.",
    "learning_roadmap": "A saved learning plan for one role, generated from the gap report.",
    "learning_roadmap_task": "One task in a plan, with the learner's progress on it.",
    "interview_session": "A mock interview, with the rubric that was in force.",
    "interview_exchange": "One question, the answer, and the feedback that followed.",
    "feedback": "Optional. Not one of the proposal's nine modules.",
}


def main() -> int:
    from sqlalchemy import text

    from app.db.session import engine

    with engine.connect() as connection:
        tables = [
            row[0]
            for row in connection.execute(
                text(
                    "select table_name from information_schema.tables "
                    "where table_schema = 'public' order by table_name"
                )
            )
            if row[0] not in EXCLUDE_TABLES
        ]

        columns: dict[str, list[tuple]] = {}
        for table in tables:
            columns[table] = connection.execute(
                text(
                    "select column_name, "
                    "       case when data_type = 'USER-DEFINED' then udt_name else data_type end, "
                    "       is_nullable, column_default "
                    "from information_schema.columns "
                    "where table_schema = 'public' and table_name = :t "
                    "order by ordinal_position"
                ),
                {"t": table},
            ).all()

        primary_keys: dict[str, list[str]] = {}
        foreign_keys: dict[str, list[tuple]] = {}
        checks: dict[str, list[str]] = {}
        uniques: dict[str, list[str]] = {}
        indexes: dict[str, list[str]] = {}

        for table in tables:
            # Unpacked, not iterated: execute().all() yields one-tuples, and
            # str() of a tuple never startswith("CHECK"), which silently
            # dropped every check constraint from the document.
            # ORDER BY is not cosmetic. PostgreSQL returns constraints in an
            # unspecified order, so without it the generated document changes
            # from run to run and `test_regeneration_is_a_no_op` fails for a
            # reason that has nothing to do with the schema.
            for (definition,) in connection.execute(
                text(
                    "select pg_get_constraintdef(oid) from pg_constraint "
                    "where conrelid = to_regclass(:t) order by conname"
                ),
                {"t": table},
            ).all():
                definition = str(definition)
                if definition.startswith("PRIMARY KEY"):
                    primary_keys[table] = [
                        c.strip().split()[0] for c in definition[11:].strip("()").split(",")
                    ]
                elif definition.startswith("FOREIGN KEY"):
                    foreign_keys.setdefault(table, []).append(definition)
                elif definition.startswith("CHECK"):
                    checks.setdefault(table, []).append(definition)
                elif definition.startswith("UNIQUE"):
                    uniques.setdefault(table, []).append(definition)

            for (definition,) in connection.execute(
                text(
                    "select indexdef from pg_indexes "
                    "where schemaname = 'public' and tablename = :t "
                    "and indexname not like '%%_pkey' "
                    "order by indexname"
                ),
                {"t": table},
            ).all():
                indexes.setdefault(table, []).append(str(definition))

    # Defensive: the queries above are ordered, but the document must not
    # depend on that alone. Sorting here makes the generator's output a pure
    # function of the schema.
    for table in tables:
        foreign_keys[table] = sorted(foreign_keys.get(table, []))
        checks[table] = sorted(checks.get(table, []))
        uniques[table] = sorted(uniques.get(table, []))
        indexes[table] = sorted(indexes.get(table, []))

    lines: list[str] = []
    add = lines.append

    add("# Entity-Relationship Diagram")
    add("")
    add(
        f"**{len(tables)} tables.** Generated by `backend/scripts/generate_erd.py` "
        "directly from the live PostgreSQL catalogue — every column, key, constraint and "
        "index below was read from the database, not typed. Re-run the script after any "
        "migration; `tests/test_erd.py` fails if this page and the schema disagree."
    )
    add("")

    add("## Diagram")
    add("")
    add("```mermaid")
    add("erDiagram")
    fk_columns: dict[str, set[str]] = {}
    for table, keys in foreign_keys.items():
        fk_columns[table] = {k.split("(")[1].split(")")[0].strip() for k in keys}

    for table in tables:
        add(f"    {table} {{")
        for name, data_type, nullable, _default in columns[table]:
            # Mermaid attribute syntax is: <type> <name> [PK|FK|UK] ["comment"]
            # The key marker follows the name -- putting it first silently renders
            # a diagram where every column is a foreign key.
            markers = []
            if name in primary_keys.get(table, []):
                markers.append("PK")
            if name in fk_columns.get(table, ()):
                markers.append("FK")
            suffix = f" {','.join(markers)}" if markers else ""
            comment = "" if nullable == "NO" else "optional"
            add(f"        {data_type.replace(' ', '_')} {name}{suffix}".rstrip())
            del comment
        add("    }")
    add("")
    for table, keys in foreign_keys.items():
        for definition in keys:
            referenced = definition.split("REFERENCES")[1].split("(")[0].strip()
            cols = definition.split("(")[1].split(")")[0].strip()
            ref_cols = definition.split("REFERENCES")[1].split("(")[1].split(")")[0].strip()
            label = f'{cols} -> {ref_cols}'
            add(f"    {referenced} ||--o{{ {table} : {label}")
    add("```")
    add("")

    add("## Tables")
    add("")
    for table in tables:
        purpose = TABLE_PURPOSE.get(table)
        add(f"### `{table}`")
        add("")
        if purpose:
            add(purpose)
            add("")
        add("| Column | Type | Null | Key | Default |")
        add("| --- | --- | --- | --- | --- |")
        for name, data_type, nullable, default in columns[table]:
            keys = []
            if name in primary_keys.get(table, []):
                keys.append("PK")
            for definition in foreign_keys.get(table, []):
                if definition.split("(")[1].split(")")[0].strip() == name:
                    referenced = definition.split("REFERENCES")[1].split("(")[0].strip()
                    keys.append(f"FK → {referenced}")
            add(
                f"| `{name}` | `{data_type}` | {'no' if nullable == 'NO' else 'yes'} "
                f"| {', '.join(keys) or '—'} | `{default or ''}` |"
            )
        add("")
        if table in foreign_keys:
            add("**Foreign keys**")
            add("")
            for definition in sorted(foreign_keys[table]):
                add(f"- `{definition}`")
            add("")
        if table in checks:
            add("**Check constraints** — these are the data-quality guarantees")
            add("")
            for definition in sorted(checks[table]):
                add(f"- `{definition}`")
            add("")
        if table in uniques:
            add("**Unique constraints**")
            add("")
            for definition in sorted(uniques[table]):
                add(f"- `{definition}`")
            add("")
        if table in indexes:
            add("**Indexes**")
            add("")
            for definition in sorted(indexes[table]):
                add(f"- `{definition}`")
            add("")

    add("## The design decisions worth arguing about")
    add("")
    add(
        "**A profile is normalised, not a text blob.** The predecessor stored skills, "
        "education and experience as delimited strings in one column. That made every "
        "query a string operation and every join impossible. Here they are separate "
        "tables, which is why `user_skill` can carry a proficiency and `job_role_skill` "
        "can carry a weight — the two things the matching engine is built on."
    )
    add("")
    add(
        "**`skill_alias` exists because matching is a text problem.** The extractor sees "
        "'k8s', 'Kubernetes' and 'K8S'; the taxonomy stores one skill. Resolving surface "
        "forms to a canonical id is what lets the CV pipeline and the taxonomy agree "
        "without either side knowing how the other spells things."
    )
    add("")
    add(
        "**`resume_detected_skill` is a separate table from `user_skill` on purpose.** "
        "The extractor proposes; the user disposes. Keeping proposals in their own table "
        "makes the invariant *every row in `user_skill` is user-confirmed* checkable, and "
        "means a parsing bug cannot silently overwrite a declaration the user typed."
    )
    add("")
    add(
        "**Both components of a score are persisted.** `recommendation_result` stores "
        "`skill_coverage` and `tfidf_similarity` alongside the combined "
        "`compatibility`, so a past run can be explained and re-derived without "
        "re-running the engine against a profile that may since have changed."
    )
    add("")
    add(
        "**`recommendation_run` is separate from its results.** One run is one shortlist "
        "at one moment, with one weight configuration. A profile edited tomorrow "
        "produces a new run rather than mutating history."
    )
    add("")
    add(
        "**`feedback` is in the schema but is not one of the proposal's nine modules.** "
        "The UI for it already existed in the predecessor, so removing it would have "
        "been a regression in scope for no requirement. It is documented here as "
        "optional rather than presented as a required module."
    )
    add("")

    add("## Verifying this document")
    add("")
    add("```bash")
    add("cd backend && python scripts/generate_erd.py && git diff --exit-code docs/erd.md")
    add("```")
    add("")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT} ({len(tables)} tables)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
