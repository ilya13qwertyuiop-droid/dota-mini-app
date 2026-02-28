"""Add created_at column to user_profiles table.

Revision ID: 0005
Revises: 0004
Create Date: 2026-02-28

Adds:
  user_profiles.created_at — DateTime, nullable.
    Populated automatically (Python-side default) for all new profiles.
    Existing rows keep NULL — they predate this column.

Used by the /admin_users bot command to count new registrations per day.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_profiles",
        sa.Column("created_at", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_profiles", "created_at")
