"""``ResumeUpload`` and ``ResumeDetectedSkill`` — the CV staging area.

The staging table is the mechanism that makes "every skill in ``user_skill`` is
user-confirmed" a *checkable invariant* rather than a UI convention. If detection
wrote straight into ``user_skill``, a false positive would silently inflate a
coverage score and a false negative would silently deflate it, with no record that
the value was never confirmed. The engine reads ``user_skill`` and never
``resume_detected_skill``.

``user_id`` is NOT NULL. In the legacy Flask app the upload routes used
``@jwt_required(optional=True)``, so anonymous callers wrote rows with
``user_id = NULL`` that were permanently unattributable (security finding S4).
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:  # pragma: no cover
    from app.models.skill import Skill
    from app.models.user import User

MAX_UPLOAD_BYTES = 5 * 1024 * 1024


class ResumeStatus(StrEnum):
    """Lifecycle of one upload."""

    UPLOADED = "uploaded"
    EXTRACTED = "extracted"
    CONFIRMED = "confirmed"
    FAILED = "failed"


class ResumeUpload(Base):
    __tablename__ = "resume_upload"
    __table_args__ = (
        CheckConstraint(
            "status IN ('uploaded','extracted','confirmed','failed')",
            name="status_valid",
        ),
        # Defence in depth: the route already rejects oversize files with 413,
        # but the database refuses to hold one even if that check is bypassed.
        CheckConstraint(f"size_bytes <= {MAX_UPLOAD_BYTES}", name="size_bytes_max"),
        Index("ix_resume_user", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    # UUID + extension. Preserves the working storage pattern from the legacy
    # guidance.py:18 while removing the user's original filename from the path,
    # which is what prevents path traversal.
    stored_filename: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    content_type: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ResumeStatus.UPLOADED.value,
        server_default=ResumeStatus.UPLOADED.value,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="resume_uploads")
    detected_skills: Mapped[list[ResumeDetectedSkill]] = relationship(
        back_populates="upload", cascade="all, delete-orphan", passive_deletes=True
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ResumeUpload id={self.id} user_id={self.user_id} status={self.status!r}>"


class ResumeDetectedSkill(Base):
    __tablename__ = "resume_detected_skill"
    __table_args__ = (
        CheckConstraint("occurrence_count > 0", name="occurrence_count_positive"),
        Index("ix_rds_accepted", "resume_upload_id", "accepted"),
    )

    resume_upload_id: Mapped[int] = mapped_column(
        ForeignKey("resume_upload.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skill.id", ondelete="CASCADE"), primary_key=True
    )
    # What literally appeared in the document, e.g. "sklearn".
    surface_form: Mapped[str] = mapped_column(String(120), nullable=False)
    match_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    match_end: Mapped[int | None] = mapped_column(Integer, nullable=True)
    occurrence_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1, server_default="1"
    )
    accepted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )

    upload: Mapped[ResumeUpload] = relationship(back_populates="detected_skills")
    skill: Mapped[Skill] = relationship(back_populates="detected_instances", lazy="joined")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ResumeDetectedSkill upload={self.resume_upload_id} skill={self.skill_id}>"
