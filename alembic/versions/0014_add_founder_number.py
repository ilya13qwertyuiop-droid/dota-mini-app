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


def upgrade() -> None:
    bind = op.get_bind()
    if "founder_number" not in _columns(bind, "teammate_profiles"):
        op.add_column(
            "teammate_profiles",
            sa.Column("founder_number", sa.Integer(), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if "founder_number" in _columns(bind, "teammate_profiles"):
        op.drop_column("teammate_profiles", "founder_number")
