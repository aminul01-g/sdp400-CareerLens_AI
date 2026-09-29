"""Project CRUD with taxonomy-based tech-stack canonicalisation."""

from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.ml.taxonomy import load as load_taxonomy
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectRead, ProjectUpdate

logger = logging.getLogger("app.services.projects")


def canonicalise_tech_stack(entries: list[str]) -> tuple[list[str], list[str]]:
    """Map free-text stack entries onto taxonomy slugs.

    Returns ``(canonical_slugs, unrecognised)``.

    Unrecognised entries are **kept, not dropped**. A user may legitimately list a
    tool the curated taxonomy has not caught up with, and silently discarding
    their input is worse than an unrecognised tag the UI badges. What is *not*
    allowed is storing the same tool twice under two spellings, which is exactly
    what canonicalisation prevents.
    """
    taxonomy = load_taxonomy()
    canonical: list[str] = []
    unrecognised: list[str] = []
    for entry in entries:
        cleaned = str(entry).strip()
        if not cleaned:
            continue
        match = taxonomy.canonicalise(cleaned)
        if match is not None:
            slug = match.slug
        else:
            slug = cleaned.lower().replace(" ", "-")
            unrecognised.append(cleaned)
        if slug not in canonical:
            canonical.append(slug)
    return canonical, unrecognised


def _to_read(project: Project, unrecognised: list[str] | None = None) -> ProjectRead:
    return ProjectRead.model_validate(project).model_copy(
        update={"unrecognised_tech": unrecognised or []}
    )


def list_projects(db: Session, user: User, *, limit: int, offset: int) -> tuple[int, list[ProjectRead]]:
    total = int(
        db.scalar(select(func.count()).select_from(Project).where(Project.user_id == user.id)) or 0
    )
    rows = db.scalars(
        select(Project)
        .where(Project.user_id == user.id)
        .order_by(Project.created_at.desc(), Project.id.desc())
        .limit(limit)
        .offset(offset)
    ).all()
    return total, [_to_read(row) for row in rows]


def get_project(db: Session, user: User, project_id: int) -> Project:
    """Ownership enforced **in the query**.

    The legacy code did ``Upload.query.get(upload_id)`` and hoped; here the
    ``user_id`` predicate is part of the lookup, so another user's project simply
    does not exist as far as this query is concerned — and a 404 (not a 403) is
    returned, which does not confirm the row exists.
    """
    project = db.scalar(
        select(Project).where(Project.id == project_id, Project.user_id == user.id)
    )
    if project is None:
        raise NotFoundError("That project does not exist.")
    return project


def create_project(db: Session, user: User, payload: ProjectCreate) -> ProjectRead:
    canonical, unrecognised = canonicalise_tech_stack(payload.tech_stack)
    project = Project(
        user_id=user.id,
        title=payload.title,
        description=payload.description,
        tech_stack=canonical,
        role=payload.role,
        start_date=payload.start_date,
        end_date=payload.end_date,
        repo_url=payload.repo_url,
        is_public=payload.is_public,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return _to_read(project, unrecognised)


def update_project(
    db: Session, user: User, project_id: int, payload: ProjectUpdate
) -> ProjectRead:
    project = get_project(db, user, project_id)
    changes = payload.model_dump(exclude_unset=True)
    unrecognised: list[str] = []

    if "tech_stack" in changes and changes["tech_stack"] is not None:
        canonical, unrecognised = canonicalise_tech_stack(changes["tech_stack"])
        changes["tech_stack"] = canonical

    for field, value in changes.items():
        setattr(project, field, value)

    # A date-range update needs the *merged* value validated, not just the field
    # that changed, or PATCHing only end_date could leave start > end.
    if project.start_date and project.end_date and project.end_date < project.start_date:
        raise ValueError("end_date must not be earlier than start_date")

    db.commit()
    db.refresh(project)
    return _to_read(project, unrecognised)


def delete_project(db: Session, user: User, project_id: int) -> None:
    project = get_project(db, user, project_id)
    db.delete(project)
    db.commit()
