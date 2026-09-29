"""``/api/profile`` — the authenticated user's profile.

There is no path parameter, so IDOR is impossible here by construction rather
than by remembering to add an ownership check. There is nothing to get wrong.
"""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.profile import ProfileCreate, ProfileRead, ProfileUpdate
from app.services import profile_service

router = APIRouter(prefix="/profile", tags=["profile"])


@router.get("", response_model=ProfileRead, summary="The caller's profile")
def get_profile(db: DbSession, user: CurrentUser) -> ProfileRead:
    return profile_service.get(db, user)


@router.post(
    "",
    response_model=ProfileRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create or replace the caller's profile",
)
def create_profile(payload: ProfileCreate, db: DbSession, user: CurrentUser) -> ProfileRead:
    """Idempotent: a user who already has a profile has it updated, not duplicated."""
    return profile_service.create(db, user, payload)


@router.patch("", response_model=ProfileRead, summary="Partially update the profile")
def update_profile(
    payload: ProfileUpdate, db: DbSession, user: CurrentUser
) -> ProfileRead:
    return profile_service.update(db, user, payload)


@router.delete(
    "",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete the profile (account and data are kept)",
)
def delete_profile(db: DbSession, user: CurrentUser) -> Response:
    """Deletes the profile row only.

    The account, its authentication, and its skills, projects, education and
    certifications all survive, so a user can rebuild their profile without
    re-registering. The confirmation dialog states this distinction, and the
    distinction is real — it follows from the schema, not from a UI promise.
    """
    profile_service.delete(db, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
