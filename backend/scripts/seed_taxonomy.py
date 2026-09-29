"""Idempotent seed of the curated skill taxonomy.

Run:  python -m scripts.seed_taxonomy

Upserts skills then aliases by slug/alias, so running it twice changes nothing.
That property is what makes it safe to call from a deployment script and from a
developer's local loop without thinking about it.
"""

from __future__ import annotations

import json
import logging
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import session_scope
from app.ml.taxonomy import normalise_surface
from app.models.skill import Skill, SkillAlias

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("seed_taxonomy")


def load_taxonomy_file() -> dict:
    path = get_settings().skills_taxonomy_path
    if not path.exists():
        raise SystemExit(f"Taxonomy file not found: {path}")
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def seed(db: Session) -> tuple[int, int]:
    payload = load_taxonomy_file()
    skills = payload.get("skills", [])

    # Which skills already exist, keyed by slug.
    existing_skills: dict[str, Skill] = {
        skill.slug: skill for skill in db.scalars(select(Skill)).all()
    }
    existing_aliases: dict[str, SkillAlias] = {
        alias.alias: alias for alias in db.scalars(select(SkillAlias)).all()
    }

    added_skills = updated_skills = 0
    added_aliases = 0

    for item in skills:
        slug = item["slug"]
        skill = existing_skills.get(slug)
        if skill is None:
            skill = Skill(
                name=item["name"],
                slug=slug,
                category=item["category"],
                description=item.get("description", ""),
            )
            db.add(skill)
            db.flush()
            existing_skills[slug] = skill
            added_skills += 1
        else:
            # Upsert: keep the curated data authoritative over local edits.
            changed = False
            for field, value in (
                ("name", item["name"]),
                ("category", item["category"]),
                ("description", item.get("description", "")),
            ):
                if getattr(skill, field) != value:
                    setattr(skill, field, value)
                    changed = True
            if changed:
                updated_skills += 1

        # The canonical name is itself a surface form, so it must resolve.
        for alias in {normalise_surface(item["name"]), slug, *item.get("aliases", [])}:
            if not alias:
                continue
            existing = existing_aliases.get(alias)
            if existing is None:
                db.add(SkillAlias(alias=alias, skill_id=skill.id))
                existing_aliases[alias] = SkillAlias(alias=alias, skill_id=skill.id)
                added_aliases += 1
            elif existing.skill_id != skill.id:
                # A collision would make one of the two skills undetectable, so
                # this is fatal rather than something to silently overwrite.
                other = db.get(Skill, existing.skill_id)
                raise SystemExit(
                    f"Alias {alias!r} is already claimed by "
                    f"{other.name if other else existing.skill_id}; refusing to reassign it "
                    f"to {skill.name}. Fix data/skills_taxonomy.json."
                )

    db.commit()

    total_skills = len(existing_skills)
    total_aliases = len(existing_aliases)
    print(f"skills: {total_skills}, aliases: {total_aliases}")
    print(f"  +{added_skills} skills, ~{updated_skills} updated, +{added_aliases} aliases")
    return total_skills, total_aliases


def main() -> int:
    logger.info("Seeding skill taxonomy from %s", get_settings().skills_taxonomy_path)
    with session_scope() as db:
        seed(db)
    return 0


if __name__ == "__main__":
    sys.exit(main())
