"""Add lobby_type column to matches table.

Revision ID: 0004
Revises: 0003
Create Date: 2026-02-27

Adds:
  matches.lobby_type — SmallInteger, nullable.
    OpenDota lobby_type codes (reference):
      0 = Public matchmaking
      7 = Ranked matchmaking
    All values are stored as-is; filtering is done by game_mode, not lobby_type.

The column is nullable so that existing rows (saved before this migration)
keep working without any backfill.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "matches",
        sa.Column("lobby_type", sa.SmallInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("matches", "lobby_type")
