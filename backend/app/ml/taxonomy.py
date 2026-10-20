"""Curated skill taxonomy: loading, alias resolution, and validation.

The JSON file ``data/skills_taxonomy.json`` is the source of truth. This module
loads it **once** at import and builds two indexes:

* ``_by_surface`` — normalised surface form -> skill. Covers every canonical name,
  slug and alias.
* ``_by_slug`` — slug -> skill, for the seed scripts and the API.

``validate()`` asserts at load time that no surface form is claimed by two
different skills. A silent collision is not a cosmetic defect: one of the two
skills becomes **undetectable**, and nothing would report it until a user noticed
a missing skill in their CV result.

**Match normalisation rule** (shared with the extractor): lowercase, strip
surrounding whitespace and trailing punctuation, collapse internal whitespace, and
treat ``-``, ``_`` and ``.`` as equivalent. That is what makes ``sci-kit learn``,
``sci_kit_learn`` and ``Scikit-learn`` one entry rather than three.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from app.ml.types import SkillRef

logger = logging.getLogger("app.ml.taxonomy")

DEFAULT_TAXONOMY_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "skills_taxonomy.json"
)

# Word characters plus the internal punctuation a skill name may legitimately use.
_SURFACE_STRIP = "\".,;:!?()[]{}\'`\u2019\u2018\u201c\u201d\""
_TOKEN_SPLIT = re.compile(r"[-_.\s]+")
_WHITESPACE = re.compile(r"\s+")


def normalise_surface(value: str) -> str:
    """Normalise a surface form for comparison.

    ``"  SKLearn "`` and ``"sci-kit learn"`` both become ``"sklearn"`` and
    ``"scikit learn"`` respectively; the separator collapse means they compare
    equal under whitespace folding.
    """
    cleaned = value.strip().lower().strip(_SURFACE_STRIP)
    cleaned = _WHITESPACE.sub(" ", cleaned)
    return _TOKEN_SPLIT.sub(" ", cleaned).strip()


@dataclass(frozen=True, slots=True)
class SkillEntry:
    """One taxonomy skill.

    ``skill_id`` is the database identity and is *not* in the JSON file — the
    seeder assigns it. The engine only ever needs the id at scoring time, and the
    taxonomy's job is to map text onto that id.
    """

    skill_id: int
    slug: str
    name: str
    category: str
    description: str
    aliases: tuple[str, ...]

    def as_ref(self) -> SkillRef:
        return SkillRef(
            skill_id=self.skill_id,
            name=self.name,
            slug=self.slug,
            category=self.category,
        )


@dataclass(frozen=True, slots=True)
class Taxonomy:
    version: str
    updated_at: str
    skills: tuple[SkillEntry, ...]
    by_slug: dict[str, SkillEntry]
    by_surface: dict[str, SkillEntry]
    #: Surface forms deliberately excluded from extraction patterns, with the
    #: reason. A one- or two-letter alias is far more likely to appear as an
    #: ordinary English token than as a genuine skill mention.
    extraction_exclusions: dict[str, str]

    # -- lookup ---------------------------------------------------------
    def canonicalise(self, term: str) -> SkillEntry | None:
        """Resolve any surface form to its skill. ``"sklearn"`` -> Scikit-learn."""
        return self.by_surface.get(normalise_surface(term))

    def by_id(self, skill_id: int) -> SkillEntry | None:
        for skill in self.skills:
            if skill.skill_id == skill_id:
                return skill
        return None

    def in_category(self, category: str) -> tuple[SkillEntry, ...]:
        return tuple(s for s in self.skills if s.category == category)

    @property
    def categories(self) -> tuple[str, ...]:
        return tuple(sorted({s.category for s in self.skills}))

    def all_patterns(self) -> list[str]:
        """Surface forms the spaCy ``PhraseMatcher`` should look for.

        Sorted longest-first so a longer alias ("scikit learn") is preferred over a
        shorter one it contains, and so the matcher's own greedy pass prefers the
        most specific phrase.
        """
        patterns: list[str] = []
        for skill in self.skills:
            for form in (skill.name, skill.slug, *skill.aliases):
                # The exclusion table is keyed on the *normalised* form, so the
                # lookup has to normalise too. Comparing the raw form would
                # silently never match, and an exclusion that does not exclude
                # is worse than no exclusion at all.
                if normalise_surface(form) in self.extraction_exclusions:
                    continue
                patterns.append(form)
        # De-duplicate on the normalised form but keep a display-friendly original.
        seen: set[str] = set()
        unique: list[str] = []
        for pattern in patterns:
            key = normalise_surface(pattern)
            if key and key not in seen and key not in self.extraction_exclusions:
                seen.add(key)
                unique.append(pattern)
        return sorted(unique, key=lambda p: (-len(p), p))

    def validate(self) -> list[str]:
        """Return a list of problems; empty means the taxonomy is coherent."""
        problems: list[str] = []

        by_name: dict[str, str] = {}
        by_slug: dict[str, str] = {}
        for skill in self.skills:
            key = normalise_surface(skill.name)
            if key in by_name:
                problems.append(f"duplicate skill name: {skill.name}")
            by_name[key] = skill.slug

            if skill.slug in by_slug:
                problems.append(f"duplicate slug: {skill.slug}")
            by_slug[skill.slug] = skill.slug

        owners: dict[str, set[str]] = {}
        for skill in self.skills:
            for form in (skill.name, skill.slug, *skill.aliases):
                owners.setdefault(normalise_surface(form), set()).add(skill.slug)
        for surface, slugs in owners.items():
            if len(slugs) > 1:
                problems.append(
                    f"surface form {surface!r} is claimed by {sorted(slugs)}"
                )

        for skill in self.skills:
            if not skill.category.strip():
                problems.append(f"{skill.slug} has an empty category")
            if len(skill.aliases) < 2:
                problems.append(
                    f"{skill.slug} has {len(skill.aliases)} aliases; at least 2 are required"
                )
        return problems


@lru_cache(maxsize=4)
def load(path: str | None = None) -> Taxonomy:
    """Load and index the taxonomy. Cached per path."""
    taxonomy_path = Path(path) if path else DEFAULT_TAXONOMY_PATH
    if not taxonomy_path.exists():
        raise FileNotFoundError(
            f"Skill taxonomy not found at {taxonomy_path}. "
            "It is version-controlled data and must not be missing."
        )

    with taxonomy_path.open(encoding="utf-8") as handle:
        raw = json.load(handle)

    exclusions: dict[str, str] = {}
    for entry in raw.get("extraction_exclusions", []):
        exclusions[normalise_surface(entry["pattern"])] = entry.get("reason", "")

    skills: list[SkillEntry] = []
    by_slug: dict[str, SkillEntry] = {}
    by_surface: dict[str, SkillEntry] = {}

    # The JSON stores no numeric id; the seeder assigns them by slug. For the
    # in-process (database-free) engine, the enumeration index is used as a
    # stable synthetic id, and the service layer replaces it with the real id.
    for index, item in enumerate(raw.get("skills", []), start=1):
        entry = SkillEntry(
            skill_id=index,
            slug=item["slug"],
            name=item["name"],
            category=item["category"],
            description=item.get("description", ""),
            aliases=tuple(item.get("aliases", [])),
        )
        skills.append(entry)
        by_slug[entry.slug] = entry
        for form in (entry.name, entry.slug, *entry.aliases):
            key = normalise_surface(form)
            if key and key not in by_surface:
                by_surface[key] = entry

    taxonomy = Taxonomy(
        version=raw.get("version", "0"),
        updated_at=raw.get("updated_at", ""),
        skills=tuple(skills),
        by_slug=by_slug,
        by_surface=by_surface,
        extraction_exclusions=exclusions,
    )

    problems = taxonomy.validate()
    if problems:
        raise ValueError(
            "Skill taxonomy is inconsistent; refusing to load it:\n  - "
            + "\n  - ".join(problems)
        )

    logger.info(
        "Loaded skill taxonomy v%s: %d skills, %d surface forms",
        taxonomy.version,
        len(taxonomy.skills),
        len(taxonomy.by_surface),
    )
    return taxonomy


def canonicalise(term: str) -> SkillEntry | None:
    """Module-level convenience wrapper around ``load().canonicalise``."""
    return load().canonicalise(term)


def all_patterns() -> list[str]:
    return load().all_patterns()


def validate() -> list[str]:
    return load().validate()
