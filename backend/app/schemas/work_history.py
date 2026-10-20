"""Work history schemas.

The rows here are the user's own record of where they have worked. A row the
CV pipeline proposed carries ``confirmed = False`` until the user accepts it,
which is the same rule that governs a detected skill: nothing that the system
proposed may influence a result without the user saying so.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator

MAX_EMPLOYER = 160
MAX_TITLE = 160


class WorkHistoryBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    employer: Annotated[str, Field(min_length=1, max_length=MAX_EMPLOYER)]
    title: Annotated[str | None, Field(max_length=MAX_TITLE)] = None
    start_date: date | None = None
    end_date: date | None = None

    @field_validator("employer")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Employer cannot be blank.")
        return value.strip()

    @field_validator("end_date")
    @classmethod
    def _end_after_start(cls, value: date | None, info) -> date | None:
        start = info.data.get("start_date")
        if value is not None and start is not None and value < start:
            raise ValueError("The end date cannot be before the start date.")
        return value


class WorkHistoryCreate(WorkHistoryBase):
    """``POST /api/work-history``."""


class WorkHistoryUpdate(BaseModel):
    """``PATCH /api/work-history/{id}`` — partial."""

    model_config = ConfigDict(str_strip_whitespace=True)

    employer: Annotated[str | None, Field(min_length=1, max_length=MAX_EMPLOYER)] = None
    title: Annotated[str | None, Field(max_length=MAX_TITLE)] = None
    start_date: date | None = None
    end_date: date | None = None


class WorkHistoryRead(BaseModel):
    """One row."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    employer: str
    title: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    source: str
    confirmed: bool
    raw_text: str | None = None
