"""``/api/auth`` routes.

Thin by design: validate, call the service, set a status code. No business logic.

``POST /logout`` returns ``204`` without touching server state. That is honest
rather than a stub — the token is stateless, so there is nothing to revoke. A real
revocation list would need a Redis dependency the proposal does not list, and a
local blacklist would leak across replicas. The trade-off is recorded in
``docs/report.md`` under security limitations.
"""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUser, DbSession
from app.schemas.auth import (
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserRead,
    UserUpdateRequest,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account and start a session",
    responses={
        409: {"description": "Email already registered"},
        422: {"description": "Validation failed"},
    },
)
def register(payload: RegisterRequest, db: DbSession) -> TokenResponse:
    """Register a new user. Returns a token so the session starts immediately."""
    user = auth_service.register_user(db, payload)
    return auth_service.build_token_response(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Exchange credentials for an access token",
    responses={401: {"description": "Invalid credentials"}},
)
def login(payload: LoginRequest, db: DbSession) -> TokenResponse:
    user = auth_service.authenticate(db, str(payload.email), payload.password)
    return auth_service.build_token_response(user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="End the client session",
    responses={401: {"description": "No valid token"}},
)
def logout(_: CurrentUser) -> Response:
    """Acknowledge a logout.

    The token is stateless, so the server holds nothing to revoke; the client
    discards the token. Documented rather than silently empty.
    """
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Issue a fresh access token",
    responses={401: {"description": "Token missing, invalid or expired"}},
)
def refresh(payload: RefreshRequest, db: DbSession, user: CurrentUser) -> TokenResponse:
    """Re-issue a token for a still-valid subject.

    The role is taken from the database, not from the presented token, so a
    demotion takes effect on the next refresh instead of at token expiry.
    """
    return auth_service.build_token_response(user)


@router.get("/me", response_model=UserRead, summary="The authenticated user")
def me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)


@router.patch("/me", response_model=UserRead, summary="Update name or password")
def update_me(
    payload: UserUpdateRequest, db: DbSession, user: CurrentUser
) -> UserRead:
    updated = auth_service.update_me(db, user, payload)
    return UserRead.model_validate(updated)


@router.delete(
    "/me",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Delete the account and all of its data",
)
def delete_me(db: DbSession, user: CurrentUser) -> Response:
    """Delete the authenticated user.

    Cascades to the profile, skills, projects, education, certifications, CV
    uploads and recommendation runs at the database level (verified by
    ``tests/test_cascade.py``).
    """
    db.delete(user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
