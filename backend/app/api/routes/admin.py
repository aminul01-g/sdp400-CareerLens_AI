"""``/api/admin`` — the knowledge-base control plane.

**This is the replacement for Flask-Admin**, and the difference is the point.
Flask-Admin (``backend/admin.py:40-54``, mounted at ``app.py:27`` with no
``is_accessible`` override) rendered a raw column grid over six models,
**including ``user.password_hash``**, to anonymous visitors — security finding S1,
critical. Everything here sits behind ``require_role("admin")``, returns curated
fields, validates through Pydantic, and enforces the database's own ``CHECK``
constraints.
"""

from __future__ import annotations

import json
import logging
from typing import Annotated, Any

from fastapi import APIRouter, Query, Response, status
from sqlalchemy import func, select

from app.api.deps import DbSession, RequireAdmin
from app.core.exceptions import ConflictError, NotFoundError
from app.ml.evaluation.harness import DEFAULT_JSON_REPORT
from app.models.project import Project
from app.models.user import User, UserRole
from app.models.user_skill import UserSkill
from app.schemas.dashboard import (
    AdminOverview,
    AdminUserRead,
    RoleUpdateRequest,
)
from app.schemas.job import (
    JobRoleRead,
    JobRoleSkillReplace,
    TaxonomyCreate,
    TaxonomyUpdate,
)
from app.schemas.pagination import PageParamsDep, build_page
from app.schemas.skill import SkillRead
from app.services import dashboard_service, job_service

logger = logging.getLogger("app.routes.admin")

router = APIRouter(prefix="/admin", tags=["admin"])

#: The committed evaluation report, charted in the admin UI.
#:
#: Imported rather than recomputed, because a second path expression for the same
#: artefact is how it ends up pointing at a file that does not exist -- which is
#: exactly what happened: this used to resolve to docs/evaluation_report.json,
#: while the harness writes JSON to app/ml/evaluation/report.json and Markdown to
#: docs/evaluation_report.md. The endpoint 404'd for an admin in a container, and
#: no test caught it because every test here stopped at the 401, before the file
#: check was ever reached.
#:
#: Living inside app/ also means the Dockerfile already ships it: there is no
#: separate COPY of docs/ to forget.
EVALUATION_REPORT_PATH = DEFAULT_JSON_REPORT


# ---------------------------------------------------------------------------
# Overview and users
# ---------------------------------------------------------------------------
@router.get("/overview", response_model=AdminOverview, summary="Real system aggregates")
def overview(db: DbSession, _: RequireAdmin) -> AdminOverview:
    return dashboard_service.admin_overview(db)


@router.get("/users", summary="Paged user list (never includes password_hash)")
def list_users(
    params: PageParamsDep, db: DbSession, _: RequireAdmin
) -> Any:
    total = int(db.scalar(select(func.count()).select_from(User)) or 0)
    users = list(
        db.scalars(
            select(User)
            .order_by(User.created_at.desc(), User.id.desc())
            .limit(params.limit)
            .offset(params.offset)
        ).all()
    )
    skill_counts: dict[int, int] = {
        user_id: int(count)
        for user_id, count in db.execute(
            select(UserSkill.user_id, func.count()).group_by(UserSkill.user_id)
        ).all()
    }
    project_counts: dict[int, int] = {
        user_id: int(count)
        for user_id, count in db.execute(
            select(Project.user_id, func.count()).group_by(Project.user_id)
        ).all()
    }
    return build_page(
        [
            AdminUserRead(
                id=u.id,
                name=u.name,
                email=u.email,
                role=u.role.value,
                is_active=u.is_active,
                created_at=u.created_at,
                last_login_at=u.last_login_at,
                skills_count=int(skill_counts.get(u.id, 0)),
                projects_count=int(project_counts.get(u.id, 0)),
            )
            for u in users
        ],
        total,
        params,
    )


