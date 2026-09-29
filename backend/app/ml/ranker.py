"""Ranking: combine the two components into one explainable, deterministic order.

Determinism is the property this module exists to guarantee, and it is asserted by
``tests/test_determinism.py``. Two things deliver it:

* No randomness anywhere. ``TfidfVectorizer`` is a closed-form transform, not a
  fit-with-seed, so it is reproducible by construction.
* The sort key is ``(-compatibility, job_role_id)`` — a **total order**. Many
  roles will score identically (two roles with the same required-skill set and
  similar descriptions are common), and without the id tiebreak Python's stable
  sort would leave the result dependent on database row order, which is not
  guaranteed to be stable across runs.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence

from app.ml.gap_analysis import analyse
from app.ml.matcher import combined_score, tfidf_cosine, weighted_skill_coverage
from app.ml.text_profile import build_profile_text
from app.ml.types import (
    MatchedSkill,
    MissingSkill,
    ProfileSnapshot,
    RoleScore,
    RoleSpec,
    proficiency_factor,
)

logger = logging.getLogger("app.ml.ranker")

DEFAULT_COVERAGE_WEIGHT = 0.6
DEFAULT_TFIDF_WEIGHT = 0.4


def rank(
    snapshot: ProfileSnapshot,
    role_specs: Sequence[RoleSpec],
    *,
    coverage_weight: float = DEFAULT_COVERAGE_WEIGHT,
    tfidf_weight: float = DEFAULT_TFIDF_WEIGHT,
    top_n: int | None = None,
    skill_names: Mapping[int, tuple[str, str]] | None = None,
    role_seniorities: Mapping[int, str] | None = None,
) -> list[RoleScore]:
    """Score and rank every candidate role.

    A role with **zero** matching skills scores exactly ``0.0`` and is still
    returned, ranked last. Dropping it would be a worse product decision than
    showing it: "ML Engineer, 0% — you have none of the required skills" is
    actionable information, and silently omitting it makes the candidate set look
    curated when it is not.
    """
    if not role_specs:
        return []

    profile_text = snapshot.profile_text or build_profile_text(snapshot)
    user_skills = snapshot.skill_proficiency
    names = skill_names or {}
    seniorities = role_seniorities or {}

    # One vectorizer fit for the whole candidate set — not one per role.
    similarities = tfidf_cosine(profile_text, role_specs)

    scores: list[RoleScore] = []
    for spec, similarity in zip(role_specs, similarities, strict=True):
        coverage = weighted_skill_coverage(user_skills, spec.required_skills)
        compatibility = combined_score(coverage, similarity, coverage_weight, tfidf_weight)

        matched: list[MatchedSkill] = []
        missing: list[MissingSkill] = []
        for skill_id, weight in spec.required_skills.items():
            weight_float = float(weight)
            name, category = names.get(skill_id, (f"Skill {skill_id}", ""))
            proficiency = user_skills.get(skill_id)
            if proficiency is None:
                missing.append(
                    MissingSkill(
                        skill_id=skill_id,
                        name=name,
                        weight=weight_float,
                        tier=(
                            "critical"
                            if weight_float >= 0.8
                            else "important"
                            if weight_float >= 0.5
                            else "desirable"
                        ),
                        category=category,
                    )
                )
            else:
                matched.append(
                    MatchedSkill(
                        skill_id=skill_id,
                        name=name,
                        weight=weight_float,
                        proficiency=int(proficiency),
                        contribution=weight_float * proficiency_factor(int(proficiency)),
                        category=category,
                    )
                )

        matched.sort(key=lambda item: (-item.weight, item.skill_id))
        missing.sort(key=lambda item: (-item.weight, item.skill_id))

        scores.append(
            RoleScore(
                job_role_id=spec.job_role_id,
                title=spec.title,
                slug=spec.slug,
                family=spec.family,
                seniority=seniorities.get(spec.job_role_id, ""),
                compatibility=compatibility,
                skill_coverage=coverage,
                tfidf_similarity=similarity,
                matched=tuple(matched),
                missing=tuple(missing),
            )
        )

    # The total order. job_role_id is the tiebreak, not an afterthought.
    scores.sort(key=lambda item: (-item.compatibility, item.job_role_id))
    for position, score in enumerate(scores, start=1):
        object.__setattr__(score, "rank", position)

    if top_n is not None and top_n > 0:
        scores = scores[:top_n]

    logger.info(
        "Ranked %d roles (%d skills, top score %.4f)",
        len(scores),
        len(user_skills),
        scores[0].compatibility if scores else 0.0,
    )
    return scores


def score_one(snapshot: ProfileSnapshot, role: RoleSpec, **kwargs) -> RoleScore:
    """Score a single role. Used by the skill-gap endpoint, which does not rank."""
    return rank(snapshot, [role], **kwargs)[0]


def gap_for(
    snapshot: ProfileSnapshot,
    role: RoleSpec,
    *,
    skill_names: Mapping[int, tuple[str, str]] | None = None,
):
    """Convenience wrapper so the API does not import two modules for one call."""
    return analyse(snapshot.skill_proficiency, role, skill_names=skill_names)
