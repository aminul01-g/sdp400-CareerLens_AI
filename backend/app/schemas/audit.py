"""Audit log schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuditEntryRead(BaseModel):
    """One audit row.

    ``action`` and ``entity_type`` are the stable, machine-readable
    identifiers. ``summary`` is prose for a human and may change wording at
    any time — a filter should never depend on it.
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    actor_id: int | None = None
    actor_email: str | None = None
    action: str
    entity_type: str
    entity_id: str | None = None
    summary: str
    changes: dict[str, Any] = Field(default_factory=dict)
    client_ip: str | None = None
    peer_ip: str | None = None
    request_id: str | None = None
    created_at: datetime


class AuditActionCount(BaseModel):
    """How many times one action has been recorded."""

    action: str
    count: int
