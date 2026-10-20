"""Idempotent seed of the AI/ML job-role knowledge base.

Run:  python -m scripts.seed_job_roles

Every ``skill_slug`` is validated against the taxonomy **before** anything is
written, and an unknown slug is fatal. Silently skipping one would produce a role
that looks complete in the admin panel but is missing a requirement, and the
resulting coverage scores would be quietly wrong.
"""

from __future__ import annotations

import json
import logging
import sys
from decimal import Decimal

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import session_scope
from app.models.job import JobRole, JobRoleSkill
from app.models.skill import Skill
from app.schemas.job import slugify

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("seed_job_roles")


def load_roles_file() -> dict:
    path = get_settings().job_roles_path
    if not path.exists():
        raise SystemExit(f"Job roles file not found: {path}")
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def seed(db: Session) -> tuple[int, int]:
    payload = load_roles_file()
    roles = payload.get("roles", [])

    skills_by_slug = {skill.slug: skill for skill in db.scalars(select(Skill)).all()}
    if not skills_by_slug:
        raise SystemExit(
            "The skill taxonomy is empty. Run `python -m scripts.seed_taxonomy` first."
        )

    # ---- validate everything before writing anything ----------------------
    problems: list[str] = []
    for item in roles:
        title = item.get("title", "<untitled>")
        if not item.get("description", "").strip():
            problems.append(f"{title}: empty description (unmatchable by TF-IDF)")
        if not item.get("skills"):
            problems.append(f"{title}: no required skills")
        for entry in item.get("skills", []):
            slug = entry.get("skill_slug")
            if slug not in skills_by_slug:
                problems.append(f"{title}: unknown skill_slug {slug!r} (not in the taxonomy)")
            weight = entry.get("weight")
            if weight is None or not 0 < float(weight) <= 1:
                problems.append(f"{title}: weight {weight!r} for {slug!r} is outside (0, 1]")
    if problems:
        raise SystemExit(
            "job_roles.json is invalid:\n  - " + "\n  - ".join(problems[:25])
        )

    existing_roles: dict[str, JobRole] = {
        role.slug: role for role in db.scalars(select(JobRole)).all()
    }

    added = updated = 0
    total_role_skills = 0

    for item in roles:
        slug = item.get("slug") or slugify(item["title"])
        role = existing_roles.get(slug)

        if role is None:
            role = JobRole(
                title=item["title"],
                slug=slug,
                family=item["family"],
                seniority=item.get("seniority"),
                min_years_experience=item.get("min_years_experience"),
                description=item["description"],
                responsibilities=item.get("responsibilities", []),
                is_active=bool(item.get("is_active", True)),
            )
            db.add(role)
            db.flush()
            existing_roles[slug] = role
            added += 1
        else:
            changed = False
            for field, value in (
                ("title", item["title"]),
                ("family", item["family"]),
                ("seniority", item.get("seniority")),
                ("min_years_experience", item.get("min_years_experience")),
                ("description", item["description"]),
                ("responsibilities", item.get("responsibilities", [])),
                ("is_active", bool(item.get("is_active", True))),
            ):
                if getattr(role, field) != value:
                    setattr(role, field, value)
                    changed = True
            if changed:
                updated += 1

        # Full replacement of the requirement set, in the same transaction.
        db.execute(delete(JobRoleSkill).where(JobRoleSkill.job_role_id == role.id))
        for entry in item["skills"]:
            db.add(
                JobRoleSkill(
                    job_role_id=role.id,
                    skill_id=skills_by_slug[entry["skill_slug"]].id,
                    weight=Decimal(str(entry["weight"])),
                )
            )
        total_role_skills += len(item["skills"])

    db.commit()

    total_roles = len(existing_roles)
    actual_role_skills = int(
        db.scalar(select(func.count()).select_from(JobRoleSkill)) or 0
    )
    print(f"roles: {total_roles}, role_skills: {actual_role_skills}")
    print(f"  +{added} roles, ~{updated} updated, {total_role_skills} requirement rows written")
    return total_roles, actual_role_skills


def main() -> int:
    logger.info("Seeding job roles from %s", get_settings().job_roles_path)
    with session_scope() as db:
        seed(db)
    return 0


if __name__ == "__main__":
    sys.exit(main())
