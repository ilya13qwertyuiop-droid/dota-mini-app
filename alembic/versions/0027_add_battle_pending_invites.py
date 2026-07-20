"""Persist pending friend-battle invitations.

Revision ID: 0027
Revises: 0026
Create Date: 2026-07-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0027"
down_revision: Union[str, None] = "0026"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "battle_pending_invites",
        sa.Column("user_id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "battle_id",
            sa.Integer(),
            sa.ForeignKey("draft_battles.id"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "subscription_verified_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_battle_pending_invites_battle_id",
        "battle_pending_invites",
        ["battle_id"],
    )
    op.create_index(
        "ix_battle_pending_invites_expires_at",
        "battle_pending_invites",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_battle_pending_invites_expires_at",
        table_name="battle_pending_invites",
    )
    op.drop_index(
        "ix_battle_pending_invites_battle_id",
        table_name="battle_pending_invites",
    )
    op.drop_table("battle_pending_invites")
