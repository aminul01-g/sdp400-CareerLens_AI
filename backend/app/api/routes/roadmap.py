"""``/api/ai/roadmaps`` — learning plans the user can keep and work through.

A generated plan is saved, not returned and forgotten. The learner marks
tasks complete, writes notes, attaches the link to what they built, and comes
back to it. Everything under this prefix is scoped to its owner: another
user's plan id returns ``404``, not ``403``.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import CurrentUser, DbSession, rate_limit
from app.schemas.ai import (
    RoadmapGenerateRequest,
    RoadmapRead,
    RoadmapSummaryRead,
    RoadmapTaskRead,
    RoadmapTaskUpdate,
)
from app.schemas.pagination import Page, PageParamsDep, build_page
from app.services import roadmap_service

# The rate limit is on the *generation* route only. Reading a saved plan,
# ticking a task off and writing a note cost nothing, and a learner coming
# back to their plan should never be told to wait.
router = APIRouter(prefix="/ai/roadmaps", tags=["ai"])


@router.get(
    "",
    response_model=Page[RoadmapSummaryRead],
    summary="The user's saved learning plans",
)
def list_roadmaps(
    db: DbSession,
    user: CurrentUser,
    params: PageParamsDep,
) -> Page[RoadmapSummaryRead]:
    """The user's plans, newest first."""
    total, summaries = roadmap_service.list_roadmaps(
        db, user, limit=params.limit, offset=params.offset
    )
    return build_page(summaries, total, params)


@router.post(
    "",
    response_model=RoadmapRead,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a learning plan for a role and save it",
    dependencies=[Depends(rate_limit("ai"))],
    responses={503: {"description": "The AI layer is not configured on this deployment."}},
)
def create_roadmap(
    request: RoadmapGenerateRequest,
    db: DbSession,
    user: CurrentUser,
) -> RoadmapRead:
    """Build a four- or six-week plan from the engine's own gap report.

    The gap report decides which skills the plan is about. The model decides
    the order, the exercises and the portfolio project. Nothing the model
    says can add a skill the engine did not report as missing, or a learning
    resource the registry does not hold.
    """
    return roadmap_service.generate(db, user, request)


@router.get(
    "/{roadmap_id}",
    response_model=RoadmapRead,
    summary="One saved learning plan",
    responses={404: {"description": "No such plan, or it belongs to somebody else."}},
)
def get_roadmap(roadmap_id: int, db: DbSession, user: CurrentUser) -> RoadmapRead:
    """A plan and the learner's progress on it."""
    return roadmap_service.get_roadmap(db, user, roadmap_id)


@router.patch(
    "/{roadmap_id}/tasks/{task_key}",
    response_model=RoadmapTaskRead,
    summary="Record progress on one task",
    responses={404: {"description": "No such plan or task."}},
)
def update_task(
    roadmap_id: int,
    task_key: str,
    update: RoadmapTaskUpdate,
    db: DbSession,
    user: CurrentUser,
) -> RoadmapTaskRead:
    """Mark a task complete, add a note, or attach a portfolio link.

    The plan document is never rewritten. Progress is recorded beside it, so
    the plan the learner is halfway through cannot change underneath them.
    """
    return roadmap_service.update_task(db, user, roadmap_id, task_key, update)


@router.delete(
    "/{roadmap_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a saved learning plan",
    responses={404: {"description": "No such plan, or it belongs to somebody else."}},
)
def delete_roadmap(roadmap_id: int, db: DbSession, user: CurrentUser) -> Response:
    """Remove a plan and its tasks."""
    roadmap_service.delete_roadmap(db, user, roadmap_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
