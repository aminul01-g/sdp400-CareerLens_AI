"""The job-description analyser.

============================  ==========================================
Constraint                    Enforcement
============================  ==========================================
The score is the application's  The compatibility figure is computed by
                               :func:`app.ml.matcher.weighted_skill_coverage_from_factors`
                               over the extracted requirements, using the
                               same proficiency and signal adjustments the
                               ranker uses. The model is asked *which*
                               skills a description wants and whether each
                               is required or preferred. It is never asked
                               for a number
Normalisation is ours          An extracted skill is resolved against the
                               application's own taxonomy, aliases
                               included. "K8s" becomes Kubernetes because
                               the taxonomy says so, not because a model said
                               so
A gap is not an absence         Three states, not two. ``met``, ``gap`` and
                               ``no_evidence`` are different claims and the
                               interface says which is which
============================  ==========================================
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import UnprocessableError
from app.ml import prompts
from app.ml.matcher import weighted_skill_coverage_from_factors
from app.ml.signals import signal_factor
from app.ml.types import proficiency_factor
from app.models.profile import Profile
from app.models.skill import Skill
from app.models.user import User
from app.models.user_skill import UserSkill
from app.schemas.ai import (
    AnalyzedRequirementRead,
    JobAnalysisRead,
    JobAnalysisRequest,
)
from app.schemas.llm import JobAnalysisOutput
from app.services import (
    ai_context_service,
    groq_service,
    recommendation_service,
    skill_service,
)

logger = logging.getLogger("app.services.job_analysis")

#: A description shorter than this cannot yield enough requirements to be
#: worth analysing.
MIN_DESCRIPTION_CHARS = 120

#: Fewer than this many extracted requirements and the description is too thin
#: to say anything reliable about the role.
MIN_REQUIREMENTS = 2

#: The weight a "required" skill carries in the coverage calculation, and the
#: weight a "preferred" one carries. Required is twice as important, which is
#: a statement about the description, not about the user.
REQUIRED_WEIGHT = 1.0
PREFERRED_WEIGHT = 0.5


def _user_skill_state(db: Session, user: User) -> dict[str, dict[str, Any]]:
    """The user's confirmed skills, keyed by canonical slug."""
    rows = list(
        db.scalars(
            select(UserSkill).where(
                UserSkill.user_id == user.id, UserSkill.confirmed.is_(True)
            )
        ).all()
    )
    state: dict[str, dict[str, Any]] = {}
    for row in rows:
        if row.skill is None:
            continue
        state[row.skill.slug] = {
            "skill_id": row.skill_id,
            "name": row.skill.name,
            "proficiency": row.proficiency,
        }
    return state


def _required_slugs_for(db: Session, job_role_id: int | None) -> set[str]:
    """The slugs a knowledge-base role verifiably requires.

    A skill is only a *genuine gap* when the application knows the role wants
    it and the user does not have it. Anything else is "no evidence" — the
    profile does not record it, which is not the same as the person lacking
    it.
    """
    if job_role_id is None:
        return set()
    return {
        str(item.get("slug", ""))
        for item in ai_context_service.role_requirements(db, job_role_id)
        if item.get("slug")
    }


def _normalise(db: Session, skill: str) -> tuple[str, str]:
    """Resolve a written skill name against the live taxonomy.

    Returns ``(canonical_name, slug)``; both empty when the taxonomy does not
    know the term.
    """
    resolved = skill_service.canonicalise_skill(db, skill)
    if resolved is None:
        return "", ""
    name, slug, _skill_id = resolved
    return name, slug


def _coverage(
    db: Session,
    user: User,
    required: dict[str, float],
) -> tuple[float, dict[str, float]]:
    """The application's own weighted coverage over the extracted requirements.

    ``required`` maps a canonical slug to its importance weight. The user's
    strength for each skill comes from the same proficiency and signal
    adjustments the ranker applies, so a skill used five years ago counts for
    less than one used last month.
    """
    if not required:
        return 0.0, {}
    slugs = list(required)
    rows = list(
        db.scalars(
            select(Skill).where(Skill.slug.in_(slugs))
        ).all()
    )
    slug_to_id = {row.slug: row.id for row in rows}
    user_rows = list(
        db.scalars(
            select(UserSkill).where(
                UserSkill.user_id == user.id,
                UserSkill.confirmed.is_(True),
                UserSkill.skill_id.in_(list(slug_to_id.values()) or [0]),
            )
        ).all()
    )
    from datetime import date

    today = date.today()
    factors: dict[int, float] = {}
    for row in user_rows:
        factors[row.skill_id] = proficiency_factor(row.proficiency) * signal_factor(
            float(row.years_used) if row.years_used is not None else None,
            row.last_used_at,
            today,
        )
    weight_by_id = {slug_to_id[slug]: weight for slug, weight in required.items() if slug in slug_to_id}
    coverage = weighted_skill_coverage_from_factors(factors, weight_by_id)
    return coverage, {slug: factors.get(slug_to_id[slug], 0.0) for slug in required if slug in slug_to_id}


