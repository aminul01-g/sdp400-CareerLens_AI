"""T043/T044 — the taxonomy loads, and every alias resolves to exactly one skill."""

from __future__ import annotations

import json

import pytest

from app.ml.taxonomy import load, normalise_surface

#: The plan's named example, verbatim.
PLAN_EXAMPLE = {
    "sklearn": "Scikit-learn",
    "scikit learn": "Scikit-learn",
    "sci-kit learn": "Scikit-learn",
    "SKLearn": "Scikit-learn",
    "sk-learn": "Scikit-learn",
    "Scikit-learn": "Scikit-learn",
}


@pytest.fixture(scope="module")
def taxonomy():
    return load()


def test_taxonomy_has_at_least_150_skills(taxonomy) -> None:
    assert len(taxonomy.skills) >= 150, f"only {len(taxonomy.skills)} skills"
    # The proposal asked for "around 150", and the catalogue is well past it.
    # The band is the same one scripts/verify_compliance.py enforces: a floor,
    # and a ceiling far enough above the floor to leave room for a catalogue
    # that is not only an AI/ML list.
    assert len(taxonomy.skills) <= 400, "the taxonomy has grown past its ceiling"


def test_every_category_is_represented(taxonomy) -> None:
    """No category is empty, and the original eight are all still there.

    The catalogue was widened with six non-technical categories, so the count
    is no longer eight. What has to stay true is that every category has
    members, and that the original eight were not emptied out to make room.
    """
    original_eight = {
        "Programming & Core",
        "Data Engineering",
        "Statistics & Mathematics",
        "ML Frameworks",
        "Deep Learning",
        "NLP & LLM",
        "MLOps & Cloud",
        "Analytics & Communication",
    }
    assert original_eight <= set(taxonomy.categories)
    for category in taxonomy.categories:
        assert taxonomy.in_category(category), f"{category} is empty"


def test_the_knowledge_base_is_not_only_ai_and_ml(taxonomy) -> None:
    """The catalogue has to reach outside the AI/ML corner to be a taxonomy."""
    non_technical = {
        "Education & Training",
        "Healthcare & Clinical",
        "Accounting & Finance",
        "Civil & Electrical Engineering",
        "Marketing",
        "Human Resources",
    }
    assert non_technical <= set(taxonomy.categories)
    for category in non_technical:
        members = taxonomy.in_category(category)
        assert len(members) >= 10, f"{category} has only {len(members)} skills"


def test_every_skill_has_at_least_two_aliases(taxonomy) -> None:
    thin = [s.slug for s in taxonomy.skills if len(s.aliases) < 2]
    assert not thin, f"skills with fewer than 2 aliases: {thin}"


def test_validation_reports_no_problems(taxonomy) -> None:
    assert taxonomy.validate() == []


def test_every_alias_resolves_to_exactly_one_skill(taxonomy) -> None:
    for skill in taxonomy.skills:
        for alias in skill.aliases:
            resolved = taxonomy.canonicalise(alias)
            assert resolved is not None, f"{alias!r} does not resolve"
            assert resolved.slug == skill.slug, (
                f"{alias!r} is claimed by both {skill.slug} and {resolved.slug}"
            )


def test_plan_example_all_resolve_to_scikit_learn(taxonomy) -> None:
    """The exact resolution the implementation plan names in section 9.3.3."""
    for surface, expected in PLAN_EXAMPLE.items():
        entry = taxonomy.canonicalise(surface)
        assert entry is not None, f"{surface!r} did not resolve"
        assert entry.name == expected, f"{surface!r} -> {entry.name}, expected {expected}"


@pytest.mark.parametrize("surface", sorted(PLAN_EXAMPLE))
def test_plan_example_normalises_to_one_key(taxonomy, surface: str) -> None:
    assert taxonomy.canonicalise(surface).slug == "scikit-learn"


def test_separators_and_case_are_equivalent(taxonomy) -> None:
    """``-``, ``_``, ``.`` and whitespace are interchangeable, and case is ignored."""
    for variant in ("PyTorch", "pytorch", "PYTORCH", "py-torch", "py torch", "py_torch", "  PyTorch  "):
        assert taxonomy.canonicalise(variant).slug == "pytorch", variant


def test_common_short_forms_resolve(taxonomy) -> None:
    """The surface forms the plan names as ones that break naive matching."""
    expected = {
        "tf": "tensorflow",
        "torch": "pytorch",
        "k8s": "kubernetes",
        "psql": "postgresql",
        "np": "numpy",
        "pd": "pandas",
        "nn": "neural-networks",
    }
    for surface, slug in expected.items():
        entry = taxonomy.canonicalise(surface)
        assert entry is not None and entry.slug == slug, f"{surface!r} -> {entry and entry.slug}"


def test_ambiguous_short_ai_token_is_deliberately_absent(taxonomy) -> None:
    """The plan explicitly excludes ``ai`` as too ambiguous."""
    assert taxonomy.canonicalise("ai") is None


def test_unknown_term_returns_none(taxonomy) -> None:
    for nonsense in ("founder", "zzzzz", "12345", "not-a-skill", ""):
        assert taxonomy.canonicalise(nonsense) is None


def test_normalisation_rule() -> None:
    assert normalise_surface("  SKLearn.  ") == "sklearn"
    assert normalise_surface("sci-kit_learn") == "sci kit learn"
    assert normalise_surface("sci.kit.learn") == "sci kit learn"
    assert normalise_surface("a  b") == "a b"


def test_every_skill_has_a_category_and_slug(taxonomy) -> None:
    for skill in taxonomy.skills:
        assert skill.slug and skill.slug == skill.slug.lower().replace(" ", "-")
        assert skill.category.strip()
        assert skill.description.strip(), f"{skill.slug} has no description"


def test_all_patterns_are_unique_and_sorted(taxonomy) -> None:
    patterns = taxonomy.all_patterns()
    assert len(patterns) == len(set(patterns))
    # Longest first, so the matcher's greedy pass prefers specific phrases.
    lengths = [len(p) for p in patterns]
    assert lengths == sorted(lengths, reverse=True)


def test_patterns_cover_every_skill(taxonomy) -> None:
    pattern_text = " | ".join(t.lower() for t in taxonomy.all_patterns())
    for skill in taxonomy.skills:
        assert skill.name.lower() in pattern_text, f"{skill.name} is not a pattern"


def test_file_declares_version_and_timestamp(taxonomy) -> None:
    """Provenance: a past run must be traceable to the taxonomy that produced it."""
    assert taxonomy.version and taxonomy.version != "0"
    assert taxonomy.updated_at


def test_taxonomy_file_is_valid_json_and_ordered() -> None:
    from app.core.config import get_settings

    with get_settings().skills_taxonomy_path.open(encoding="utf-8") as handle:
        raw = json.load(handle)
    assert "version" in raw and "skills" in raw
    slugs = [s["slug"] for s in raw["skills"]]
    assert len(slugs) == len(set(slugs)), "duplicate slugs in the file"
    names = [s["name"] for s in raw["skills"]]
    assert len(names) == len(set(names)), "duplicate names in the file"
