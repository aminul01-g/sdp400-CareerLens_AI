"""Writing and reading the audit log.

The service layer calls :func:`record` **before** its own ``commit``, so the
audit row and the change it describes are written in one transaction. That is
the whole point: an audit log that can disagree with the data is worse than no
audit log, because it looks authoritative.

The client address and the request id are read from the ambient request
context rather than passed in, so a service function that changes something
does not have to know it is being audited. See ``app/core/request_context.py``.

The functions here do not commit. The caller commits, and that commit covers
both the change and the audit row.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.logging import request_id_var
from app.core.request_context import current_client_ip, current_peer_ip
from app.models.audit import AuditLog
from app.models.user import User

logger = logging.getLogger("app.services.audit")

#: The actions the system writes. Kept as a set so a typo is a test failure
#: rather than a row nobody can filter for.
ACTIONS: frozenset[str] = frozenset(
    {
        "auth.registered",
        "auth.login_succeeded",
        "auth.login_failed",
        "auth.logged_out",
        "auth.password_changed",
        "auth.email_verified",
        "auth.password_reset_requested",
        "auth.password_reset_completed",
        "user.role_changed",
        "user.deactivated",
        "job_role.created",
        "job_role.updated",
        "job_role.deleted",
        "job_role.skills_replaced",
        "taxonomy.skill_created",
        "taxonomy.skill_updated",
        "taxonomy.skill_deleted",
        "recommendation.feedback_recorded",
    }
)

#: The kinds of thing an action can be performed on.
ENTITY_TYPES: frozenset[str] = frozenset(
    {"auth", "user", "job_role", "taxonomy", "recommendation", "profile"}
)


def record(
    db: Session,
    *,
    action: str,
    entity_type: str,
    summary: str,
    entity_id: str | int | None = None,
    actor: User | None = None,
    changes: dict[str, Any] | None = None,
) -> AuditLog:
    """Stage an audit row. **The caller commits.**

    Args:
        db: The session the change is being made in.
        action: A short, stable identifier from :data:`ACTIONS`.
        entity_type: A short, stable identifier from :data:`ENTITY_TYPES`.
        summary: One line, for a human reading the table.
        entity_id: The thing that was acted on, as a string or an int.
        actor: The user who did it, or ``None`` for an anonymous event such as
            a failed login. The email is copied onto the row so the record
            survives the account.
        changes: The structured detail — the payload applied, and the state
            before it where the caller knows it.
    """
    if action not in ACTIONS:
        raise ValueError(
            f"Unknown audit action {action!r}; add it to app.services.audit_service.ACTIONS."
        )
    if entity_type not in ENTITY_TYPES:
        raise ValueError(
            f"Unknown audit entity type {entity_type!r}; add it to "
            "app.services.audit_service.ENTITY_TYPES."
        )

    entry = AuditLog(
        actor_id=actor.id if actor is not None else None,
        actor_email=actor.email if actor is not None else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        summary=summary,
        changes=changes or {},
        client_ip=current_client_ip(),
        peer_ip=current_peer_ip(),
        request_id=request_id_var.get(),
    )
    db.add(entry)
    logger.info(
        "Audit %s %s:%s by %s",
        action,
        entity_type,
        entry.entity_id,
        entry.actor_email or "anonymous",
        extra={"kind": "audit"},
    )
    return entry


def list_entries(
    db: Session,
    *,
    limit: int,
    offset: int,
    action: str | None = None,
    entity_type: str | None = None,
    actor_id: int | None = None,
) -> tuple[int, list[AuditLog]]:
    """The audit trail, newest first."""
    stmt = select(AuditLog)
    count_stmt = select(func.count()).select_from(AuditLog)

    filters = []
    if action:
        filters.append(AuditLog.action == action)
    if entity_type:
        filters.append(AuditLog.entity_type == entity_type)
    if actor_id is not None:
        filters.append(AuditLog.actor_id == actor_id)
    for condition in filters:
        stmt = stmt.where(condition)
        count_stmt = count_stmt.where(condition)

    total = int(db.scalar(count_stmt) or 0)
    rows = list(
        db.scalars(
            stmt.order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(limit)
            .offset(offset)
        ).all()
    )
    return total, rows
