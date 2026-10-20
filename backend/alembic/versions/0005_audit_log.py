"""Revision 5 — the audit log.

``docs/limitations.md`` used to say there was no audit log, and that
``recommendation_run`` was "history of computations, not of administrative
change". It was right. This revision adds the second kind of history.

The table records who changed what, when, and from where. Three properties are
deliberate:

* **The actor does not cascade.** ``actor_id`` is ``ON DELETE SET NULL``, and
  the email is copied onto the row, so deleting an account does not delete the
  record of what that account did.
* **The row is written with the change.** The service layer adds the audit row
  before its own ``commit``, so the two are one transaction. An audit log that
  can disagree with the data is worse than none, because it looks
  authoritative.
* **It is not a proposal requirement.** The proposal does not list an audit log
  among its nine modules, so this is an extra in the same sense ``feedback``
  is — and it gets its own revision rather than inflating the 14-table core.

Revision ID: 0005_audit_log
Revises: 0004_signals
Create Date: 2026-10-19
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_audit_log"
down_revision: str | None = "0004_signals"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        # SET NULL, not CASCADE: deleting an account must not delete the record
        # of what that account did.
        sa.Column("actor_id", sa.Integer(), nullable=True),
        sa.Column("actor_email", sa.String(length=320), nullable=True),
        sa.Column("action", sa.String(length=60), nullable=False),
        sa.Column("entity_type", sa.String(length=60), nullable=False),
        sa.Column("entity_id", sa.String(length=120), nullable=True),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column(
            "changes",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
        sa.Column("client_ip", sa.String(length=45), nullable=True),
        sa.Column("peer_ip", sa.String(length=45), nullable=True),
        sa.Column("request_id", sa.String(length=32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["user.id"],
            name="fk_audit_log_actor_id_user",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_audit_log"),
    )
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"], unique=False)
    op.create_index(
        "ix_audit_log_actor", "audit_log", ["actor_id", "created_at"], unique=False
    )
    op.create_index(
        "ix_audit_log_entity", "audit_log", ["entity_type", "entity_id"], unique=False
    )
    op.create_index(
        "ix_audit_log_action", "audit_log", ["action", "created_at"], unique=False
    )

    # -- user: when the password last changed --------------------------------
    #
    # This belongs in the same revision as the audit log rather than with the
    # rest of the authentication work, because the two are the same idea: a
    # record of *when* something changed. A JWT issued before this instant is
    # rejected, which is how a password change invalidates the sessions that
    # were outstanding when it happened.
    op.add_column(
        "user",
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user", "password_changed_at")
    op.drop_index("ix_audit_log_action", table_name="audit_log")
    op.drop_index("ix_audit_log_entity", table_name="audit_log")
    op.drop_index("ix_audit_log_actor", table_name="audit_log")
    op.drop_index("ix_audit_log_created_at", table_name="audit_log")
    op.drop_table("audit_log")
