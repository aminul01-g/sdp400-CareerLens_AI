"""Education record and certification CRUD."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.models.education import Certification, EducationRecord
from app.models.user import User
from app.schemas.education import (
    CertificationCreate,
    CertificationRead,
    CertificationUpdate,
    EducationCreate,
    EducationRead,
    EducationUpdate,
)

# Chronological, newest first — the order a CV lists qualifications in.
_EDUCATION_ORDER = (
    EducationRecord.end_year.desc().nullslast(),
    EducationRecord.start_year.desc().nullslast(),
    EducationRecord.id.desc(),
)
_CERTIFICATION_ORDER = (Certification.issued_on.desc().nullslast(), Certification.id.desc())


# --------------------------------------------------------------------------
# Education records
# --------------------------------------------------------------------------
def list_education(db: Session, user: User, *, limit: int, offset: int) -> tuple[int, list[EducationRead]]:
    total = int(
        db.scalar(
            select(func.count()).select_from(EducationRecord).where(
                EducationRecord.user_id == user.id
            )
        )
        or 0
    )
    rows = db.scalars(
        select(EducationRecord)
        .where(EducationRecord.user_id == user.id)
        .order_by(*_EDUCATION_ORDER)
        .limit(limit)
        .offset(offset)
    ).all()
    return total, [EducationRead.model_validate(row) for row in rows]


def get_education(db: Session, user: User, record_id: int) -> EducationRecord:
    record = db.scalar(
        select(EducationRecord).where(
            EducationRecord.id == record_id, EducationRecord.user_id == user.id
        )
    )
    if record is None:
        raise NotFoundError("That education record does not exist.")
    return record


def create_education(db: Session, user: User, payload: EducationCreate) -> EducationRead:
    record = EducationRecord(user_id=user.id, **payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return EducationRead.model_validate(record)


def update_education(
    db: Session, user: User, record_id: int, payload: EducationUpdate
) -> EducationRead:
    record = get_education(db, user, record_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    return EducationRead.model_validate(record)


def delete_education(db: Session, user: User, record_id: int) -> None:
    record = get_education(db, user, record_id)
    db.delete(record)
    db.commit()


# --------------------------------------------------------------------------
# Certifications
# --------------------------------------------------------------------------
def list_certifications(
    db: Session, user: User, *, limit: int, offset: int
) -> tuple[int, list[CertificationRead]]:
    total = int(
        db.scalar(
            select(func.count()).select_from(Certification).where(
                Certification.user_id == user.id
            )
        )
        or 0
    )
    rows = db.scalars(
        select(Certification)
        .where(Certification.user_id == user.id)
        .order_by(*_CERTIFICATION_ORDER)
        .limit(limit)
        .offset(offset)
    ).all()
    return total, [CertificationRead.model_validate(row) for row in rows]


def get_certification(db: Session, user: User, cert_id: int) -> Certification:
    record = db.scalar(
        select(Certification).where(
            Certification.id == cert_id, Certification.user_id == user.id
        )
    )
    if record is None:
        raise NotFoundError("That certification does not exist.")
    return record


def create_certification(
    db: Session, user: User, payload: CertificationCreate
) -> CertificationRead:
    record = Certification(user_id=user.id, **payload.model_dump())
    db.add(record)
    db.commit()
    db.refresh(record)
    return CertificationRead.model_validate(record)


def update_certification(
    db: Session, user: User, cert_id: int, payload: CertificationUpdate
) -> CertificationRead:
    record = get_certification(db, user, cert_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)
    db.commit()
    db.refresh(record)
    return CertificationRead.model_validate(record)


def delete_certification(db: Session, user: User, cert_id: int) -> None:
    record = get_certification(db, user, cert_id)
    db.delete(record)
    db.commit()
