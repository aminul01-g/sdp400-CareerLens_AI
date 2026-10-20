"""``RecommendationRun`` and ``RecommendationResult`` — the persisted engine output.

A run is **immutable by design**. Making results mutable would make the Phase 9
evaluation report unverifiable, because a reader could never tell whether a score
was produced by the engine version the report describes.

Provenance is the point of this pair:

* ``profile_snapshot`` records the exact skills/projects/education the run saw.
* ``coverage_weight`` / ``tfidf_weight`` record the weights actually used, so a run
  generated *before* Phase 9 weight tuning is still explicable.
* ``engine_version`` lets a past run be traced to the taxonomy that produced it.

``matched_skill_ids`` / ``missing_skill_ids`` are stored as **id arrays**, not
denormalised names. Joining ``skill`` at render time means renaming a skill
updates historical explanations for free — and lets the explainability test assert
that the two arrays partition the role's required set, which is a real correctness
check rather than a formatting one.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:  # pragma: no cover
    from app.models.job import JobRole
    from app.models.user import User


class RecommendationRun(Base):
    __tablename__ = "recommendation_run"
    __table_args__ = (
        CheckConstraint(
            "coverage_weight >= 0 AND tfidf_weight >= 0 AND coverage_weight + tfidf_weight = 1",
            name="weights_partition_unit_interval",
        ),
        CheckConstraint("candidate_count >= 0", name="candidate_count_non_negative"),
        Index("ix_run_user", "user_id", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("user.id", ondelete="CASCADE"), nullable=False
    )
    profile_snapshot: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    coverage_weight: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False)
    tfidf_weight: Mapped[Decimal] = mapped_column(Numeric(3, 2), nullable=False)
    engine_version: Mapped[str] = mapped_column(String(20), nullable=False)
    candidate_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    user: Mapped[User] = relationship(back_populates="recommendation_runs")
    results: Mapped[list[RecommendationResult]] = relationship(
        back_populates="run",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="RecommendationResult.rank",
    )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<RecommendationRun id={self.id} user_id={self.user_id}>"


class RecommendationResult(Base):
    __tablename__ = "recommendation_result"
    __table_args__ = (
        CheckConstraint("compatibility_score BETWEEN 0 AND 1", name="compatibility_range"),
        CheckConstraint("skill_coverage BETWEEN 0 AND 1", name="skill_coverage_range"),
        CheckConstraint("tfidf_similarity BETWEEN 0 AND 1", name="tfidf_similarity_range"),
        CheckConstraint("rank >= 1", name="rank_positive"),
        CheckConstraint(
            "declared_coverage BETWEEN 0 AND 1", name="declared_coverage_range"
        ),
        CheckConstraint("signal_coverage BETWEEN 0 AND 1", name="signal_coverage_range"),
        CheckConstraint("level_fit BETWEEN 0 AND 1", name="level_fit_range"),
        CheckConstraint("role_prior BETWEEN -1 AND 1", name="role_prior_range"),
        # Stable paging over a ranked list.
        Index("uq_result_rank", "run_id", "rank", unique=True),
    )

    run_id: Mapped[int] = mapped_column(
        ForeignKey("recommendation_run.id", ondelete="CASCADE"), primary_key=True
    )
    # RESTRICT, not CASCADE: a stored run is history, and history outlives the
    # admin who created the role. See the module docstring.
    job_role_id: Mapped[int] = mapped_column(
        ForeignKey("job_role.id", ondelete="RESTRICT"), primary_key=True
    )
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    compatibility_score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    skill_coverage: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    tfidf_similarity: Mapped[Decimal] = mapped_column(Numeric(6, 5), nullable=False)
    # The two intermediate coverages, so a stored run can be explained months
    # later without re-running the engine: what the user declared, and what it
    # was worth once recency, depth and level fit were applied.
    declared_coverage: Mapped[Decimal] = mapped_column(
        Numeric(6, 5), nullable=False, default=0, server_default="0"
    )
    signal_coverage: Mapped[Decimal] = mapped_column(
        Numeric(6, 5), nullable=False, default=0, server_default="0"
    )
    level_fit: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), nullable=False, default=1, server_default="1"
    )
    # The community prior applied to this row, and the number of observations
    # behind it. Stored, so a run explains itself months later.
    role_prior: Mapped[Decimal] = mapped_column(
        Numeric(4, 3), nullable=False, default=0, server_default="0"
    )
    feedback_samples: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    matched_skill_ids: Mapped[list[int]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )
    missing_skill_ids: Mapped[list[int]] = mapped_column(
        JSONB, nullable=False, default=list, server_default="[]"
    )

    run: Mapped[RecommendationRun] = relationship(back_populates="results")
    job_role: Mapped[JobRole] = relationship(back_populates="results", lazy="joined")

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<RecommendationResult run={self.run_id} role={self.job_role_id} "
            f"rank={self.rank} score={self.compatibility_score}>"
        )
