"""Skill-gap analysis: ``required - present``, ordered by importance weight.

Tiers are a **pure function of the weight that already exists** in
``job_role_skill``, not a second computation. That is what guarantees the badge a
user sees cannot drift from the order the table is sorted by.

This module reads the user's *confirmed* skills only. An unconfirmed CV extraction
can therefore neither appear as matched nor suppress a genuine gap.
"""

from __future__ import annotations

from collections.abc import Mapping

from app.ml.matcher import weighted_skill_coverage
from app.ml.types import GapReport, MatchedSkill, MissingSkill, RoleSpec, proficiency_factor

#: Tier boundaries. Mirrored by ``schemas.gap.tier_of`` so the API response and
#: the engine agree; both are covered by ``test_gap_analysis.py``.
CRITICAL_THRESHOLD = 0.8
IMPORTANT_THRESHOLD = 0.5


def tier_of(weight: float) -> str:
    """Band an importance weight: ``critical`` / ``important`` / ``desirable``."""
    if weight >= CRITICAL_THRESHOLD:
        return "critical"
    if weight >= IMPORTANT_THRESHOLD:
        return "important"
    return "desirable"


def analyse(
    user_skills: Mapping[int, int],
    role: RoleSpec,
    *,
    skill_names: Mapping[int, tuple[str, str]] | None = None,
) -> GapReport:
    """Compare a user's skills against one role's weighted requirements.

    Args:
        user_skills: ``skill_id -> proficiency`` (1-5).
        role: The target role and its required ``skill_id -> weight`` map.
        skill_names: Optional ``skill_id -> (name, category)`` for readable output.
            The engine itself does not need names; the API layer supplies them.

    Returns:
        A :class:`GapReport` whose ``missing`` list is sorted by **descending
        weight**, with the ``skill_id`` as a tiebreak so the order is total and
        therefore deterministic.
    """
    names = skill_names or {}
    matched: list[MatchedSkill] = []
    missing: list[MissingSkill] = []

    for skill_id, weight in role.required_skills.items():
        weight_float = float(weight)
        name, category = names.get(skill_id, (f"Skill {skill_id}", ""))
        proficiency = user_skills.get(skill_id)

        if proficiency is None:
            missing.append(
                MissingSkill(
                    skill_id=skill_id,
                    name=name,
                    weight=weight_float,
                    tier=tier_of(weight_float),
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

    # Descending weight is the feature: the first row is the single most valuable
    # thing to learn next. The id tiebreak makes equal weights stable.
    missing.sort(key=lambda item: (-item.weight, item.skill_id))
    matched.sort(key=lambda item: (-item.weight, item.skill_id))

    return GapReport(
        job_role_id=role.job_role_id,
        title=role.title,
        family=role.family,
        coverage=weighted_skill_coverage(user_skills, role.required_skills),
        matched=tuple(matched),
        missing=tuple(missing),
    )
