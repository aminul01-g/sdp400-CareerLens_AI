"""The CV improvement assistant.

============================  ==========================================
Constraint                    Enforcement
============================  ==========================================
No invention                  The prompt carries the CV and the user's
                               stored records, and the rules state plainly
                               that nothing may be added. A claim with no
                               source becomes a question in
                               ``needs_information`` rather than a sentence
                               in a draft
The original stays separate    The response is a list of *suggestions*.
                               The CV itself is never modified, never
                               overwritten, and never written back to the
                               upload
No ATS promise                The disclaimer is part of every response and
                               says what the tool is and is not
============================  ==========================================
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError, UnprocessableError
from app.ml import prompts
from app.models.profile import Profile
from app.models.resume import ResumeUpload
from app.models.user import User
from app.schemas.ai import CvAdviceRead, CvAdviceRequest
from app.schemas.llm import CvAdviceOutput
from app.services import ai_context_service, groq_service

logger = logging.getLogger("app.services.cv_advisor")

#: The shortest CV that can be reviewed at all.
MIN_CV_CHARS = 80


def _load_cv_text(db: Session, user: User, resume_upload_id: int) -> str:
    """The text of one of the user's own uploads.

    Scoped by owner in the query, so somebody else's upload id is a 404 and
    not a peek.
    """
    upload = db.scalar(
        select(ResumeUpload).where(
            ResumeUpload.id == resume_upload_id, ResumeUpload.user_id == user.id
        )
    )
    if upload is None:
        raise NotFoundError("That CV does not exist.")
    return upload.extracted_text or ""


def _resolve_language(db: Session, user: User, requested: str | None) -> str:
    if requested:
        return prompts.normalise_language(requested)
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    if profile is not None:
        return prompts.normalise_language(profile.preferred_language)
    return "en"


def advise(
    db: Session,
    user: User,
    request: CvAdviceRequest,
) -> CvAdviceRead:
    """Suggest how to present a CV more effectively, without inventing anything."""
    groq_service.require_provider()
    cv_text = request.cv_text.strip()
    if request.resume_upload_id is not None:
        cv_text = _load_cv_text(db, user, request.resume_upload_id)
    if len(cv_text) < MIN_CV_CHARS:
        raise UnprocessableError(
            "There is not enough CV text to review. Upload and analyse a CV "
            "first, or paste the full text of one.",
            code="insufficient_cv",
        )

    facts = ai_context_service.build_facts(db, user, job_role_id=request.job_role_id)
    role_requirements = (
        ai_context_service.role_requirements(db, request.job_role_id)
        if request.job_role_id is not None
        else []
    )
    role_title = ""
    if request.job_role_id is not None:
        target = facts.get("target_role")
        if isinstance(target, dict):
            role_title = str(target.get("title", ""))

    language = _resolve_language(db, user, request.language)
    messages = prompts.cv_advice_prompt(
        cv_text=cv_text,
        facts=facts,
        target_role=role_title,
        role_requirements=role_requirements,
        include_cover_letter=request.include_cover_letter,
        language=language,
    )
    advice = groq_service.run_structured(
        messages,
        CvAdviceOutput,
        schema_name="cv_advice",
        reasoning_effort="medium",
        max_completion_tokens=5000,
    )

    return CvAdviceRead(
        generated_by=f"groq:{groq_service.provider_status().get('model', '')}",
        language=language,
        effective_summary=list(advice.effective_summary),
        emphasise=list(advice.emphasise),
        clarity_suggestions=list(advice.clarity_suggestions),
        wording_suggestions=list(advice.wording_suggestions),
        project_suggestions=list(advice.project_suggestions),
        job_specific_recommendations=list(advice.job_specific_recommendations),
        professional_summary=advice.professional_summary,
        bullet_points=list(advice.bullet_points),
        cover_letter=advice.cover_letter,
        needs_information=list(advice.needs_information),
    )
