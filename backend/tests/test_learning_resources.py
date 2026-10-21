"""The verified learning-resource registry.

The registry is the only place a learning link can come from, so its own
integrity is the thing that makes "the model cannot invent a URL" true rather
than aspirational. These tests check the registry is sound, that it agrees
with the taxonomy, and that an identifier the registry does not hold resolves
to nothing.
"""

from __future__ import annotations

import json

import pytest

from app.ml.learning_resources import load
from app.ml.taxonomy import load as load_taxonomy


@pytest.fixture(scope="module")
def registry():
    return load()


def test_the_registry_is_not_empty(registry) -> None:
    assert len(registry.resources) >= 50
    assert len(registry.by_skill) >= 50


def test_every_resource_has_a_real_https_url(registry) -> None:
    for resource in registry.resources.values():
        assert resource.url.startswith("https://"), resource.id
        assert " " not in resource.url, resource.id


def test_every_resource_has_a_title_and_a_kind(registry) -> None:
    for resource in registry.resources.values():
        assert resource.title.strip(), resource.id
        assert resource.kind in {
            "official_docs",
            "reference",
            "tutorial",
            "interactive",
            "course",
            "book",
        }, resource.id


def test_the_registry_has_no_problems(registry) -> None:
    assert registry.validate() == []


def test_every_mapped_skill_exists_in_the_taxonomy(registry) -> None:
    """A mapping to a skill the taxonomy does not have is a mapping to
    nothing."""
    taxonomy = load_taxonomy()
    slugs = {skill.slug for skill in taxonomy.skills}
    unknown = sorted(slug for slug in registry.by_skill if slug not in slugs)
    assert unknown == []


def test_the_registry_covers_most_of_the_taxonomy(registry) -> None:
    taxonomy = load_taxonomy()
    slugs = {skill.slug for skill in taxonomy.skills}
    covered = sum(1 for slug in slugs if slug in registry.by_skill)
    assert covered >= 0.8 * len(slugs), f"only {covered} of {len(slugs)} skills covered"


def test_an_unknown_identifier_resolves_to_nothing(registry) -> None:
    """The boundary that stops an invented link."""
    assert registry.resolve(["totally-made-up-resource"]) == ()
    assert registry.resolve([]) == ()
    assert registry.resolve(["python-docs"])[0].id == "python-docs"


def test_resolving_keeps_the_order_and_drops_duplicates(registry) -> None:
    resolved = registry.resolve(["python-docs", "python-docs", "sqlbolt"])
    assert [item.id for item in resolved] == ["python-docs", "sqlbolt"]


def test_a_skill_with_no_resource_returns_nothing(registry) -> None:
    assert registry.for_skill("a-skill-that-does-not-exist") == ()


def test_resources_for_several_skills_are_deduplicated(registry) -> None:
    collected = registry.for_skills(["python", "sql"])
    identifiers = [item.id for item in collected]
    assert len(identifiers) == len(set(identifiers))


def test_the_registry_file_is_valid_json_with_a_version() -> None:
    from pathlib import Path

    from app.ml.learning_resources import DEFAULT_PATH

    payload = json.loads(Path(DEFAULT_PATH).read_text(encoding="utf-8"))
    assert payload["version"]
    assert payload["resources"]
    assert payload["skills"]


def test_the_model_is_never_shown_a_url(registry) -> None:
    """The prompt builder is what enforces the last line of defence."""
    from app.ml import prompts

    described = [
        {"id": resource.id, "title": resource.title, "summary": resource.summary}
        for resource in list(registry.resources.values())[:5]
    ]
    messages = prompts.roadmap_prompt(
        role_title="Data Analyst",
        weeks=4,
        facts={"profile": {}},
        missing_skills=[{"name": "SQL", "weight": 1.0, "tier": "critical"}],
        resources=described,
    )
    content = messages[0]["content"]
    resource_block = content.split("<verified_learning_resources>")[1]
    assert "https://" not in resource_block
    assert "python-docs" in resource_block
