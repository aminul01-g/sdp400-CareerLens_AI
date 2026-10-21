"""``InterviewSession`` and ``InterviewExchange`` — a saved mock interview.

A session is a conversation, so it is stored as a session with an ordered list
of exchanges rather than as one wide row. Each exchange keeps the question,
the answer and the feedback that was given, which is what makes the history
page useful: a learner can read what they said and what they were told, weeks
later, and try the same question again.

============================  ==========================================
Constraint                    Enforcement
============================  ==========================================
The rubric is stored          ``rubric`` holds the five dimensions, their
                               descriptions and the maximum score that were
                               in force when the session ran. A score is
                               therefore explicable months later, and a
                               change to the rubric cannot retroactively
                               change what an old score meant
The rating is the model's      The per-dimension ratings come from the
                               provider, but the total is computed here, and
                               the dimensions are fixed in code. The provider
                               cannot invent a dimension
The language is recorded       ``language`` is the language the feedback was
                               given in, so re-reading a session shows the
                               same language the learner was reading
============================  ==========================================
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:  # pragma: no cover
    from app.models.job import JobRole
    from app.models.user import User

#: The languages an interview may be conducted in.
ALLOWED_LANGUAGES = ("en", "bn")

#: The same list as a SQL fragment, for the check constraint.
_LANGUAGE_CHECK = "language IN (" + ", ".join(f"'{value}'" for value in ALLOWED_LANGUAGES) + ")"


class InterviewSession(Base):
    __tablename__ = "interview_session"
    __table_args__ = (
        CheckConstraint(_LANGUAGE_CHECK, name="language_allowed"),
        CheckConstraint("length(trim(job_label)) > 0", name="job_label_not_blank"),
        Index("ix_interview_session_user", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    job_role_id: Mapped[int | None] = mapped_column(
        ForeignKey("job_role.id", ondelete="SET NULL"), nullable=True
    )
    #: The role title, or a short description of a pasted job. Kept as text so
    #: a session survives the role it was for being retired.
    job_label: Mapped[str] = mapped_column(String(200), nullable=False)
    language: Mapped[str] = mapped_column(String(2), nullable=False, default="en")
    #: The rubric definition in force for this session.
    rubric: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped[User] = relationship(back_populates="interview_sessions")
    job_role: Mapped[JobRole | None] = relationship(lazy="joined")
    exchanges: Mapped[list[InterviewExchange]] = relationship(
        back_populates="session",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="InterviewExchange.position",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<InterviewSession id={self.id} user_id={self.user_id} "
            f"job={self.job_label!r}>"
        )


class InterviewExchange(Base):
    __tablename__ = "interview_exchange"
    __table_args__ = (
        CheckConstraint("position >= 1", name="position_positive"),
        # One exchange per position within a session.
        Index("uq_exchange_position", "session_id", "position", unique=True),
        Index("ix_exchange_session", "session_id", "position"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("interview_session.id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    #: The question, its category and what it assesses.
    question: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    answer: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    #: The validated feedback. Empty until the answer has been assessed.
    feedback: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    session: Mapped[InterviewSession] = relationship(back_populates="exchanges")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<InterviewExchange id={self.id} session_id={self.session_id} pos={self.position}>"
