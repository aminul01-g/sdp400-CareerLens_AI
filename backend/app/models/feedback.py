"""``Feedback`` — a thin in-app feature, not a core table.

The proposal does not list feedback among its nine modules, so it is not part of
the 14-table core. It is kept because the UI for it already exists in the
predecessor app and costs nothing, and the compliance matrix records it as a
retained extra rather than a proposal requirement.

The legacy ``Event`` analytics table is **not** recreated: it has no proposal
justification and the client-side export that wrote it had no caller.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Integer, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:  # pragma: no cover
    from app.models.user import User


class Feedback(Base):
    __tablename__ = "feedback"
    __table_args__ = (
        CheckConstraint(
            "category IN ('general','bug','feature','ui','data','other')",
            name="category_valid",
        ),
        CheckConstraint("rating IS NULL OR rating BETWEEN 1 AND 5", name="rating_range"),
        Index("ix_feedback_user", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # NOT NULL: the legacy routes used @jwt_required(optional=True), so anonymous
    # callers wrote rows with user_id = NULL that were permanently unattributable
    # (security finding S4). Auth is now required.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(60), nullable=False, server_default="general")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    rating: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped[User] = relationship()

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Feedback id={self.id} user_id={self.user_id} category={self.category!r}>"
