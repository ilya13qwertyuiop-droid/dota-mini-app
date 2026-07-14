"""«Битва драфтов»: счётчик сыгранных живых боёв (состояние калибровки рейтинга).

Revision ID: 0021
Revises: 0020
Create Date: 2026-06-19

Рейтинг считается только за бои с живым соперником. Первые
_BT_CALIBRATION_GAMES таких боёв — калибровка (большой K, ранг скрыт за
бейджем «Калибровка»). Чтобы дёшево знать, на калибровке игрок или нет, и
какой K применять, держим счётчик завершённых живых боёв на профиле.
Идемпотентно (inspector), как 0016-0020.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0021"
down_revision: Union[str, None] = "0020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "user_profiles"
_COL = "battle_games_played"


def _has_column(bind) -> bool:
    insp = sa.inspect(bind)
    if _TABLE not in set(insp.get_table_names()):
        return True   # таблицы нет — её создаст create_all уже с колонкой
    return _COL in {c["name"] for c in insp.get_columns(_TABLE)}


def upgrade() -> None:
    if not _has_column(op.get_bind()):
        op.add_column(
            _TABLE,
            sa.Column(_COL, sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    if _has_column(op.get_bind()):
        op.drop_column(_TABLE, _COL)
