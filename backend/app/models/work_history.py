"""``WorkHistory`` — where somebody has worked, and for how long.

The limitations document said the CV pipeline produced "a bag of skill mentions
and some text. Nothing else is extracted, so nothing else influences the
score." One of the things worth extracting is the work history, because it is
what turns "years of experience" from a number the user typed into something
the document supports.

The table mirrors ``user_skill`` in its shape, and for the same reasons:

* ``source`` says whether the row was typed by the user or read out of a CV.
* ``confirmed`` says whether the user has accepted it. A row extracted by the
  pipeline is a **proposal**, and a proposal that the user has not accepted
  does not influence anything.
* ``resume_upload_id`` records where a proposed row came from, so it can be
  withdrawn with its upload.

Overlapping roles are legitimate — somebody can hold two jobs at once — and
are stored as they are written. The service layer is where the arithmetic
happens, because that is a policy question rather than a storage question.
"""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:  # pragma: no cover
    from app.models.resume import ResumeUpload
    from app.models.user import User


class WorkHistorySource(StrEnum):
    """Where a work-history row came from."""

    MANUAL = "manual"
    CV_EXTRACTED = "cv_extracted"


class WorkHistory(Base, TimestampMixin):
    __tablename__ = "work_history"
    __table_args__ = (
        CheckConstraint(
            "source IN ('manual','cv_extracted')", name="source_valid"
        ),
        CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR end_date >= start_date",
            name="end_date_after_start",
        ),
        CheckConstraint("length(trim(employer)) > 0", name="employer_not_blank"),
        # "What has this user done?"
        Index("ix_work_history_user", "user_id", "start_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    employer: Mapped[str] = mapped_column(String(160), nullable=False)
    title: Mapped[str | None] = mapped_column(String(160), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, default=WorkHistorySource.MANUAL.value,
        server_default=WorkHistorySource.MANUAL.value,
    )
    # A row read out of a CV is a proposal until the user accepts it.
    confirmed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    # Where a proposed row came from, so it can be withdrawn with its upload.
    resume_upload_id: Mapped[int | None] = mapped_column(
        ForeignKey("resume_upload.id", ondelete="CASCADE"), nullable=True
    )
    # The text the proposal was read from, so the user can see what the system
    # thinks it read.
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped[User] = relationship()
    resume_upload: Mapped[ResumeUpload | None] = relationship()

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<WorkHistory id={self.id} user_id={self.user_id} "
            f"employer={self.employer!r} source={self.source!r}>"
        )
