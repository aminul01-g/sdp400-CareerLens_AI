"""Password hashing and JWT issuance.

Two responsibilities, deliberately in one module because they are the two halves
of one security boundary:

* **bcrypt** via passlib for password storage. Werkzeug's PBKDF2 (used by the
  legacy ``backend/auth.py``) is perfectly adequate, but bcrypt is the
  proposal-compatible choice and is the algorithm every tool in the ecosystem
  recognises as "the" password hash.
* **PyJWT HS256** for access tokens, with explicit ``exp``, ``iat``, ``sub``,
  ``role`` and ``jti`` claims. The legacy implementation
  (``backend/auth.py:31``) called ``create_access_token(identity=...)`` with no
  expiry at all, so its tokens never expired.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any, Final

import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

# bcrypt silently truncates beyond 72 bytes; rejecting long inputs explicitly is
# better than accepting a password whose tail is ignored.
MAX_PASSWORD_BYTES: Final = 72
BCRYPT_ROUNDS: Final = 12

_pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=BCRYPT_ROUNDS,
)


class TokenError(Exception):
    """Raised when a token is absent, malformed, expired or badly signed."""


def hash_password(plain_password: str) -> str:
    """Hash a plaintext password with bcrypt."""
    encoded = plain_password.encode("utf-8")
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise ValueError(
            f"Password must not exceed {MAX_PASSWORD_BYTES} bytes when UTF-8 encoded."
        )
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Constant-time verification of a plaintext password against a bcrypt hash."""
    if not password_hash or len(plain_password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        return False
    try:
        return bool(_pwd_context.verify(plain_password, password_hash))
    except ValueError:
        # A malformed hash in the database must not become a 500.
        return False


def create_access_token(
    *,
    subject: str,
    role: str,
    expires_delta: timedelta | None = None,
    extra_claims: dict[str, Any] | None = None,
) -> tuple[str, int]:
    """Issue a signed access token.

    Returns the token and its lifetime in seconds so the API can tell the client
    when to refresh instead of making it guess.
    """
    settings = get_settings()
    now = datetime.now(UTC)
    expires_in = expires_delta or timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload: dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_in).timestamp()),
        "jti": uuid.uuid4().hex,
        "typ": "access",
    }
    if extra_claims:
        payload.update(extra_claims)

    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, int(expires_in.total_seconds())


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a signed access token.

    Raises:
        TokenError: the token is expired, malformed, or the signature is invalid.
    """
    settings = get_settings()
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["exp", "iat", "sub"]},
        )
    except jwt.ExpiredSignatureError as exc:
        raise TokenError("token_expired") from exc
    except jwt.InvalidTokenError as exc:
        raise TokenError("token_invalid") from exc
    return payload
