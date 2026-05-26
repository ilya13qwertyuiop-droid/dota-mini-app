"""Add teammate_profiles.founder_number — метка «первопроходца».

Revision ID: 0014
Revises: 0013
Create Date: 2026-05-26

Первым пользователям, заполнившим профиль (пока выдано меньше
_TM_FOUNDER_CAP в api.py), присваивается порядковый номер. Сам номер
наружу не отдаём — наружу уходит только факт is_founder = (номер есть).
Используется для янтарной метки на карточке + счётчика «осталось N мест».

Идемпотентность через inspector (как 0009-0013).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(bind, table: str) -> set[str]:
    insp = sa.inspect(bind)
    if table not in set(insp.get_table_names()):
        return set()
    return {c["name"] for c in insp.get_columns(table)}


# Должно совпадать с _TM_FOUNDER_CAP в backend/api.py.
_FOUNDER_CAP = 1000


def upgrade() -> None:
    bind = op.get_bind()
    if "founder_number" not in _columns(bind, "teammate_profiles"):
        op.add_column(
            "teammate_profiles",
            sa.Column("founder_number", sa.Integer(), nullable=True),
        )
        # Backfill: уже существующие профили — самые ранние пользователи,
        # они и есть первопроходцы. Нумеруем по дате создания (1..cap).
        # ROW_NUMBER работает и в PostgreSQL, и в современном SQLite.
        bind.execute(
            sa.text(
                """
                WITH ranked AS (
                    SELECT user_id,
                           ROW_NUMBER() OVER (ORDER BY created_at, user_id) AS rn
                    FROM teammate_profiles
                )
                UPDATE teammate_profiles AS tp
                SET founder_number = ranked.rn
                FROM ranked
                WHERE tp.user_id = ranked.user_id
                  AND ranked.rn <= :cap
                """
            ),
            {"cap": _FOUNDER_CAP},
        )


def downgrade() -> None:
    bind = op.get_bind()
    if "founder_number" in _columns(bind, "teammate_profiles"):
        op.drop_column("teammate_profiles", "founder_number")
