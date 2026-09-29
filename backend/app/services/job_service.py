"""Job role and taxonomy administration.

``replace_skills`` is the interesting method. It performs a **full replacement in
one transaction** — delete the existing set, insert the new one — rather than
computing a diff. Full replacement is atomic, which incremental add/remove is not,
and it makes the client's state model trivial: the editor always PUTs the whole
set it has on screen.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.core.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.ml.taxonomy import normalise_surface
from app.models.job import JobRole, JobRoleSkill
from app.models.recommendation import RecommendationResult
from app.models.skill import Skill, SkillAlias
from app.schemas.job import (
    FamilyCount,
    JobRoleAdminSummary,
    JobRoleCreate,
    JobRoleRead,
    JobRoleSkillReplace,
    JobRoleSummary,
    JobRoleUpdate,
    SkillWeightIn,
    SkillWeightRead,
    TaxonomyCreate,
    TaxonomyUpdate,
    slugify,
)

logger = logging.getLogger("app.services.jobs")

MAX_SKILLS = 40


def _skill_weight_map(db: Session, role: JobRole) -> list[SkillWeightRead]:
    rows = db.execute(
        select(JobRoleSkill, Skill)
        .join(Skill, Skill.id == JobRoleSkill.skill_id)
        .where(JobRoleSkill.job_role_id == role.id)
        .order_by(JobRoleSkill.weight.desc(), Skill.name.asc())
    ).all()
    return [
        SkillWeightRead(
            skill_id=skill.id,
            name=skill.name,
            slug=skill.slug,
            category=skill.category,
            weight=requirement.weight,
        )
        for requirement, skill in rows
    ]


def to_read(db: Session, role: JobRole) -> JobRoleRead:
    data = JobRoleRead.model_validate(role)
    return data.model_copy(update={"skills": _skill_weight_map(db, role)})


# ---------------------------------------------------------------------------
# Public reads
# ---------------------------------------------------------------------------
def list_roles(
    db: Session,
    *,
    family: str | None = None,
    q: str | None = None,
    include_inactive: bool = False,
    limit: int = 20,
    offset: int = 0,
) -> tuple[int, list[JobRoleSummary]]:
    conditions: list[ColumnElement[bool]] = []
    if not include_inactive:
        conditions.append(JobRole.is_active.is_(True))
    if family and family.strip():
        conditions.append(JobRole.family == family.strip())
    if q and q.strip():
        needle = f"%{q.strip().lower()}%"
        conditions.append(
            or_(func.lower(JobRole.title).like(needle), func.lower(JobRole.family).like(needle))
        )

    base = select(JobRole)
    count_stmt = select(func.count()).select_from(JobRole)
    if conditions:
        base = base.where(*conditions)
        count_stmt = count_stmt.where(*conditions)

    total = int(db.scalar(count_stmt) or 0)
    rows = db.scalars(
        base.order_by(JobRole.family.asc(), JobRole.title.asc()).limit(limit).offset(offset)
    ).all()

    counts = _requirement_counts(db, [r.id for r in rows])
    return total, [
        JobRoleSummary(
            id=r.id,
            title=r.title,
            slug=r.slug,
            family=r.family,
            seniority=r.seniority,
            description=r.description,
            is_active=r.is_active,
            required_skills_count=counts.get(r.id, 0),
        )
        for r in rows
    ]


def _requirement_counts(db: Session, role_ids: list[int]) -> dict[int, int]:
    if not role_ids:
        return {}
    rows = db.execute(
        select(JobRoleSkill.job_role_id, func.count())
        .where(JobRoleSkill.job_role_id.in_(role_ids))
        .group_by(JobRoleSkill.job_role_id)
    ).all()
    return {role_id: int(count) for role_id, count in rows}


def get_role(db: Session, role_id: int, *, require_active: bool = False) -> JobRole:
    role = db.get(JobRole, role_id)
    if role is None or (require_active and not role.is_active):
        raise NotFoundError("That job role does not exist.")
    return role


def families(db: Session, *, active_only: bool = True) -> list[FamilyCount]:
    stmt = select(JobRole.family, func.count(JobRole.id)).group_by(JobRole.family)
    if active_only:
        stmt = stmt.where(JobRole.is_active.is_(True))
    return [FamilyCount(family=f, count=int(c)) for f, c in db.execute(stmt).all()]


# ---------------------------------------------------------------------------
# Admin writes
# ---------------------------------------------------------------------------
def _validate_skill_ids(db: Session, entries: list[SkillWeightIn]) -> list[Skill]:
    """Every referenced skill must exist. Resolved up front, before any write."""
    ids = [entry.skill_id for entry in entries]
    skills = {s.id: s for s in db.scalars(select(Skill).where(Skill.id.in_(ids))).all()}
    missing = [i for i in ids if i not in skills]
    if missing:
        raise UnprocessableError(
            f"Unknown skill_id(s): {missing}. They must exist in the taxonomy.",
            code="unknown_skill",
            errors=[{"field": "skills", "message": f"Unknown skill_id {i}."} for i in missing],
        )
    return [skills[i] for i in ids]


def create_role(db: Session, payload: JobRoleCreate) -> JobRoleRead:
    if db.scalar(select(JobRole).where(JobRole.title == payload.title)) is not None:
        raise ConflictError(
            f"A job role titled '{payload.title}' already exists.", code="role_title_exists"
        )

    slug = slugify(payload.title)
    if db.scalar(select(JobRole).where(JobRole.slug == slug)) is not None:
        slug = f"{slug}-{db.scalar(select(func.count()).select_from(JobRole)) or 0}"

    _validate_skill_ids(db, payload.skills)

    role = JobRole(
        title=payload.title,
        slug=slug,
        family=payload.family,
        seniority=payload.seniority,
        description=payload.description,
        responsibilities=payload.responsibilities,
        is_active=payload.is_active,
    )
    role.skill_requirements = [
        JobRoleSkill(skill_id=entry.skill_id, weight=Decimal(str(entry.weight)))
        for entry in payload.skills
    ]
    db.add(role)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            f"A job role titled '{payload.title}' already exists.", code="role_title_exists"
        ) from exc
    db.refresh(role)
    logger.info("Created job role id=%s slug=%s", role.id, role.slug, extra={"kind": "job"})
    return to_read(db, role)


def update_role(db: Session, role_id: int, payload: JobRoleUpdate) -> JobRoleRead:
    role = get_role(db, role_id)
    changes = payload.model_dump(exclude_unset=True)
    if not changes:
        return to_read(db, role)

    if "title" in changes and changes["title"] and changes["title"] != role.title:
        clash = db.scalar(
            select(JobRole).where(JobRole.title == changes["title"], JobRole.id != role.id)
        )
        if clash is not None:
            raise ConflictError(
                f"A job role titled '{changes['title']}' already exists.",
                code="role_title_exists",
            )
        changes["slug"] = slugify(changes["title"])

    for field, value in changes.items():
        setattr(role, field, value)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("That change conflicts with an existing job role.", code="conflict") from exc
    db.refresh(role)
    return to_read(db, role)


def replace_skills(db: Session, role_id: int, payload: JobRoleSkillReplace) -> JobRoleRead:
    """Atomically replace a role's weighted requirement set.

    **Validation happens before the DELETE.** A request naming an unknown skill
    raises and rolls back, so the previous set survives intact. The alternative
    order would leave a role with no requirements after a typo.
    """
    role = get_role(db, role_id)
    if not payload.skills:
        raise UnprocessableError(
            "A job role needs at least one required skill.", code="empty_skill_set"
        )
    if len(payload.skills) > MAX_SKILLS:
        raise UnprocessableError(
            f"At most {MAX_SKILLS} required skills per role.", code="too_many_skills"
        )

    seen: set[int] = set()
    for entry in payload.skills:
        if entry.skill_id in seen:
            raise UnprocessableError(
                f"Duplicate skill_id {entry.skill_id}.", code="duplicate_skill"
            )
        seen.add(entry.skill_id)
        if not (0 < float(entry.weight) <= 1.0):
            raise UnprocessableError(
                f"Weight {entry.weight} for skill {entry.skill_id} must be within (0, 1].",
                code="weight_out_of_range",
            )
    _validate_skill_ids(db, payload.skills)

    try:
        db.execute(delete(JobRoleSkill).where(JobRoleSkill.job_role_id == role.id))
        db.flush()
        db.add_all(
            [
                JobRoleSkill(
                    job_role_id=role.id,
                    skill_id=entry.skill_id,
                    weight=Decimal(str(entry.weight)),
                )
                for entry in payload.skills
            ]
        )
        db.commit()
    except Exception:
        db.rollback()
        # The DELETE was in the same transaction, so the previous set is intact.
        raise
    db.refresh(role)
    logger.info(
        "Replaced %d required skills on role id=%s", len(payload.skills), role.id,
        extra={"kind": "job"},
    )
    return to_read(db, role)


def delete_role(db: Session, role_id: int) -> None:
    """Delete a role, or refuse if history would be destroyed.

    ``recommendation_result.job_role_id`` is ``ON DELETE RESTRICT``, so PostgreSQL
    blocks the delete. Rather than surfacing an opaque foreign-key error we check
    first and return ``409 conflict_role_in_use`` with an actionable message:
    deactivate the role instead. Destroying a user's recommendation history
    because an admin removed a role is a worse outcome than an orphaned title.
    """
    role = get_role(db, role_id)
    referencing = int(
        db.scalar(
            select(func.count())
            .select_from(RecommendationResult)
            .where(RecommendationResult.job_role_id == role.id)
        )
        or 0
    )
    if referencing:
        raise ConflictError(
            f"'{role.title}' is referenced by {referencing} stored recommendation result(s). "
            "Deactivate it instead of deleting it, so users' recommendation history is "
            "preserved.",
            code="conflict_role_in_use",
        )
    db.delete(role)
    db.commit()
    logger.info("Deleted job role id=%s", role_id, extra={"kind": "job"})


def list_roles_admin(
    db: Session, *, q: str | None = None, family: str | None = None,
    is_active: bool | None = None, limit: int = 20, offset: int = 0,
) -> tuple[int, list[JobRoleAdminSummary]]:
    """Admin list — includes inactive roles and shows the numbers a table needs."""
    conditions: list[ColumnElement[bool]] = []
    if family and family.strip():
        conditions.append(JobRole.family == family.strip())
    if is_active is not None:
        conditions.append(JobRole.is_active.is_(is_active))
    if q and q.strip():
        needle = f"%{q.strip().lower()}%"
        conditions.append(
            or_(
                func.lower(JobRole.title).like(needle),
                func.lower(JobRole.family).like(needle),
                func.lower(JobRole.description).like(needle),
            )
        )

    base = select(JobRole)
    count_stmt = select(func.count()).select_from(JobRole)
    if conditions:
        base = base.where(*conditions)
        count_stmt = count_stmt.where(*conditions)

    total = int(db.scalar(count_stmt) or 0)
    rows = db.scalars(
        base.order_by(JobRole.updated_at.desc(), JobRole.id.desc()).limit(limit).offset(offset)
    ).all()

    counts = _requirement_counts(db, [r.id for r in rows])
    totals = _total_weights(db, [r.id for r in rows])

    return total, [
        JobRoleAdminSummary(
            id=r.id,
            title=r.title,
            slug=r.slug,
            family=r.family,
            seniority=r.seniority,
            description=r.description,
            is_active=r.is_active,
            required_skills_count=counts.get(r.id, 0),
            total_weight=totals.get(r.id, Decimal("0")),
            updated_at=r.updated_at,
        )
        for r in rows
    ]


def _total_weights(db: Session, role_ids: list[int]) -> dict[int, Decimal]:
    if not role_ids:
        return {}
    rows = db.execute(
        select(JobRoleSkill.job_role_id, func.sum(JobRoleSkill.weight))
        .where(JobRoleSkill.job_role_id.in_(role_ids))
        .group_by(JobRoleSkill.job_role_id)
    ).all()
    return {role_id: Decimal(str(total or 0)) for role_id, total in rows}


# ---------------------------------------------------------------------------
# Taxonomy administration
# ---------------------------------------------------------------------------
def list_taxonomy(
    db: Session, *, q: str | None = None, category: str | None = None,
    limit: int = 50, offset: int = 0,
) -> tuple[int, list[tuple[Skill, list[str]]]]:

    conditions: list[ColumnElement[bool]] = []
    if q and q.strip():
        needle = f"%{q.strip().lower()}%"
        alias_ids = select(SkillAlias.skill_id).where(SkillAlias.alias.like(needle))
        conditions.append(
            or_(func.lower(Skill.name).like(needle), Skill.id.in_(alias_ids))
        )
    if category and category.strip():
        conditions.append(Skill.category == category.strip())

    base = select(Skill)
    count_stmt = select(func.count()).select_from(Skill)
    if conditions:
        base = base.where(*conditions)
        count_stmt = count_stmt.where(*conditions)

    total = int(db.scalar(count_stmt) or 0)
    skills = list(
        db.scalars(base.order_by(Skill.category.asc(), Skill.name.asc()).limit(limit).offset(offset)).all()
    )
    alias_map = _aliases_for(db, [s.id for s in skills])
    return total, [(s, alias_map.get(s.id, [])) for s in skills]


def _aliases_for(db: Session, skill_ids: list[int]) -> dict[int, list[str]]:
    if not skill_ids:
        return {}
    rows = db.execute(
        select(SkillAlias.skill_id, SkillAlias.alias).where(SkillAlias.skill_id.in_(skill_ids))
    ).all()
    grouped: dict[int, list[str]] = {}
    for skill_id, alias in rows:
        grouped.setdefault(skill_id, []).append(alias)
    return grouped


def _assert_aliases_free(db: Session, aliases: list[str], *, exclude_skill_id: int | None = None) -> None:
    """Refuse an alias already claimed by another skill.

    A collision makes one of the two skills **undetectable**, and nothing would
    report it until a user noticed a missing skill in a CV result. The database
    would stop the exact-duplicate case via the primary key, but not the
    case-insensitive one, so it is checked explicitly.
    """
    normalised = {normalise_surface(alias) for alias in aliases if alias.strip()}
    normalised.discard("")
    if not normalised:
        return
    stmt = select(SkillAlias).where(SkillAlias.alias.in_(normalised))
    if exclude_skill_id is not None:
        stmt = stmt.where(SkillAlias.skill_id != exclude_skill_id)
    clashes = db.scalars(stmt).all()
    if clashes:
        raise ConflictError(
            f"Alias(es) already in use: {sorted({c.alias for c in clashes})}. "
            "An alias may belong to exactly one skill.",
            code="alias_conflict",
        )


def create_skill(db: Session, payload: TaxonomyCreate) -> tuple[Skill, list[str]]:
    if db.scalar(select(Skill).where(Skill.name == payload.name)) is not None:
        raise ConflictError(f"A skill named '{payload.name}' already exists.", code="skill_exists")
    if db.scalar(select(Skill).where(Skill.slug == payload.slug)) is not None:
        raise ConflictError(f"A skill with slug '{payload.slug}' already exists.", code="skill_exists")

    aliases = [a for a in payload.aliases if normalise_surface(a) != normalise_surface(payload.name)]
    _assert_aliases_free(db, aliases)

    skill = Skill(
        name=payload.name,
        slug=payload.slug,
        category=payload.category,
        description=payload.description,
    )
    db.add(skill)
    db.flush()
    db.add_all([SkillAlias(alias=a, skill_id=skill.id) for a in aliases])
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("That name, slug, or alias is already taken.", code="conflict") from exc
    db.refresh(skill)
    logger.info("Created taxonomy skill id=%s slug=%s", skill.id, skill.slug, extra={"kind": "taxonomy"})
    return skill, aliases


def update_skill(
    db: Session, skill_id: int, payload: TaxonomyUpdate
) -> tuple[Skill, list[str]]:
    skill = db.get(Skill, skill_id)
    if skill is None:
        raise NotFoundError("That skill does not exist.")

    changes = payload.model_dump(exclude_unset=True)
    aliases: list[str] | None = changes.pop("aliases", None)

    for field, value in changes.items():
        if value is not None:
            setattr(skill, field, value)

    if aliases is not None:
        kept = [
            a for a in aliases
            if normalise_surface(a) not in (normalise_surface(skill.name),)
        ]
        _assert_aliases_free(db, kept, exclude_skill_id=skill.id)
        db.execute(delete(SkillAlias).where(SkillAlias.skill_id == skill.id))
        db.flush()
        db.add_all([SkillAlias(alias=a, skill_id=skill.id) for a in kept])
    else:
        kept = sorted(a.alias for a in db.scalars(
            select(SkillAlias).where(SkillAlias.skill_id == skill.id)
        ).all())

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError("That name, slug, or alias is already taken.", code="conflict") from exc
    db.refresh(skill)
    return skill, kept or []


def delete_skill(db: Session, skill_id: int) -> None:
    skill = db.get(Skill, skill_id)
    if skill is None:
        raise NotFoundError("That skill does not exist.")
    referenced = int(
        db.scalar(
            select(func.count()).select_from(JobRoleSkill).where(JobRoleSkill.skill_id == skill_id)
        )
        or 0
    )
    if referenced:
        raise ConflictError(
            f"'{skill.name}' is required by {referenced} job role(s). Remove it from those "
            "roles first.",
            code="skill_in_use",
        )
    db.delete(skill)
    db.commit()


def skill_to_read(skill: Skill, aliases: list[str]):
    from app.schemas.skill import SkillRead

    return SkillRead(
        id=skill.id,
        name=skill.name,
        slug=skill.slug,
        category=skill.category,
        description=skill.description,
        aliases=sorted(aliases),
    )
