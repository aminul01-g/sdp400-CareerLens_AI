"""``UserSkill`` — the replacement for the legacy ``profile.skills`` string.

One row per (user, skill) is what makes three otherwise-impossible requirements
representable:

1. **Per-skill proficiency.** ``"python,sql,ml"`` has three tokens and nowhere to
   store three different proficiency values.
2. **Weighted coverage.** Importance is per *(role, skill)* pair, so it lives on
   ``job_role_skill``, not here. What lives here is the user's own strength, which
   is what the coverage function scales by.
3. **Set-difference gap analysis.** Canonical ``skill_id`` rather than free text,
   so ``sklearn`` and ``Scikit-learn`` cannot become two different facts about
   one person.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Numeric,
    SmallInteger,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:  # pragma: no cover
    from app.models.skill import Skill
    from app.models.user import User

MIN_PROFICIENCY = 1
MAX_PROFICIENCY = 5


class SkillSource(StrEnum):
    """Provenance of a skill record."""

    MANUAL = "manual"
    CV_EXTRACTED = "cv_extracted"


class UserSkill(Base, TimestampMixin):
    __tablename__ = "user_skill"
    __table_args__ = (
        CheckConstraint(
            f"proficiency BETWEEN {MIN_PROFICIENCY} AND {MAX_PROFICIENCY}",
            name="proficiency_range",
        ),
        CheckConstraint(
            "source IN ('manual','cv_extracted')",
            name="source_valid",
        ),
        CheckConstraint(
            "years_used IS NULL OR years_used >= 0",
            name="years_used_non_negative",
        ),
        # Reverse lookup for the admin "most-required skills" view.
        Index("ix_user_skill_skill", "skill_id"),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), primary_key=True
    )
    skill_id: Mapped[int] = mapped_column(
        ForeignKey("skill.id", ondelete="CASCADE"), primary_key=True
    )
    proficiency: Mapped[int] = mapped_column(
        SmallInteger, nullable=False, default=3, server_default="3"
    )
    source: Mapped[str] = mapped_column(
        String(20), nullable=False, default=SkillSource.MANUAL.value,
        server_default=SkillSource.MANUAL.value,
    )
    years_used: Mapped[Decimal | None] = mapped_column(Numeric(3, 1), nullable=True)
    # When the skill was last used. ``None`` means "not stated", which the engine
    # treats as neutral — a skill with no date is not treated as a stale one.
    last_used_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    # Distinguishes "extracted from a CV" from "the user confirmed this".
    # Together with `source` this implements the proposal's "show detected skills
    # for user confirmation" as *data*, not as transient UI state.
    confirmed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    user: Mapped[User] = relationship(back_populates="skills")
    skill: Mapped[Skill] = relationship(back_populates="user_skills", lazy="joined")

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<UserSkill user_id={self.user_id} skill_id={self.skill_id} "
            f"proficiency={self.proficiency}>"
        )
