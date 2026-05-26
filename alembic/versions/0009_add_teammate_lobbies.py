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

ИДЕМПОТЕНТНОСТЬ. До этой версии миграция падала с
«relation ix_teammate_lobby_slots_user_id already exists». Две причины:

  1) Backend на staging поднимался с новыми models.py ДО `alembic upgrade head`.
     SQLAlchemy `Base.metadata.create_all()` при первом запросе создаёт ВСЕ
     таблицы, включая лобби-таблицы и их auto-индексы (из `index=True` на
     ORM-колонках). Когда потом запускали миграцию — она пыталась
     CREATE TABLE по уже существующему имени.

  2) В первой версии миграции `user_id` колонка в teammate_lobby_slots была
     объявлена с `index=True` И ниже стоял дублирующий
     `op.create_index("ix_teammate_lobby_slots_user_id", …)` с тем же
     дефолтным именем. На чистой БД это тоже падало бы — `index=True`
     создаёт авто-индекс с именем `ix_<table>_<column>`, явный create_index
     ругался бы duplicate.

Фикс — inspector-based existence-чеки перед каждой операцией + удаление
дубля. Composite-индекс `ix_teammate_lobbies_status_expires` остаётся
явным (auto-создание срабатывает только для single-column index=True).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_tables(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def _existing_indexes(bind, table: str) -> set[str]:
    """Имена индексов на таблице. Пустое множество, если таблицы нет."""
    insp = sa.inspect(bind)
    if table not in set(insp.get_table_names()):
        return set()
    # index["name"] может быть None для unnamed unique-constraint'ов;
    # фильтруем чтобы set не получил None.
    return {ix["name"] for ix in insp.get_indexes(table) if ix.get("name")}


def upgrade() -> None:
    bind = op.get_bind()

    # ── teammate_lobbies ──────────────────────────────────────────────
    if "teammate_lobbies" not in _existing_tables(bind):
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
            # JSON array of rank strings. NULL = открыто всем рангам.
            # Обязательно для mode='ranked' в API-логике, не на уровне БД.
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

    # Composite-индекс (status, expires_at) — НЕ автоматический из `index=True`,
    # нужен явный create_index. Полезен для expiry-воркера, который сканит
    # `WHERE status='open' AND expires_at <= now`.
    if "ix_teammate_lobbies_status_expires" not in _existing_indexes(bind, "teammate_lobbies"):
        op.create_index(
            "ix_teammate_lobbies_status_expires",
            "teammate_lobbies",
            ["status", "expires_at"],
        )

    # ── teammate_lobby_slots ──────────────────────────────────────────
    if "teammate_lobby_slots" not in _existing_tables(bind):
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

    # Note: индекс ix_teammate_lobby_slots_user_id создаётся АВТОМАТИЧЕСКИ
    # из `index=True` на user_id-колонке выше. Раньше тут стоял дублирующий
    # явный `op.create_index` с тем же именем — это вызывало
    # «relation already exists». Удалено.


def downgrade() -> None:
    bind = op.get_bind()

    # Drop в обратном порядке. drop_table каскадно удаляет связанные индексы.
    if "teammate_lobby_slots" in _existing_tables(bind):
        op.drop_table("teammate_lobby_slots")

    # Composite-индекс должен исчезнуть вместе с drop_table, но на всякий
    # случай (батч-режим SQLite, edge-cases) дроп явно если ещё остался.
    if "ix_teammate_lobbies_status_expires" in _existing_indexes(bind, "teammate_lobbies"):
        op.drop_index(
            "ix_teammate_lobbies_status_expires",
            table_name="teammate_lobbies",
        )

    if "teammate_lobbies" in _existing_tables(bind):
        op.drop_table("teammate_lobbies")
