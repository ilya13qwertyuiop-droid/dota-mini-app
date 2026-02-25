"""Add match_players table with extended per-player stats.

Revision ID: 0002
Revises: 0001
Create Date: 2026-02-26

Adds:
  match_players — one row per player per match; includes hero_id, side,
                  lane, lane_role, combat/economy stats, ward counts,
                  and up to 3 core item IDs.

All extended stats columns are nullable so that existing matches can be
backfilled incrementally via the BACKFILL_ENABLED worker mode.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "match_players",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        # Intentionally no FK constraint so SQLite implicit cascade rules
        # don't interfere; delete_matches_and_recalculate cleans this table
        # explicitly before removing matches rows.
        sa.Column("match_id", sa.BigInteger(), nullable=False),
        sa.Column("hero_id", sa.Integer(), nullable=False),
        sa.Column("player_slot", sa.Integer(), nullable=False),
        sa.Column("is_radiant", sa.Integer(), nullable=False),  # 0 or 1

        # Extended stats — nullable for backfill compatibility
        sa.Column("lane", sa.SmallInteger(), nullable=True),
        sa.Column("lane_role", sa.SmallInteger(), nullable=True),
        sa.Column("gpm", sa.Integer(), nullable=True),
        sa.Column("xpm", sa.Integer(), nullable=True),
        sa.Column("kills", sa.Integer(), nullable=True),
        sa.Column("deaths", sa.Integer(), nullable=True),
        sa.Column("assists", sa.Integer(), nullable=True),
        sa.Column("hero_damage", sa.Integer(), nullable=True),
        sa.Column("tower_damage", sa.Integer(), nullable=True),
        sa.Column("obs_placed", sa.Integer(), nullable=True),
        sa.Column("sen_placed", sa.Integer(), nullable=True),

        # Top-3 core item IDs (consumables filtered out)
        sa.Column("item0", sa.Integer(), nullable=True),
        sa.Column("item1", sa.Integer(), nullable=True),
        sa.Column("item2", sa.Integer(), nullable=True),

        sa.UniqueConstraint("match_id", "player_slot", name="uq_match_player"),
    )
    op.create_index("ix_match_players_match_id", "match_players", ["match_id"])


def downgrade() -> None:
    op.drop_index("ix_match_players_match_id", table_name="match_players")
    op.drop_table("match_players")
