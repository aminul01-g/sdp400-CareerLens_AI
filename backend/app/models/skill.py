"""``Skill`` and ``SkillAlias`` — the curated taxonomy.

``SkillAlias.alias`` is the **primary key**, which is a deliberate choice. The
extractor's inner loop is "map this matched string to a skill id". Making the
lookup column the key turns that into a single indexed probe rather than a scan,
and — more importantly — makes a duplicate alias impossible at the storage layer
rather than by convention. One alias claimed by two skills would mean one of
them can never be detected, so the database must make it unrepresentable.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:  # pragma: no cover
    from app.models.job import JobRoleSkill
    from app.models.resume import ResumeDetectedSkill
    from app.models.user_skill import UserSkill

SKILL_CATEGORIES: tuple[str, ...] = (
    "Programming & Core",
    "Data Engineering",
    "Statistics & Mathematics",
    "ML Frameworks",
    "Deep Learning",
    "NLP & LLM",
    "MLOps & Cloud",
    "Analytics & Communication",
)


class Skill(Base, TimestampMixin):
    __tablename__ = "skill"
    __table_args__ = (Index("ix_skill_category", "category"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Display form, e.g. "Scikit-learn".
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    # Stable key, e.g. "scikit-learn". Used by the seed files and the API.
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    category: Mapped[str] = mapped_column(String(60), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    aliases: Mapped[list[SkillAlias]] = relationship(
        back_populates="skill", cascade="all, delete-orphan", passive_deletes=True
    )
    user_skills: Mapped[list[UserSkill]] = relationship(
        back_populates="skill", cascade="all, delete-orphan", passive_deletes=True
    )
    role_requirements: Mapped[list[JobRoleSkill]] = relationship(
        back_populates="skill", cascade="all, delete-orphan", passive_deletes=True
    )
    detected_instances: Mapped[list[ResumeDetectedSkill]] = relationship(
        back_populates="skill", cascade="all, delete-orphan", passive_deletes=True
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Skill id={self.id} slug={self.slug!r}>"


class SkillAlias(Base):
    __tablename__ = "skill_alias"
    __table_args__ = (Index("ix_skill_alias_skill", "skill_id"),)

    # Lowercased surface form. Primary key by design — see the module docstring.
    alias: Mapped[str] = mapped_column(String(120), primary_key=True)
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skill.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    skill: Mapped[Skill] = relationship(back_populates="aliases")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<SkillAlias alias={self.alias!r} -> skill_id={self.skill_id}>"
