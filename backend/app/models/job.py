"""``JobRole`` and ``JobRoleSkill`` — the knowledge base the engine matches against.

``JobRoleSkill`` is the most important table in the schema. A comma-separated
string cannot express "Docker is 0.9 for MLOps Engineer and 0.3 for Data
Analyst"; a normalised (role, skill, weight) row can, and that difference *is* the
weighted-coverage requirement from proposal section 4.2.

Deletion semantics are deliberate and asymmetric: ``job_role_skill`` cascades from
``job_role`` (the requirement set goes with the role), but
``recommendation_result.job_role_id`` is ``ON DELETE RESTRICT`` — destroying a
user's recommendation history because an admin removed a role is a worse outcome
than an orphaned title, so the service returns ``409`` and suggests deactivating
(``is_active = false``) instead.
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:  # pragma: no cover
    from app.models.recommendation import RecommendationResult
    from app.models.skill import Skill


class JobRole(Base, TimestampMixin):
    __tablename__ = "job_role"
    __table_args__ = (
        CheckConstraint("length(trim(title)) > 0", name="title_not_blank"),
        CheckConstraint("length(trim(family)) > 0", name="family_not_blank"),
        # A role with no description cannot be TF-IDF-matched, so the database
        # refuses to hold one.
        CheckConstraint("length(trim(description)) > 0", name="description_not_blank"),
        Index("ix_job_role_family", "family"),
        Index("ix_job_role_active", "is_active"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(140), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(140), nullable=False, unique=True)
    family: Mapped[str] = mapped_column(String(80), nullable=False)
    seniority: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # This is the TF-IDF corpus document for the role.
    description: Mapped[str] = mapped_column(Text, nullable=False)
    responsibilities: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    skill_requirements: Mapped[list[JobRoleSkill]] = relationship(
        back_populates="job_role", cascade="all, delete-orphan", passive_deletes=True
    )
    results: Mapped[list[RecommendationResult]] = relationship(
        back_populates="job_role", passive_deletes=True
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<JobRole id={self.id} title={self.title!r} family={self.family!r}>"


class JobRoleSkill(Base):
    __tablename__ = "job_role_skill"
    __table_args__ = (
        # The scale is (0, 1]. A zero-weight requirement would mean "listed but
        # irrelevant", which the data model should not express — omit it instead.
        CheckConstraint("weight > 0 AND weight <= 1", name="weight_range"),
        # "Which roles need this skill?" — the reverse lookup.
        Index("ix_jrs_skill", "skill_id"),
    )

    job_role_id: Mapped[int] = mapped_column(
        ForeignKey("job_role.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skill.id", ondelete="CASCADE"), primary_key=True
    )
    weight: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False)

    job_role: Mapped[JobRole] = relationship(back_populates="skill_requirements")
    skill: Mapped[Skill] = relationship(back_populates="role_requirements", lazy="joined")

    def as_float(self) -> float:
        return float(self.weight)

    def __repr__(self) -> str:  # pragma: no cover
        return f"<JobRoleSkill role={self.job_role_id} skill={self.skill_id} w={self.weight}>"
