"""«Битва драфтов»: индекс лидерборда на user_profiles.

Revision ID: 0022
Revises: 0021
Create Date: 2026-07-10

/api/battle/leaderboard: WHERE battle_games_played >= N ORDER BY
battle_rating DESC — без индекса на десятках тысяч профилей это
seq scan + sort на каждый вход в топ. Имя индекса = имени в модели
(конвенция 0015/0016). Идемпотентно (inspector).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0022"
down_revision: Union[str, None] = "0021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "user_profiles"
_INDEX = "ix_user_profiles_battle_lb"


def _index_exists(bind) -> bool:
    insp = sa.inspect(bind)
    if _TABLE not in set(insp.get_table_names()):
        return True   # таблицы нет — её создаст create_all уже с индексом
    return _INDEX in {ix["name"] for ix in insp.get_indexes(_TABLE)}


def upgrade() -> None:
    if not _index_exists(op.get_bind()):
        op.create_index(
            _INDEX, _TABLE, ["battle_games_played", "battle_rating"]
        )


def downgrade() -> None:
    if _index_exists(op.get_bind()):
        op.drop_index(_INDEX, table_name=_TABLE)
