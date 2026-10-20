"""The work history: what somebody has done, and for how long.

Two things live here:

* **The CRUD**, over the user's own rows.
* **The arithmetic.** How much experience does a work history actually
  represent? A person who held two roles at once has not gained a year of
  experience by holding two jobs at once, so overlapping roles are counted
  once. That is a policy question, and policy questions do not belong in the
  ML layer or in the schema.

Only **confirmed** rows count. A row the CV pipeline proposed is a proposal
until the user accepts it, and a proposal that has not been accepted does not
influence anything — the same rule that governs a detected skill.
"""

from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.ml.work_history import total_months
from app.models.user import User
from app.models.work_history import WorkHistory, WorkHistorySource
from app.schemas.work_history import (
    WorkHistoryCreate,
    WorkHistoryRead,
    WorkHistoryUpdate,
)

logger = logging.getLogger("app.services.work_history")

#: The number of months in a year, for turning months into a whole number of
#: years. A fractional figure would be more precise and less useful: "7 years"
#: is what a person says, and what a role's expected experience is written in.
MONTHS_PER_YEAR = 12


def _to_read(row: WorkHistory) -> WorkHistoryRead:
    return WorkHistoryRead(
        id=row.id,
        employer=row.employer,
        title=row.title,
        start_date=row.start_date,
        end_date=row.end_date,
        source=row.source,
        confirmed=row.confirmed,
        raw_text=row.raw_text,
    )


def list_entries(db: Session, user: User) -> list[WorkHistoryRead]:
    """The user's work history, most recent first."""
    rows = db.scalars(
        select(WorkHistory)
        .where(WorkHistory.user_id == user.id)
        .order_by(
            WorkHistory.start_date.is_(None),
            WorkHistory.start_date.desc(),
            WorkHistory.id.desc(),
        )
    ).all()
    return [_to_read(row) for row in rows]


def get_entry(db: Session, user: User, entry_id: int) -> WorkHistory:
    """Ownership enforced in the query: 404, not 403."""
    row = db.get(WorkHistory, entry_id)
    if row is None or row.user_id != user.id:
        raise NotFoundError("That work history entry does not exist.")
    return row


def create_entry(
    db: Session, user: User, payload: WorkHistoryCreate
) -> WorkHistoryRead:
    row = WorkHistory(
        user_id=user.id,
        employer=payload.employer,
        title=payload.title,
        start_date=payload.start_date,
        end_date=payload.end_date,
        source=WorkHistorySource.MANUAL.value,
        # A row the user typed is a fact, so it starts confirmed.
        confirmed=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_read(row)


def update_entry(
    db: Session, user: User, entry_id: int, payload: WorkHistoryUpdate
) -> WorkHistoryRead:
    row = get_entry(db, user, entry_id)
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(row, field, value)
    if changes:
        db.commit()
        db.refresh(row)
    return _to_read(row)


def delete_entry(db: Session, user: User, entry_id: int) -> None:
    row = get_entry(db, user, entry_id)
    db.delete(row)
    db.commit()


def confirm_entry(db: Session, user: User, entry_id: int) -> WorkHistoryRead:
    """Accept a proposal the CV pipeline made.

    Until this happens the row does not count towards the experience signal.
    """
    row = get_entry(db, user, entry_id)
    row.confirmed = True
    db.commit()
    db.refresh(row)
    logger.info(
        "Confirmed work history entry id=%s employer=%s", row.id, row.employer,
        extra={"kind": "work_history"},
    )
    return _to_read(row)


def observed_months(db: Session, user: User, *, today: date | None = None) -> int:
    """How many months the user's confirmed work history covers.

    Overlapping roles are counted once, by the month.
    """
    rows = db.scalars(
        select(WorkHistory).where(
            WorkHistory.user_id == user.id, WorkHistory.confirmed.is_(True)
        )
    ).all()
    from app.ml.work_history import WorkHistoryEntry

    return total_months(
        [
            WorkHistoryEntry(
                employer=row.employer,
                start_date=row.start_date,
                end_date=row.end_date,
                is_current=row.end_date is None,
            )
            for row in rows
        ],
        today=today,
    )


def observed_years(db: Session, user: User, *, today: date | None = None) -> int | None:
    """The work history in whole years, or ``None`` when there is none.

    ``None`` rather than ``0``, because "no work history" and "no experience"
    are different answers and only one of them should override a declared
    figure.
    """
    months = observed_months(db, user, today=today)
    if months <= 0:
        return None
    return months // MONTHS_PER_YEAR


__all__ = [
    "confirm_entry",
    "create_entry",
    "delete_entry",
    "get_entry",
    "list_entries",
    "observed_months",
    "observed_years",
    "update_entry",
]
