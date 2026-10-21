"""``/api/ai/job-analysis`` — reading a job description.

The route is a thin shell. The extraction, the normalisation and the coverage
calculation all live in the service, because each of them has a rule that
must not vary with the caller: the score is the application's, the skill
names are the taxonomy's, and the difference between "you do not have this"
and "you have not written this down" is not the model's to blur.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, DbSession, rate_limit
from app.schemas.ai import JobAnalysisRead, JobAnalysisRequest
from app.services import job_analysis_service

router = APIRouter(prefix="/ai/job-analysis", tags=["ai"])


@router.post(
    "",
    response_model=JobAnalysisRead,
    summary="Analyse a job description against the user's profile",
    dependencies=[Depends(rate_limit("ai"))],
    responses={
        422: {"description": "The description does not contain enough to analyse."},
        503: {"description": "The AI layer is not configured on this deployment."},
    },
)
def analyse(
    request: JobAnalysisRequest,
    db: DbSession,
    user: CurrentUser,
) -> JobAnalysisRead:
    """Extract the requirements, normalise them, and compare them with the profile.

    A pasted description too short to analyse is refused with a clear
    explanation rather than a thin, confident-looking answer.
    """
    return job_analysis_service.analyse(db, user, request)
