"""The verified fact block the AI layer is allowed to see.

============================  ==========================================
Constraint                    Enforcement
============================  ==========================================
Every fact is engine-produced  This module reads the database and the
                               engine's own outputs. Nothing here is
                               generated, guessed or inferred by a model
Only confirmed skills         ``user_skill`` rows with ``confirmed=True``.
                               A CV extraction that has not been confirmed
                               is a proposal, and a proposal is not a fact
Scored, never recomputed      The compatibility score and the coverage come
                               from the stored run or from
                               :func:`app.services.recommendation_service.analyse_gap`.
                               This module reads them; it never calculates
                               a different one
============================  ==========================================

The result is a plain dictionary that is serialised into the prompt. It is
deliberately *not* a Pydantic model: this is the boundary where verified
application data stops being application data and becomes text for a model,
and it should be obvious from the shape that nothing here was invented.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.ml.types import GapReport, RoleSpec
from app.models.education import Certification, EducationRecord
from app.models.job import JobRole, JobRoleSkill
from app.models.profile import Profile
from app.models.project import Project
from app.models.recommendation import RecommendationResult, RecommendationRun
from app.models.skill import Skill
from app.models.user import User
from app.models.user_skill import UserSkill
from app.models.work_history import WorkHistory
from app.services import recommendation_service

#: How many recommended roles are shown to the model. Five is enough to
#: explain a ranking without turning the prompt into the whole shortlist.
MAX_RECOMMENDED_ROLES = 5

#: How many skills are listed. The full set is usually long, and the model's
#: attention is better spent on the skills that matter for the question.
MAX_SKILLS = 40

#: How many projects are listed.
MAX_PROJECTS = 15


def _confirmed_skills(db: Session, user: User) -> list[UserSkill]:
    return list(
        db.scalars(
            select(UserSkill)
            .options(selectinload(UserSkill.skill))
            .where(UserSkill.user_id == user.id, UserSkill.confirmed.is_(True))
            .order_by(UserSkill.skill_id)
        ).all()
    )


def profile_facts(db: Session, user: User) -> dict[str, Any]:
    """The user's own record, as they wrote it."""
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    if profile is None:
        return {"headline": "", "career_goal": "", "bio": "", "education_level": "",
                "years_experience": None, "seniority": "", "industry": "",
                "preferred_role_family": "", "links": {}}
    return {
        "headline": profile.headline or "",
        "career_goal": profile.career_goal or "",
        "bio": profile.bio or "",
        "education_level": profile.education_level or "",
        "years_experience": profile.years_experience,
        "seniority": profile.seniority or "",
        "industry": profile.industry or "",
        "preferred_role_family": profile.preferred_role_family or "",
        "links": dict(profile.links or {}),
    }


def skill_facts(db: Session, user: User) -> list[dict[str, Any]]:
    """The user's confirmed skills."""
    rows = _confirmed_skills(db, user)
    facts: list[dict[str, Any]] = []
    for row in rows[:MAX_SKILLS]:
        skill = row.skill
        if skill is None:
            continue
        facts.append(
            {
                "name": skill.name,
                "slug": skill.slug,
                "category": skill.category,
                "proficiency": row.proficiency,
                "years_used": float(row.years_used) if row.years_used is not None else None,
                "last_used_at": row.last_used_at.isoformat() if row.last_used_at else None,
            }
        )
    return facts


def project_facts(db: Session, user: User) -> list[dict[str, Any]]:
    """The user's projects."""
    rows = list(
        db.scalars(
            select(Project)
            .where(Project.user_id == user.id)
            .order_by(Project.start_date.desc().nullslast(), Project.id.desc())
            .limit(MAX_PROJECTS)
        ).all()
    )
    return [
        {
            "title": row.title,
            "description": row.description or "",
            "tech_stack": list(row.tech_stack or []),
            "role": row.role or "",
            "repo_url": row.repo_url or "",
        }
        for row in rows
    ]


def education_facts(db: Session, user: User) -> list[dict[str, Any]]:
    """The user's education."""
    rows = list(
        db.scalars(
            select(EducationRecord)
            .where(EducationRecord.user_id == user.id)
            .order_by(EducationRecord.end_year.desc().nullslast(), EducationRecord.id)
        ).all()
    )
    return [
        {
            "institution": row.institution,
            "degree": row.degree or "",
            "field_of_study": row.field_of_study or "",
            "start_year": row.start_year,
            "end_year": row.end_year,
            "grade": row.grade or "",
        }
        for row in rows
    ]


def certification_facts(db: Session, user: User) -> list[dict[str, Any]]:
    """The user's certifications."""
    rows = list(
        db.scalars(
            select(Certification)
            .where(Certification.user_id == user.id)
            .order_by(Certification.issued_on.desc().nullslast(), Certification.id)
        ).all()
    )
    return [
        {
            "name": row.name,
            "issuer": row.issuer or "",
            "issued_on": row.issued_on.isoformat() if row.issued_on else None,
        }
        for row in rows
    ]


def work_history_facts(db: Session, user: User) -> list[dict[str, Any]]:
    """The user's confirmed work history.

    Only confirmed rows. A CV-extracted row is a proposal the user has not
    agreed to, and the model is not the right place to turn a proposal into a
    fact.
    """
    rows = list(
        db.scalars(
            select(WorkHistory)
            .where(WorkHistory.user_id == user.id, WorkHistory.confirmed.is_(True))
            .order_by(WorkHistory.start_date.desc().nullslast(), WorkHistory.id)
        ).all()
    )
    return [
        {
            "employer": row.employer,
            "title": row.title or "",
            "start_date": row.start_date.isoformat() if row.start_date else None,
            "end_date": row.end_date.isoformat() if row.end_date else None,
            "current": row.end_date is None,
        }
        for row in rows
    ]


