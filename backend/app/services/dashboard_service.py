"""Dashboard aggregates and user feedback.

Every number produced here is a real aggregate. That is the whole point of the
module: the legacy dashboard hard-coded ``totalUsers: "12,847"``,
``successRate: "94%"`` and ``careerPaths: "500+"``, none of which corresponded to
anything.
"""

from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.education import Certification, EducationRecord
from app.models.feedback import Feedback
from app.models.job import JobRole
from app.models.profile import Profile
from app.models.project import Project
from app.models.recommendation import RecommendationResult, RecommendationRun
from app.models.resume import ResumeUpload
from app.models.user import User
from app.models.user_skill import UserSkill
from app.schemas.cv import FeedbackCreate, FeedbackRead
from app.schemas.dashboard import (
    AdminOverview,
    DashboardSummary,
    OnboardingStep,
    ProfileCompleteness,
)

logger = logging.getLogger("app.services.dashboard")

#: Number of fields the completeness score is computed from.
COMPLETENESS_FIELDS = 8


def _count(db: Session, model, *conditions) -> int:
    return int(db.scalar(select(func.count()).select_from(model).where(*conditions)) or 0)


def summary(db: Session, user: User) -> DashboardSummary:
    user_id = user.id
    latest_run = db.scalar(
        select(RecommendationRun)
        .where(RecommendationRun.user_id == user_id)
        .order_by(RecommendationRun.created_at.desc(), RecommendationRun.id.desc())
        .limit(1)
    )
    top_result = None
    if latest_run is not None:
        top_result = db.scalar(
            select(RecommendationResult).where(
                RecommendationResult.run_id == latest_run.id,
                RecommendationResult.rank == 1,
            )
        )

    return DashboardSummary(
        skills_count=_count(db, UserSkill, UserSkill.user_id == user_id),
        projects_count=_count(db, Project, Project.user_id == user_id),
        education_count=_count(db, EducationRecord, EducationRecord.user_id == user_id),
        certifications_count=_count(db, Certification, Certification.user_id == user_id),
        resume_uploads_count=_count(db, ResumeUpload, ResumeUpload.user_id == user_id),
        total_recommendation_runs=_count(
            db, RecommendationRun, RecommendationRun.user_id == user_id
        ),
        latest_run_at=latest_run.created_at if latest_run else None,
        top_role_id=top_result.job_role_id if top_result else None,
        top_role_title=top_result.job_role.title if top_result and top_result.job_role else None,
        top_compatibility_pct=(
            round(float(top_result.compatibility_score) * 100, 1) if top_result else None
        ),
        member_since=user.created_at,
    )


def completeness(db: Session, user: User) -> ProfileCompleteness:
    """A real 0-100 score derived from field presence, plus named next steps.

    Each step is a plain question about the database, so the score cannot drift
    from reality: add a skill and the number moves.
    """
    user_id = user.id
    profile = db.scalar(select(Profile).where(Profile.user_id == user_id))

    has_headline = bool(profile and profile.headline and profile.headline.strip())
    has_goal = bool(profile and profile.career_goal and profile.career_goal.strip())
    has_links = bool(profile and profile.links)
    skills = _count(db, UserSkill, UserSkill.user_id == user_id)
    projects = _count(db, Project, Project.user_id == user_id)
    education = _count(db, EducationRecord, EducationRecord.user_id == user_id)
    uploads = _count(db, ResumeUpload, ResumeUpload.user_id == user_id)
    runs = _count(db, RecommendationRun, RecommendationRun.user_id == user_id)

    steps = [
        OnboardingStep(
            key="profile_headline",
            label="Add a headline",
            completed=has_headline,
            href="/profile",
            hint="One line describing the role you are aiming at.",
        ),
        OnboardingStep(
            key="career_goal",
            label="Describe your career goal",
            completed=has_goal,
            href="/profile",
            hint="Where you want to be in 1-2 years. This feeds your profile text.",
        ),
        OnboardingStep(
            key="skills",
            label="Add at least 5 skills",
            completed=skills >= 5,
            href="/skills",
            hint="Search the taxonomy, or upload a CV and confirm what is detected.",
        ),
        OnboardingStep(
            key="projects",
            label="Add a project",
            completed=projects >= 1,
            href="/projects",
            hint="Projects add real signal to your profile text.",
        ),
        OnboardingStep(
            key="education",
            label="Add your education",
            completed=education >= 1,
            href="/education",
            hint="Degree, field of study, and institution.",
        ),
        OnboardingStep(
            key="links",
            label="Add a portfolio or GitHub link",
            completed=has_links,
            href="/profile",
            hint="Optional, but it rounds out your profile.",
        ),
        OnboardingStep(
            key="cv",
            label="Upload your CV",
            completed=uploads >= 1,
            href="/resume",
            hint="We extract skills from a PDF or DOCX for you to confirm.",
        ),
        OnboardingStep(
            key="recommendations",
            label="Generate recommendations",
            completed=runs >= 1,
            href="/recommendations",
            hint="See your ranked AI/ML roles with an explained score.",
        ),
    ]

    completed = sum(1 for step in steps if step.completed)
    score = int(round(completed / len(steps) * 100))
    next_action = next((step for step in steps if not step.completed), None)

    return ProfileCompleteness(
        score=score,
        completed_fields=completed,
        total_fields=len(steps),
        steps=steps,
        next_action=next_action,
    )


