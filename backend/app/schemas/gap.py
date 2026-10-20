"""Skill-gap analysis schemas.

The gap is ``required - present``, ordered by descending importance weight. Tiers
are a pure function of the weight that already exists in ``job_role_skill``, so
they are a reading aid rather than a second computation that could drift out of
step with the ranking.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

CRITICAL_THRESHOLD = 0.8
IMPORTANT_THRESHOLD = 0.5


def tier_of(weight: float) -> str:
    """Map an importance weight to a band. Mirrors ``ml.gap_analysis.tier_of``."""
    if weight >= CRITICAL_THRESHOLD:
        return "critical"
    if weight >= IMPORTANT_THRESHOLD:
        return "important"
    return "desirable"


class GapRoleSummary(BaseModel):
    job_role_id: int
    title: str
    family: str
    seniority: str | None = None
    required_skills_count: int


class MatchedSkill(BaseModel):
    skill_id: int
    name: str
    category: str | None = None
    weight: float
    proficiency: int
    # weight * proficiency_factor — what this skill actually contributed.
    contribution: float


class MissingSkill(BaseModel):
    skill_id: int
    name: str
    category: str | None = None
    weight: float
    tier: str


class TierCounts(BaseModel):
    critical: int = 0
    important: int = 0
    desirable: int = 0


class SkillGapResponse(BaseModel):
    """``GET /api/skill-gap/{job_role_id}``."""

    job_role: GapRoleSummary
    coverage: float = Field(..., ge=0.0, le=1.0)
    coverage_pct: float = Field(..., ge=0.0, le=100.0)
    required_count: int
    matched_count: int
    missing_count: int
    matched: list[MatchedSkill]
    # Strictly descending by weight — the ordering is the feature.
    missing: list[MissingSkill]
    tiers: TierCounts
    learning_path_available: bool = False
    # The coverage the user declared, before recency and depth were applied.
    declared_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    # That coverage after the recency and depth adjustments.
    signal_coverage: float = Field(default=0.0, ge=0.0, le=1.0)
    # The multiplier for the distance between the user's level and the role's.
    level_fit: float = Field(default=1.0, gt=0.0, le=1.0)
