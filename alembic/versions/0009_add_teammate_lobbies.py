"""Add teammate-lobby tables (party-finder v1).

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-13

Adds tables that power the «Лобби» feature — instant-only host-led groups
of 3-5 players. Design brief: instant search (no scheduling), open-join
(no host approval), max 1 active membership per user, TTL 30 minutes.

  teammate_lobbies          — лобби (host, party_size, mode, rank_filter,
                              needed_positions, status, expires_at).
  teammate_lobby_slots      — слот = position. PK (lobby_id, position).
                              user_id NULL = пустой слот. Один row на каждую
                              позицию (host'а + needed_positions). При создании
                              лобби сразу создаются N rows: 1 заполненный
                              host'ом, остальные пустые.

Status lifecycle:
  open      — собирается, может принимать join'ы
  filled    — все слоты заняты, push разослан, лобби «отплыло»
  disbanded — host явно распустил
  expired   — TTL прошёл, лобби не собралось

Все datetime'ы — TIMESTAMPTZ с момента 0008 (см. её комментарий).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "teammate_lobbies",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "host_id",
            sa.BigInteger(),
            sa.ForeignKey("user_profiles.user_id"),
            nullable=False,
            index=True,
        ),
        # 3 / 4 / 5; в коде валидируется по mode (ranked → 3 or 5).
        sa.Column("party_size", sa.Integer(), nullable=False),
        # ranked / normal / turbo
        sa.Column("mode", sa.String(16), nullable=False),
        # JSON array of rank strings (например ["Легенда","Властелин","Божество"]).
        # NULL = открыто для всех рангов. Обязательно для mode='ranked' в API-логике.
        sa.Column("rank_filter", sa.JSON(), nullable=True),
        # JSON array of ints (1..5) — нужные позиции, КРОМЕ host'а.
        # len(needed_positions) == party_size - 1.
        sa.Column("needed_positions", sa.JSON(), nullable=False),
        # 1..5 — позиция host'а; в needed_positions её НЕТ.
        sa.Column("host_position", sa.Integer(), nullable=False),
        # open / filled / disbanded / expired
        sa.Column(
            "status",
            sa.String(16),
            nullable=False,
            server_default="open",
            index=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        # Когда последний слот заполнился (или NULL если ещё не filled).
        sa.Column("filled_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_teammate_lobbies_status_expires",
        "teammate_lobbies",
        ["status", "expires_at"],
    )

    op.create_table(
        "teammate_lobby_slots",
        sa.Column(
            "lobby_id",
            sa.Integer(),
            sa.ForeignKey("teammate_lobbies.id"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        # NULL = пустой слот; non-NULL = занятый user'ом.
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("user_profiles.user_id"),
            nullable=True,
            index=True,
        ),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("lobby_id", "position"),
    )
    # Индекс на user_id уже даётся декларацией index=True выше, но явно
    # называем его, чтобы downgrade умел его drop'нуть по имени.
    op.create_index(
        "ix_teammate_lobby_slots_user_id",
        "teammate_lobby_slots",
        ["user_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_teammate_lobby_slots_user_id", table_name="teammate_lobby_slots")
    op.drop_table("teammate_lobby_slots")
    op.drop_index("ix_teammate_lobbies_status_expires", table_name="teammate_lobbies")
    op.drop_table("teammate_lobbies")
