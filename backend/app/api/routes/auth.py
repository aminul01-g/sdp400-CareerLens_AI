"""``/api/auth`` routes.

Thin by design: validate, call the service, set a status code. No business logic.

``POST /logout`` returns ``204`` without touching server state. That is honest
rather than a stub — the token is stateless, so there is nothing to revoke. A real
revocation list would need a Redis dependency the proposal does not list, and a
local blacklist would leak across replicas. The trade-off is recorded in
``docs/report.md`` under security limitations.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import CurrentUser, DbSession, rate_limit
from app.schemas.auth import (
    AcceptedResponse,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserRead,
    UserUpdateRequest,
    VerifyEmailRequest,
)
from app.services import account_service, auth_service, cv_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account and start a session",
    dependencies=[Depends(rate_limit("auth"))],
    responses={
        409: {"description": "Email already registered"},
        422: {"description": "Validation failed"},
        429: {"description": "Too many attempts from this address"},
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
    dependencies=[Depends(rate_limit("auth"))],
    responses={
        401: {"description": "Invalid credentials"},
        429: {"description": "Too many attempts from this address"},
    },
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
    ``tests/test_ownership.py::test_cascade_removes_the_whole_subtree``).

    The uploaded CV *files* are removed as well. The cascade removes the
    database rows, but a row is not a file: without this the CV would still
    be on disk after the account was gone, holding the name, contact details
    and employment history in plain text. Proposal section 6.4 lists
    "allow deletion of files and profile" as the privacy mitigation for
    uploaded CVs, and deleting the account is the strongest form of that
    request.
    """
    cv_service.purge_user_files(db, user)
    db.delete(user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------
@router.post(
    "/verify-email",
    response_model=UserRead,
    summary="Confirm an email address",
    responses={
        422: {"description": "The link is invalid, used, or expired"},
    },
)
def verify_email(payload: VerifyEmailRequest, db: DbSession) -> UserRead:
    """Consume a verification token and mark the address as verified.

    The token is single-use, and the link in the email is the only copy of it.
    """
    user = account_service.verify_email(db, payload.token)
    return UserRead.model_validate(user)


@router.post(
    "/resend-verification",
    response_model=AcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Send another verification email",
    dependencies=[Depends(rate_limit("auth"))],
)
def resend_verification(db: DbSession, user: CurrentUser) -> AcceptedResponse:
    """Send a fresh verification email to the signed-in user."""
    account_service.send_verification(db, user)
    return AcceptedResponse(
        message="If that address needs confirming, a new link is on its way."
    )


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------
@router.post(
    "/forgot-password",
    response_model=AcceptedResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Ask for a password-reset link",
    dependencies=[Depends(rate_limit("auth"))],
    responses={
        429: {"description": "Too many requests from this address"},
    },
)
def forgot_password(payload: ForgotPasswordRequest, db: DbSession) -> AcceptedResponse:
    """Start a password reset.

    **The response is identical whether or not the address is registered.**
    Anything else would make this an account-enumeration oracle, which is the
    failure the legacy login route had.
    """
    account_service.request_password_reset(db, payload.email)
    return AcceptedResponse(
        message="If that address has an account, a reset link is on its way."
    )


@router.post(
    "/reset-password",
    response_model=UserRead,
    summary="Set a new password with a reset token",
    responses={
        422: {"description": "The link is invalid, used, or expired"},
    },
)
def reset_password(payload: ResetPasswordRequest, db: DbSession) -> UserRead:
    """Consume a reset token and set a new password.

    The password is checked against the same policy as every other password,
    and the sessions that were outstanding when the reset happened stop
    working immediately.
    """
    user = account_service.reset_password(db, payload.token, payload.new_password)
    return UserRead.model_validate(user)
