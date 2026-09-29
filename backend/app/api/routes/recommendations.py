"""``/api/recommendations`` — generate a run, list runs, read a stored run."""

from __future__ import annotations

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.pagination import PageParamsDep
from app.schemas.recommendation import (
    RecommendationRequest,
    RecommendationResponse,
    RunDetail,
    RunPageResponse,
)
from app.services import recommendation_service

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post(
    "",
    response_model=RecommendationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a ranked, explainable set of recommendations",
    responses={
        401: {"description": "Authentication required"},
        409: {"description": "Profile has no confirmed skills"},
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
