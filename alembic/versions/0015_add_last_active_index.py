"""Add index on teammate_profiles.last_active_at — сортировка ленты.

Revision ID: 0015
Revises: 0014
Create Date: 2026-05-26

Лента (/api/teammates/feed) сортируется `ORDER BY last_active_at DESC`, но
индекса на этом поле не было — на росте базы это full-scan + sort на каждый
запрос ленты. Добавляем индекс. Имя совпадает с дефолтным SQLAlchemy
(`ix_teammate_profiles_last_active_at`), чтобы не задвоиться с create_all,
который на свежих БД уже создаёт индекс из index=True в модели.

Идемпотентность через inspector (как 0009-0014).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0015"
down_revision: Union[str, None] = "0014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "teammate_profiles"
_INDEX = "ix_teammate_profiles_last_active_at"


def _has_index(bind, table: str, index: str) -> bool:
    insp = sa.inspect(bind)
    if table not in set(insp.get_table_names()):
        return False
    return index in {ix["name"] for ix in insp.get_indexes(table)}


def upgrade() -> None:
    bind = op.get_bind()
    if not _has_index(bind, _TABLE, _INDEX):
        op.create_index(_INDEX, _TABLE, ["last_active_at"])


def downgrade() -> None:
    bind = op.get_bind()
    if _has_index(bind, _TABLE, _INDEX):
        op.drop_index(_INDEX, table_name=_TABLE)
