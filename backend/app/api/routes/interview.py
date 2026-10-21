"""``/api/ai/interviews`` — the mock interview simulator.

A session is a private record: the questions that were asked, the answers that
were given, and the feedback that followed. Every route here is scoped to
its owner in the query, so another user's session id returns ``404``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import CurrentUser, DbSession, rate_limit
from app.schemas.ai import (
    InterviewAnswerRequest,
    InterviewExchangeRead,
    InterviewQuestionRead,
    InterviewSessionRead,
    InterviewSessionSummaryRead,
    InterviewStartRequest,
)
from app.schemas.pagination import Page, PageParamsDep, build_page
from app.services import interview_service

# The rate limit is on the routes that reach the provider. Reading a past
# session, and deleting one, cost nothing.
router = APIRouter(prefix="/ai/interviews", tags=["ai"])


@router.get(
    "",
    response_model=Page[InterviewSessionSummaryRead],
    summary="The user's interview history",
)
def list_sessions(
    db: DbSession,
    user: CurrentUser,
    params: PageParamsDep,
) -> Page[InterviewSessionSummaryRead]:
    """Past sessions, newest first, with the practice score each one averaged."""
    total, summaries = interview_service.list_sessions(
        db, user, limit=params.limit, offset=params.offset
    )
    return build_page(summaries, total, params)


@router.post(
    "",
    response_model=InterviewSessionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Start a mock interview and generate its questions",
    dependencies=[Depends(rate_limit("ai"))],
    responses={
        422: {"description": "No role or description was supplied."},
        503: {"description": "The AI layer is not configured on this deployment."},
    },
)
def start(
    request: InterviewStartRequest,
    db: DbSession,
    user: CurrentUser,
) -> InterviewSessionRead:
    """Prepare an interview for a role or a pasted job description.

    The questions are drawn from the role's requirements and the candidate's
    real experience, so they are answerable rather than generic.
    """
    return interview_service.start(db, user, request)


@router.get(
    "/{session_id}",
    response_model=InterviewSessionRead,
    summary="One interview session with its feedback",
    responses={404: {"description": "No such session, or it belongs to somebody else."}},
)
def get_session(session_id: int, db: DbSession, user: CurrentUser) -> InterviewSessionRead:
    """The session, every exchange, and the feedback given."""
    return interview_service.get_session(db, user, session_id)


@router.post(
    "/{session_id}/answers",
    response_model=InterviewExchangeRead,
    summary="Submit an answer and receive structured feedback",
    dependencies=[Depends(rate_limit("ai"))],
    responses={
        404: {"description": "No such session or question."},
        422: {"description": "The answer is too short to assess."},
        503: {"description": "The AI layer is not configured on this deployment."},
    },
)
def answer(
    session_id: int,
    request: InterviewAnswerRequest,
    db: DbSession,
    user: CurrentUser,
) -> InterviewExchangeRead:
    """Assess one answer against the five-dimension rubric.

    The feedback is saved with the session, so it can be read again later.
    """
    return interview_service.answer(db, user, session_id, request)


@router.post(
    "/{session_id}/next-question",
    response_model=InterviewQuestionRead,
    summary="A follow-up question based on the previous answer",
    dependencies=[Depends(rate_limit("ai"))],
    responses={
        404: {"description": "No such session, or nothing has been answered yet."},
        503: {"description": "The AI layer is not configured on this deployment."},
    },
)
def next_question(
    session_id: int,
    db: DbSession,
    user: CurrentUser,
) -> InterviewQuestionRead:
    """A question that digs into what the candidate actually said."""
    return interview_service.next_question(db, user, session_id)


@router.delete(
    "/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an interview session",
    responses={404: {"description": "No such session, or it belongs to somebody else."}},
)
def delete_session(session_id: int, db: DbSession, user: CurrentUser) -> Response:
    """Remove the session and its exchanges."""
    interview_service.delete_session(db, user, session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