def admin_overview(db: Session) -> AdminOverview:
    """Real aggregates for the admin dashboard — no invented figures."""
    from app.models.skill import Skill, SkillAlias

    families = [
        {"family": family, "count": int(count)}
        for family, count in db.execute(
            select(JobRole.family, func.count(JobRole.id))
            .where(JobRole.is_active.is_(True))
            .group_by(JobRole.family)
            .order_by(func.count(JobRole.id).desc())
        ).all()
    ]

    from app.models.job import JobRoleSkill

    top_skills = [
        {"skill_id": skill_id, "name": name, "category": category, "role_count": int(count)}
        for skill_id, name, category, count in db.execute(
            select(
                Skill.id,
                Skill.name,
                Skill.category,
                func.count(JobRoleSkill.job_role_id),
            )
            .join(JobRoleSkill, JobRoleSkill.skill_id == Skill.id)
            .group_by(Skill.id, Skill.name, Skill.category)
            .order_by(func.count(JobRoleSkill.job_role_id).desc())
            .limit(12)
        ).all()
    ]

    latest_run = db.scalar(select(func.max(RecommendationRun.created_at)))

    return AdminOverview(
        role_count=_count(db, JobRole),
        active_role_count=_count(db, JobRole, JobRole.is_active.is_(True)),
        skill_count=_count(db, Skill),
        alias_count=_count(db, SkillAlias),
        user_count=_count(db, User),
        recommendation_run_count=_count(db, RecommendationRun),
        latest_run_at=latest_run,
        families=families,
        top_skills=top_skills,
    )


# ---------------------------------------------------------------------------
# Feedback
# ---------------------------------------------------------------------------
def create_feedback(db: Session, user: User, payload: FeedbackCreate) -> FeedbackRead:
    """Store feedback. **Auth is required** — it was optional at ``guidance.py:94``
    (finding S4), which let anonymous callers write unattributable rows."""
    row = Feedback(
        user_id=user.id,
        category=payload.category,
        message=payload.message,
        rating=payload.rating,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    logger.info("Stored feedback id=%s from user=%s", row.id, user.id)
    return FeedbackRead.model_validate(row)


def list_feedback(
    db: Session, *, limit: int, offset: int, category: str | None = None
) -> tuple[int, list[FeedbackRead]]:
    """Admin listing. Never selects anything sensitive — the model has no such column."""
    conditions = []
    if category and category.strip():
        conditions.append(Feedback.category == category.strip())

    stmt = select(func.count()).select_from(Feedback)
    query = select(Feedback)
    if conditions:
        stmt = stmt.where(*conditions)
        query = query.where(*conditions)

    total = int(db.scalar(stmt) or 0)
    rows = db.scalars(
        query.order_by(Feedback.created_at.desc(), Feedback.id.desc()).limit(limit).offset(offset)
    ).all()
    return total, [FeedbackRead.model_validate(row) for row in rows]
