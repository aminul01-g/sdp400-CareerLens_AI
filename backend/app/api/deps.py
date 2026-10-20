"""Route dependencies: database session, current user, role gate.

The authorization rules this module enforces, in one place, because retrofitting
them is how the legacy IDOR at ``guidance.py:31`` happened:

1. **Every write requires a valid token.** The legacy app used
   ``@jwt_required(optional=True)`` on four write endpoints (finding S4), so
   anonymous callers could create rows.
2. **Every read of user-owned data is scoped by ``user_id`` *in the query*,**
   never by loading a row and checking in Python. ``Upload.query.get(id)`` with a
   later ownership check is the pattern being replaced.
3. **A non-owner gets 404, not 403.** A 403 confirms the row exists, which is
   itself an information leak.
4. **No endpoint ever accepts a ``user_id`` from the client.** The identity always
   comes from the token.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Any

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import TokenError, decode_access_token
from app.db.session import get_db
from app.models.user import User, UserRole

# auto_error=False so a missing header reaches our handler and produces the
# standard error envelope instead of FastAPI's bare {"detail": ...}.
_bearer_scheme = HTTPBearer(auto_error=False, description="JWT access token")

DbSession = Annotated[Session, Depends(get_db)]
BearerToken = Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)]


def get_current_user(
    db: DbSession,
    credentials: BearerToken,
) -> User:
    """Resolve the authenticated user or raise ``401``.

    ``401`` is returned for: no token, a malformed token, a bad signature, an
    expired token, and a token naming a user that no longer exists. A suspended
    (``is_active = False``) account is also ``401`` — the account is not
    authenticable, and calling it "forbidden" would imply the credentials were
    accepted.
    """
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("Authentication is required.", code="unauthorized")

    try:
        payload = decode_access_token(credentials.credentials)
    except TokenError as exc:
        if str(exc) == "token_expired":
            raise UnauthorizedError(
                "Your session has expired. Please sign in again.", code="token_expired"
            ) from exc
        raise UnauthorizedError("Invalid authentication token.", code="token_invalid") from exc

    subject = payload.get("sub")
    if subject is None:
        raise UnauthorizedError("Invalid authentication token.", code="token_invalid")

    user = db.get(User, int(subject))
    if user is None:
        raise UnauthorizedError("Invalid authentication token.", code="token_invalid")
    if not user.is_active:
        raise UnauthorizedError(
            "This account has been deactivated.", code="account_disabled"
        )
    _reject_stale_session(user, payload)
    return user


def _reject_stale_session(user: User, payload: dict[str, Any]) -> None:
    """Refuse a token whose session counter is out of date.

    A password change has to invalidate the sessions that were outstanding
    when it happened, or "change your password because you think it is
    compromised" is not much of a remedy.

    The check is **stateless**. The token carries the user's session counter
    as ``ver``; the user row carries the current one; and a mismatch is
    refused. No revocation list, no Redis, and it works across replicas —
    which is the property a local blacklist would not have.

    A token issued before the ``ver`` claim existed reads as version 0, which
    is the value every account starts at, so an old token is refused exactly
    when the counter has moved on.
    """
    token_version = payload.get("ver")
    if token_version is None:
        token_version = 0
    if int(token_version) != int(user.token_version):
        raise UnauthorizedError(
            "Your password has changed since this session started. Please sign in again.",
            code="session_stale",
        )


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_active_user(user: CurrentUser) -> User:
    """Explicit "must be a usable account" gate, for readability at call sites."""
    if not user.is_active:  # pragma: no cover - get_current_user already checks
        raise ForbiddenError("This account has been deactivated.")
    return user


def require_role(role: UserRole | str) -> Callable[[User], User]:
    """Build a dependency that requires a specific role.

    Returns ``403`` for an authenticated user with the wrong role and ``401`` for
    an anonymous one — because ``get_current_user`` runs first, by dependency
    ordering. This replaces the single hand-rolled inline check at
    ``guidance.py:157-163``, which was applied to exactly one route.
    """
    required = role.value if isinstance(role, UserRole) else str(role)

    def _dependency(user: CurrentUser) -> User:
        if user.role.value != required:
            raise ForbiddenError(
                f"This action requires the '{required}' role.", code="forbidden"
            )
        return user

    _dependency.__name__ = f"require_{required}"
    return _dependency


RequireAdmin = Annotated[User, Depends(require_role(UserRole.ADMIN))]
RequireUser = Annotated[User, Depends(require_active_user)]


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------
def rate_limit(bucket: str) -> Callable[[], None]:
    """Build a dependency that rate-limits a route.

    Used as ``dependencies=[Depends(rate_limit("auth"))]``. The bucket decides
    which limit applies; the client address decides who is counted.

    The client address comes from the ambient request context, which the
    middleware in ``app/main.py`` sets. Reading it from there rather than from
    the ``Request`` means the dependency works the same whether it is applied
    to a route or a router.

    The address is only taken from ``X-Forwarded-For`` when the request came
    from a proxy in ``TRUSTED_PROXY_CIDRS``; otherwise it is the peer
    address. That matters here specifically: this limit is what stands
    between the password endpoints and a guessing attack, and a
    client-supplied header that the server believed unconditionally would
    let the caller rotate it and get an unlimited number of attempts.
    """

    def _dependency() -> None:
        from app.core.config import get_settings
        from app.core.rate_limit import check
        from app.core.request_context import current_client_ip

        settings = get_settings()
        if not settings.rate_limit_enabled:
            return

        limits = {
            "auth": (settings.rate_limit_auth_requests, settings.rate_limit_auth_window_seconds),
            "generate": (
                settings.rate_limit_generate_requests,
                settings.rate_limit_generate_window_seconds,
            ),
            "upload": (
                settings.rate_limit_upload_requests,
                settings.rate_limit_upload_window_seconds,
            ),
        }
        limit, window = limits.get(bucket, (0, 0))
        if limit <= 0:
            return
        check(
            f"{bucket}:{current_client_ip()}",
            limit=limit,
            window=float(window),
            bucket=bucket,
        )

    _dependency.__name__ = f"rate_limit_{bucket}"
    return _dependency


def get_client_ip(request: Request) -> str:
    """Best-effort client IP.

    The implementation lives in ``app.core.request_context`` so that the audit
    log can read the same value the middleware set, instead of re-deriving it
    and possibly disagreeing with it.
    """
    from app.core.config import get_settings
    from app.core.request_context import resolve_client_ip

    client, _peer = resolve_client_ip(
        request.client.host if request.client else None,
        request.headers.get("x-forwarded-for"),
        get_settings().trusted_proxy_networks,
    )
    return client
