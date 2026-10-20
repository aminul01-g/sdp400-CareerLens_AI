"""The DB <-> ML bridge.

**This is the only module in the project that imports both SQLAlchemy and
``app.ml``.** Everything else speaks exactly one dialect:

* ``app/ml/*`` takes and returns dataclasses and never touches a database, which
  is what makes it unit-testable without one, runnable as
  ``python -m app.ml.evaluation`` with no HTTP server, and replaceable without
  touching a route.
* ``app/services/*`` other than this one never import ``app.ml``.

The request lifecycle is exactly: load the user's data, load the candidate roles,
build a ``ProfileSnapshot``, call the pure ranker, persist the run, return.
Database access happens only in steps 1-2 and 5; step 4 is pure computation.
"""

from __future__ import annotations

import logging
import time
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import get_settings
from app.core.exceptions import ConflictError, NotFoundError
from app.ml.gap_analysis import analyse
from app.ml.ranker import rank
from app.ml.signals import level_fit as compute_level_fit
from app.ml.signals import normalise_band, signal_factor, user_level_band
from app.ml.text_profile import build_profile_text
from app.ml.types import (
    CertificationFact,
    EducationFact,
    ProfileSnapshot,
    ProjectFact,
    RoleSpec,
    UserSkillFact,
    proficiency_factor,
)
from app.models.education import Certification, EducationRecord
from app.models.job import JobRole, JobRoleSkill
from app.models.profile import Profile
from app.models.project import Project
from app.models.recommendation import RecommendationResult, RecommendationRun
from app.models.skill import Skill
from app.models.user import User
from app.models.user_skill import UserSkill
from app.schemas.recommendation import (
    RecommendationResponse,
    RecommendationWeights,
    RoleRecommendation,
    RunDetail,
    RunSummary,
    SkillContribution,
)
from app.services import feedback_service, work_history_service

logger = logging.getLogger("app.services.recommendations")

#: A profile with no confirmed skills cannot produce a meaningful ranking, and
#: returning 60 rows of 0% is worse than one actionable error.
MIN_SKILLS_FOR_RECOMMENDATION = 1


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def _load_user_snapshot(db: Session, user: User) -> ProfileSnapshot:
    """Everything the engine may know about the user, in one query set."""
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))

    skill_rows = db.execute(
        select(UserSkill, Skill)
        .join(Skill, Skill.id == UserSkill.skill_id)
        .where(UserSkill.user_id == user.id, UserSkill.confirmed.is_(True))
        .order_by(Skill.name)
    ).all()

    projects = db.scalars(
        select(Project).where(Project.user_id == user.id).order_by(Project.created_at.desc())
    ).all()
    education = db.scalars(
        select(EducationRecord).where(EducationRecord.user_id == user.id)
    ).all()
    certifications = db.scalars(
        select(Certification).where(Certification.user_id == user.id)
    ).all()

    # The experience signal. A declared figure wins; otherwise the work
    # history the user has confirmed is used. "None" and "0" are different
    # answers, and only one of them should override a declared figure.
    declared_years = profile.years_experience if profile else None
    if declared_years is None:
        observed_years = work_history_service.observed_years(db, user)
    else:
        observed_years = None

    snapshot = ProfileSnapshot(
        user_id=user.id,
        headline=profile.headline or "" if profile else "",
        career_goal=profile.career_goal or "" if profile else "",
        bio=profile.bio or "" if profile else "",
        preferred_role_family=profile.preferred_role_family or "" if profile else "",
        # The context signals. All optional, all neutral when absent.
        years_experience=declared_years if declared_years is not None else observed_years,
        seniority=profile.seniority or "" if profile else "",
        industry=profile.industry or "" if profile else "",
        location=profile.location or "" if profile else "",
        skills=tuple(
            UserSkillFact(
                skill_id=row.skill_id,
                proficiency=row.proficiency,
                name=skill.name,
                slug=skill.slug,
                years_used=float(row.years_used) if row.years_used is not None else None,
                last_used_at=row.last_used_at,
            )
            for row, skill in skill_rows
        ),
        projects=tuple(
            ProjectFact(
                title=p.title,
                description=p.description,
                tech_stack=tuple(p.tech_stack or ()),
            )
            for p in projects
        ),
        education=tuple(
            EducationFact(
                institution=e.institution,
                degree=e.degree,
                field_of_study=e.field_of_study or "",
            )
            for e in education
        ),
        certifications=tuple(
            CertificationFact(name=c.name, issuer=c.issuer) for c in certifications
        ),
    )
    from dataclasses import replace

    return replace(snapshot, profile_text=build_profile_text(snapshot))


