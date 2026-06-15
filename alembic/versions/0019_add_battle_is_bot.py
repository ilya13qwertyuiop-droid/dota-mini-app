"""«Битва драфтов»: флаг is_bot — соперник-ИИ при пустом матчмейкинге.

Revision ID: 0019
Revises: 0018
Create Date: 2026-06-15

Когда живой соперник не нашёлся за таймаут поиска, в комнату подсаживается
бот: guest_id остаётся NULL, is_bot=True, роль бота — 'guest'. Колонка нужна,
чтобы сериализация/ходы/финализация отличали бота от живого гостя.
Идемпотентно (inspector), как 0016-0018.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0019"
down_revision: Union[str, None] = "0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "draft_battles"
_COL = "is_bot"


def _has_column(bind) -> bool:
    insp = sa.inspect(bind)
    if _TABLE not in set(insp.get_table_names()):
        return True   # таблицы нет — её создаст create_all уже с колонкой
    return _COL in {c["name"] for c in insp.get_columns(_TABLE)}


def upgrade() -> None:
    if not _has_column(op.get_bind()):
        op.add_column(
            _TABLE,
            sa.Column(_COL, sa.Boolean(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    if _has_column(op.get_bind()):
        op.drop_column(_TABLE, _COL)
