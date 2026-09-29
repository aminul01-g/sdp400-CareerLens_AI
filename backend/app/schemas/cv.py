"""CV upload, extraction result, and dashboard schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_FILENAME = 255


class DetectedSkill(BaseModel):
    """A skill found in an uploaded document, staged for confirmation.

    Nothing here has reached ``user_skill`` yet. That is the point: the engine
    reads ``user_skill`` only, so an unconfirmed extraction cannot influence a
    recommendation in either direction.
    """

    skill_id: int
    canonical_name: str
    slug: str
    category: str
    surface_form: str = Field(..., description="The literal text found in the document.")
    occurrence_count: int
    match_start: int | None = None
    match_end: int | None = None
    accepted: bool = False
    already_confirmed: bool = Field(
        default=False, description="The user already holds this skill."
    )


class ResumeUploadRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: str
    content_type: str
    size_bytes: int
    status: str
    error_message: str | None = None
    created_at: datetime | None = None
    text_length: int | None = None
    detected_skills: list[DetectedSkill] = Field(default_factory=list)


class UploadResponse(BaseModel):
    """``POST /api/cv/upload`` — extraction happened on upload."""

    resume_upload_id: int
    status: str
    filename: str
    size_bytes: int
    text_length: int
    page_count: int | None = None
    detected_skills: list[DetectedSkill]
    already_confirmed: list[str] = Field(default_factory=list)
    message: str


class ExtractedTextResponse(BaseModel):
    text: str
    text_length: int
    page_count: int | None = None


class FeedbackCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    category: Annotated[str, Field(max_length=60)] = "general"
    message: Annotated[str, Field(min_length=5, max_length=4000)]
    rating: Annotated[int | None, Field(ge=1, le=5)] = None

    @field_validator("category")
    @classmethod
    def _category_allowed(cls, value: str) -> str:
        allowed = {"general", "bug", "feature", "ui", "data", "other"}
        if value not in allowed:
            raise ValueError(f"Category must be one of: {', '.join(sorted(allowed))}")
        return value


class FeedbackRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    category: str
    message: str
    rating: int | None = None
    created_at: datetime | None = None



    """Real aggregates. Replaces the fabricated ``mockStats`` on the old dashboard."""

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
