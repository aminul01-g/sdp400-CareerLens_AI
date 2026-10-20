"""Skill, user-skill, taxonomy-search and CV-confirmation schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

MIN_PROFICIENCY = 1
MAX_PROFICIENCY = 5
Proficiency = Annotated[int, Field(ge=MIN_PROFICIENCY, le=MAX_PROFICIENCY)]


class SkillRead(BaseModel):
    """A taxonomy entry. Read-only for users; maintained by admins."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    category: str
    description: str | None = None
    aliases: list[str] = Field(default_factory=list)


class UserSkillCreate(BaseModel):
    """``POST /api/skills``."""

    model_config = ConfigDict(str_strip_whitespace=True)

    skill_id: int = Field(..., gt=0)
    proficiency: Proficiency = 3
    years_used: Annotated[float | None, Field(ge=0, le=60)] = None
    last_used_at: date | None = None
    source: str = Field(default="manual", pattern="^(manual|cv_extracted)$")


class UserSkillUpdate(BaseModel):
    """``PATCH /api/skills/{skill_id}`` — partial."""

    model_config = ConfigDict(str_strip_whitespace=True)

    proficiency: Proficiency | None = None
    years_used: Annotated[float | None, Field(ge=0, le=60)] = None
    last_used_at: date | None = None
    confirmed: bool | None = None


class UserSkillRead(BaseModel):
    """A confirmed skill the user holds, joined with its taxonomy entry."""

    model_config = ConfigDict(from_attributes=True)

    skill_id: int
    name: str = ""
    slug: str = ""
    category: str = ""
    proficiency: int
    years_used: float | None = None
    last_used_at: date | None = None
    source: str
    confirmed: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TaxonomySearchResponse(BaseModel):
    total: int
    items: list[SkillRead]
    query: str | None = None
    category: str | None = None


class DetectedSkillConfirmItem(BaseModel):
    """One row of the CV confirmation panel."""

    skill_id: int = Field(..., gt=0)
    accepted: bool
    proficiency: Proficiency | None = None


class DetectedSkillConfirm(BaseModel):
    """``POST /api/skills/confirm``.

    Idempotent by design: a double-click or a page refresh after confirming
    changes nothing. That matters because the panel's primary button is one
    click away from the upload that produced it.
    """

    skills: Annotated[list[DetectedSkillConfirmItem], Field(min_length=1, max_length=200)]
    resume_upload_id: int | None = Field(
        default=None,
        description="When present, the matched staged rows are marked accepted/rejected.",
    )

    @field_validator("skills")
    @classmethod
    def _no_duplicate_skill_ids(cls, value: list[DetectedSkillConfirmItem]) -> list[DetectedSkillConfirmItem]:
        ids = [item.skill_id for item in value]
        if len(ids) != len(set(ids)):
            raise ValueError("Each skill_id may appear at most once.")
        return value


class ConfirmResult(BaseModel):
    """Per-item outcome. Partial success is reported, not raised."""

    added: int = 0
    updated: int = 0
    skipped: int = 0
    rejected: list[int] = Field(default_factory=list, description="skill_ids not in the taxonomy")
    accepted: int = 0
    declined: int = 0
    details: list[dict[str, Any]] = Field(default_factory=list)
