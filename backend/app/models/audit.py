"""``AuditLog`` — who changed what, when, and from where.

``docs/limitations.md`` used to say there was no audit log, and that
``recommendation_run`` was "history of computations, not of administrative
change". It was right. This table is the second kind of history.

Three decisions in the shape of this table are worth stating:

1. **The actor is nullable, and the email is stored as well as the id.** An
   admin who is later deleted must not erase the record of what they did, so
   the foreign key is ``ON DELETE SET NULL`` and the email is copied onto the
   row. The row outlives the account.
2. **The change is recorded with the change, in one transaction.** The
   service layer calls :func:`app.services.audit_service.record` before its
   own ``commit``, so the audit row and the thing it describes are written
   together or not at all. An audit log that can disagree with the data is
   worse than none, because it looks authoritative.
3. **Free-text summaries, structured filters.** ``action`` and ``entity_type``
   are short, stable identifiers that a filter can use; ``summary`` is prose
   for a human reading the table. Machine queries should use the former and
   never parse the latter.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:  # pragma: no cover
    from app.models.user import User


class AuditLog(Base):
    __tablename__ = "audit_log"
    __table_args__ = (
        # "What happened, in order" — the query the admin page runs.
        Index("ix_audit_log_created_at", "created_at"),
        # "What has this actor done?"
        Index("ix_audit_log_actor", "actor_id", "created_at"),
        # "What has happened to this thing?"
        Index("ix_audit_log_entity", "entity_type", "entity_id"),
        # "Everything of one kind" — e.g. every failed login.
        Index("ix_audit_log_action", "action", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # SET NULL, not CASCADE: deleting an account must not delete the record of
    # what that account did.
    actor_id: Mapped[int | None] = mapped_column(
        ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    # Copied, so the record survives the account.
    actor_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    # A short, stable identifier: "job_role.updated", "auth.login_failed".
    action: Mapped[str] = mapped_column(String(60), nullable=False)
    # What kind of thing was acted on: "job_role", "taxonomy", "user", "auth".
    entity_type: Mapped[str] = mapped_column(String(60), nullable=False)
    # The identifier of that thing, as a string so that non-numeric ids work.
    entity_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # One line, for a human reading the table.
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    # The structured detail: the payload that was applied, and the state
    # before it, where the caller knows it.
    changes: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict, server_default="{}"
    )
    # The apparent client address, and the peer that actually served it.
    client_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    peer_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    # Correlates the row with the application's own log lines.
    request_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    actor: Mapped[User | None] = relationship()

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<AuditLog id={self.id} action={self.action!r} "
            f"entity={self.entity_type}:{self.entity_id}>"
        )
