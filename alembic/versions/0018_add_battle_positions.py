"""«Битва драфтов»: стадия расстановки позиций — host/guest_positions.

Revision ID: 0018
Revises: 0017
Create Date: 2026-06-12

Двухстадийный драфт: после последнего пика battle переходит в status
'assigning' — оба игрока за общий таймер приватно раскладывают своих героев
по позициям 1-5; затем финализация с позиционным штрафом. Раскладки хранятся
JSON-колонками в draft_battles. Идемпотентно (inspector), как 0016-0017.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0018"
down_revision: Union[str, None] = "0017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "draft_battles"
_COLS = ("host_positions", "guest_positions")


def _existing_columns(bind) -> set[str]:
    insp = sa.inspect(bind)
    if _TABLE not in set(insp.get_table_names()):
        return set(_COLS)   # таблицы нет — её создаст create_all уже с колонками
    return {c["name"] for c in insp.get_columns(_TABLE)}


def upgrade() -> None:
    existing = _existing_columns(op.get_bind())
    for col in _COLS:
        if col not in existing:
            op.add_column(_TABLE, sa.Column(col, sa.JSON, nullable=True))


def downgrade() -> None:
    existing = _existing_columns(op.get_bind())
    for col in _COLS:
        if col in existing:
            op.drop_column(_TABLE, col)
