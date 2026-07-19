"""Remove legacy Telegram file URLs containing the bot token.

Revision ID: 0025
Revises: 0024
Create Date: 2026-07-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0025"
down_revision: Union[str, None] = "0024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    # Incident response: the compromised bot token could forge Telegram
    # initData and mint app sessions for arbitrary (including admin) user IDs.
    # Existing rows also contain raw bearer tokens; all must be invalidated.
    if "tokens" in tables:
        op.execute(sa.text("DELETE FROM tokens"))
    if "user_profiles" not in tables:
        return

    dialect = bind.dialect.name
    if dialect == "postgresql":
        settings_type = next(
            column["type"]
            for column in inspector.get_columns("user_profiles")
            if column["name"] == "settings"
        )
        expression = "settings::jsonb - 'photo_url'"
        if not isinstance(settings_type, postgresql.JSONB):
            expression = f"({expression})::json"
        op.execute(sa.text(
            f"UPDATE user_profiles SET settings = {expression} "
            "WHERE settings::jsonb ? 'photo_url'"
        ))
    elif dialect == "sqlite":
        op.execute(sa.text(
            "UPDATE user_profiles SET settings = json_remove(settings, '$.photo_url') "
            "WHERE json_type(settings, '$.photo_url') IS NOT NULL"
        ))


def downgrade() -> None:
    # Deleted credentials must never be reconstructed.
    pass