def _checklist(requirements: list[AnalyzedRequirementRead]) -> list[str]:
    """The prioritised preparation steps, built in code.

    The ordering is the application's, not the model's: a *required* skill the
    user does not have comes before a *preferred* one, and within a band the
    heavier requirement comes first. A model-supplied checklist would be a
    model-supplied ordering, and an ordering is exactly the thing a user acts
    on.
    """
    gaps = [item for item in requirements if item.status == "gap"]
    unknown = [item for item in requirements if item.status == "no_evidence"]
    steps: list[str] = []

    for item in gaps:
        verb = "Learn" if item.importance == "required" else "Familiarise yourself with"
        steps.append(
            f"{verb} {item.normalized_skill or item.skill} — the description lists it as "
            f"{item.importance} and it is not in your profile yet."
        )
    for item in unknown:
        steps.append(
            f"Check whether you have used {item.normalized_skill or item.skill}. "
            "The description asks for it and your profile does not record it either way, "
            "so add it if it is true."
        )
    for item in requirements:
        if item.status != "met":
            continue
        if item.proficiency is not None and item.proficiency <= 2:
            steps.append(
                f"Strengthen {item.normalized_skill or item.skill} — you have it on your "
                "profile, but the description expects more depth than your current "
                "proficiency shows."
            )
    if not steps:
        steps.append(
            "Your profile already covers the skills this description asks for. "
            "Focus on how you describe that experience in your CV and in interviews."
        )
    return steps


def analyse(
    db: Session,
    user: User,
    request: JobAnalysisRequest,
) -> JobAnalysisRead:
    """Read a job description and say how the user stands against it."""
    groq_service.require_provider()
    description = request.job_description.strip()
    if len(description) < MIN_DESCRIPTION_CHARS:
        raise UnprocessableError(
            "That job description is too short to analyse. Paste the full "
            "description — the responsibilities and the requirements — and try again.",
            code="insufficient_job_description",
        )

    language = _resolve_language(db, user, request.language)
    messages = prompts.job_analysis_prompt(
        job_description=description,
        language=language,
    )
    analysis = groq_service.run_structured(
        messages,
        JobAnalysisOutput,
        schema_name="job_analysis",
        reasoning_effort="medium",
        max_completion_tokens=4000,
    )

    extracted = list(analysis.required_skills) + list(analysis.preferred_skills)
    if len(extracted) < MIN_REQUIREMENTS:
        raise UnprocessableError(
            "That job description does not contain enough skills to analyse. "
            "It needs a requirements section — the tools, technologies and "
            "experience it asks for — before a useful comparison is possible.",
            code="insufficient_job_description",
        )

    user_skills = _user_skill_state(db, user)
    required_slugs = _required_slugs_for(db, request.job_role_id)

    requirements: list[AnalyzedRequirementRead] = []
    unrecognised: list[str] = []
    weights: dict[str, float] = {}

    for item in extracted:
        canonical_name, slug = _normalise(db, item.skill)
        if not slug:
            unrecognised.append(item.skill)
            requirements.append(
                AnalyzedRequirementRead(
                    skill=item.skill,
                    importance=item.importance,
                    evidence=item.evidence,
                    normalized_skill="",
                    normalized_slug="",
                    status="no_evidence",
                    note=(
                        "This skill is not in the application's taxonomy, so it "
                        "cannot be compared against your profile."
                    ),
                )
            )
            continue

        weights[slug] = (
            REQUIRED_WEIGHT if item.importance == "required" else PREFERRED_WEIGHT
        )
        held = user_skills.get(slug)
        if held is not None:
            status = "met"
            note = "Recorded on your profile."
            proficiency = held["proficiency"]
        elif slug in required_slugs:
            status = "gap"
            note = (
                "Required by this role in the application's knowledge base, and "
                "not recorded on your profile."
            )
            proficiency = None
        else:
            status = "no_evidence"
            note = (
                "The description asks for this, but your profile does not record "
                "it. That is not the same as you not having it — add it if it is true."
            )
            proficiency = None

        requirements.append(
            AnalyzedRequirementRead(
                skill=item.skill,
                importance=item.importance,
                evidence=item.evidence,
                normalized_skill=canonical_name,
                normalized_slug=slug,
                status=status,
                proficiency=proficiency,
                note=note,
            )
        )

    coverage, _strengths = _coverage(db, user, weights)

    official: float | None = None
    if request.job_role_id is not None:
        _role, report = recommendation_service.analyse_gap(
            db, user, request.job_role_id
        )
        official = round(report.coverage * 100, 1)

    matched = sum(1 for item in requirements if item.status == "met")
    gaps = sum(1 for item in requirements if item.status == "gap")
    unknown_count = sum(1 for item in requirements if item.status == "no_evidence")

    return JobAnalysisRead(
        role_title=analysis.role_title,
        summary=analysis.summary,
        generated_by=f"groq:{groq_service.provider_status().get('model', '')}",
        language=language,
        coverage=round(coverage, 6),
        coverage_pct=round(coverage * 100, 1),
        official_compatibility_pct=official,
        matched_count=matched,
        gap_count=gaps,
        no_evidence_count=unknown_count,
        requirements=requirements,
        tools_and_technologies=list(analysis.tools_and_technologies),
        experience_requirement=analysis.experience_requirement,
        education_requirement=analysis.education_requirement,
        responsibilities=list(analysis.responsibilities),
        deliverables=list(analysis.deliverables),
        checklist=_checklist(requirements),
        limitations=list(analysis.limitations),
        unrecognised_skills=unrecognised,
    )


def _resolve_language(db: Session, user: User, requested: str | None) -> str:
    """Which language the analysis is written in."""
    if requested:
        return prompts.normalise_language(requested)
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    if profile is not None:
        return prompts.normalise_language(profile.preferred_language)
    return "en"
