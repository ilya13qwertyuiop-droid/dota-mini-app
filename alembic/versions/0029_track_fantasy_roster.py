"""Отмечать игроков актуального состава для Fantasy.

Revision ID: 0029
Revises: 0028
Create Date: 2026-07-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0029"
down_revision: Union[str, None] = "0028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "fantasy_players" not in set(inspector.get_table_names()):
        return
    existing = {
        column["name"]
        for column in inspector.get_columns("fantasy_players")
    }
    if "is_active" not in existing:
        op.add_column(
            "fantasy_players",
            sa.Column(
                "is_active",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "fantasy_players" not in set(inspector.get_table_names()):
        return
    existing = {
        column["name"]
        for column in inspector.get_columns("fantasy_players")
    }
    if "is_active" in existing:
        op.drop_column("fantasy_players", "is_active")
