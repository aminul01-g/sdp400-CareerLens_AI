"""Declarative base, constraint naming convention, and shared mixins.

The ``naming_convention`` below is not cosmetic. Without it PostgreSQL
auto-names check constraints ``user_skill_proficiency_check``,
``user_skill_proficiency_check1``, ``user_skill_proficiency_check2``, ... and the
third Alembic autogenerate run starts producing spurious diffs. Fixing the names
at the metadata level makes every autogenerate and every ``downgrade()``
deterministic.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base for every CareerLens table."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    def to_dict(self) -> dict[str, Any]:
        """A plain dict of loaded columns. Used by audit logging, never by a
        response schema — response schemas are explicit on purpose so a new
        column cannot leak by accident."""
        return {
            column.key: getattr(self, column.key)
            for column in self.__table__.columns
            if getattr(self, column.key, None) is not None
        }

    def __repr__(self) -> str:  # pragma: no cover - developer convenience
        identifier = getattr(self, "id", None)
        return f"<{type(self).__name__} id={identifier}>"


class TimestampMixin:
    """``created_at`` / ``updated_at`` as ``TIMESTAMPTZ`` with server defaults."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
