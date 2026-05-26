"""Drop teammate_profiles.mood — настрой удалён из продукта.

Revision ID: 0013
Revises: 0012
Create Date: 2026-05-18

«Настрой» (win/fun/stomp) собирался в форме профиля, но нигде не
отображался — ни на карточке, ни в фильтрах. Мёртвые данные. Убрали
из формы/API/модели, дропаем колонку.

Идемпотентность через inspector (как 0009-0012). На SQLite drop_column
в современном alembic исполняется через batch автоматически.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(bind, table: str) -> set[str]:
    insp = sa.inspect(bind)
    if table not in set(insp.get_table_names()):
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    if "mood" in _columns(bind, "teammate_profiles"):
        op.drop_column("teammate_profiles", "mood")


def downgrade() -> None:
    bind = op.get_bind()
    if "mood" not in _columns(bind, "teammate_profiles"):
        op.add_column(
            "teammate_profiles",
            sa.Column("mood", sa.String(16), nullable=True),
        )