@router.patch("/users/{user_id}/role", response_model=AdminUserRead, summary="Promote or demote")
def update_user_role(
    user_id: int, payload: RoleUpdateRequest, db: DbSession, admin: RequireAdmin
) -> AdminUserRead:
    """An admin cannot demote themselves.

    Without this check the last admin can lock every other admin out of the panel
    and nobody can undo it, because undoing it requires being an admin.
    """
    target = db.get(User, user_id)
    if target is None:
        raise NotFoundError("That user does not exist.")
    if target.id == admin.id and payload.role != "admin":
        raise ConflictError(
            "You cannot remove your own admin role — that would lock you out of the panel.",
            code="cannot_demote_self",
        )

    target.role = UserRole(payload.role)
    db.commit()
    db.refresh(target)
    logger.info("Admin %s set user %s role to %s", admin.id, target.id, payload.role)
    return AdminUserRead.model_validate(target)


# ---------------------------------------------------------------------------
# Job roles (delegated to job_service; see jobs.py for the route definitions)
# ---------------------------------------------------------------------------
@router.put(
    "/jobs/{role_id}/skills",
    response_model=JobRoleRead,
    summary="Atomically replace a role's weighted skill set",
)
def replace_skills_admin(
    role_id: int, payload: JobRoleSkillReplace, db: DbSession, _: RequireAdmin
) -> JobRoleRead:
    return job_service.replace_skills(db, role_id, payload)


# ---------------------------------------------------------------------------
# Skill taxonomy
# ---------------------------------------------------------------------------
@router.get("/taxonomy", summary="Browse the skill taxonomy")
def list_taxonomy(
    params: PageParamsDep,
    db: DbSession,
    _: RequireAdmin,
    q: Annotated[str | None, Query(max_length=120)] = None,
    category: Annotated[str | None, Query(max_length=60)] = None,
) -> Any:
    total, pairs = job_service.list_taxonomy(
        db, q=q, category=category, limit=params.limit, offset=params.offset
    )
    return build_page(
        [job_service.skill_to_read(skill, aliases) for skill, aliases in pairs], total, params
    )


@router.post(
    "/taxonomy",
    response_model=SkillRead,
    status_code=status.HTTP_201_CREATED,
    summary="Add a skill to the taxonomy",
    responses={409: {"description": "Name, slug, or an alias is already taken"}},
)
def create_skill(payload: TaxonomyCreate, db: DbSession, _: RequireAdmin) -> SkillRead:
    skill, aliases = job_service.create_skill(db, payload)
    return job_service.skill_to_read(skill, aliases)


@router.patch(
    "/taxonomy/{skill_id}",
    response_model=SkillRead,
    responses={404: {"description": "No such skill"}, 409: {"description": "Alias collision"}},
)
def update_skill(
    skill_id: int, payload: TaxonomyUpdate, db: DbSession, _: RequireAdmin
) -> SkillRead:
    skill, aliases = job_service.update_skill(db, skill_id, payload)
    return job_service.skill_to_read(skill, aliases)


@router.delete(
    "/taxonomy/{skill_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={404: {"description": "No such skill"}, 409: {"description": "Still referenced"}},
)
def delete_skill(skill_id: int, db: DbSession, _: RequireAdmin) -> Response:
    job_service.delete_skill(db, skill_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Feedback and evaluation
# ---------------------------------------------------------------------------
@router.get("/feedback", summary="Submitted feedback, paged")
def list_feedback(
    params: PageParamsDep,
    db: DbSession,
    _: RequireAdmin,
    category: Annotated[str | None, Query(max_length=60)] = None,
) -> Any:
    total, items = dashboard_service.list_feedback(
        db, limit=params.limit, offset=params.offset, category=category
    )
    return build_page(items, total, params)


@router.get(
    "/evaluation",
    summary="The committed evaluation report as JSON",
    responses={404: {"description": "The report has not been generated yet"}},
)
def evaluation(_: RequireAdmin) -> Any:
    """Serve the **committed** report rather than re-running the harness.

    The admin chart then can never disagree with the document in the repository,
    which is the whole point of publishing the numbers as an artefact.
    """
    if not EVALUATION_REPORT_PATH.exists():
        raise NotFoundError(
            "The evaluation report has not been generated yet. "
            "Run: python -m app.ml.evaluation"
        )
    with EVALUATION_REPORT_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


@router.get("/health", summary="Lightweight admin liveness probe")
def admin_health(_: RequireAdmin) -> dict[str, str]:
    """A probe proving the role gate works end to end.

    ``tests/test_roles.py`` asserts 200 for an admin, 403 for a user, and 401 for
    an anonymous caller against this single endpoint.
    """
    return {"status": "ok", "scope": "admin"}
