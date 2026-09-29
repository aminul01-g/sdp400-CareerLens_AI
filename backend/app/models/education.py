"""``EducationRecord`` and ``Certification``.

These are two tables rather than one table with a ``kind`` discriminator because
they genuinely differ: a certification has an **issuer** and a **credential URL**,
a degree has an **institution** and a **grade**. Merging them forces every
consumer to null-check four columns it never uses. The proposal names them
together (section 4.1) but they are different concepts.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Integer, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

if TYPE_CHECKING:  # pragma: no cover
    from app.models.user import User

MIN_YEAR = 1950
MAX_YEAR = 2100


class EducationRecord(Base, TimestampMixin):
    __tablename__ = "education_record"
    __table_args__ = (
        CheckConstraint("length(trim(institution)) > 0", name="institution_not_blank"),
        CheckConstraint("length(trim(degree)) > 0", name="degree_not_blank"),
        CheckConstraint(
            "end_year IS NULL OR start_year IS NULL OR end_year >= start_year",
            name="end_year_after_start",
        ),
        CheckConstraint(
            f"(start_year IS NULL OR start_year BETWEEN {MIN_YEAR} AND {MAX_YEAR}) "
            f"AND (end_year IS NULL OR end_year BETWEEN {MIN_YEAR} AND {MAX_YEAR})",
            name="year_range",
        ),
        Index("ix_education_user", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    institution: Mapped[str] = mapped_column(String(180), nullable=False)
    degree: Mapped[str] = mapped_column(String(120), nullable=False)
    field_of_study: Mapped[str | None] = mapped_column(String(120), nullable=True)
    start_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    end_year: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    grade: Mapped[str | None] = mapped_column(String(40), nullable=True)

    user: Mapped[User] = relationship(back_populates="education_records")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<EducationRecord id={self.id} degree={self.degree!r}>"


class Certification(Base, TimestampMixin):
    __tablename__ = "certification"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="name_not_blank"),
        CheckConstraint("length(trim(issuer)) > 0", name="issuer_not_blank"),
        CheckConstraint(
            "expires_on IS NULL OR issued_on IS NULL OR expires_on > issued_on",
            name="expires_after_issued",
        ),
        Index("ix_certification_user", "user_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    issuer: Mapped[str] = mapped_column(String(160), nullable=False)
    issued_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    expires_on: Mapped[date | None] = mapped_column(Date, nullable=True)
    credential_url: Mapped[str | None] = mapped_column(String(400), nullable=True)

    user: Mapped[User] = relationship(back_populates="certifications")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Certification id={self.id} name={self.name!r}>"
