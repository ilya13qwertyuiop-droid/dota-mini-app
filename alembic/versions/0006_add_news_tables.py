"""Add news tables and notify_news flag.

Revision ID: 0006
Revises: 0005
Create Date: 2026-03-05

Changes:
  user_profiles.notify_news — Boolean, default FALSE.
    Toggled via /news bot command; users with TRUE receive broadcast messages.

  dota_news — Stores parsed RSS entries to avoid duplicate notifications.
    guid        TEXT PRIMARY KEY  — RSS <guid> field (unique per item)
    title       TEXT NOT NULL     — article headline
    link        TEXT NOT NULL     — URL to full article
    published_at TIMESTAMP NULL   — parsed from RSS <pubDate>
    notified_at  TIMESTAMP NULL   — set after broadcast is sent
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user_profiles",
        sa.Column(
            "notify_news",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    op.create_table(
        "dota_news",
        sa.Column("guid", sa.Text(), primary_key=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("link", sa.Text(), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notified_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("dota_news")
    op.drop_column("user_profiles", "notify_news")
