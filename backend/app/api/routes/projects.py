"""``/api/projects`` — full CRUD, ownership-scoped in the query."""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.pagination import PageParamsDep, build_page
from app.schemas.project import ProjectCreate, ProjectPageResponse, ProjectRead, ProjectUpdate
from app.services import project_service

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=ProjectPageResponse, summary="The caller's projects")
def list_projects(params: PageParamsDep, db: DbSession, user: CurrentUser) -> ProjectPageResponse:
    total, items = project_service.list_projects(db, user, limit=params.limit, offset=params.offset)
    return build_page(items, total, params)


@router.post(
    "",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a project",
)
def create_project(
    payload: ProjectCreate, db: DbSession, user: CurrentUser
) -> ProjectRead:
    return project_service.create_project(db, user, payload)


@router.get(
    "/{project_id}",
    response_model=ProjectRead,
    summary="One project",
    responses={404: {"description": "Does not exist, or belongs to another user"}},
)
def get_project(project_id: int, db: DbSession, user: CurrentUser) -> ProjectRead:
    return ProjectRead.model_validate(project_service.get_project(db, user, project_id))


@router.patch(
    "/{project_id}",
    response_model=ProjectRead,
    summary="Update a project",
    responses={404: {"description": "Does not exist, or belongs to another user"}},
)
def update_project(
    project_id: int, payload: ProjectUpdate, db: DbSession, user: CurrentUser
) -> ProjectRead:
    return project_service.update_project(db, user, project_id, payload)


@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete a project",
    responses={404: {"description": "Does not exist, or belongs to another user"}},
)
def delete_project(project_id: int, db: DbSession, user: CurrentUser) -> Response:
    project_service.delete_project(db, user, project_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
