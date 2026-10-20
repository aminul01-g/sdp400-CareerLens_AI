"""Revision 6 — email verification and password reset.

``docs/limitations.md`` used to say there was no email verification and no
password reset, and that a user who forgot their password had no self-service
route. It also called that "a genuine gap for anything beyond a classroom
project", which was fair.

This revision adds what the two flows need:

* ``user.is_verified`` and ``user.email_verified_at`` — whether the address
  has been proven to belong to the person who registered it.
* ``auth_token`` — the one-time tokens the two flows issue. Only the SHA-256
  digest is stored, each token is single-use, each expires, and issuing a new
  one invalidates the outstanding ones.

``user.password_changed_at`` was added in revision 5, alongside the audit log,
because it is the same idea: a record of *when* something changed. A token
issued before that instant is rejected, which is how a password change
invalidates the sessions that were outstanding when it happened.

Revision ID: 0006_auth_tokens
Revises: 0005_audit_log
Create Date: 2026-10-19
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_auth_tokens"
down_revision: str | None = "0005_audit_log"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column(
            "is_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "user",
        sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    # The session counter. Bumped on a password change so that the sessions
    # outstanding at the time stop working.
    op.add_column(
        "user",
        sa.Column(
            "token_version",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )

    op.create_table(
        "auth_token",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("purpose", sa.String(length=32), nullable=False),
        # The SHA-256 digest. The token itself is never stored.
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "purpose IN ('email_verification','password_reset')",
            name="ck_auth_token_purpose_valid",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name="fk_auth_token_user_id_user",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_auth_token"),
    )
    op.create_index("uq_auth_token_hash", "auth_token", ["token_hash"], unique=True)
    op.create_index(
        "ix_auth_token_user", "auth_token", ["user_id", "purpose"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_auth_token_user", table_name="auth_token")
    op.drop_index("uq_auth_token_hash", table_name="auth_token")
    op.drop_table("auth_token")

    op.drop_column("user", "token_version")
    op.drop_column("user", "email_verified_at")
    op.drop_column("user", "is_verified")
