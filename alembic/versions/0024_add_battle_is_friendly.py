"""«Битва драфтов»: флаг is_friendly — товарищеский матч по вызову друга.

Revision ID: 0024
Revises: 0023
Create Date: 2026-07-17

«Сыграть с другом»: приватная комната (status='waiting'), вход по deep-link
из шаринга. Товарищеские бои НЕ двигают рейтинг (win-trading через твинков)
и помечаются в истории. Идемпотентно (inspector), как 0016-0023.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0024"
down_revision: Union[str, None] = "0023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE = "draft_battles"
_COL = "is_friendly"


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
