"""Add game_mode column to matches table.

Revision ID: 0003
Revises: 0002
Create Date: 2026-02-27

Adds:
  matches.game_mode — SmallInteger, nullable.
    OpenDota codes used as filter:
      1  = All Pick (unranked)
      22 = Ranked All Pick
      23 = Turbo  (now excluded from ingestion)
    All other modes are also excluded by the worker's ALLOWED_GAME_MODES filter.

The column is nullable so that existing rows (saved before this migration)
keep working without any backfill.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "matches",
        sa.Column("game_mode", sa.SmallInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("matches", "game_mode")
