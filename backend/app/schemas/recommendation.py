"""Recommendation and skill-gap response schemas.

The score decomposition is not decoration. It is the direct implementation of the
proposal's "explain each score with matched skills", and it is the differentiator
the competitor comparison claims over LinkedIn, Jobscan and Bdjobs — so the API
carries both components, both weights, and the per-skill evidence, rather than a
single opaque percentage.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, Field


class RecommendationRequest(BaseModel):
    """``POST /api/recommendations`` body. All fields optional."""

    limit: Annotated[int, Field(ge=1, le=50)] = 10
    role_family: Annotated[str | None, Field(max_length=80)] = None
    min_score: Annotated[float | None, Field(ge=0.0, le=1.0)] = None


class SkillContribution(BaseModel):
    """One skill's contribution to a role's score."""

    skill_id: int
    name: str
    weight: float = Field(..., description="Importance of this skill for the role, in (0, 1].")
    proficiency: int | None = Field(
        default=None, description="The user's proficiency; null for a missing skill."
    )
    category: str | None = None
    # Weighted contribution = weight * proficiency_factor, for matched skills.
    contribution: float = 0.0


class RoleRecommendation(BaseModel):
    """One ranked role, fully explained."""

    rank: int
    job_role_id: int
    title: str
    slug: str
    family: str
    seniority: str | None = None
    # 0-100, rounded for display. The stored value is the exact [0, 1] score.
    compatibility_pct: float
    skill_coverage: float
    tfidf_similarity: float
    matched_skills: list[SkillContribution] = Field(default_factory=list)
    missing_skills: list[SkillContribution] = Field(default_factory=list)
    coverage_contribution: float = 0.0
    tfidf_contribution: float = 0.0
    # The coverage the user declared, before recency and depth were applied.
    declared_coverage: float = 0.0
    # That coverage after the recency and depth adjustments.
    signal_coverage: float = 0.0
    # The multiplier for the distance between the user's level and the role's.
    # 1.0 when no level has been declared.
    level_fit: float = 1.0
    # The community signal for this role, in [-1, 1]. 0.0 when there is not
    # enough evidence to use one.
    role_prior: float = 0.0
    # How many observations the prior is based on.
    feedback_samples: int = 0


class RecommendationWeights(BaseModel):
    skill_coverage: float
    tfidf_similarity: float


class RecommendationResponse(BaseModel):
    run_id: int
    engine_version: str
    weights: RecommendationWeights
    generated_at: datetime
    total_candidates: int
    results: list[RoleRecommendation]


class RunSummary(BaseModel):
    """One row of the run history list."""

    id: int
    created_at: datetime
    engine_version: str
    total_candidates: int
    top_role_id: int | None = None
    top_role_title: str | None = None
    top_compatibility: float | None = None
    coverage_weight: float
    tfidf_weight: float


class RunPageResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[RunSummary]


class RunDetail(BaseModel):
    """A persisted run, read from the database — never recomputed.

    Recomputing would silently change the numbers if the knowledge base was edited
    between the run and the page view, which would make stored history a fiction.
    """

    id: int
    created_at: datetime
    engine_version: str
    weights: RecommendationWeights
    total_candidates: int
    duration_ms: int | None = None
    profile_snapshot: dict[str, Any] = Field(default_factory=dict)
    results: list[RoleRecommendation]


class LearningPathStep(BaseModel):
    order: int
    skill_id: int
    skill_name: str
    weight: float
    tier: str
    guidance: str


class LearningPathResponse(BaseModel):
    job_role_id: int
    job_role_title: str
    generated_by: str
    steps: list[LearningPathStep]
