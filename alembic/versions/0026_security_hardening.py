"""Add authoritative game sessions and shared abuse controls.

Revision ID: 0026
Revises: 0025
Create Date: 2026-07-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0026"
down_revision: Union[str, None] = "0025"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "draft_challenges",
        sa.Column("challenge_id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("user_profiles.user_id"), nullable=False),
        sa.Column("enemy", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_draft_challenges_user_id", "draft_challenges", ["user_id"])
    op.create_index("ix_draft_challenges_expires_at", "draft_challenges", ["expires_at"])
    op.create_index(
        "uq_draft_challenges_unconsumed_user",
        "draft_challenges",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("consumed_at IS NULL"),
        sqlite_where=sa.text("consumed_at IS NULL"),
    )

    op.create_table(
        "used_telegram_init_data",
        sa.Column("digest", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_used_telegram_init_data_user_id", "used_telegram_init_data", ["user_id"])
    op.create_index("ix_used_telegram_init_data_expires_at", "used_telegram_init_data", ["expires_at"])

    op.create_table(
        "api_rate_limit_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("scope", sa.String(length=64), nullable=False),
        sa.Column("subject", sa.String(length=128), nullable=False),
        sa.Column("occurred_at", sa.Float(), nullable=False),
    )
    op.create_index(
        "ix_api_rate_limit_scope_subject_ts",
        "api_rate_limit_events",
        ["scope", "subject", "occurred_at"],
    )
    op.create_index(
        "ix_api_rate_limit_occurred_at",
        "api_rate_limit_events",
        ["occurred_at"],
    )

    op.create_table(
        "minigame_runs",
        sa.Column("run_id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("user_profiles.user_id"), nullable=False),
        sa.Column("game", sa.String(length=16), nullable=False),
        sa.Column("metric", sa.String(length=16), nullable=False),
        sa.Column("reference_id", sa.Integer(), nullable=False),
        sa.Column("reference_value", sa.Float(), nullable=False),
        sa.Column("challenger_id", sa.Integer(), nullable=False),
        sa.Column("challenger_value", sa.Float(), nullable=False),
        sa.Column("round", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("streak", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("recent_hero_ids", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=12), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_minigame_runs_user_id", "minigame_runs", ["user_id"])
    op.create_index("ix_minigame_runs_expires_at", "minigame_runs", ["expires_at"])
    op.create_index("ix_minigame_runs_user_status", "minigame_runs", ["user_id", "status"])
    op.create_index(
        "uq_minigame_runs_active_user_game",
        "minigame_runs",
        ["user_id", "game"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
        sqlite_where=sa.text("status = 'active'"),
    )

    # Legacy scores were supplied by the browser and cannot be distinguished
    # from forged values. Remove the whole trust-tainted leaderboard.
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "user_profiles" in set(inspector.get_table_names()):
        if bind.dialect.name == "postgresql":
            settings_type = next(
                c["type"] for c in inspector.get_columns("user_profiles") if c["name"] == "settings"
            )
            expression = "settings::jsonb - 'minigame_best'"
            if not isinstance(settings_type, postgresql.JSONB):
                expression = f"({expression})::json"
            op.execute(sa.text(
                f"UPDATE user_profiles SET settings = {expression} "
                "WHERE settings::jsonb ? 'minigame_best'"
            ))
        elif bind.dialect.name == "sqlite":
            op.execute(sa.text(
                "UPDATE user_profiles SET settings = json_remove(settings, '$.minigame_best') "
                "WHERE json_type(settings, '$.minigame_best') IS NOT NULL"
            ))

    # Previous solo results used client-selected enemy drafts and were
    # optimizable by automation. Only new single-use server challenges are
    # eligible for history and ranking.
    if "draft_results" in set(inspector.get_table_names()):
        op.execute(sa.text("DELETE FROM draft_results"))


def downgrade() -> None:
    op.drop_index("uq_minigame_runs_active_user_game", table_name="minigame_runs")
    op.drop_index("ix_minigame_runs_user_status", table_name="minigame_runs")
    op.drop_index("ix_minigame_runs_expires_at", table_name="minigame_runs")
    op.drop_index("ix_minigame_runs_user_id", table_name="minigame_runs")
    op.drop_table("minigame_runs")
    op.drop_index("ix_api_rate_limit_occurred_at", table_name="api_rate_limit_events")
    op.drop_index("ix_api_rate_limit_scope_subject_ts", table_name="api_rate_limit_events")
    op.drop_table("api_rate_limit_events")
    op.drop_index("ix_used_telegram_init_data_expires_at", table_name="used_telegram_init_data")
    op.drop_index("ix_used_telegram_init_data_user_id", table_name="used_telegram_init_data")
    op.drop_table("used_telegram_init_data")
    op.drop_index("ix_draft_challenges_expires_at", table_name="draft_challenges")
    op.drop_index("ix_draft_challenges_user_id", table_name="draft_challenges")
    op.drop_index("uq_draft_challenges_unconsumed_user", table_name="draft_challenges")
    op.drop_table("draft_challenges")
