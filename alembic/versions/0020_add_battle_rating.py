"""«Битва драфтов»: задел под рейтинг — per-battle снимки рейтинга + рейтинг игрока.

Revision ID: 0020
Revises: 0019
Create Date: 2026-06-19

Этап истории битв. Логику пересчёта рейтинга добавим позже; здесь только
закладываем схему, чтобы не делать вторую миграцию:
  draft_battles.{host,guest}_rating_{before,after} — снимок рейтинга обеих
    сторон на момент финализации (nullable: до включения рейтинга — NULL).
  user_profiles.battle_rating — текущий рейтинг игрока в «Битве драфтов»,
    стартовое значение _BT_RATING_BASE (1000).
Идемпотентно (inspector), как 0016-0019.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0020"
down_revision: Union[str, None] = "0019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_RATING_BASE = 1000

_BATTLE_COLS = (
    "host_rating_before",
    "host_rating_after",
    "guest_rating_before",
    "guest_rating_after",
)


def _columns(bind, table) -> set:
    insp = sa.inspect(bind)
    if table not in set(insp.get_table_names()):
        return None  # таблицы нет — её создаст create_all уже с колонками
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()

    cols = _columns(bind, "draft_battles")
    if cols is not None:
        for name in _BATTLE_COLS:
            if name not in cols:
                op.add_column(
                    "draft_battles", sa.Column(name, sa.Integer(), nullable=True)
                )

    cols = _columns(bind, "user_profiles")
    if cols is not None and "battle_rating" not in cols:
        op.add_column(
            "user_profiles",
            sa.Column(
                "battle_rating",
                sa.Integer(),
                nullable=False,
                server_default=str(_RATING_BASE),
            ),
        )


def downgrade() -> None:
    bind = op.get_bind()

    cols = _columns(bind, "user_profiles")
    if cols is not None and "battle_rating" in cols:
        op.drop_column("user_profiles", "battle_rating")

    cols = _columns(bind, "draft_battles")
    if cols is not None:
        for name in _BATTLE_COLS:
            if name in cols:
                op.drop_column("draft_battles", name)