def _load_role_specs(
    db: Session, *, role_family: str | None = None
) -> tuple[list[RoleSpec], dict[int, str], dict[int, tuple[str, str]]]:
    """Active roles with their weighted requirements, plus display metadata."""
    stmt = (
        select(JobRole)
        .options(selectinload(JobRole.skill_requirements).selectinload(JobRoleSkill.skill))
        .where(JobRole.is_active.is_(True))
    )
    if role_family and role_family.strip():
        stmt = stmt.where(JobRole.family == role_family.strip())
    roles = list(db.scalars(stmt.order_by(JobRole.id)).all())

    specs: list[RoleSpec] = []
    seniorities: dict[int, str] = {}
    skill_names: dict[int, tuple[str, str]] = {}

    for role in roles:
        required = {
            requirement.skill_id: float(requirement.weight)
            for requirement in role.skill_requirements
        }
        specs.append(
            RoleSpec(
                job_role_id=role.id,
                title=role.title,
                slug=role.slug,
                family=role.family,
                description=role.description,
                required_skills=required,
            )
        )
        seniorities[role.id] = role.seniority or ""
        for requirement in role.skill_requirements:
            if requirement.skill is not None:
                skill_names[requirement.skill_id] = (
                    requirement.skill.name,
                    requirement.skill.category,
                )
    return specs, seniorities, skill_names


