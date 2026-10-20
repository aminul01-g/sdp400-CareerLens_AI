"""Profile schemas.

``ProfileUpdate`` is all-optional and the router distinguishes "absent" from
"explicit null" via ``model_fields_set``, so ``PATCH {"bio": null}`` clears the
bio while ``PATCH {"headline": "x"}`` leaves it alone. Without that distinction a
partial update is indistinguishable from a full one and every PATCH silently
wipes fields.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_HEADLINE = 200
MAX_LOCATION = 120
MAX_LINKS = 10
MAX_INDUSTRY = 120
ALLOWED_LINK_KEYS = {"github", "linkedin", "portfolio", "website", "other"}

#: The seniority bands the engine compares a user against. Kept here rather than
#: imported from ``app.ml.signals`` because a schema must not depend on the
#: engine, and the two are cross-checked in ``tests/test_signals.py``.
SENIORITY_BANDS = ("Entry", "Junior", "Mid", "Senior", "Lead", "Principal")


def _validate_links(value: dict[str, Any] | None) -> dict[str, Any]:
    if value is None:
        return {}
    if len(value) > MAX_LINKS:
        raise ValueError(f"At most {MAX_LINKS} links may be supplied.")
    for key, url in value.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("Link keys must be non-empty strings.")
        if not isinstance(url, str):
            raise ValueError(f"Link '{key}' must be a string URL.")
        cleaned = url.strip()
        if cleaned and not cleaned.startswith(("http://", "https://")):
            raise ValueError(f"Link '{key}' must start with http:// or https://")
        if len(cleaned) > 400:
            raise ValueError(f"Link '{key}' is too long (max 400 characters).")
    return {k.strip().lower(): v.strip() for k, v in value.items() if v and v.strip()}


class ProfileBase(BaseModel):
    headline: Annotated[str | None, Field(max_length=MAX_HEADLINE)] = None
    career_goal: Annotated[str | None, Field(max_length=2000)] = None
    bio: Annotated[str | None, Field(max_length=4000)] = None
    location: Annotated[str | None, Field(max_length=MAX_LOCATION)] = None
    education_level: Annotated[str | None, Field(max_length=80)] = None
    years_experience: Annotated[int | None, Field(ge=0, le=60)] = None
    preferred_role_family: Annotated[str | None, Field(max_length=80)] = None
    seniority: Annotated[str | None, Field(max_length=40)] = None
    industry: Annotated[str | None, Field(max_length=MAX_INDUSTRY)] = None
    links: dict[str, str] = Field(default_factory=dict)

    @field_validator("seniority")
    @classmethod
    def _known_band(cls, value: str | None) -> str | None:
        """Reject a level the engine cannot compare against a role's."""
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        for band in SENIORITY_BANDS:
            if band.casefold() == cleaned.casefold():
                return band
        raise ValueError(
            "Seniority must be one of: " + ", ".join(SENIORITY_BANDS) + "."
        )

    @field_validator("links")
    @classmethod
    def _links(cls, value: dict[str, str]) -> dict[str, str]:
        return _validate_links(value)

    @model_validator(mode="after")
    def _trim(self) -> ProfileBase:
        for field in (
            "headline",
            "location",
            "education_level",
            "preferred_role_family",
            "industry",
        ):
            value = getattr(self, field)
            if isinstance(value, str):
                setattr(self, field, value.strip() or None)
        for field in ("career_goal", "bio"):
            value = getattr(self, field)
            if isinstance(value, str):
                setattr(self, field, value.strip() or None)
        return self


class ProfileCreate(ProfileBase):
    """``POST /api/profile``. The service is get-or-create, so this is idempotent."""


class ProfileUpdate(BaseModel):
    """Every field optional; ``model_fields_set`` distinguishes absent from null."""

    model_config = ConfigDict(str_strip_whitespace=True)

    headline: Annotated[str | None, Field(max_length=MAX_HEADLINE)] = None
    career_goal: Annotated[str | None, Field(max_length=2000)] = None
    bio: Annotated[str | None, Field(max_length=4000)] = None
    location: Annotated[str | None, Field(max_length=MAX_LOCATION)] = None
    education_level: Annotated[str | None, Field(max_length=80)] = None
    years_experience: Annotated[int | None, Field(ge=0, le=60)] = None
    preferred_role_family: Annotated[str | None, Field(max_length=80)] = None
    seniority: Annotated[str | None, Field(max_length=40)] = None
    industry: Annotated[str | None, Field(max_length=MAX_INDUSTRY)] = None
    links: dict[str, str] | None = None

    @field_validator("seniority")
    @classmethod
    def _known_band(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        for band in SENIORITY_BANDS:
            if band.casefold() == cleaned.casefold():
                return band
        raise ValueError(
            "Seniority must be one of: " + ", ".join(SENIORITY_BANDS) + "."
        )

    @field_validator("links")
    @classmethod
    def _links(cls, value: dict[str, str] | None) -> dict[str, str] | None:
        return None if value is None else _validate_links(value)


class ProfileRead(BaseModel):
    """Read model. Includes live counts so the dashboard needs no second call."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    headline: str | None = None
    career_goal: str | None = None
    bio: str | None = None
    location: str | None = None
    education_level: str | None = None
    years_experience: int | None = None
    preferred_role_family: str | None = None
    seniority: str | None = None
    industry: str | None = None
    links: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    skills_count: int = 0
    projects_count: int = 0
    education_count: int = 0
    certifications_count: int = 0
