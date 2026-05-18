"""Add last_active_at column to teammate_profiles.

Revision ID: 0010
Revises: 0009
Create Date: 2026-05-15

Adds:
  teammate_profiles.last_active_at — TIMESTAMPTZ, NULL. Обновляется на каждом
                                     authenticated teammate-endpoint'е (см.
                                     _tm_bump_last_active в api.py).

Семантика: «когда юзер последний раз делал что-то в miniapp». Backgrounded
вкладка / locked phone — таймеры pause'ятся через Page Visibility API, так
что значение реально отражает «открыт ли миниап у юзера перед лицом», а не
«запущен ли где-то в фоне».

Используется во фронте для отображения «🟢 в сети» / «был 5 мин назад» в
meta-строке player-card'ов в ленте «Дуо».

Идемпотентность через inspector-check (как 0009) — на случай если колонка
уже существует от прошлых ручных правок или create_all.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_columns(bind, table: str) -> set[str]:
    insp = sa.inspect(bind)
    if table not in set(insp.get_table_names()):
        return set()
    return {col["name"] for col in insp.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    if "last_active_at" not in _existing_columns(bind, "teammate_profiles"):
        op.add_column(
            "teammate_profiles",
            sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    if "last_active_at" in _existing_columns(bind, "teammate_profiles"):
        op.drop_column("teammate_profiles", "last_active_at")
