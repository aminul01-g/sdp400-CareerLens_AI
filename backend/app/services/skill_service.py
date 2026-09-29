"""Skill management: the user's confirmed skills, taxonomy search, CV confirmation."""

from __future__ import annotations

import logging
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, UnprocessableError
from app.models.skill import Skill, SkillAlias
from app.models.user import User
from app.models.user_skill import SkillSource, UserSkill
from app.schemas.skill import (
    ConfirmResult,
    DetectedSkillConfirm,
    SkillRead,
    TaxonomySearchResponse,
    UserSkillCreate,
    UserSkillRead,
    UserSkillUpdate,
)

logger = logging.getLogger("app.services.skills")

MAX_RESULTS = 100


def _get_skill_or_error(db: Session, skill_id: int) -> Skill:
    skill = db.get(Skill, skill_id)
    if skill is None:
        raise UnprocessableError(
            f"Skill {skill_id} is not in the taxonomy.",
            code="unknown_skill",
            errors=[{"field": "skill_id", "message": "Not a known taxonomy skill."}],
        )
    return skill


def _to_read(row: UserSkill) -> UserSkillRead:
    skill = row.skill
    return UserSkillRead(
        skill_id=row.skill_id,
        name=skill.name if skill else "",
        slug=skill.slug if skill else "",
        category=skill.category if skill else "",
        proficiency=row.proficiency,
        years_used=float(row.years_used) if row.years_used is not None else None,
        source=row.source,
        confirmed=row.confirmed,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def list_user_skills(
    db: Session,
    user: User,
    *,
    source: str | None = None,
    category: str | None = None,
) -> list[UserSkillRead]:
    """The caller's skills, joined with the taxonomy for name and category."""
    stmt = (
        select(UserSkill)
        .join(Skill, Skill.id == UserSkill.skill_id)
        .where(UserSkill.user_id == user.id)
    )
    if source:
        stmt = stmt.where(UserSkill.source == source)
    if category:
        stmt = stmt.where(Skill.category == category)
    # Deterministic order: strongest first, then by name. The UI's default sort.
    stmt = stmt.order_by(UserSkill.proficiency.desc(), Skill.name.asc())
    return [_to_read(row) for row in db.scalars(stmt).all()]


def add_skill(db: Session, user: User, payload: UserSkillCreate) -> UserSkillRead:
    """Add a skill from the taxonomy.

    ``422`` for an id that is not in the taxonomy, ``409`` for one already held.
    Both are deliberate: ``422`` means the client sent nonsense, ``409`` means the
    request collided with existing state, and conflating them makes the UI's error
    message wrong.
    """
    skill = _get_skill_or_error(db, payload.skill_id)

    existing = db.get(UserSkill, (user.id, payload.skill_id))
    if existing is not None:
        raise ConflictError(
            f"You have already added {skill.name}.", code="skill_already_present"
        )

    row = UserSkill(
        user_id=user.id,
        skill_id=payload.skill_id,
        proficiency=payload.proficiency,
        source=payload.source,
        years_used=Decimal(str(payload.years_used)) if payload.years_used is not None else None,
        confirmed=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_read(row)


def update_skill(
    db: Session, user: User, skill_id: int, payload: UserSkillUpdate
) -> UserSkillRead:
    """Update proficiency / years used / confirmed, scoped to the owner."""
    row = db.get(UserSkill, (user.id, skill_id))
    if row is None:
        # 404, not 403: a 403 would confirm the skill exists for *someone*.
        raise NotFoundError("You have not added that skill.")

    changes = payload.model_dump(exclude_unset=True)
    if "years_used" in changes and changes["years_used"] is not None:
        changes["years_used"] = Decimal(str(changes["years_used"]))
    for field, value in changes.items():
        setattr(row, field, value)
    if changes:
        db.commit()
        db.refresh(row)
    return _to_read(row)


def remove_skill(db: Session, user: User, skill_id: int) -> None:
    row = db.get(UserSkill, (user.id, skill_id))
    if row is None:
        raise NotFoundError("You have not added that skill.")
    db.delete(row)
    db.commit()


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


def search_taxonomy(
    db: Session,
    *,
    q: str | None = None,
    category: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> TaxonomySearchResponse:
    """Search the taxonomy by name **or alias**.

    Matching aliases is what makes typing ``sklearn`` find ``Scikit-learn`` — the
    alias feature made visible, and a small lesson in the system's vocabulary.
    The trigram index on ``skill.name`` supports the substring case.
    """
    limit = max(1, min(limit, MAX_RESULTS))
    offset = max(0, offset)

    conditions = []
    if q and q.strip():
        needle = f"%{q.strip().lower()}%"
        alias_match = (
            select(SkillAlias.skill_id)
            .where(SkillAlias.alias.like(needle))
            .correlate(None)
        )
        conditions.append(
            or_(
                func.lower(Skill.name).like(needle),
                func.lower(Skill.slug).like(needle),
                Skill.id.in_(alias_match),
            )
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
    aliases = _aliases_for(db, [s.id for s in skills])

    return TaxonomySearchResponse(
        total=total,
        query=q,
        category=category,
        items=[
            SkillRead(
                id=s.id,
                name=s.name,
                slug=s.slug,
                category=s.category,
                description=s.description,
                aliases=sorted(aliases.get(s.id, [])),
            )
            for s in skills
        ],
    )


def confirm_detected_skills(
    db: Session, user: User, payload: DetectedSkillConfirm
) -> ConfirmResult:
    """Upsert CV-detected skills the user accepted.

    **This is the boundary that makes "every skill in ``user_skill`` is
    user-confirmed" a checkable invariant.** Rejected items are recorded against
    the staged row with ``accepted = false`` and never enter ``user_skill``,
    so an unconfirmed extraction can influence nothing.

    Idempotent: confirming the same list twice changes nothing, so a double-click
    or a page refresh after confirming is harmless.
    """
    result = ConfirmResult()
    known: dict[int, Skill] = {}
    staged_updates: list[tuple[bool, int, int]] = []

    for item in payload.skills:
        skill = known.get(item.skill_id)
        if skill is None:
            skill = db.get(Skill, item.skill_id)
            if skill is None:
                # Per-item rejection, not a whole-request failure. One stale id in a
                # 20-item list should not discard 19 good confirmations.
                result.rejected.append(item.skill_id)
                logger.info(
                    "Rejected confirmation for unknown skill_id=%s (user=%s)",
                    item.skill_id,
                    user.id,
                )
                continue
            known[item.skill_id] = skill

        if not item.accepted:
            result.declined += 1
            if payload.resume_upload_id is not None:
                staged_updates.append((False, payload.resume_upload_id, item.skill_id))
            continue

        existing = db.get(UserSkill, (user.id, item.skill_id))
        if existing is None:
            db.add(
                UserSkill(
                    user_id=user.id,
                    skill_id=item.skill_id,
                    proficiency=item.proficiency or 3,
                    source=SkillSource.CV_EXTRACTED.value,
                    confirmed=True,
                )
            )
            result.added += 1
        else:
            # An accepted skill the user already holds: upgrade provenance and
            # apply the proficiency they just chose, if they gave one.
            changed = False
            if item.proficiency is not None and item.proficiency != existing.proficiency:
                existing.proficiency = item.proficiency
                changed = True
            if existing.source != SkillSource.CV_EXTRACTED.value:
                existing.source = SkillSource.CV_EXTRACTED.value
                changed = True
            if not existing.confirmed:
                existing.confirmed = True
                changed = True
            if changed:
                result.updated += 1
            else:
                result.skipped += 1
        result.accepted += 1

        if payload.resume_upload_id is not None:
            staged_updates.append((True, payload.resume_upload_id, item.skill_id))
        result.details.append(
            {"skill_id": item.skill_id, "name": skill.name, "accepted": True}
        )

    if staged_updates:
        from app.models.resume import ResumeDetectedSkill, ResumeUpload

        for accepted, upload_id, skill_id in staged_updates:
            staged = db.get(ResumeDetectedSkill, (upload_id, skill_id))
            if staged is not None:
                staged.accepted = accepted
        upload = db.get(ResumeUpload, payload.resume_upload_id)
        if upload is not None and upload.user_id == user.id:
            upload.status = "confirmed"

    db.commit()
    logger.info(
        "Confirmed CV skills for user %s: added=%s updated=%s skipped=%s declined=%s rejected=%s",
        user.id,
        result.added,
        result.updated,
        result.skipped,
        result.declined,
        len(result.rejected),
    )
    return result
