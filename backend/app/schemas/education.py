"""Education and certification schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MIN_YEAR = 1950
MAX_YEAR = 2100
Year = Annotated[int, Field(ge=MIN_YEAR, le=MAX_YEAR)]


class EducationBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    institution: Annotated[str, Field(min_length=1, max_length=180)]
    degree: Annotated[str, Field(min_length=1, max_length=120)]
    field_of_study: Annotated[str | None, Field(max_length=120)] = None
    start_year: Year | None = None
    end_year: Year | None = None
    grade: Annotated[str | None, Field(max_length=40)] = None

    @field_validator("institution", "degree", "field_of_study", "grade", mode="before")
    @classmethod
    def _strip(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def _year_order(self) -> EducationBase:
        if self.start_year and self.end_year and self.end_year < self.start_year:
            raise ValueError("end_year must not be earlier than start_year")
        return self


class EducationCreate(EducationBase):
    pass


class EducationUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    institution: Annotated[str | None, Field(min_length=1, max_length=180)] = None
    degree: Annotated[str | None, Field(min_length=1, max_length=120)] = None
    field_of_study: Annotated[str | None, Field(max_length=120)] = None
    start_year: Year | None = None
    end_year: Year | None = None
    grade: Annotated[str | None, Field(max_length=40)] = None

    @model_validator(mode="after")
    def _year_order(self) -> EducationUpdate:
        if self.start_year and self.end_year and self.end_year < self.start_year:
            raise ValueError("end_year must not be earlier than start_year")
        return self


class EducationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    institution: str
    degree: str
    field_of_study: str | None = None
    start_year: int | None = None
    end_year: int | None = None
    grade: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CertificationBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: Annotated[str, Field(min_length=1, max_length=160)]
    issuer: Annotated[str, Field(min_length=1, max_length=160)]
    issued_on: date | None = None
    expires_on: date | None = None
    credential_url: Annotated[str | None, Field(max_length=400)] = None

    @field_validator("name", "issuer", mode="before")
    @classmethod
    def _strip(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("credential_url")
    @classmethod
    def _credential_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            return None
        if not cleaned.startswith(("http://", "https://")):
            raise ValueError("Credential URL must start with http:// or https://")
        return cleaned

    @model_validator(mode="after")
    def _date_order(self) -> CertificationBase:
        if self.issued_on and self.expires_on and self.expires_on <= self.issued_on:
            raise ValueError("expires_on must be later than issued_on")
        return self


class CertificationCreate(CertificationBase):
    pass


class CertificationUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: Annotated[str | None, Field(min_length=1, max_length=160)] = None
    issuer: Annotated[str | None, Field(min_length=1, max_length=160)] = None
    issued_on: date | None = None
    expires_on: date | None = None
    credential_url: Annotated[str | None, Field(max_length=400)] = None

    @model_validator(mode="after")
    def _date_order(self) -> CertificationUpdate:
        if self.issued_on and self.expires_on and self.expires_on <= self.issued_on:
            raise ValueError("expires_on must be later than issued_on")
        return self


class CertificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    name: str
    issuer: str
    issued_on: date | None = None
    expires_on: date | None = None
    credential_url: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
