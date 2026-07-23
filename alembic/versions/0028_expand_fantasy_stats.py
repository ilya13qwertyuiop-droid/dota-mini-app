"""Расширить сырые показатели Fantasy и добавить адаптивный JSON-снимок.

Revision ID: 0028
Revises: 0027
Create Date: 2026-07-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0028"
down_revision: Union[str, None] = "0027"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_COLUMNS: tuple[sa.Column, ...] = (
    sa.Column("hero_id", sa.Integer(), nullable=True),
    sa.Column("duration", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("start_time", sa.BigInteger(), nullable=True),
    sa.Column("patch", sa.Integer(), nullable=True),
    sa.Column("win", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("denies", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("net_worth", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("hero_damage", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("hero_healing", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("tower_damage", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("sen_placed", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("rune_pickups", sa.Integer(), nullable=False, server_default="0"),
    sa.Column(
        "teamfight_participation",
        sa.Float(),
        nullable=False,
        server_default="0",
    ),
    sa.Column("courier_kills", sa.Integer(), nullable=False, server_default="0"),
    sa.Column(
        "firstblood_claimed",
        sa.Integer(),
        nullable=False,
        server_default="0",
    ),
    sa.Column("smokes_used", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("watchers_taken", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("madstones_used", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("tormentor_kills", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("lotuses_used", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("buyback_count", sa.Integer(), nullable=False, server_default="0"),
    sa.Column("metrics_json", sa.Text(), nullable=True),
)


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "fantasy_match_snapshots" not in tables:
        op.create_table(
            "fantasy_match_snapshots",
            sa.Column("match_id", sa.BigInteger(), primary_key=True),
            sa.Column("league_id", sa.Integer(), nullable=False),
            sa.Column("payload_gzip", sa.LargeBinary(), nullable=False),
            sa.Column(
                "schema_version",
                sa.Integer(),
                nullable=False,
                server_default="1",
            ),
            sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "fantasy_player_stats" not in tables:
        return
    existing = {
        column["name"]
        for column in inspector.get_columns("fantasy_player_stats")
    }
    for column in _COLUMNS:
        if column.name not in existing:
            op.add_column("fantasy_player_stats", column)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    tables = set(inspector.get_table_names())
    if "fantasy_player_stats" in tables:
        existing = {
            column["name"]
            for column in inspector.get_columns("fantasy_player_stats")
        }
        with op.batch_alter_table("fantasy_player_stats") as batch:
            for column in reversed(_COLUMNS):
                if column.name in existing:
                    batch.drop_column(column.name)
    if "fantasy_match_snapshots" in tables:
        op.drop_table("fantasy_match_snapshots")
