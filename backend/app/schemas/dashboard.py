"""Dashboard and admin-aggregate schemas.

These exist to *replace fabricated numbers*. The legacy dashboard hard-coded
``totalUsers: "12,847"``, ``successRate: "94%"``, ``careerPaths: "500+"`` and an
``averageCompletion: "18 minutes"``. Every field below is a real aggregate
computed by ``services/dashboard_service`` — the schema exists so those values
have a declared shape and so a future field cannot be invented at the call site.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field


class DashboardSummary(BaseModel):
    """Real aggregates for the signed-in user."""

    skills_count: int
    projects_count: int
    education_count: int
    certifications_count: int
    resume_uploads_count: int
    total_recommendation_runs: int
    latest_run_at: datetime | None = None
    top_role_id: int | None = None
    top_role_title: str | None = None
    top_compatibility_pct: float | None = None
    member_since: datetime | None = None


class OnboardingStep(BaseModel):
    key: str
    label: str
    completed: bool
    href: str
    hint: str


class ProfileCompleteness(BaseModel):
    """A 0-100 score derived from real field presence — not an invented constant."""

    score: int = Field(..., ge=0, le=100)
    completed_fields: int
    total_fields: int
    steps: list[OnboardingStep]
    next_action: OnboardingStep | None = None


class AdminOverview(BaseModel):
    role_count: int
    active_role_count: int
    skill_count: int
    alias_count: int
    user_count: int
    recommendation_run_count: int
    latest_run_at: datetime | None = None
    families: list[dict[str, Any]] = Field(default_factory=list)
    top_skills: list[dict[str, Any]] = Field(default_factory=list)


class AdminUserRead(BaseModel):
    """Never includes ``password_hash`` — see ``schemas.auth.UserRead``."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime | None = None
    last_login_at: datetime | None = None
    skills_count: int = 0
    projects_count: int = 0


class RoleUpdateRequest(BaseModel):
    role: Annotated[str, Field(pattern="^(user|admin)$")]
