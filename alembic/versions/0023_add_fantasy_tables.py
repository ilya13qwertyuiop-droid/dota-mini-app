"""Фэнтези TI: статистика про-игроков с крупных турниров сезона.

Revision ID: 0023
Revises: 0022
Create Date: 2026-07-15

Кормится новым stats_updater.py (переписан под фэнтези-парсер):
  fantasy_players      — справочник игроков TI-команд (снапшот команды/ника)
  fantasy_player_stats — пер-матчевые фэнтези-показатели (сырые, БЕЗ очков:
                         механика компендиума TI2026 неизвестна — формула
                         прикрутится конфигом на этапе 2)
Идемпотентно (inspector), как 0016-0022.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0023"
down_revision: Union[str, None] = "0022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    tables = set(insp.get_table_names())

    if "fantasy_players" not in tables:
        op.create_table(
            "fantasy_players",
            sa.Column("account_id", sa.BigInteger(), primary_key=True),
            sa.Column("name", sa.String(64), nullable=True),
            sa.Column("team_id", sa.BigInteger(), nullable=True),
            sa.Column("team_name", sa.String(64), nullable=True),
            # 'core' / 'support' из OpenDota fantasy_role; mid OpenDota не
            # различает — уточнится ручной разметкой на этапе 2.
            sa.Column("position", sa.String(12), nullable=True),
        )

    if "fantasy_player_stats" not in tables:
        op.create_table(
            "fantasy_player_stats",
            sa.Column("match_id", sa.BigInteger(), primary_key=True),
            sa.Column("account_id", sa.BigInteger(), primary_key=True),
            sa.Column("league_id", sa.Integer(), nullable=False),
            sa.Column("kills", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("deaths", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("assists", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_hits", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("gold_per_min", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("xp_per_min", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("stuns", sa.Float(), nullable=False, server_default="0"),
            sa.Column("obs_placed", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("camps_stacked", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("tower_kills", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("roshan_kills", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index(
            "ix_fantasy_player_stats_account", "fantasy_player_stats",
            ["account_id"],
        )
        op.create_index(
            "ix_fantasy_player_stats_league", "fantasy_player_stats",
            ["league_id"],
        )


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    tables = set(insp.get_table_names())
    if "fantasy_player_stats" in tables:
        op.drop_table("fantasy_player_stats")
    if "fantasy_players" in tables:
        op.drop_table("fantasy_players")
