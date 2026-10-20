"""Job role and taxonomy administration schemas.

``JobRoleRead`` includes the weighted skill set (admins need it); ``JobRoleSummary``
does not (public role browsing does not need to expose the scoring internals).
Two models rather than one with a flag, so the public shape cannot accidentally
grow a field.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_TITLE = 140
MAX_SKILLS_PER_ROLE = 40
Weight = Annotated[Decimal, Field(ge=Decimal("0.01"), le=Decimal("1.00"), decimal_places=2)]


def slugify(value: str) -> str:
    """Derive a stable slug from a title. Used for the unique ``job_role.slug``."""
    cleaned = value.strip().lower()
    out: list[str] = []
    for char in cleaned:
        if char.isalnum():
            out.append(char)
        elif char in {" ", "-", "_", "/", "&", "."}:
            out.append("-")
    slug = "".join(out)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-") or "role"


class SkillWeightIn(BaseModel):
    """One required skill and its importance for a role."""

    model_config = ConfigDict(str_strip_whitespace=True)

    skill_id: int = Field(..., gt=0)
    weight: Weight


class SkillWeightRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    skill_id: int
    name: str = ""
    slug: str = ""
    category: str = ""
    weight: Decimal


class JobRoleBase(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: Annotated[str, Field(min_length=1, max_length=MAX_TITLE)]
    family: Annotated[str, Field(min_length=1, max_length=80)]
    seniority: Annotated[str | None, Field(max_length=40)] = None
    # The experience the role typically expects. Display context, and the
    # fallback source for a role's band when ``seniority`` is blank.
    min_years_experience: Annotated[int | None, Field(ge=0, le=60)] = None
    # A role with no description cannot be TF-IDF-matched, so it is refused.
    description: Annotated[str, Field(min_length=1, max_length=8000)]
    responsibilities: Annotated[list[str], Field(max_length=30)] = Field(
        default_factory=list
    )
    is_active: bool = True


class JobRoleCreate(JobRoleBase):
    skills: Annotated[list[SkillWeightIn], Field(min_length=1, max_length=MAX_SKILLS_PER_ROLE)]

    @field_validator("skills")
    @classmethod
    def _no_duplicate_skill_ids(cls, value: list[SkillWeightIn]) -> list[SkillWeightIn]:
        ids = [item.skill_id for item in value]
        if len(ids) != len(set(ids)):
            raise ValueError("A skill_id may appear at most once in a role's requirement set.")
        return value

    @model_validator(mode="after")
    def _description_present(self) -> JobRoleCreate:
        if not self.description.strip():
            raise ValueError("A job role requires a description to be matchable.")
        return self


class JobRoleUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: Annotated[str | None, Field(min_length=1, max_length=MAX_TITLE)] = None
    family: Annotated[str | None, Field(min_length=1, max_length=80)] = None
    seniority: Annotated[str | None, Field(max_length=40)] = None
    description: Annotated[str | None, Field(min_length=1, max_length=8000)] = None
    responsibilities: Annotated[list[str], Field(max_length=30)] | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def _description_not_emptied(self) -> JobRoleUpdate:
        # Absent is fine (partial update); present-but-blank is not, because a role
        # with no description cannot be TF-IDF-matched.
        if (
            self.description is not None
            and "description" in self.model_fields_set
            and not self.description.strip()
        ):
            raise ValueError("A job role requires a description to be matchable.")
        return self


class JobRoleSkillReplace(BaseModel):
    """Body of ``PUT /api/admin/jobs/{id}/skills`` — a full replacement."""

    skills: Annotated[list[SkillWeightIn], Field(min_length=1, max_length=MAX_SKILLS_PER_ROLE)]

    @field_validator("skills")
    @classmethod
    def _no_duplicates(cls, value: list[SkillWeightIn]) -> list[SkillWeightIn]:
        ids = [item.skill_id for item in value]
        if len(ids) != len(set(ids)):
            raise ValueError("A skill_id may appear at most once in a role's requirement set.")
        return value


class JobRoleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    family: str
    seniority: str | None = None
    min_years_experience: int | None = None
    description: str
    responsibilities: list[str] = Field(default_factory=list)
    is_active: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None
    skills: list[SkillWeightRead] = Field(default_factory=list)


class JobRoleSummary(BaseModel):
    """Public read shape — no weights, no requirement set."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    slug: str
    family: str
    seniority: str | None = None
    min_years_experience: int | None = None
    description: str
    is_active: bool
    required_skills_count: int = 0


class JobRoleAdminSummary(JobRoleSummary):
    """Admin list shape — adds the numbers a maintenance table needs."""

    total_weight: Decimal = Decimal("0")
    updated_at: datetime | None = None


class FamilyCount(BaseModel):
    family: str
    count: int


class TaxonomyCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: Annotated[str, Field(min_length=1, max_length=120)]
    category: Annotated[str, Field(min_length=1, max_length=60)]
    description: Annotated[str | None, Field(max_length=2000)] = None
    aliases: Annotated[list[str], Field(max_length=30)] = Field(default_factory=list)
    slug: Annotated[str | None, Field(max_length=120)] = None

    @field_validator("aliases")
    @classmethod
    def _clean_aliases(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        for alias in value:
            entry = alias.strip().lower()
            if entry and entry not in cleaned:
                cleaned.append(entry)
        return cleaned

    @model_validator(mode="after")
    def _default_slug(self) -> TaxonomyCreate:
        if not self.slug:
            self.slug = slugify(self.name)
        return self


class TaxonomyUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: Annotated[str | None, Field(min_length=1, max_length=120)] = None
    category: Annotated[str | None, Field(min_length=1, max_length=60)] = None
    description: Annotated[str | None, Field(max_length=2000)] = None
    aliases: Annotated[list[str], Field(max_length=30)] | None = None
    slug: Annotated[str | None, Field(max_length=120)] = None