# ---------------------------------------------------------------------------
# Generation
# ---------------------------------------------------------------------------
def generate(
    db: Session,
    user: User,
    *,
    limit: int = 10,
    role_family: str | None = None,
    min_score: float | None = None,
) -> RecommendationResponse:
    """Run the engine, persist the run, and return the explainable response."""
    started = time.perf_counter()
    settings = get_settings()

    snapshot = _load_user_snapshot(db, user)
    if len(snapshot.skills) < MIN_SKILLS_FOR_RECOMMENDATION:
        raise ConflictError(
            "Add at least one skill before generating recommendations. "
            "You can search the taxonomy or upload your CV for suggestions.",
            code="profile_incomplete",
        )

    specs, seniorities, skill_names = _load_role_specs(db, role_family=role_family)
    if not specs:
        raise NotFoundError(
            "No active job roles are available. Ask an administrator to add the knowledge base."
        )

    # The community prior. Computed here, in the service layer, so that the
    # engine stays a pure function of plain values.
    priors = feedback_service.compute_priors(db)
    prior_by_role = feedback_service.prior_values(priors)
    samples_by_role = feedback_service.prior_samples(priors)

    scored = rank(
        snapshot,
        specs,
        coverage_weight=settings.skill_coverage_weight,
        tfidf_weight=settings.tfidf_weight,
        top_n=None,  # persist everything, so the run is complete
        skill_names=skill_names,
        role_seniorities=seniorities,
        # The reference date for the recency signal. Supplied here rather than
        # read inside the engine, so the engine stays a pure function.
        today=date.today(),
        # The community signal, bounded and evidence-gated. See
        # app/services/feedback_service.py.
        role_priors=prior_by_role,
        prior_strength=settings.feedback_prior_strength,
    )

    if min_score is not None:
        scored = [s for s in scored if s.compatibility >= min_score]

    duration_ms = int((time.perf_counter() - started) * 1000)

    run = RecommendationRun(
        user_id=user.id,
        profile_snapshot={
            "skills": [
                {"skill_id": s.skill_id, "name": s.name, "proficiency": s.proficiency}
                for s in snapshot.skills
            ],
            "projects": [
                {"title": p.title, "tech_stack": list(p.tech_stack)} for p in snapshot.projects
            ],
            "education": [
                {"institution": e.institution, "degree": e.degree} for e in snapshot.education
            ],
            "certifications": [c.name for c in snapshot.certifications],
            "skill_count": len(snapshot.skills),
        },
        coverage_weight=Decimal(str(settings.skill_coverage_weight)),
        tfidf_weight=Decimal(str(settings.tfidf_weight)),
        engine_version=settings.engine_version,
        candidate_count=len(scored),
        duration_ms=duration_ms,
    )
    db.add(run)
    db.flush()

    db.add_all(
        [
            RecommendationResult(
                run_id=run.id,
                job_role_id=score.job_role_id,
                rank=score.rank,
                compatibility_score=Decimal(str(round(score.compatibility, 6))),
                skill_coverage=Decimal(str(round(score.skill_coverage, 6))),
                tfidf_similarity=Decimal(str(round(score.tfidf_similarity, 6))),
                declared_coverage=Decimal(str(round(score.declared_coverage, 6))),
                signal_coverage=Decimal(str(round(score.signal_coverage, 6))),
                level_fit=Decimal(str(round(score.level_fit, 4))),
                role_prior=Decimal(str(round(score.role_prior, 4))),
                feedback_samples=samples_by_role.get(score.job_role_id, 0),
                matched_skill_ids=[m.skill_id for m in score.matched],
                missing_skill_ids=[m.skill_id for m in score.missing],
            )
            for score in scored
        ]
    )
    db.commit()
    db.refresh(run)

    logger.info(
        "Generated recommendation run id=%s for user=%s candidates=%s duration=%sms",
        run.id,
        user.id,
        len(scored),
        duration_ms,
    )

    return RecommendationResponse(
        run_id=run.id,
        engine_version=settings.engine_version,
        weights=RecommendationWeights(
            skill_coverage=settings.skill_coverage_weight,
            tfidf_similarity=settings.tfidf_weight,
        ),
        generated_at=run.created_at,
        total_candidates=len(scored),
        results=[
            _to_recommendation(score, settings, samples_by_role)
            for score in scored[:limit]
        ],
    )


def _to_recommendation(score, settings, samples_by_role: dict[int, int]) -> RoleRecommendation:
    return RoleRecommendation(
        rank=score.rank,
        job_role_id=score.job_role_id,
        title=score.title,
        slug=score.slug,
        family=score.family,
        seniority=score.seniority or None,
        compatibility_pct=score.compatibility_pct,
        skill_coverage=round(score.skill_coverage, 6),
        tfidf_similarity=round(score.tfidf_similarity, 6),
        matched_skills=[
            SkillContribution(
                skill_id=m.skill_id,
                name=m.name,
                weight=round(m.weight, 4),
                proficiency=m.proficiency,
                category=m.category or None,
                contribution=round(m.contribution, 6),
            )
            for m in score.matched
        ],
        missing_skills=[
            SkillContribution(
                skill_id=m.skill_id,
                name=m.name,
                weight=round(m.weight, 4),
                proficiency=None,
                category=m.category or None,
                contribution=0.0,
            )
            for m in score.missing
        ],
        coverage_contribution=round(
            settings.skill_coverage_weight * score.skill_coverage, 6
        ),
        tfidf_contribution=round(settings.tfidf_weight * score.tfidf_similarity, 6),
        declared_coverage=round(score.declared_coverage, 6),
        signal_coverage=round(score.signal_coverage, 6),
        level_fit=round(score.level_fit, 4),
        role_prior=round(score.role_prior, 4),
        feedback_samples=samples_by_role.get(score.job_role_id, 0),
    )


