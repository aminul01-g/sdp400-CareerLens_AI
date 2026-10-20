"""``User`` — the authentication identity and the authorization role."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Index,
    Integer,
    String,
    func,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:  # pragma: no cover
    from app.models.education import Certification, EducationRecord
    from app.models.profile import Profile
    from app.models.project import Project
    from app.models.recommendation import RecommendationRun
    from app.models.resume import ResumeUpload
    from app.models.user_skill import UserSkill


class UserRole(StrEnum):
    """The two roles the proposal requires (section 4.1, "User/Admin roles")."""

    USER = "user"
    ADMIN = "admin"


class User(Base, TimestampMixin):
    __tablename__ = "user"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="name_not_blank"),
        CheckConstraint("length(trim(email)) > 0", name="email_not_blank"),
        Index("ix_user_role", "role"),
        # A functional unique index on lower(email) is what actually closes
        # security finding S9: the legacy app compared raw strings, so
        # "A@B.com" and "a@b.com" became two separate accounts.
        Index("uq_user_email_lower", func.lower("email"), unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=UserRole.USER,
        server_default=UserRole.USER.value,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    # Whether the address has been proven to belong to the person who
    # registered it. The gate on this is off by default — see
    # ``Settings.require_email_verification`` — because a product that locks
    # out a user who has not clicked a link reads as broken.
    is_verified: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # When the password last changed. Kept for the audit trail and for display.
    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # A counter, bumped whenever the sessions that were outstanding should stop
    # working. It is embedded in every token, and a token whose counter does not
    # match the user's is refused.
    #
    # A timestamp was the obvious alternative and it is subtly wrong: ``iat`` is
    # an integer number of seconds, so a token issued in the same second as a
    # password change cannot be ordered against it. Either the change is missed
    # or a user who resets their password and signs in immediately is locked
    # out. A counter has no such ambiguity.
    token_version: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )

    # Every child cascades. Deleting a user must remove the whole subtree in one
    # statement (verified by tests/test_cascade.py). passive_deletes=True tells
    # the ORM to let the database do it instead of issuing a SELECT-then-DELETE
    # per row.
    profile: Mapped[Profile | None] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True, uselist=False
    )
    skills: Mapped[list[UserSkill]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    projects: Mapped[list[Project]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    education_records: Mapped[list[EducationRecord]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    certifications: Mapped[list[Certification]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    resume_uploads: Mapped[list[ResumeUpload]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )
    recommendation_runs: Mapped[list[RecommendationRun]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<User id={self.id} email={self.email!r} role={self.role}>"
