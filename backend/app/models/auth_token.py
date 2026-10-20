"""``AuthToken`` — one-time tokens for email verification and password reset.

The table is the server-side half of the two flows the limitations document
used to say were missing:

* **Email verification.** ``purpose = 'email_verification'``.
* **Password reset.** ``purpose = 'password_reset'``.

Four properties are deliberate:

1. **Only the hash is stored.** The plaintext token exists in the email and
   nowhere else, so a database leak does not hand out working reset links.
2. **A token is single-use.** ``used_at`` is set when the token is consumed,
   and a consumed token is refused. Issuing a new one invalidates the old.
3. **A token expires.** ``expires_at`` is checked on every use.
4. **Only one live token per purpose per user.** Issuing a new one deletes
   the outstanding ones, so a user who requests three reset links has one
   that works, not three.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:  # pragma: no cover
    from app.models.user import User


class TokenPurpose(StrEnum):
    """What a token may be used for.

    A token issued for one purpose is never accepted for the other. The
    purpose is part of the lookup, not a field that is checked afterwards.
    """

    EMAIL_VERIFICATION = "email_verification"
    PASSWORD_RESET = "password_reset"


class AuthToken(Base):
    __tablename__ = "auth_token"
    __table_args__ = (
        # A token is looked up by its hash, and the hash is unique.
        Index("uq_auth_token_hash", "token_hash", unique=True),
        # "Which live tokens does this user have?"
        Index("ix_auth_token_user", "user_id", "purpose"),
        # A token is issued for one purpose and is never accepted for the
        # other. The database refuses the third possibility, so the
        # application never has to decide what to do with one.
        CheckConstraint(
            "purpose IN ('email_verification','password_reset')",
            name="purpose_valid",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    # SHA-256 of the token. Never the token itself.
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Set when the token is consumed. A token with this set is refused.
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped[User] = relationship()

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<AuthToken id={self.id} user_id={self.user_id} "
            f"purpose={self.purpose!r} expired={self.expires_at.isoformat()}>"
        )