def recommendation_facts(db: Session, user: User) -> list[dict[str, Any]]:
    """The user's most recent shortlist, with the engine's own numbers.

    Read from the stored run, never recomputed: a stored run is history, and
    history does not change when the knowledge base does.
    """
    run = db.scalar(
        select(RecommendationRun)
        .where(RecommendationRun.user_id == user.id)
        .order_by(RecommendationRun.created_at.desc(), RecommendationRun.id.desc())
        .limit(1)
    )
    if run is None:
        return []
    results = list(
        db.scalars(
            select(RecommendationResult)
            .options(selectinload(RecommendationResult.job_role))
            .where(RecommendationResult.run_id == run.id)
            .order_by(RecommendationResult.rank)
            .limit(MAX_RECOMMENDED_ROLES)
        ).all()
    )
    facts: list[dict[str, Any]] = []
    for result in results:
        role = result.job_role
        facts.append(
            {
                "rank": result.rank,
                "title": role.title if role else "",
                "family": role.family if role else "",
                "seniority": role.seniority if role else "",
                # The engine's score, quoted verbatim. The model may explain
                # it; it may not restate it differently.
                "compatibility_score": float(result.compatibility_score),
                "skill_coverage": float(result.skill_coverage),
                "tfidf_similarity": float(result.tfidf_similarity),
                "level_fit": float(result.level_fit),
            }
        )
    return facts


def build_facts(
    db: Session,
    user: User,
    *,
    job_role_id: int | None = None,
) -> dict[str, Any]:
    """Everything the model is told about the user.

    ``job_role_id`` adds the gap report for one role, which is what makes
    "which skill should I learn first?" answerable from verified data rather
    than from the model's opinion.
    """
    facts: dict[str, Any] = {
        "profile": profile_facts(db, user),
        "skills": skill_facts(db, user),
        "projects": project_facts(db, user),
        "education": education_facts(db, user),
        "certifications": certification_facts(db, user),
        "work_history": work_history_facts(db, user),
        "recommendations": recommendation_facts(db, user),
    }

    if job_role_id is not None:
        facts["target_role"] = role_facts(db, user, job_role_id)
    return facts


def role_facts(db: Session, user: User, job_role_id: int) -> dict[str, Any]:
    """The engine's reading of one role, for this user.

    The coverage and the missing skills come from
    :func:`app.services.recommendation_service.analyse_gap`, which reads
    confirmed skills only and applies the same recency, depth and level-fit
    adjustments the ranker uses.
    """
    role, report = recommendation_service.analyse_gap(db, user, job_role_id)
    return {
        "job_role_id": role.id,
        "title": role.title,
        "family": role.family,
        "seniority": role.seniority,
        "description": role.description or "",
        "coverage": round(report.coverage, 4),
        "coverage_pct": round(report.coverage * 100, 1),
        "matched": [
            {
                "name": item.name,
                "weight": round(item.weight, 4),
                "proficiency": item.proficiency,
                "contribution": round(item.contribution, 4),
            }
            for item in report.matched
        ],
        "missing": [
            {
                "name": item.name,
                "weight": round(item.weight, 4),
                "tier": item.tier,
            }
            for item in report.missing
        ],
    }


def gap_report(
    db: Session, user: User, job_role_id: int
) -> tuple[JobRole, RoleSpec, GapReport]:
    """The raw gap report, for code that needs the engine's own types."""
    role, report = recommendation_service.analyse_gap(db, user, job_role_id)
    requirements = {
        requirement.skill_id: float(requirement.weight)
        for requirement in role.skill_requirements
    }
    spec = RoleSpec(
        job_role_id=role.id,
        title=role.title,
        slug=role.slug,
        family=role.family,
        description=role.description or "",
        required_skills=requirements,
    )
    return role, spec, report


def role_requirements(db: Session, job_role_id: int) -> list[dict[str, Any]]:
    """A role's weighted requirements, as the knowledge base holds them."""
    role = db.scalar(
        select(JobRole)
        .options(selectinload(JobRole.skill_requirements).selectinload(JobRoleSkill.skill))
        .where(JobRole.id == job_role_id)
    )
    if role is None:
        return []
    requirements: list[dict[str, Any]] = []
    for requirement in role.skill_requirements:
        if requirement.skill is None:
            continue
        requirements.append(
            {
                "skill_id": requirement.skill_id,
                "name": requirement.skill.name,
                "slug": requirement.skill.slug,
                "weight": float(requirement.weight),
            }
        )
    requirements.sort(key=lambda item: (-item["weight"], item["skill_id"]))
    return requirements


def user_skill_names(db: Session, user: User) -> dict[int, str]:
    """``skill_id -> canonical name`` for the user's confirmed skills."""
    return {
        row.skill_id: row.skill.name
        for row in _confirmed_skills(db, user)
        if row.skill is not None
    }


def taxonomy_skill_ids(db: Session) -> dict[str, int]:
    """``slug -> id`` for every skill in the taxonomy."""
    rows = db.execute(select(Skill.slug, Skill.id)).all()
    return {str(slug): int(skill_id) for slug, skill_id in rows}
