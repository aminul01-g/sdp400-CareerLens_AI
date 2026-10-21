"""``LearningRoadmap`` and ``LearningRoadmapTask`` — a saved action plan.

A roadmap is a *user artefact*, not engine output. The engine decides which
skills are missing; the model decides the order, the exercises and the
project; the user decides what they actually do. All three are recorded, so
the plan can be reopened months later and still mean what it meant.

============================  ==========================================
Constraint                    Enforcement
============================  ==========================================
The plan is a snapshot        ``plan`` holds the document as it was generated.
                               Regenerating produces a new roadmap rather
                               than overwriting this one, so a plan a learner
                               is halfway through cannot change underneath
                               them
Progress is the user's        ``is_complete``, ``notes`` and
                               ``portfolio_url`` live on the task row, not
                               inside the JSON blob. A blob would make
                               "which tasks have I finished" a question
                               about JSON scanning rather than a query
The verified gap is recorded  ``gap_skills`` holds the skills the engine
                               reported as missing when the plan was made,
                               so a later gap report can be compared with
                               what the plan actually targeted
============================  ==========================================
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:  # pragma: no cover
    from app.models.job import JobRole
    from app.models.user import User

#: The two plan lengths the application offers.
ALLOWED_DURATIONS = (4, 6)

#: The languages a plan may be written in.
ALLOWED_LANGUAGES = ("en", "bn")

#: The same lists as SQL fragments, for the check constraints.
_DURATION_CHECK = (
    "duration_weeks IN (" + ", ".join(str(value) for value in ALLOWED_DURATIONS) + ")"
)
_LANGUAGE_CHECK = "language IN (" + ", ".join(f"'{value}'" for value in ALLOWED_LANGUAGES) + ")"


class LearningRoadmap(Base):
    __tablename__ = "learning_roadmap"
    __table_args__ = (
        CheckConstraint(_DURATION_CHECK, name="duration_weeks_allowed"),
        CheckConstraint(_LANGUAGE_CHECK, name="language_allowed"),
        CheckConstraint("length(trim(title)) > 0", name="title_not_blank"),
        Index("ix_roadmap_user", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    # SET NULL, not RESTRICT: a saved plan belongs to the learner, not to the
    # role. An administrator retiring a role from the knowledge base must not
    # destroy somebody's plan.
    job_role_id: Mapped[int | None] = mapped_column(
        ForeignKey("job_role.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    duration_weeks: Mapped[int] = mapped_column(Integer, nullable=False)
    language: Mapped[str] = mapped_column(String(2), nullable=False, default="en")
    #: The generated document, exactly as it was produced.
    plan: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    #: Which provider produced it, e.g. ``groq:openai/gpt-oss-120b``.
    generated_by: Mapped[str] = mapped_column(String(80), nullable=False)
    #: The skills the engine reported as missing when this plan was made.
    gap_skills: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
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

    user: Mapped[User] = relationship(back_populates="learning_roadmaps")
    job_role: Mapped[JobRole | None] = relationship(lazy="joined")
    tasks: Mapped[list[LearningRoadmapTask]] = relationship(
        back_populates="roadmap",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="LearningRoadmapTask.position",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<LearningRoadmap id={self.id} user_id={self.user_id} title={self.title!r}>"


class LearningRoadmapTask(Base):
    __tablename__ = "learning_roadmap_task"
    __table_args__ = (
        CheckConstraint("week >= 1", name="week_positive"),
        CheckConstraint("position >= 1", name="position_positive"),
        CheckConstraint("length(trim(title)) > 0", name="title_not_blank"),
        # One task key per roadmap. The key is what the API path addresses, so
        # it has to be unique within the plan it belongs to.
        Index("uq_roadmap_task_key", "roadmap_id", "task_key", unique=True),
        Index("ix_roadmap_task_roadmap", "roadmap_id", "position"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    roadmap_id: Mapped[int] = mapped_column(
        ForeignKey("learning_roadmap.id", ondelete="CASCADE"), nullable=False
    )
    #: Stable within the plan, e.g. ``w1-02``. Derived from the plan's own
    #: ordering, so it survives the plan document being re-serialised.
    task_key: Mapped[str] = mapped_column(String(24), nullable=False)
    week: Mapped[int] = mapped_column(Integer, nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(300), nullable=False)
    is_complete: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    portfolio_url: Mapped[str] = mapped_column(
        String(600), nullable=False, default="", server_default=""
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
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

    roadmap: Mapped[LearningRoadmap] = relationship(back_populates="tasks")

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<LearningRoadmapTask id={self.id} roadmap_id={self.roadmap_id} "
            f"key={self.task_key!r} complete={self.is_complete}>"
        )
