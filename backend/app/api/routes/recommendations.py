"""``/api/recommendations`` — generate a run, list runs, read a stored run."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, DbSession, rate_limit
from app.schemas.feedback import FeedbackActionRead, FeedbackActionRequest
from app.schemas.pagination import PageParamsDep
from app.schemas.recommendation import (
    RecommendationRequest,
    RecommendationResponse,
    RunDetail,
    RunPageResponse,
)
from app.services import feedback_service, recommendation_service

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post(
    "",
    response_model=RecommendationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a ranked, explainable set of recommendations",
    dependencies=[Depends(rate_limit("generate"))],
    responses={
        401: {"description": "Authentication required"},
        409: {"description": "Profile has no confirmed skills"},
        429: {"description": "Too many generations from this address"},
    },
)
def generate(
    payload: RecommendationRequest, db: DbSession, user: CurrentUser
) -> RecommendationResponse:
    """Runs the deterministic engine and persists the run.

    Triggered by a button rather than on page load, so opening the page never
    burns a computation or a run-history row.

    ``409 profile_incomplete`` at zero confirmed skills is deliberate: a list of
    sixty 0 % roles is less useful than "add some skills first".
    """
    return recommendation_service.generate(
        db,
        user,
        limit=payload.limit,
        role_family=payload.role_family,
        min_score=payload.min_score,
    )


@router.get("/runs", response_model=RunPageResponse, summary="The caller's run history")
def list_runs(params: PageParamsDep, db: DbSession, user: CurrentUser) -> RunPageResponse:
    total, items = recommendation_service.list_runs(
        db, user, limit=params.limit, offset=params.offset
    )
    return RunPageResponse(total=total, page=params.page, page_size=params.page_size, items=items)


@router.get(
    "/runs/{run_id}",
    response_model=RunDetail,
    summary="A persisted run, read from the database",
    responses={404: {"description": "Does not exist, or belongs to another user"}},
)
def get_run(run_id: int, db: DbSession, user: CurrentUser) -> RunDetail:
    """Read-only, and never recomputed — a stored run is a historical record."""
    return recommendation_service.get_run(db, user, run_id)


@router.post(
    "/runs/{run_id}/roles/{job_role_id}/feedback",
    response_model=FeedbackActionRead,
    status_code=status.HTTP_201_CREATED,
    summary="Record what the user did with a recommended role",
    responses={
        401: {"description": "Authentication required"},
        404: {"description": "No such run, or the role was not in it"},
    },
)
def record_feedback(
    run_id: int,
    job_role_id: int,
    payload: FeedbackActionRequest,
    db: DbSession,
    user: CurrentUser,
) -> FeedbackActionRead:
    """Say whether a role is worth keeping.

    Idempotent: marking the same role again **updates** the record rather than
    adding a second one, so a single user cannot vote twice and a change of
    mind is recorded as a change of mind.

    The aggregate of everybody's answers nudges future rankings by at most
    10%, and only once a role has enough observations to be worth acting on.
    See ``app/services/feedback_service.py``.
    """
    row = feedback_service.record_action(
        db, user, run_id, job_role_id, payload.action
    )
    return FeedbackActionRead(
        job_role_id=row.job_role_id,
        action=row.action,
        created_at=row.created_at,
    )


@router.get(
    "/runs/{run_id}/feedback",
    summary="What the caller said about the roles in a run",
)
def list_feedback(
    run_id: int, db: DbSession, user: CurrentUser
) -> dict[int, str]:
    """``job_role_id -> action`` for one of the caller's runs."""
    return feedback_service.list_user_actions(db, user, run_id)
