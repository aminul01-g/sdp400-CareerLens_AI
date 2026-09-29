"""``Project`` — what the user has built.

``tech_stack`` stores **canonical taxonomy slugs**, not free text. The service
layer runs every entry through ``ml.taxonomy.canonicalise`` before persisting, so
``"sklearn"`` and ``"Scikit-learn"`` cannot become two different facts about the
same project.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Any

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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:  # pragma: no cover
    from app.models.user import User


class Project(Base, TimestampMixin):
    __tablename__ = "project"
    __table_args__ = (
        CheckConstraint(
            "start_date IS NULL OR end_date IS NULL OR end_date >= start_date",
            name="end_date_after_start",
        ),
        CheckConstraint("length(trim(title)) > 0", name="title_not_blank"),
        CheckConstraint("length(trim(description)) > 0", name="description_not_blank"),
        Index("ix_project_user", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    # Array of canonical taxonomy slugs.
    tech_stack: Mapped[list[str]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    role: Mapped[str | None] = mapped_column(String(120), nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    repo_url: Mapped[str | None] = mapped_column(String(400), nullable=True)
    is_public: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )

    user: Mapped[User] = relationship(back_populates="projects")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Project id={self.id} title={self.title!r}>"
