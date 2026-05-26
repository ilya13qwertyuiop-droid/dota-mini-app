"""Add teammate-finder tables.

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-11

Adds:
  teammate_profiles  — per-user search profile (rank, hours, positions, modes,
                       mic/discord, mood, favourite heroes, free-text about,
                       active-search flag + expiry).
  teammate_requests  — pending/accepted/declined invites between users.
                       review_sent drives the 90-minute follow-up nudge
                       prompting both sides to leave a review.
  teammate_reviews   — post-game feedback containing the tags selected by the
                       reviewer (one row per review).
  teammate_tags      — per-user aggregate counters: how many times each tag
                       has been applied to the user.  Composite PK (user_id, tag).

Indexes:
  teammate_profiles  : is_searching, rank        — feed filtering
  teammate_requests  : from_user_id, to_user_id, status — inbox queries
  teammate_reviews   : to_user_id                — list reviews received
  teammate_tags      : user_id                   — explicit index even though
                                                   user_id is the leftmost PK
                                                   column (mirrors how
                                                   hero_matchups treats hero_b)
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # teammate_profiles
    # ------------------------------------------------------------------
    op.create_table(
        "teammate_profiles",
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("user_profiles.user_id"),
            primary_key=True,
        ),
        # Rank: Рекрут / Страж / Рыцарь / Герой / Легенда / Властелин / Божество / Титан
        sa.Column("rank", sa.String(32), nullable=True),
        sa.Column("hours", sa.Integer(), nullable=True),
        # Array of ints 1..5 (multi-select)
        sa.Column("positions", sa.JSON(), nullable=True),
        # Array of strings: ranked / normal / turbo
        sa.Column("game_modes", sa.JSON(), nullable=True),
        sa.Column(
            "microphone", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("discord", sa.Boolean(), nullable=False, server_default=sa.false()),
        # Mood: win / fun / stomp
        sa.Column("mood", sa.String(16), nullable=True),
        # Array of hero_id, capped at 3 in the app layer
        sa.Column("favorite_heroes", sa.JSON(), nullable=True),
        sa.Column("about", sa.Text(), nullable=True),
        sa.Column(
            "is_searching", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("search_expires_at", sa.DateTime(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_teammate_profiles_is_searching", "teammate_profiles", ["is_searching"]
    )
    op.create_index("ix_teammate_profiles_rank", "teammate_profiles", ["rank"])

    # ------------------------------------------------------------------
    # teammate_requests
    # ------------------------------------------------------------------
    op.create_table(
        "teammate_requests",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "from_user_id",
            sa.BigInteger(),
            sa.ForeignKey("user_profiles.user_id"),
            nullable=False,
        ),
        sa.Column(
            "to_user_id",
            sa.BigInteger(),
            sa.ForeignKey("user_profiles.user_id"),
            nullable=False,
        ),
        # status: pending / accepted / declined
        sa.Column(
            "status", sa.String(16), nullable=False, server_default="pending"
        ),
        # Set to True after the 90-minute follow-up reminder has been delivered
        sa.Column(
            "review_sent", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("accepted_at", sa.DateTime(), nullable=True),
    )
    op.create_index(
        "ix_teammate_requests_from_user_id", "teammate_requests", ["from_user_id"]
    )
    op.create_index(
        "ix_teammate_requests_to_user_id", "teammate_requests", ["to_user_id"]
    )
    op.create_index("ix_teammate_requests_status", "teammate_requests", ["status"])

    # ------------------------------------------------------------------
    # teammate_reviews
    # ------------------------------------------------------------------
    op.create_table(
        "teammate_reviews",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "from_user_id",
            sa.BigInteger(),
            sa.ForeignKey("user_profiles.user_id"),
            nullable=False,
        ),
        sa.Column(
            "to_user_id",
            sa.BigInteger(),
            sa.ForeignKey("user_profiles.user_id"),
            nullable=False,
        ),
        sa.Column(
            "request_id",
            sa.Integer(),
            sa.ForeignKey("teammate_requests.id"),
            nullable=False,
        ),
        # Array of tag strings selected by the reviewer
        sa.Column("tags", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_teammate_reviews_to_user_id", "teammate_reviews", ["to_user_id"]
    )

    # ------------------------------------------------------------------
    # teammate_tags  (per-user aggregate counters)
    # ------------------------------------------------------------------
    op.create_table(
        "teammate_tags",
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("user_profiles.user_id"),
            nullable=False,
        ),
        sa.Column("tag", sa.String(64), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="1"),
        # True for positive tags (Бустер, Душа компании, Командный, No tilted,
        # 1x9), False for negative tags (Токсик, Фидер, AFK, Фотограф,
        # Агент Габена).  Stored on each row so a single SELECT can compute
        # both positive and negative totals.
        sa.Column("is_positive", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("user_id", "tag"),
    )
    op.create_index("ix_teammate_tags_user_id", "teammate_tags", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_teammate_tags_user_id", table_name="teammate_tags")
    op.drop_table("teammate_tags")
    op.drop_index("ix_teammate_reviews_to_user_id", table_name="teammate_reviews")
    op.drop_table("teammate_reviews")
    op.drop_index("ix_teammate_requests_status", table_name="teammate_requests")
    op.drop_index(
        "ix_teammate_requests_to_user_id", table_name="teammate_requests"
    )
    op.drop_index(
        "ix_teammate_requests_from_user_id", table_name="teammate_requests"
    )
    op.drop_table("teammate_requests")
    op.drop_index("ix_teammate_profiles_rank", table_name="teammate_profiles")
    op.drop_index(
        "ix_teammate_profiles_is_searching", table_name="teammate_profiles"
    )
    op.drop_table("teammate_profiles")
