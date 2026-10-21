"""Aggregate router.

One place that knows the full API surface, so ``main.py`` has a single import and
adding a domain is a one-line change here.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.routes import (
    admin,
    ai,
    auth,
    certifications,
    cv,
    cv_advisor,
    dashboard,
    education,
    feedback,
    interview,
    job_analysis,
    jobs,
    mentor,
    profile,
    projects,
    recommendations,
    roadmap,
    skill_gap,
    skills,
    work_history,
)

api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(profile.router)
api_router.include_router(skills.router)
api_router.include_router(projects.router)
api_router.include_router(education.router)
api_router.include_router(certifications.router)
# jobs.py mounts two routers on related prefixes: public read and admin write.
api_router.include_router(jobs.public_router)
api_router.include_router(jobs.admin_router)
api_router.include_router(cv.router)
api_router.include_router(recommendations.router)
api_router.include_router(skill_gap.router)
api_router.include_router(work_history.router)
api_router.include_router(dashboard.router)
api_router.include_router(feedback.router)
# The AI layer. Every route here answers 503 when the provider is not
# configured, and none of them is on the path of any core feature.
api_router.include_router(ai.router)
api_router.include_router(mentor.router)
api_router.include_router(roadmap.router)
api_router.include_router(job_analysis.router)
api_router.include_router(cv_advisor.router)
api_router.include_router(interview.router)
api_router.include_router(admin.router)

__all__ = ["api_router"]
