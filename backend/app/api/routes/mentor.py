"""``/api/ai/mentor`` — the conversational career assistant.

Every route here is optional by construction. With no provider configured the
route answers ``503 feature_disabled`` and the rest of the application is
unaffected, which is the same promise the optional learning path has made
since the beginning.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, DbSession, rate_limit
from app.schemas.ai import MentorAnswerRead, MentorAskRequest
from app.services import mentor_service

router = APIRouter(prefix="/ai/mentor", tags=["ai"])


@router.post(
    "/ask",
    response_model=MentorAnswerRead,
    summary="Ask the career assistant a question",
    dependencies=[Depends(rate_limit("ai"))],
    responses={503: {"description": "The AI layer is not configured on this deployment."}},
)
def ask(
    request: MentorAskRequest,
    db: DbSession,
    user: CurrentUser,
) -> MentorAnswerRead:
    """Answer one question, grounded in the user's verified record.

    The conversation window is bounded on the server: only the last few turns
    are sent to the provider, and the whole window is capped, so a long
    conversation cannot grow the request without bound.
    """
    return mentor_service.ask(db, user, request)
