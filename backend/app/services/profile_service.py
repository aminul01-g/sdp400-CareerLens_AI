"""Profile business logic.

The profile is scoped by the *current user*, never by a path parameter. That is
what makes IDOR impossible here by construction rather than by remembering to add
a check — there is no ``/profile/{id}`` route to get wrong.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.education import Certification, EducationRecord
from app.models.profile import Profile
from app.models.project import Project
from app.models.user import User
from app.models.user_skill import UserSkill
from app.schemas.profile import ProfileCreate, ProfileRead, ProfileUpdate

logger = logging.getLogger("app.services.profile")


def _counts(db: Session, user_id: int) -> dict[str, int]:
    """Live child-row counts so the read model needs no second round trip."""

    def scalar(stmt: Any) -> int:
        return int(db.scalar(stmt) or 0)

    return {
        "skills_count": scalar(
            select(func.count()).select_from(UserSkill).where(UserSkill.user_id == user_id)
        ),
        "projects_count": scalar(
            select(func.count()).select_from(Project).where(Project.user_id == user_id)
        ),
        "education_count": scalar(
            select(func.count()).select_from(EducationRecord).where(
                EducationRecord.user_id == user_id
            )
        ),
        "certifications_count": scalar(
            select(func.count()).select_from(Certification).where(
                Certification.user_id == user_id
            )
        ),
    }


def _to_read(db: Session, profile: Profile) -> ProfileRead:
    data = ProfileRead.model_validate(profile)
    return data.model_copy(update=_counts(db, profile.user_id))


def get_or_create(db: Session, user: User) -> Profile:
    """Fetch the user's profile, creating an empty one on first access."""
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    if profile is None:
        profile = Profile(user_id=user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
        logger.info("Created empty profile for user id=%s", user.id, extra={"kind": "profile"})
    return profile


def get(db: Session, user: User) -> ProfileRead:
    return _to_read(db, get_or_create(db, user))


def create(db: Session, user: User, payload: ProfileCreate) -> ProfileRead:
    """Create-or-update. Idempotent, so a double-submitted form is harmless."""
    profile = get_or_create(db, user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return _to_read(db, profile)


def update(db: Session, user: User, payload: ProfileUpdate) -> ProfileRead:
    """Partial update.

    ``model_fields_set`` is the important part: only fields the client actually
    sent are touched, so a PATCH that omits ``bio`` leaves it alone. A PATCH that
    sends ``bio: null`` explicitly clears it.
    """
    profile = get_or_create(db, user)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(profile, field, value)
    if changes:
        db.commit()
        db.refresh(profile)
    return _to_read(db, profile)


def delete(db: Session, user: User) -> None:
    """Delete only the profile row.

    The user, their authentication, and their skills/projects/education survive, so
    a user who dislikes their profile can rebuild it without re-registering. The
    proposal treats those as separate modules with their own delete operations, and
    this is what the ``/profile`` delete dialog states.
    """
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    if profile is None:
        raise NotFoundError("You do not have a profile to delete.")
    db.delete(profile)
    db.commit()
    logger.info("Deleted profile for user id=%s", user.id, extra={"kind": "profile"})
