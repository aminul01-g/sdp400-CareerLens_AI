"""Revision 1 — infrastructure and the `user` table.

Kept separate from the domain schema so the authentication identity lands before
anything that references it, and so Phase 1's migration round-trip check
(T028) can be verified against a single, minimal table.

The functional unique index on ``lower(email)`` is here, not in revision 2,
because it is an authentication concern and the whole point of revision 1 is
that security finding S9 is closed the moment this migration runs.

Revision ID: 0001_infra_and_user
Revises:
Create Date: 2026-09-30
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_infra_and_user"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("user", "admin", name="user_role"),
            server_default="user",
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("length(trim(name)) > 0", name="ck_user_name_not_blank"),
        sa.CheckConstraint("length(trim(email)) > 0", name="ck_user_email_not_blank"),
        sa.PrimaryKeyConstraint("id", name="pk_user"),
    )
    op.create_index("ix_user_role", "user", ["role"], unique=False)

    # S9 fix. A plain UNIQUE on `email` would still admit "A@B.com" and
    # "a@b.com" as two rows, because text comparison is case-sensitive. The
    # application also lowercases on the way in, so this index is the second of
    # two independent defences rather than the only one.
    op.create_index(
        "uq_user_email_lower", "user", [sa.text("lower(email)")], unique=True
    )


def downgrade() -> None:
    op.drop_index("uq_user_email_lower", table_name="user")
    op.drop_index("ix_user_role", table_name="user")
    op.drop_table("user")
    sa.Enum(name="user_role").drop(op.get_bind(), checkfirst=True)
