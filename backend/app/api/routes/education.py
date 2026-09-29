"""``/api/education`` — degree records, full CRUD."""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.education import EducationCreate, EducationRead, EducationUpdate
from app.schemas.pagination import PageParamsDep, build_page
from app.services import education_service

router = APIRouter(prefix="/education", tags=["education"])


@router.get("", summary="The caller's education records")
def list_education(params: PageParamsDep, db: DbSession, user: CurrentUser):
    total, items = education_service.list_education(db, user, limit=params.limit, offset=params.offset)
    return build_page(items, total, params)


@router.post(
    "",
    response_model=EducationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a degree",
)
def create_education(payload: EducationCreate, db: DbSession, user: CurrentUser) -> EducationRead:
    return education_service.create_education(db, user, payload)


@router.get(
    "/{record_id}",
    response_model=EducationRead,
    responses={404: {"description": "Does not exist, or belongs to another user"}},
)
def get_education(record_id: int, db: DbSession, user: CurrentUser) -> EducationRead:
    return EducationRead.model_validate(education_service.get_education(db, user, record_id))


@router.patch(
    "/{record_id}",
    response_model=EducationRead,
    responses={404: {"description": "Does not exist, or belongs to another user"}},
)
def update_education(
    record_id: int, payload: EducationUpdate, db: DbSession, user: CurrentUser
) -> EducationRead:
    return education_service.update_education(db, user, record_id, payload)


@router.delete(
    "/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"description": "Does not exist, or belongs to another user"}},
)
def delete_education(record_id: int, db: DbSession, user: CurrentUser) -> Response:
    education_service.delete_education(db, user, record_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
