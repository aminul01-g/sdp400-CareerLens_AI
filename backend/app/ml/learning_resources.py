"""The verified learning-resource registry.

============================  ==========================================
Constraint                    Enforcement
============================  ==========================================
The model cannot produce a URL   The provider is shown resource
                               *identifiers and titles only. It has no field
                               in its output schema for a link, so a link it
                               did not receive cannot appear in a plan
Unknown identifiers are dropped  :meth:`LearningResources.resolve` returns
                               only identifiers that are in the registry. A
                               model that invents ``doc-42`` gets nothing
                               for it rather than a fabricated link
Pure module                    Reads a JSON file and the standard library.
                               No ORM, no framework, no network
============================  ==========================================

The registry is deliberately small and deliberately conservative: official
documentation and established free educational material only. A resource that
cannot be verified is left out, and the learning task is still given without
one — a task with no link is a worse answer than a task with a wrong link,
but not a dishonest one.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

BACKEND_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PATH = BACKEND_ROOT / "data" / "learning_resources.json"

#: The kinds a resource may have. Used to label it in the UI.
RESOURCE_KINDS = ("official_docs", "reference", "tutorial", "interactive", "course", "book")


@dataclass(frozen=True)
class LearningResource:
    """One verified resource."""

    id: str
    title: str
    url: str
    kind: str
    summary: str

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "title": self.title,
            "url": self.url,
            "kind": self.kind,
            "summary": self.summary,
        }


@dataclass(frozen=True)
class LearningResources:
    """The registry, indexed for lookup."""

    version: str
    resources: dict[str, LearningResource]
    by_skill: dict[str, tuple[str, ...]]

    def get(self, resource_id: str) -> LearningResource | None:
        return self.resources.get(resource_id.strip().lower())

    def for_skill(self, skill_slug: str) -> tuple[LearningResource, ...]:
        """The resources registered for one skill, in registry order."""
        ids = self.by_skill.get(skill_slug.strip().lower(), ())
        found = [self.resources[resource_id] for resource_id in ids if resource_id in self.resources]
        return tuple(found)

    def for_skills(self, skill_slugs: list[str]) -> tuple[LearningResource, ...]:
        """The resources for several skills, de-duplicated, in first-seen order."""
        seen: set[str] = set()
        collected: list[LearningResource] = []
        for slug in skill_slugs:
            for resource in self.for_skill(slug):
                if resource.id in seen:
                    continue
                seen.add(resource.id)
                collected.append(resource)
        return tuple(collected)

    def resolve(self, resource_ids: list[str]) -> tuple[LearningResource, ...]:
        """Turn identifiers into resources, dropping the ones we do not have.

        This is the boundary that makes "the model must not invent a URL"
        mechanically true rather than a matter of prompt wording.
        """
        resolved: list[LearningResource] = []
        seen: set[str] = set()
        for resource_id in resource_ids:
            key = resource_id.strip().lower()
            if not key or key in seen:
                continue
            resource = self.resources.get(key)
            if resource is None:
                continue
            seen.add(key)
            resolved.append(resource)
        return tuple(resolved)

    def validate(self) -> list[str]:
        """Return a list of problems. Empty means the registry is sound."""
        problems: list[str] = []
        for resource_id, resource in self.resources.items():
            if not resource.url.startswith("https://"):
                problems.append(f"{resource_id}: url is not https")
            if resource.kind not in RESOURCE_KINDS:
                problems.append(f"{resource_id}: unknown kind {resource.kind!r}")
            if not resource.title.strip():
                problems.append(f"{resource_id}: blank title")
        for slug, ids in self.by_skill.items():
            for resource_id in ids:
                if resource_id not in self.resources:
                    problems.append(f"{slug}: unknown resource {resource_id!r}")
        return problems


def _parse(payload: dict[str, Any]) -> LearningResources:
    resources: dict[str, LearningResource] = {}
    for entry in payload.get("resources", []):
        resource = LearningResource(
            id=str(entry["id"]).strip().lower(),
            title=str(entry["title"]).strip(),
            url=str(entry["url"]).strip(),
            kind=str(entry.get("kind", "official_docs")).strip(),
            summary=str(entry.get("summary", "")).strip(),
        )
        if resource.id in resources:
            raise ValueError(f"duplicate learning resource id: {resource.id}")
        resources[resource.id] = resource

    by_skill: dict[str, tuple[str, ...]] = {}
    for slug, ids in payload.get("skills", {}).items():
        by_skill[str(slug).strip().lower()] = tuple(
            str(item).strip().lower() for item in ids
        )

    return LearningResources(
        version=str(payload.get("version", "0")),
        resources=resources,
        by_skill=by_skill,
    )


@lru_cache(maxsize=4)
def load(path: str | None = None) -> LearningResources:
    """Load and validate the registry.

    Raises ``ValueError`` when the file is malformed, so a broken registry is
    a boot-time failure rather than a runtime surprise.
    """
    target = Path(path) if path else DEFAULT_PATH
    if not target.exists():
        raise ValueError(f"learning resource registry not found: {target}")
    payload = json.loads(target.read_text(encoding="utf-8"))
    registry = _parse(payload)
    problems = registry.validate()
    if problems:
        raise ValueError(
            "learning resource registry is invalid: " + "; ".join(problems[:5])
        )
    return registry
