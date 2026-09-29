"""Authentication business logic.

One rule worth stating explicitly: **an unknown email and a wrong password
produce the identical error message and both take the same code path.** The legacy
``auth.py`` distinguished them, which turns the login form into an account
enumeration oracle. Here both branches call :func:`verify_password` against a
dummy hash when the user does not exist, so the two cases are also close to
identical in *time*.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, ForbiddenError, NotFoundError, UnauthorizedError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.profile import Profile
from app.models.user import User, UserRole
from app.schemas.auth import RegisterRequest, TokenResponse, UserRead, UserUpdateRequest

logger = logging.getLogger("app.auth")

# A real bcrypt hash of a value nobody knows. Verifying against it when the email
# is unknown keeps the failure path's cost comparable to the wrong-password path.
_DUMMY_HASH = hash_password("TimingOnly-Password-1")


def normalise_email(email: str) -> str:
    """Trim and lowercase. The first half of the S9 fix."""
    return email.strip().lower()


def get_user_by_email(db: Session, email: str) -> User | None:
    """Look a user up by normalised email, case-insensitively."""
    return db.scalar(select(User).where(func.lower(User.email) == normalise_email(email)))


def register_user(db: Session, payload: RegisterRequest) -> User:
    """Create a ``User`` and its empty ``Profile`` in one transaction.

    The profile is created immediately so ``GET /api/profile`` never has to
    invent one, and so a user who registers and abandons the app still has a
    consistent row to delete.
    """
    email = normalise_email(str(payload.email))

    if get_user_by_email(db, email) is not None:
        raise ConflictError(
            "An account with that email address already exists.", code="email_exists"
        )

    user = User(
        name=payload.name,
        email=email,
        password_hash=hash_password(payload.password),
        role=UserRole.USER,
        is_active=True,
    )
    profile = Profile(user=user, education_level=payload.education_level)

    db.add_all([user, profile])
    try:
        db.commit()
    except IntegrityError as exc:
        # The unique index is the authority. Two simultaneous registrations of
        # the same new address both pass the SELECT above; only one INSERT wins.
        db.rollback()
        raise ConflictError(
            "An account with that email address already exists.", code="email_exists"
        ) from exc

    db.refresh(user)
    logger.info("Registered user id=%s", user.id, extra={"kind": "register"})
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    """Verify credentials or raise ``401`` with a deliberately vague message."""
    user = get_user_by_email(db, email)

    if user is None:
        verify_password(password, _DUMMY_HASH)
        raise UnauthorizedError("Email or password is incorrect.", code="invalid_credentials")

    if not verify_password(password, user.password_hash):
        raise UnauthorizedError("Email or password is incorrect.", code="invalid_credentials")

    if not user.is_active:
        raise UnauthorizedError("This account has been deactivated.", code="account_disabled")

    user.last_login_at = datetime.now(UTC)
    db.commit()
    db.refresh(user)
    return user


def build_token_response(user: User) -> TokenResponse:
    """Issue a token bound to the role currently stored in the database.

    The role is read from the row, not from the incoming token, so a user
    demoted by an admin cannot keep admin access by replaying an old token until
    it expires.
    """
    token, expires_in = create_access_token(subject=str(user.id), role=user.role.value)
    return TokenResponse(
        user=UserRead.model_validate(user),
        access_token=token,
        token_type="bearer",
        expires_in=expires_in,
    )


def update_me(db: Session, user: User, payload: UserUpdateRequest) -> User:
    """Update name and/or password for the authenticated user."""
    fields = payload.model_fields_set - {"current_password"}
    if not fields:
        return user

    if "password" in fields:
        if not payload.current_password:
            raise ForbiddenError(
                "Current password is required to set a new password.", code="current_password_required"
            )
        if not verify_password(payload.current_password, user.password_hash):
            raise UnauthorizedError(
                "Current password is incorrect.", code="current_password_incorrect"
            )
        user.password_hash = hash_password(payload.password or "")

    if "name" in fields and payload.name:
        user.name = payload.name

    db.commit()
    db.refresh(user)
    logger.info("Updated user id=%s fields=%s", user.id, sorted(fields), extra={"kind": "update_me"})
    return user


def get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("That user does not exist.")
    return user
