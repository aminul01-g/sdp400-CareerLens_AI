"""Project schemas.

``tech_stack`` accepts free text from the client and is canonicalised server-side
through ``ml.taxonomy.canonicalise`` before storage, so ``"sklearn"`` and
``"Scikit-learn"`` cannot become two different facts about one project. Entries
the taxonomy does not know are **kept but flagged** rather than rejected: a user
may legitimately list a tool the taxonomy has not caught up with, and silently
discarding their input would be worse than an unrecognised tag.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_TITLE = 160
MAX_DESCRIPTION = 5000
MAX_TECH_STACK = 30


class ProjectBase(BaseModel):
    title: Annotated[str, Field(min_length=1, max_length=MAX_TITLE)]
    description: Annotated[str, Field(min_length=1, max_length=MAX_DESCRIPTION)]
    tech_stack: Annotated[list[str], Field(max_length=MAX_TECH_STACK)] = Field(
        default_factory=list
    )
    role: Annotated[str | None, Field(max_length=120)] = None
    start_date: date | None = None
    end_date: date | None = None
    repo_url: Annotated[str | None, Field(max_length=400)] = None
    is_public: bool = True

    @field_validator("tech_stack")
    @classmethod
    def _normalise_stack(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for item in value:
            entry = str(item).strip()
            if not entry:
                continue
            if entry not in cleaned:
                cleaned.append(entry)
        return cleaned

    @field_validator("repo_url")
    @classmethod
    def _repo_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        if not cleaned.startswith(("http://", "https://")):
            raise ValueError("Repository URL must start with http:// or https://")
        return cleaned

    @model_validator(mode="after")
    def _date_order(self) -> ProjectBase:
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must not be earlier than start_date")
        return self


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    """``PATCH`` — every field optional; ``model_fields_set`` marks presence."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: Annotated[str | None, Field(min_length=1, max_length=MAX_TITLE)] = None
    description: Annotated[str | None, Field(min_length=1, max_length=MAX_DESCRIPTION)] = None
    tech_stack: Annotated[list[str], Field(max_length=MAX_TECH_STACK)] | None = None
    role: Annotated[str | None, Field(max_length=120)] = None
    start_date: date | None = None
    end_date: date | None = None
    repo_url: Annotated[str | None, Field(max_length=400)] = None
    is_public: bool | None = None

    @field_validator("tech_stack")
    @classmethod
    def _normalise_stack(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        cleaned: list[str] = []
        for item in value:
            entry = str(item).strip()
            if entry and entry not in cleaned:
                cleaned.append(entry)
        return cleaned

    @model_validator(mode="after")
    def _repo_url_scheme(self) -> ProjectUpdate:
        if self.repo_url and not self.repo_url.strip().startswith(("http://", "https://")):
            raise ValueError("Repository URL must start with http:// or https://")
        return self


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    description: str
    tech_stack: list[str] = Field(default_factory=list)
    role: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    repo_url: str | None = None
    is_public: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
    # Entries the taxonomy could not canonicalise, surfaced for the UI badge.
    unrecognised_tech: list[str] = Field(default_factory=list)
