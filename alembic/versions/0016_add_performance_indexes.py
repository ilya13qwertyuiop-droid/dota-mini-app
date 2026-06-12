"""Add performance indexes — analytics_events, match_players, matches, tokens.

Revision ID: 0016
Revises: 0015
Create Date: 2026-06-12

Индексы по итогам аудита производительности:

  ix_analytics_events_created_at_user_id — (created_at, user_id).
      /analytics (get_analytics_overview) гоняет ~50 запросов с фильтром по
      created_at (DAU по дням + retention-cohorts); таблица растёт на каждое
      открытие страницы и без индекса каждый запрос — full-scan.

  ix_match_players_hero_id_match_id — (hero_id, match_id).
      get_hero_core_items (6 UNION-сканов по hero_id на героя, builds_updater
      гоняет для ~125 героев) и strict-режим get_hero_matchup_rows /
      get_hero_synergy_rows фильтруют по hero_id; индексирован был только
      match_id. При 300k матчей это ~3M строк full-scan.

  ix_matches_start_time — (start_time).
      get_old_match_ids / get_oldest_match_ids (cleanup), get_latest_match_patch
      (ORDER BY start_time DESC LIMIT 1 на каждый пересбор /api/meta) и
      fallback пула мини-игры.

  ix_tokens_expires_at — (expires_at).
      Под периодическую чистку протухших токенов (cleanup_expired_tokens в
      db.py): DELETE ... WHERE expires_at < now() без индекса — full-scan
      постоянно растущей таблицы.

Имена индексов совпадают с объявленными в models.py (__table_args__), чтобы
не задвоиться с create_all на свежих БД — та же схема, что у 0015.

Часть таблиц (analytics_events, tokens) создаётся не Alembic'ом, а create_all
при старте приложения. На БД, где приложение ещё не стартовало, таких таблиц
нет — тогда индекс пропускаем: create_all создаст таблицу сразу с индексом
из модели.

Идемпотентность через inspector (как 0009-0015).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0016"
down_revision: Union[str, None] = "0015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (index_name, table, [columns])
_INDEXES: list[tuple[str, str, list[str]]] = [
    ("ix_analytics_events_created_at_user_id", "analytics_events", ["created_at", "user_id"]),
    ("ix_match_players_hero_id_match_id",      "match_players",    ["hero_id", "match_id"]),
    ("ix_matches_start_time",                  "matches",          ["start_time"]),
    ("ix_tokens_expires_at",                   "tokens",           ["expires_at"]),
]


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    tables = set(insp.get_table_names())
    for index, table, columns in _INDEXES:
        if table not in tables:
            # Таблицу (вместе с индексом из модели) создаст create_all
            # при первом старте приложения.
            continue
        if index not in {ix["name"] for ix in insp.get_indexes(table)}:
            op.create_index(index, table, columns)


def downgrade() -> None:
    insp = sa.inspect(op.get_bind())
    tables = set(insp.get_table_names())
    for index, table, _columns in _INDEXES:
        if table in tables and index in {ix["name"] for ix in insp.get_indexes(table)}:
            op.drop_index(index, table_name=table)
