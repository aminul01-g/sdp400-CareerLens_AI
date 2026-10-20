"""``Profile`` — the user's narrative data.

Note what is **absent**: there is no ``skills``, ``education`` or ``experience``
TEXT column here. The legacy ``backend/models.py:26-28`` had exactly those three
columns, storing skills as a comma-separated string. A single string cannot
express per-skill proficiency, per-role importance weights, or a set difference
against a role's requirements — which are the three proposal requirements the
recommendation engine needs. They are replaced by the ``user_skill``,
``education_record`` and ``certification`` tables.

This is the single most important schema decision in the project.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:  # pragma: no cover
    from app.models.user import User


class Profile(Base, TimestampMixin):
    __tablename__ = "profile"
    __table_args__ = (
        CheckConstraint(
            "years_experience IS NULL OR years_experience BETWEEN 0 AND 60",
            name="years_experience_range",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # UNIQUE is what makes this 1:1 with the user.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )

    headline: Mapped[str | None] = mapped_column(String(200), nullable=True)
    career_goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    education_level: Mapped[str | None] = mapped_column(String(80), nullable=True)
    years_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    preferred_role_family: Mapped[str | None] = mapped_column(String(80), nullable=True)
    # The level the user is at. One of Entry/Junior/Mid/Senior/Lead/Principal;
    # compared against the role's own seniority when the engine scores a match.
    # ``None`` means "not stated", which the engine treats as neutral.
    seniority: Mapped[str | None] = mapped_column(String(40), nullable=True)
    # The sector the user works in. Topical, so it joins the profile text the
    # TF-IDF similarity is computed over.
    industry: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # {"github": ..., "linkedin": ..., "portfolio": ...}
    links: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )

    user: Mapped[User] = relationship(back_populates="profile")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Profile id={self.id} user_id={self.user_id}>"
