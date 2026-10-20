"""Create the single admin account from environment variables.

Run:  python -m scripts.seed_admin

Reads ``ADMIN_EMAIL`` / ``ADMIN_PASSWORD`` from the environment (``.env``). It
refuses the ``.env.example`` placeholder password and refuses anything that would
fail the application's own registration policy — so the seeded admin is one the
rest of the system would accept.

Idempotent: re-running resets the password and role rather than creating a
duplicate, which is what makes it safe as a deployment step. It is run as part
of the start command, so a deployment with no admin configured logs a warning
and carries on rather than failing to boot.
"""

from __future__ import annotations

import logging
import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import session_scope
from app.models.user import User, UserRole
from app.schemas.auth import validate_password_strength

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("seed_admin")

PLACEHOLDER_MARKERS = ("ChangeMe", "CHANGE_ME", "changeme", "replace-with")
# Must be a domain the API's `EmailStr` accepts. `.local` is reserved by
# RFC 6762 for mDNS, so an admin seeded with it is created fine here and then
# rejected at login with a 422 that no user can act on.
DEFAULT_ADMIN_EMAIL = "admin@careerlens.dev"


def seed(db: Session) -> User:
    settings = get_settings()
    email = settings.admin_email.strip()
    password = settings.admin_password

    if not email or not password:
        raise SystemExit(
            "ADMIN_EMAIL and ADMIN_PASSWORD must be set. Add them to backend/.env "
            f"(see .env.example) and re-run. ENVIRONMENT={settings.environment}"
        )
    if any(marker in password for marker in PLACEHOLDER_MARKERS):
        raise SystemExit(
            "ADMIN_PASSWORD still holds the .env.example placeholder. Generate a real "
            'one, e.g. python -c "import secrets; print(\'Adm-\' + secrets.token_urlsafe(16))"'
        )
    try:
        validate_password_strength(password)
    except ValueError as exc:
        raise SystemExit(f"ADMIN_PASSWORD does not meet the password policy: {exc}") from exc

    normalised = email.strip().lower()
    user = db.scalar(select(User).where(User.email == normalised))

    if user is None:
        user = User(
            name="CareerLens Administrator",
            email=normalised,
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"Created admin user id={user.id} email={user.email}")
        return user

    user.password_hash = hash_password(password)
    user.role = UserRole.ADMIN
    user.is_active = True
    db.commit()
    db.refresh(user)
    print(f"Updated admin user id={user.id} email={user.email}")
    return user


def main() -> int:
    logger.info("Seeding the admin account")
    settings = get_settings()
    if not settings.admin_email.strip() or not settings.admin_password:
        # Not an error. The admin account is optional: the application works
        # perfectly well without one, and a deployment that does not want an
        # administrator should not fail to boot because of it. The seed runs
        # as part of the start command, so raising here would take the whole
        # service down.
        logger.warning(
            "ADMIN_EMAIL and ADMIN_PASSWORD are not set; no admin account was created. "
            "Set them and redeploy if this deployment needs an administrator."
        )
        return 0
    with session_scope() as db:
        seed(db)
    return 0


if __name__ == "__main__":
    sys.exit(main())
