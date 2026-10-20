"""Generate the signal study's label file.

The file this writes is committed, and the evaluation harness reads it. What
this script adds is the *rule* by which the pairs were chosen, so that the
selection is auditable rather than a matter of picking the pairs that
produced a flattering number.

The rule
--------

Every pair is two descriptions of one candidate, and the two descriptions
declare **identical skills and proficiencies**. They differ only in whether
the candidate declares years of experience, a level, and per-skill recency and
depth. Because ``seniority`` and ``years_experience`` are not part of the
profile text (``app/ml/text_profile.py``), the two variants produce the same
TF-IDF vector, so every difference in the outcome is attributable to the
signals.

Three kinds of pair are generated, and each has a mechanical construction:

``level``
    Two roles from the **same family** at **different seniority bands**. The
    candidate holds every requirement of both roles at proficiency 5, and
    declares the level of the expected one. The signals can only help the
    expected role: it keeps a level fit of 1.0 while the competing role is
    discounted for being at a different band.

``recency``
    Two roles from the **same family** at the **same seniority band**. The
    candidate holds the expected role's requirements at proficiency 5 and the
    skills that only the competing role requires at proficiency 4. Those
    exclusive skills are declared **stale** (last used in 2015); everything
    else is declared current. The expected role's coverage is therefore
    unchanged by the signals, and the competing role's coverage falls.

``depth``
    The same construction, with the exclusive skills declared **shallow**
    (half a year) rather than stale.

In every case the direction of the effect is a property of the construction
rather than of a lucky score, and the harness checks the resulting direction
anyway.

Run it with::

    cd backend && python -m scripts.make_signal_profiles
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from app.ml.signals import LEVEL_BANDS

_BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROLES_PATH = _BACKEND_ROOT / "data" / "job_roles.json"
DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parents[1] / "app" / "ml" / "evaluation" / "signal_profiles.jsonl"

#: A stale skill: last used in January 2015, against a reference date of
#: 30 September 2026. That is 11 years and 8 months, well past the 36-month
#: half life, so the recency factor is close to its floor of 0.70.
STALE_DATE = "2015-01-15"

#: A skill the candidate still uses.
#:
#: Set to the evaluation's reference date, so the recency factor is *exactly*
#: 1.0 rather than 0.994. The comparison depends on the expected role's
#: coverage being untouched: a skill used a month ago would carry a small
#: residual discount, and that discount would leak into the margin the study
#: is trying to attribute to the stale skills alone.
REFERENCE_DATE = "2026-09-30"

#: Depth declared for a skill the candidate has barely touched.
SHALLOW_YEARS = 0.5

#: Depth declared for a skill the candidate has used for years.
DEEP_YEARS = 8.0

#: Proficiency for the expected role's requirements.
STRONG = 5

#: Proficiency for the skills that only the competing role requires.
MODERATE = 4

#: How many pairs of each kind to generate.
#:
#: Twelve pairs in total: six exercise the level fit and three each exercise
#: recency and depth. The study is a correctness check on a mechanism, not a
#: statistical survey, and a larger set of synthetic pairs would add volume
#: without adding evidence.
LEVEL_PAIR_COUNT = 6
RECENCY_PAIR_COUNT = 3
DEPTH_PAIR_COUNT = 3


def load_roles(path: Path = DEFAULT_ROLES_PATH) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    roles = payload.get("roles") or []
    if not roles:
        raise RuntimeError(f"no roles found in {path}")
    return roles


def _requirements(role: Mapping[str, Any]) -> dict[str, float]:
    return {str(entry["skill_slug"]): float(entry["weight"]) for entry in role.get("skills", ())}


def _level_pairs(roles: Sequence[Mapping[str, Any]]) -> list[tuple[str, str, str]]:
    """Same family, adjacent bands, sharing most of their requirements.

    The band order comes from ``app.ml.signals.LEVEL_BANDS``, so "higher" means
    the same thing to the generator and to the engine. Two constraints keep the
    pairs meaningful rather than arbitrary:

    * the bands must be **adjacent**, so the pair is "the same job one level
      up" rather than "a graduate role against a head of department";
    * the two roles must **share at least half** of their requirements, so the
      candidate really is close to both.
    """
    by_family: dict[str, list[Mapping[str, Any]]] = {}
    for role in roles:
        by_family.setdefault(str(role.get("family", "")), []).append(role)

    pairs: list[tuple[str, str, str]] = []
    for family in sorted(by_family):
        members = sorted(by_family[family], key=lambda r: str(r["slug"]))
        for expected in members:
            expected_skills = set(_requirements(expected))
            for competing in members:
                if expected["slug"] == competing["slug"]:
                    continue
                expected_band = str(expected.get("seniority", ""))
                competing_band = str(competing.get("seniority", ""))
                if expected_band not in LEVEL_BANDS or competing_band not in LEVEL_BANDS:
                    continue
                distance = LEVEL_BANDS.index(expected_band) - LEVEL_BANDS.index(competing_band)
                if distance != 1:
                    continue
                competing_skills = set(_requirements(competing))
                shared = expected_skills & competing_skills
                if len(shared) * 2 < len(expected_skills | competing_skills):
                    continue
                pairs.append((str(expected["slug"]), str(competing["slug"]), family))
    return pairs


def _same_band_pairs(
    roles: Sequence[Mapping[str, Any]],
) -> list[tuple[str, str, str]]:
    """Same family, same band, with a skill that only the second role requires.

    The exclusivity requirement is what makes the recency and depth pairs
    meaningful: the expected role's coverage must be untouched by the signal
    for the comparison to isolate the signal. A pair with a large exclusive set
    is rejected, because a candidate who holds a dozen skills the other role
    needs and has abandoned is a strange person.
    """
    by_family: dict[str, list[Mapping[str, Any]]] = {}
    for role in roles:
        by_family.setdefault(str(role.get("family", "")), []).append(role)

    pairs: list[tuple[str, str, str]] = []
    for family in sorted(by_family):
        members = sorted(by_family[family], key=lambda r: str(r["slug"]))
        for expected in members:
            expected_skills = set(_requirements(expected))
            for competing in members:
                if expected["slug"] == competing["slug"]:
                    continue
                if expected.get("seniority") != competing.get("seniority"):
                    continue
                competing_skills = set(_requirements(competing))
                exclusive = competing_skills - expected_skills
                if not 1 <= len(exclusive) <= 3:
                    continue
                if len(expected_skills & competing_skills) < 4:
                    continue
                pairs.append((str(expected["slug"]), str(competing["slug"]), family))
    return pairs


def _years_for_band(band: str) -> int:
    """A plausible number of years for a seniority band."""
    return {
        "Entry": 0,
        "Junior": 1,
        "Mid": 4,
        "Senior": 8,
        "Lead": 12,
        "Principal": 15,
    }.get(band, 0)


def _build_records(
    *,
    pair_id: str,
    kind: str,
    expected: Mapping[str, Any],
    competing: Mapping[str, Any],
    family: str,
    name: str,
    rationale: str,
    skills: Sequence[tuple[str, int]],
    stale_skills: Sequence[str],
    years_experience: int | None,
    seniority: str,
) -> list[dict[str, Any]]:
    expected_slug = str(expected["slug"])
    competing_slug = str(competing["slug"])

    def variant(variant_name: str, *, with_signals: bool) -> dict[str, Any]:
        signal_entries: list[dict[str, Any]] = []
        for slug, _ in skills:
            if slug not in stale_skills:
                continue
            entry: dict[str, Any] = {"skill_slug": slug}
            if kind == "recency":
                entry["last_used_at"] = STALE_DATE
            elif kind == "depth":
                entry["years_used"] = SHALLOW_YEARS
            signal_entries.append(entry)

        # Everything the candidate still uses is declared current and deep, so
        # the only discounted skills in the profile are the ones the competing
        # role alone needs.
        current_entries: list[dict[str, Any]] = []
        for slug, _ in skills:
            if slug in stale_skills:
                continue
            entry = {"skill_slug": slug}
            if kind == "recency":
                entry["last_used_at"] = REFERENCE_DATE
            elif kind == "depth":
                entry["years_used"] = DEEP_YEARS
            current_entries.append(entry)

        record: dict[str, Any] = {
            "id": f"{pair_id}-{variant_name}",
            "pair_id": pair_id,
            "variant": variant_name,
            "name": name,
            "expected_role": expected_slug,
            "expected_family": family,
            "competing_role": competing_slug,
            "signal_kind": kind,
            "headline": name,
            "bio": rationale,
            "skills": [{"skill_slug": slug, "proficiency": p} for slug, p in skills],
            "rationale": rationale,
        }
        if with_signals:
            record["skill_signals"] = signal_entries + current_entries
            if kind == "level":
                record["seniority"] = seniority
                record["years_experience"] = years_experience
        else:
            # The control states nothing at all.
            record["skill_signals"] = []
        return record

    return [
        variant("with_signals", with_signals=True),
        variant("without_signals", with_signals=False),
    ]


def build_records(roles: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Build every pair, in a deterministic order.

    At most one pair of a given kind is taken from any one family, so the
    study samples across the knowledge base instead of measuring the same
    corner of it six times.
    """
    by_slug = {str(role["slug"]): role for role in roles}
    records: list[dict[str, Any]] = []

    # ---- level pairs -----------------------------------------------------
    used_families: set[str] = set()
    index = 0
    for expected_slug, competing_slug, family in _level_pairs(roles):
        if family in used_families or index >= LEVEL_PAIR_COUNT:
            continue
        used_families.add(family)
        index += 1
        expected = by_slug[expected_slug]
        competing = by_slug[competing_slug]
        skills = sorted(set(_requirements(expected)) | set(_requirements(competing)))
        band = str(expected.get("seniority", ""))
        records.extend(
            _build_records(
                pair_id=f"L{index:02d}",
                kind="level",
                expected=expected,
                competing=competing,
                family=family,
                name=f"Level pair {index}: {expected.get('title')} at {band}",
                rationale=(
                    f"A candidate who holds every requirement of both the "
                    f"{expected.get('title')} and the {competing.get('title')} roles, and "
                    f"declares themselves {band}. The {band} role should be the one "
                    f"the level fit favours."
                ),
                skills=[(slug, STRONG) for slug in skills],
                stale_skills=(),
                years_experience=_years_for_band(band),
                seniority=band,
            )
        )

    # ---- recency and depth pairs ----------------------------------------
    for kind, prefix, limit in (
        ("recency", "R", RECENCY_PAIR_COUNT),
        ("depth", "D", DEPTH_PAIR_COUNT),
    ):
        used_families = set()
        index = 0
        for expected_slug, competing_slug, family in _same_band_pairs(roles):
            if family in used_families or index >= limit:
                continue
            used_families.add(family)
            index += 1
            expected = by_slug[expected_slug]
            competing = by_slug[competing_slug]
            expected_skills = set(_requirements(expected))
            competing_skills = set(_requirements(competing))
            exclusive = sorted(competing_skills - expected_skills)
            skills = sorted(
                [(slug, STRONG) for slug in expected_skills]
                + [(slug, MODERATE) for slug in exclusive]
            )
            if kind == "recency":
                explanation = (
                    "has not used them in over a decade, so the recency signal "
                    "discounts them"
                )
            else:
                explanation = (
                    "has barely used them, so the depth signal discounts them"
                )
            records.extend(
                _build_records(
                    pair_id=f"{prefix}{index:02d}",
                    kind=kind,
                    expected=expected,
                    competing=competing,
                    family=family,
                    name=(
                        f"{kind.title()} pair {index}: "
                        f"{expected.get('title')} over {competing.get('title')}"
                    ),
                    rationale=(
                        f"A candidate who holds the {expected.get('title')} role's "
                        f"requirements outright, and holds the skills that only the "
                        f"{competing.get('title')} role requires but {explanation}. "
                        f"The {expected.get('title')} role should keep its coverage "
                        f"while the competing role's falls."
                    ),
                    skills=skills,
                    stale_skills=exclusive,
                    years_experience=None,
                    seniority="",
                )
            )

    return records


def main() -> int:
    roles = load_roles()
    records = build_records(roles)
    output = DEFAULT_OUTPUT_PATH
    lines = [json.dumps(record, ensure_ascii=False) for record in records]
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")

    pairs = len(records) // 2
    kinds: dict[str, int] = {}
    for record in records:
        if record["variant"] == "with_signals":
            kinds[record["signal_kind"]] = kinds.get(record["signal_kind"], 0) + 1
    print(f"wrote {output}")
    print(f"pairs   : {pairs}")
    for kind in sorted(kinds):
        print(f"  {kind:8s}: {kinds[kind]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
