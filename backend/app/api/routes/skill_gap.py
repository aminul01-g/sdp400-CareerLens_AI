"""``/api/skill-gap`` — required minus present for one target role."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.core.exceptions import FeatureDisabledError
from app.ml.types import RoleSpec
from app.schemas.gap import (
    GapRoleSummary,
    MatchedSkill,
    MissingSkill,
    SkillGapResponse,
    TierCounts,
)
from app.schemas.recommendation import LearningPathResponse, LearningPathStep
from app.services import recommendation_service

router = APIRouter(prefix="/skill-gap", tags=["skill-gap"])


@router.get(
    "/{job_role_id}",
    response_model=SkillGapResponse,
    summary="Skill-gap analysis for a target role",
    responses={404: {"description": "No such role"}},
)
def skill_gap(job_role_id: int, db: DbSession, user: CurrentUser) -> SkillGapResponse:
    """Reads confirmed ``user_skill`` rows only.

    An unconfirmed CV extraction can therefore neither appear as matched nor
    suppress a genuine gap, which is the property the staging table exists to
    provide.
    """
    role, report = recommendation_service.analyse_gap(db, user, job_role_id)

    tiers = TierCounts(
        critical=sum(1 for m in report.missing if m.tier == "critical"),
        important=sum(1 for m in report.missing if m.tier == "important"),
        desirable=sum(1 for m in report.missing if m.tier == "desirable"),
    )

    return SkillGapResponse(
        job_role=GapRoleSummary(
            job_role_id=role.id,
            title=role.title,
            family=role.family,
            seniority=role.seniority,
            required_skills_count=report.required_count,
        ),
        coverage=round(report.coverage, 6),
        coverage_pct=round(report.coverage * 100, 1),
        required_count=report.required_count,
        matched_count=len(report.matched),
        missing_count=len(report.missing),
        matched=[
            MatchedSkill(
                skill_id=m.skill_id,
                name=m.name,
                category=m.category or None,
                weight=round(m.weight, 4),
                proficiency=m.proficiency,
                contribution=round(m.contribution, 6),
            )
            for m in report.matched
        ],
        # Already sorted by descending weight inside ml.gap_analysis.
        missing=[
            MissingSkill(
                skill_id=m.skill_id,
                name=m.name,
                category=m.category or None,
                weight=round(m.weight, 4),
                tier=m.tier,
            )
            for m in report.missing
        ],
        tiers=tiers,
        learning_path_available=get_settings().llm_enabled,
    )


@router.post(
    "/{job_role_id}/learning-path",
    response_model=LearningPathResponse,
    summary="Optional LLM-generated learning path",
    responses={503: {"description": "LLM_ENABLED is false — the feature is off"}},
)
def learning_path(job_role_id: int, db: DbSession, user: CurrentUser) -> LearningPathResponse:
    """The one route in the system that may return ``503``.

    Proposal section 4.2: "The core features work without it." Returning a
    distinct status proves the core path is genuinely independent of the LLM
    rather than merely claiming to be. With the flag off — the default, and the
    only configuration used in evaluation — this endpoint is simply unavailable
    and every other endpoint is unaffected.
    """
    settings = get_settings()
    if not settings.llm_enabled:
        raise FeatureDisabledError(
            "The learning-path feature is disabled. It is optional: the skill-gap "
            "report above is complete without it. Set LLM_ENABLED=true to enable it."
        )

    from app.ml.learning_path import build_learning_path

    role, report = recommendation_service.analyse_gap(db, user, job_role_id)
    spec = RoleSpec(
        job_role_id=role.id,
        title=role.title,
        slug=role.slug,
        family=role.family,
        description=role.description,
        required_skills={m.skill_id: m.weight for m in report.matched}
        | {m.skill_id: m.weight for m in report.missing},
    )
    # Credentials are passed in as plain arguments so app/ml stays free of any
    # application-configuration import.
    steps, generated_by = build_learning_path(
        spec,
        report,
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        base_url=settings.llm_base_url,
        timeout=settings.llm_timeout_seconds,
    )
    return LearningPathResponse(
        job_role_id=role.id,
        job_role_title=role.title,
        generated_by=generated_by,
        steps=[LearningPathStep(**step) for step in steps],
    )
