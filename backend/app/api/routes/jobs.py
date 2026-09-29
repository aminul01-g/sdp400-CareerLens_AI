"""``/api/jobs`` — public read, admin write.

The split is enforced by mounting two routers on the same prefix, so the
authorization requirement is visible in the route definitions themselves rather
than buried in a helper. This replaces the legacy Flask-Admin panel, which was
mounted at ``app.py:27`` with **no** ``is_accessible`` override and therefore
publicly reachable, listing ``user.password_hash`` to anonymous visitors
(security finding S1).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Response, status

from app.api.deps import DbSession, RequireAdmin
from app.schemas.job import (
    FamilyCount,
    JobRoleCreate,
    JobRoleRead,
    JobRoleSkillReplace,
    JobRoleUpdate,
)
from app.schemas.pagination import PageParamsDep, build_page
from app.services import job_service

# ---- Public read -----------------------------------------------------------
public_router = APIRouter(prefix="/jobs", tags=["jobs"])


@public_router.get("", summary="Browse active job roles")
def list_jobs(
    params: PageParamsDep,
    db: DbSession,
    family: Annotated[str | None, Query(max_length=80)] = None,
    q: Annotated[str | None, Query(max_length=120)] = None,
) -> object:
    total, items = job_service.list_roles(
        db, family=family, q=q, limit=params.limit, offset=params.offset
    )
    return build_page(items, total, params)


@public_router.get("/families", response_model=list[FamilyCount], summary="Role families with counts")
def list_families(db: DbSession) -> list[FamilyCount]:
    return job_service.families(db)


@public_router.get(
    "/{role_id}",
    response_model=JobRoleRead,
    responses={404: {"description": "No such role"}},
)
def get_job(role_id: int, db: DbSession) -> JobRoleRead:
    """Includes the weighted skill set, so a user can see what a role asks for."""
    return job_service.to_read(db, job_service.get_role(db, role_id))


# ---- Admin write -----------------------------------------------------------
admin_router = APIRouter(prefix="/admin/jobs", tags=["admin/jobs"])


@admin_router.get(
    "",
    summary="List every role, including deactivated ones",
    dependencies=[],
)
def list_jobs_admin(
    params: PageParamsDep,
    db: DbSession,
    _: RequireAdmin,
    q: Annotated[str | None, Query(max_length=120)] = None,
    family: Annotated[str | None, Query(max_length=80)] = None,
    is_active: Annotated[bool | None, Query()] = None,
) -> object:
    total, items = job_service.list_roles_admin(
        db, q=q, family=family, is_active=is_active, limit=params.limit, offset=params.offset
    )
    return build_page(items, total, params)


@admin_router.post(
    "",
    response_model=JobRoleRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a job role with its weighted required skills",
    responses={409: {"description": "Title already exists"}},
)
def create_job(payload: JobRoleCreate, db: DbSession, _: RequireAdmin) -> JobRoleRead:
    return job_service.create_role(db, payload)


@admin_router.get(
    "/{role_id}", response_model=JobRoleRead, responses={404: {"description": "No such role"}}
)
def get_job_admin(role_id: int, db: DbSession, _: RequireAdmin) -> JobRoleRead:
    return job_service.to_read(db, job_service.get_role(db, role_id))


@admin_router.patch(
    "/{role_id}",
    response_model=JobRoleRead,
    responses={404: {"description": "No such role"}, 409: {"description": "Title clash"}},
)
def update_job(
    role_id: int, payload: JobRoleUpdate, db: DbSession, _: RequireAdmin
) -> JobRoleRead:
    return job_service.update_role(db, role_id, payload)


@admin_router.put(
    "/{role_id}/skills",
    response_model=JobRoleRead,
    summary="Atomically replace a role's weighted required-skill set",
    responses={404: {"description": "No such role"}, 422: {"description": "Invalid skill set"}},
)
def replace_job_skills(
    role_id: int, payload: JobRoleSkillReplace, db: DbSession, _: RequireAdmin
) -> JobRoleRead:
    """Full replacement, not a diff.

    Atomicity is the reason: a request that fails validation raises *before* the
    DELETE runs, so the previous requirement set survives intact. A differential
    API would need its own compensation logic and would have a much larger space
    of partial-failure states.
    """
    return job_service.replace_skills(db, role_id, payload)


@admin_router.delete(
    "/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete a job role",
    responses={
        404: {"description": "No such role"},
        409: {"description": "Referenced by stored results; deactivate instead"},
    },
)
def delete_job(role_id: int, db: DbSession, _: RequireAdmin) -> Response:
    job_service.delete_role(db, role_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
