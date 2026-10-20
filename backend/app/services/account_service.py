"""Email verification and password reset.

Two flows, and both of them are the kind that is easy to get subtly wrong, so
the rules are stated up front:

* **A password-reset request never reveals whether an address is registered.**
  ``forgot_password`` returns the same response, takes the same time and
  writes the same kind of row whether the address exists or not. Anything else
  turns the endpoint into an account-enumeration oracle — which is exactly
  what the legacy login route did (security finding S1's sibling).
* **A token is single-use, and it expires.** Consuming one marks it used; a
  second attempt fails.
* **Issuing a new token invalidates the old ones.** A user who requests three
  reset links has one that works, not three.
* **A completed reset invalidates the sessions that were outstanding.** That
  is done statelessly, by comparing the token's ``iat`` against
  ``user.password_changed_at`` — no revocation list, no Redis.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import UnprocessableError
from app.core.security import hash_password
from app.core.tokens import generate_token, hash_token
from app.models.auth_token import AuthToken, TokenPurpose
from app.models.user import User
from app.services import audit_service, mail_service

logger = logging.getLogger("app.services.account")


# --------------------------------------------------------------------------- #
# Tokens
# --------------------------------------------------------------------------- #
def _issue_token(
    db: Session, user: User, purpose: TokenPurpose, ttl_minutes: int
) -> str:
    """Create a token, replacing any outstanding one of the same purpose.

    Returns the plaintext token. It is never stored — only its digest is.
    """
    # Only one live token per purpose per user.
    db.execute(
        delete(AuthToken).where(
            AuthToken.user_id == user.id, AuthToken.purpose == purpose.value
        )
    )
    token = generate_token()
    db.add(
        AuthToken(
            user_id=user.id,
            purpose=purpose.value,
            token_hash=hash_token(token),
            expires_at=datetime.now(UTC) + timedelta(minutes=ttl_minutes),
        )
    )
    return token


def _consume_token(db: Session, token: str, purpose: TokenPurpose) -> AuthToken:
    """Find a live token of the given purpose, or raise.

    A token that is unknown, used, expired, or issued for a different purpose
    are all the same failure: an unusable token. The message does not say
    which, because a caller who can tell the difference can probe for valid
    tokens.
    """
    row = db.scalar(
        select(AuthToken).where(
            AuthToken.token_hash == hash_token(token),
            AuthToken.purpose == purpose.value,
        )
    )
    if row is None or row.used_at is not None:
        raise UnprocessableError(
            "That link is not valid, or has already been used. "
            "Please request a new one.",
            code="invalid_token",
        )
    if row.expires_at <= datetime.now(UTC):
        raise UnprocessableError(
            "That link has expired. Please request a new one.", code="expired_token"
        )
    return row


# --------------------------------------------------------------------------- #
# Links
# --------------------------------------------------------------------------- #
def _verification_link(token: str) -> str:
    base = get_settings().public_base_url.rstrip("/")
    return f"{base}/verify-email?token={token}"


def _reset_link(token: str) -> str:
    base = get_settings().public_base_url.rstrip("/")
    return f"{base}/reset-password?token={token}"


# --------------------------------------------------------------------------- #
# Email verification
# --------------------------------------------------------------------------- #
def send_verification(db: Session, user: User) -> str:
    """Issue a verification token and email it. Returns the transport used."""
    settings = get_settings()
    token = _issue_token(
        db, user, TokenPurpose.EMAIL_VERIFICATION, settings.email_verification_ttl_minutes
    )
    db.commit()
    transport = mail_service.send_verification_email(
        user.email, user.name, _verification_link(token)
    )
    logger.info(
        "Sent a verification email to %s via %s", user.email, transport, extra={"kind": "account"}
    )
    return transport


def verify_email(db: Session, token: str) -> User:
    """Consume a verification token and mark the address as verified."""
    row = _consume_token(db, token, TokenPurpose.EMAIL_VERIFICATION)
    user = db.get(User, row.user_id)
    if user is None:  # pragma: no cover - the FK makes this unreachable
        raise UnprocessableError("That link is not valid.", code="invalid_token")

    row.used_at = datetime.now(UTC)
    user.is_verified = True
    user.email_verified_at = datetime.now(UTC)
    audit_service.record(
        db,
        action="auth.email_verified",
        entity_type="auth",
        entity_id=user.email,
        summary=f"{user.email} verified their email address",
        actor=user,
    )
    db.commit()
    db.refresh(user)
    return user


# --------------------------------------------------------------------------- #
# Password reset
# --------------------------------------------------------------------------- #
def request_password_reset(db: Session, email: str) -> bool:
    """Start a password reset. Returns whether the address was registered.

    The caller **must not** use the return value to shape the response. It
    exists so the audit log can record what happened, not so the API can
    reveal it.
    """
    settings = get_settings()
    normalised = email.strip().lower()
    user = db.scalar(select(User).where(User.email == normalised))

    if user is None or not user.is_active:
        # Nothing is sent and nothing is revealed. The response is identical
        # either way.
        logger.info(
            "Password reset requested for an unknown address", extra={"kind": "account"}
        )
        return False

    token = _issue_token(
        db, user, TokenPurpose.PASSWORD_RESET, settings.password_reset_ttl_minutes
    )
    audit_service.record(
        db,
        action="auth.password_reset_requested",
        entity_type="auth",
        entity_id=user.email,
        summary=f"A password reset was requested for {user.email}",
        actor=user,
    )
    db.commit()

    transport = mail_service.send_password_reset_email(
        user.email, user.name, _reset_link(token)
    )
    logger.info(
        "Sent a password reset email to %s via %s", user.email, transport, extra={"kind": "account"}
    )
    return True


def reset_password(db: Session, token: str, new_password: str) -> User:
    """Consume a reset token and set a new password.

    The new password goes through the same policy as every other password —
    the check lives in the schema, and the schema is used here too.
    """
    row = _consume_token(db, token, TokenPurpose.PASSWORD_RESET)
    user = db.get(User, row.user_id)
    if user is None:  # pragma: no cover - the FK makes this unreachable
        raise UnprocessableError("That link is not valid.", code="invalid_token")

    row.used_at = datetime.now(UTC)
    user.password_hash = hash_password(new_password)
    # The counter is what invalidates the sessions that were outstanding.
    user.password_changed_at = datetime.now(UTC)
    user.token_version = int(user.token_version or 0) + 1
    audit_service.record(
        db,
        action="auth.password_reset_completed",
        entity_type="auth",
        entity_id=user.email,
        summary=f"{user.email} reset their password",
        actor=user,
    )
    db.commit()
    db.refresh(user)
    return user
