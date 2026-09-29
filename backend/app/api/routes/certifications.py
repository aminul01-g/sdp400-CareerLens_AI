"""``/api/certifications`` — professional certifications, full CRUD."""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.education import CertificationCreate, CertificationRead, CertificationUpdate
from app.schemas.pagination import PageParamsDep, build_page
from app.services import education_service

router = APIRouter(prefix="/certifications", tags=["certifications"])


@router.get("", summary="The caller's certifications")
def list_certifications(params: PageParamsDep, db: DbSession, user: CurrentUser):
    total, items = education_service.list_certifications(
        db, user, limit=params.limit, offset=params.offset
    )
    return build_page(items, total, params)


@router.post(
    "",
    response_model=CertificationRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a certification",
)
def create_certification(
    payload: CertificationCreate, db: DbSession, user: CurrentUser
) -> CertificationRead:
    return education_service.create_certification(db, user, payload)


@router.get(
    "/{cert_id}",
    response_model=CertificationRead,
    responses={404: {"description": "Does not exist, or belongs to another user"}},
)
def get_certification(cert_id: int, db: DbSession, user: CurrentUser) -> CertificationRead:
    return CertificationRead.model_validate(education_service.get_certification(db, user, cert_id))


@router.patch(
    "/{cert_id}",
    response_model=CertificationRead,
    responses={404: {"description": "Does not exist, or belongs to another user"}},
)
def update_certification(
    cert_id: int, payload: CertificationUpdate, db: DbSession, user: CurrentUser
) -> CertificationRead:
    return education_service.update_certification(db, user, cert_id, payload)


@router.delete(
    "/{cert_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"description": "Does not exist, or belongs to another user"}},
)
def delete_certification(cert_id: int, db: DbSession, user: CurrentUser) -> Response:
    education_service.delete_certification(db, user, cert_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