# ---------------------------------------------------------------------------
# Reading stored runs
# ---------------------------------------------------------------------------
def list_runs(db: Session, user: User, *, limit: int, offset: int) -> tuple[int, list[RunSummary]]:
    from sqlalchemy import func

    total = int(
        db.scalar(
            select(func.count())
            .select_from(RecommendationRun)
            .where(RecommendationRun.user_id == user.id)
        )
        or 0
    )
    runs = list(
        db.scalars(
            select(RecommendationRun)
            .where(RecommendationRun.user_id == user.id)
            .order_by(RecommendationRun.created_at.desc(), RecommendationRun.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )
    return total, [_run_summary(db, run) for run in runs]


def _run_summary(db: Session, run: RecommendationRun) -> RunSummary:
    top = db.scalar(
        select(RecommendationResult)
        .where(RecommendationResult.run_id == run.id, RecommendationResult.rank == 1)
    )
    return RunSummary(
        id=run.id,
        created_at=run.created_at,
        engine_version=run.engine_version,
        total_candidates=run.candidate_count,
        top_role_id=top.job_role_id if top else None,
        top_role_title=top.job_role.title if top else None,
        top_compatibility=float(top.compatibility_score) if top else None,
        coverage_weight=float(run.coverage_weight),
        tfidf_weight=float(run.tfidf_weight),
    )


def get_run(db: Session, user: User, run_id: int) -> RunDetail:
    """Read a **persisted** run. Never recompute.

    Recomputing would silently change the numbers if the knowledge base was edited
    between the run and the page view, which would make stored history a fiction.
    """
    run = db.scalar(
        select(RecommendationRun).where(
            RecommendationRun.id == run_id, RecommendationRun.user_id == user.id
        )
    )
    if run is None:
        raise NotFoundError("That recommendation run does not exist.")

    results = list(
        db.scalars(
            select(RecommendationResult)
            .where(RecommendationResult.run_id == run.id)
            .order_by(RecommendationResult.rank)
        ).all()
    )
    skill_ids = {sid for r in results for sid in (r.matched_skill_ids or []) + (r.missing_skill_ids or [])}
    names = _skill_names(db, list(skill_ids))
    role_ids = [r.job_role_id for r in results]
    weights_by_skill = _role_weights(db, role_ids)

    return RunDetail(
        id=run.id,
        created_at=run.created_at,
        engine_version=run.engine_version,
        weights=RecommendationWeights(
            skill_coverage=float(run.coverage_weight),
            tfidf_similarity=float(run.tfidf_weight),
        ),
        total_candidates=run.candidate_count,
        duration_ms=run.duration_ms,
        profile_snapshot=run.profile_snapshot or {},
        results=[
            _stored_to_recommendation(
                r,
                names,
                weights_by_skill.get(r.job_role_id, {}),
                float(run.coverage_weight),
                float(run.tfidf_weight),
            )
            for r in results
        ],
    )


def _role_weights(db: Session, role_ids: list[int]) -> dict[int, dict[int, float]]:
    """``role_id -> {skill_id: weight}``, used to annotate stored explanations."""
    if not role_ids:
        return {}
    rows = db.execute(
        select(JobRoleSkill.job_role_id, JobRoleSkill.skill_id, JobRoleSkill.weight).where(
            JobRoleSkill.job_role_id.in_(role_ids)
        )
    ).all()
    grouped: dict[int, dict[int, float]] = {}
    for role_id, skill_id, weight in rows:
        grouped.setdefault(role_id, {})[skill_id] = float(weight)
    return grouped


def _skill_names(db: Session, ids: list[int]) -> dict[int, tuple[str, str]]:
    if not ids:
        return {}
    return {
        s.id: (s.name, s.category) for s in db.scalars(select(Skill).where(Skill.id.in_(ids))).all()
    }


def _stored_to_recommendation(
    result: RecommendationResult,
    names: dict[int, tuple[str, str]],
    weights_by_skill: dict[int, float],
    coverage_weight: float,
    tfidf_weight: float,
) -> RoleRecommendation:
    """Render a persisted result.

    Per-skill weights are re-read from ``job_role_skill`` rather than stored on
    the result row. That is deliberate: the run stores *which* skills were matched
    and missed, and the weight is a property of the role, so an admin correcting a
    weight corrects the displayed explanation for every stored run at once. The
    *scores* stay frozen, which is what the evaluation report depends on.
    """
    coverage = float(result.skill_coverage)
    cosine = float(result.tfidf_similarity)

    def contribution(skill_id: int) -> SkillContribution:
        name, category = names.get(skill_id, (f"Skill {skill_id}", ""))
        return SkillContribution(
            skill_id=skill_id,
            name=name,
            category=category or None,
            weight=round(weights_by_skill.get(skill_id, 0.0), 4),
            contribution=0.0,
        )

    return RoleRecommendation(
        rank=result.rank,
        job_role_id=result.job_role_id,
        title=result.job_role.title if result.job_role else "",
        slug=result.job_role.slug if result.job_role else "",
        family=result.job_role.family if result.job_role else "",
        seniority=result.job_role.seniority if result.job_role else None,
        compatibility_pct=round(float(result.compatibility_score) * 100, 1),
        skill_coverage=coverage,
        tfidf_similarity=cosine,
        matched_skills=[contribution(sid) for sid in (result.matched_skill_ids or [])],
        missing_skills=[contribution(sid) for sid in (result.missing_skill_ids or [])],
        coverage_contribution=round(coverage_weight * coverage, 6),
        tfidf_contribution=round(tfidf_weight * cosine, 6),
        declared_coverage=round(float(result.declared_coverage), 6),
        signal_coverage=round(float(result.signal_coverage), 6),
        level_fit=round(float(result.level_fit), 4),
        role_prior=round(float(result.role_prior), 4),
        feedback_samples=int(result.feedback_samples or 0),
    )


# ---------------------------------------------------------------------------
# Skill gap
# ---------------------------------------------------------------------------
def analyse_gap(db: Session, user: User, job_role_id: int) -> Any:
    """``required - present`` for one target role, read from ``user_skill`` only."""
    role = db.scalar(
        select(JobRole)
        .options(selectinload(JobRole.skill_requirements).selectinload(JobRoleSkill.skill))
        .where(JobRole.id == job_role_id)
    )
    if role is None:
        raise NotFoundError("That job role does not exist.")

    requirements = {
        requirement.skill_id: float(requirement.weight)
        for requirement in role.skill_requirements
    }
    spec = RoleSpec(
        job_role_id=role.id,
        title=role.title,
        slug=role.slug,
        family=role.family,
        description=role.description,
        required_skills=requirements,
    )
    skill_names = {
        requirement.skill_id: (requirement.skill.name, requirement.skill.category)
        for requirement in role.skill_requirements
        if requirement.skill is not None
    }

    # Confirmed skills only. An unconfirmed CV extraction can therefore neither
    # appear as matched nor suppress a genuine gap.
    rows = db.scalars(
        select(UserSkill).where(
            UserSkill.user_id == user.id, UserSkill.confirmed.is_(True)
        )
    ).all()
    user_skills = {row.skill_id: row.proficiency for row in rows}

    # The same strengths the ranker would use, so the gap report and the
    # shortlist agree on what the user actually meets.
    today = date.today()
    factors = {
        row.skill_id: proficiency_factor(row.proficiency)
        * signal_factor(
            float(row.years_used) if row.years_used is not None else None,
            row.last_used_at,
            today,
        )
        for row in rows
    }

    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    user_band = user_level_band(
        profile.seniority if profile else None,
        profile.years_experience if profile else None,
    )
    fit = compute_level_fit(user_band, normalise_band(role.seniority))

    report = analyse(user_skills, spec, skill_names=skill_names, factors=factors, level_fit=fit)
    return role, report
