"""«Битва драфтов»: draft_battles + draft_battle_actions.

Revision ID: 0017
Revises: 0016
Create Date: 2026-06-12

PvP-драфтер: комнаты (очередь/приватные по коду), журнал ходов, серверные
таймеры с резервом. Схема зеркалит модели DraftBattle / DraftBattleAction
в backend/models.py; на свежих БД таблицы создаёт create_all — миграция
идемпотентно пропускает существующее (конвенция 0009-0016).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0017"
down_revision: Union[str, None] = "0016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _tables(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def upgrade() -> None:
    bind = op.get_bind()
    existing = _tables(bind)

    if "draft_battles" not in existing:
        op.create_table(
            "draft_battles",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("code", sa.String(8), nullable=False),
            sa.Column("mode", sa.String(8), nullable=False),
            sa.Column("status", sa.String(12), nullable=False, server_default="waiting"),
            sa.Column("host_id", sa.BigInteger,
                      sa.ForeignKey("user_profiles.user_id"), nullable=False),
            sa.Column("guest_id", sa.BigInteger,
                      sa.ForeignKey("user_profiles.user_id"), nullable=True),
            sa.Column("first_pick", sa.String(5), nullable=True),
            sa.Column("turn_index", sa.SmallInteger, nullable=False, server_default="0"),
            sa.Column("state_version", sa.Integer, nullable=False, server_default="1"),
            sa.Column("turn_started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("deadline_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("host_reserve_ms", sa.Integer, nullable=False, server_default="120000"),
            sa.Column("guest_reserve_ms", sa.Integer, nullable=False, server_default="120000"),
            sa.Column("result", sa.JSON, nullable=True),
            sa.Column("winner", sa.String(5), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_action_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_draft_battles_code", "draft_battles", ["code"], unique=True)
        op.create_index("ix_draft_battles_status", "draft_battles", ["status"])
        op.create_index("ix_draft_battles_host_id", "draft_battles", ["host_id"])
        op.create_index("ix_draft_battles_guest_id", "draft_battles", ["guest_id"])
        op.create_index("ix_draft_battles_status_mode", "draft_battles", ["status", "mode"])

    if "draft_battle_actions" not in existing:
        op.create_table(
            "draft_battle_actions",
            sa.Column("battle_id", sa.Integer,
                      sa.ForeignKey("draft_battles.id"), primary_key=True),
            sa.Column("idx", sa.SmallInteger, primary_key=True),
            sa.Column("actor", sa.String(5), nullable=False),
            sa.Column("kind", sa.String(4), nullable=False),
            sa.Column("hero_id", sa.Integer, nullable=False),
            sa.Column("is_auto", sa.Boolean, nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade() -> None:
    bind = op.get_bind()
    existing = _tables(bind)
    if "draft_battle_actions" in existing:
        op.drop_table("draft_battle_actions")
    if "draft_battles" in existing:
        op.drop_table("draft_battles")
