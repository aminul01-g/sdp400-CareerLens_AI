"""``/api/skills`` — the caller's confirmed skills, plus taxonomy search."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.skill import (
    ConfirmResult,
    DetectedSkillConfirm,
    TaxonomySearchResponse,
    UserSkillCreate,
    UserSkillRead,
    UserSkillUpdate,
)
from app.services import skill_service

router = APIRouter(prefix="/skills", tags=["skills"])


@router.get("", response_model=list[UserSkillRead], summary="The caller's skills")
def list_skills(
    db: DbSession,
    user: CurrentUser,
    source: Annotated[str | None, Query(pattern="^(manual|cv_extracted)$")] = None,
    category: Annotated[str | None, Query(max_length=60)] = None,
) -> list[UserSkillRead]:
    return skill_service.list_user_skills(db, user, source=source, category=category)


@router.post(
    "",
    response_model=UserSkillRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a skill from the taxonomy",
    responses={409: {"description": "Already added"}, 422: {"description": "Unknown skill_id"}},
)
def add_skill(payload: UserSkillCreate, db: DbSession, user: CurrentUser) -> UserSkillRead:
    return skill_service.add_skill(db, user, payload)


@router.get(
    "/taxonomy",
    response_model=TaxonomySearchResponse,
    summary="Search the skill taxonomy by name or alias",
)
def search_taxonomy(
    db: DbSession,
    _: CurrentUser,
    q: Annotated[str | None, Query(max_length=120, description="Name, slug, or alias.")] = None,
    category: Annotated[str | None, Query(max_length=60)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TaxonomySearchResponse:
    """Searching ``sklearn`` finds ``Scikit-learn`` — the alias feature made visible."""
    return skill_service.search_taxonomy(db, q=q, category=category, limit=limit, offset=offset)


@router.get(
    "/taxonomy/categories",
    response_model=list[str],
    summary="The taxonomy's categories, for a filter that does not depend on the user",
)
def taxonomy_categories(db: DbSession, _: CurrentUser) -> list[str]:
    """The distinct categories in the skill taxonomy.

    The skills screen filters by category, and a filter built from the
    *caller's own* skills is empty for anyone who has not added one yet —
    which is precisely the person who needs the picker. This is the
    catalogue's own list.
    """
    return skill_service.list_taxonomy_categories(db)


@router.post(
    "/confirm",
    response_model=ConfirmResult,
    summary="Confirm or reject CV-detected skills",
)
def confirm_skills(
    payload: DetectedSkillConfirm, db: DbSession, user: CurrentUser
) -> ConfirmResult:
    """Upsert accepted skills into ``user_skill``.

    This is the step that implements the proposal's "show detected skills for user
    confirmation", and it is the boundary that makes "every skill in ``user_skill``
    is user-confirmed" a checkable invariant. Idempotent: confirming twice changes
    nothing.
    """
    return skill_service.confirm_detected_skills(db, user, payload)


@router.patch(
    "/{skill_id}",
    response_model=UserSkillRead,
    summary="Update proficiency, years used, or confirmed state",
    responses={404: {"description": "Not held by the caller"}},
)
def update_skill(
    skill_id: int, payload: UserSkillUpdate, db: DbSession, user: CurrentUser
) -> UserSkillRead:
    return skill_service.update_skill(db, user, skill_id, payload)


@router.delete(
    "/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Remove a skill",
    responses={404: {"description": "Not held by the caller"}},
)
def remove_skill(skill_id: int, db: DbSession, user: CurrentUser) -> Response:
    skill_service.remove_skill(db, user, skill_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
