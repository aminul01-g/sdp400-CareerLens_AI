"""``/api/ai/cv-advice`` — how to present a CV more effectively.

This route *enhances* the existing CV analysis. It never modifies an upload,
never changes a detected skill, and never writes a suggestion back to the
CV. The response is a separate list of suggestions the user reviews and
accepts or rejects themselves.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, DbSession, rate_limit
from app.schemas.ai import CvAdviceRead, CvAdviceRequest
from app.services import cv_advisor_service

router = APIRouter(prefix="/ai/cv-advice", tags=["ai"])


@router.post(
    "",
    response_model=CvAdviceRead,
    summary="Suggest how to present a CV more effectively",
    dependencies=[Depends(rate_limit("ai"))],
    responses={
        404: {"description": "No such CV, or it belongs to somebody else."},
        422: {"description": "There is not enough CV text to review."},
        503: {"description": "The AI layer is not configured on this deployment."},
    },
)
def advise(
    request: CvAdviceRequest,
    db: DbSession,
    user: CurrentUser,
) -> CvAdviceRead:
    """Review an analysed CV and suggest clearer, more effective wording.

    The suggestions are built only from what the CV and the profile already
    say. Where something is missing, it is asked for in ``needs_information``
    rather than invented in a draft.
    """
    return cv_advisor_service.advise(db, user, request)
