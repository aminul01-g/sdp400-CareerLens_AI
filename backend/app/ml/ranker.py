"""Ranking: combine the two components into one explainable, deterministic order.

Determinism is the property this module exists to guarantee, and it is asserted
by ``tests/test_determinism.py``. Two things deliver it:

* No randomness anywhere. ``TfidfVectorizer`` is a closed-form transform, not a
  fit-with-seed, so it is reproducible by construction.
* The sort key is ``(-compatibility, job_role_id)`` — a **total order**. Many
  roles will score identically (two roles with the same required-skill set and
  similar descriptions are common), and without the id tiebreak Python's stable
  sort would leave the result dependent on database row order, which is not
  guaranteed to be stable across runs.

The score itself is unchanged in shape:

.. code-block:: text

    compatibility = w_cov * skill_coverage + w_txt * tfidf_similarity

``skill_coverage`` is the weighted coverage of declared proficiency after two
adjustments — recency and depth, and level fit. The intermediate numbers are
reported alongside it so the arithmetic stays reconstructible by hand. See
``app/ml/signals.py`` for the adjustments and why they are bounded.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from datetime import date

from app.ml.gap_analysis import analyse
from app.ml.matcher import (
    combined_score,
    tfidf_cosine,
    weighted_skill_coverage_from_factors,
)
from app.ml.signals import level_fit as compute_level_fit
from app.ml.signals import normalise_band, signal_factor, user_level_band
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

#: How much the community prior may move a score, as a fraction.
#:
#: Deliberately small. The prior is evidence about a *role*, not about a
#: person, and a role that everybody dismisses should still be shown and
#: explained. The prior reorders; it does not exclude.
PRIOR_STRENGTH = 0.10


def rank(
    snapshot: ProfileSnapshot,
    role_specs: Sequence[RoleSpec],
    *,
    coverage_weight: float = DEFAULT_COVERAGE_WEIGHT,
    tfidf_weight: float = DEFAULT_TFIDF_WEIGHT,
    top_n: int | None = None,
    skill_names: Mapping[int, tuple[str, str]] | None = None,
    role_seniorities: Mapping[int, str] | None = None,
    today: date | None = None,
    role_priors: Mapping[int, float] | None = None,
    prior_strength: float = PRIOR_STRENGTH,
) -> list[RoleScore]:
    """Score and rank every candidate role.

    A role with **zero** matching skills scores exactly ``0.0`` and is still
    returned, ranked last. Dropping it would be a worse product decision than
    showing it: "ML Engineer, 0% — you have none of the required skills" is
    actionable information, and silently omitting it makes the candidate set look
    curated when it is not.

    ``today`` is the reference date for the recency signal. It is an argument
    rather than a call to the system clock so that this function stays pure:
    the service layer passes the real date, and the evaluation harness passes a
    fixed one. ``None`` means "no reference date", which makes the recency
    half of the signal neutral and leaves the depth half in force.

    ``role_priors`` is the community signal, ``role_id -> prior`` in
    ``[-1, 1]``. It is applied as a bounded multiplier *after* the two
    components are combined, so the published formula for the components
    still holds exactly. A role with no prior is unaffected.

    ``prior_strength`` is how much the prior may move a score. It is a
    parameter so that the deployment can set it, and so that the engine
    remains free of a configuration dependency.
    """
    if not role_specs:
        return []

    profile_text = snapshot.profile_text or build_profile_text(snapshot)
    names = skill_names or {}
    seniorities = role_seniorities or {}
    priors = role_priors or {}

    # One vectorizer fit for the whole candidate set — not one per role.
    similarities = tfidf_cosine(profile_text, role_specs)

    # Two strength maps for every skill the user holds: what they declared, and
    # what that declaration is worth once recency and depth are taken into
    # account. A user who has stated nothing extra gets two identical maps, and
    # therefore exactly the score they got before these signals existed.
    declared_factors: dict[int, float] = {}
    signal_factors: dict[int, float] = {}
    for skill in snapshot.skills:
        declared = proficiency_factor(skill.proficiency)
        declared_factors[skill.skill_id] = declared
        signal_factors[skill.skill_id] = declared * signal_factor(
            skill.years_used, skill.last_used_at, today
        )

    user_band = user_level_band(snapshot.seniority, snapshot.years_experience)
    user_skills = snapshot.skill_proficiency

    scores: list[RoleScore] = []
    for spec, similarity in zip(role_specs, similarities, strict=True):
        declared_coverage = weighted_skill_coverage_from_factors(
            declared_factors, spec.required_skills
        )
        signal_coverage = weighted_skill_coverage_from_factors(
            signal_factors, spec.required_skills
        )
        fit = compute_level_fit(user_band, normalise_band(seniorities.get(spec.job_role_id)))
        coverage = signal_coverage * fit
        compatibility = combined_score(coverage, similarity, coverage_weight, tfidf_weight)

        # The community prior, applied last and bounded. A prior of -1 with the
        # default strength removes 10% of the score; a prior of +1 adds 10%.
        prior = float(priors.get(spec.job_role_id, 0.0))
        if prior and prior_strength:
            compatibility = max(
                0.0, min(1.0, compatibility * (1.0 + prior_strength * prior))
            )

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
                strength = signal_factors.get(skill_id)
                if strength is None:
                    strength = proficiency_factor(int(proficiency))
                matched.append(
                    MatchedSkill(
                        skill_id=skill_id,
                        name=name,
                        weight=weight_float,
                        proficiency=int(proficiency),
                        contribution=weight_float * strength,
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
                declared_coverage=declared_coverage,
                signal_coverage=signal_coverage,
                level_fit=fit,
                role_prior=prior,
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
        len(signal_factors),
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
