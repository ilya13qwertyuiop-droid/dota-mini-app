"""Replace TTL search model with permanent profile status.

Revision ID: 0012
Revises: 0011
Create Date: 2026-05-17

Меняем модель «поиск на 3 часа» (is_searching + search_expires_at) на
постоянный статус профиля.

Колонка status (nullable):
  ready_now        — Готов играть сейчас (верхний приоритет в ленте)
  looking_regular  — Ищу постоянных тиммейтов (средний)
  looking_casual   — Ищу, не срочно (низкий)
  hidden           — Не показывать меня (не в ленте)
  NULL             — статус ещё НЕ выбран → юзер увидит обязательный
                     экран выбора статуса в ленте, и его не видно другим

Почему nullable без server_default: новый профиль должен иметь status=NULL
чтобы сработал обязательный экран выбора. Если бы стоял default — все новые
автоматически попадали бы в ленту с дефолтным статусом, без осознанного
выбора.

Backfill существующих профилей:
  is_searching=true (и не истёкший)  → ready_now
  остальные                          → looking_regular
(staging-тестеры не проваливаются через gate — у них уже будет статус)

Идемпотентность через inspector (как 0009-0011).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _columns(bind, table: str) -> set[str]:
    insp = sa.inspect(bind)
    if table not in set(insp.get_table_names()):
        return set()
    return {c["name"] for c in insp.get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    cols = _columns(bind, "teammate_profiles")
    if not cols:
        return  # таблицы нет — нечего мигрировать

    # 1) Добавляем status (nullable, индекс).
    if "status" not in cols:
        op.add_column(
            "teammate_profiles",
            sa.Column("status", sa.String(20), nullable=True),
        )
        op.create_index(
            "ix_teammate_profiles_status", "teammate_profiles", ["status"]
        )

    # 2) Backfill из старой модели (только если старые колонки ещё есть).
    if "is_searching" in cols and "search_expires_at" in cols:
        # Активный непросроченный поиск → ready_now.
        op.execute(
            """
            UPDATE teammate_profiles
            SET status = 'ready_now'
            WHERE status IS NULL
              AND is_searching = TRUE
              AND search_expires_at IS NOT NULL
              AND search_expires_at > NOW()
            """
        )
        # Все остальные существующие профили → looking_regular (чтобы
        # staging-тестеры не упирались в обязательный gate).
        op.execute(
            """
            UPDATE teammate_profiles
            SET status = 'looking_regular'
            WHERE status IS NULL
            """
        )

    # 3) Удаляем старые колонки.
    cols_now = _columns(bind, "teammate_profiles")
    if "search_expires_at" in cols_now:
        op.drop_column("teammate_profiles", "search_expires_at")
    if "is_searching" in cols_now:
        # Индекс на is_searching (создавался в 0007) уйдёт вместе с колонкой
        # на PG автоматически; на SQLite batch не нужен для drop_column в
        # современном alembic.
        op.drop_column("teammate_profiles", "is_searching")


def downgrade() -> None:
    bind = op.get_bind()
    cols = _columns(bind, "teammate_profiles")
    if not cols:
        return

    # Возвращаем старые колонки (без точного backfill — это аварийный путь).
    if "is_searching" not in cols:
        op.add_column(
            "teammate_profiles",
            sa.Column(
                "is_searching", sa.Boolean(), nullable=False,
                server_default=sa.false(),
            ),
        )
    if "search_expires_at" not in cols:
        op.add_column(
            "teammate_profiles",
            sa.Column("search_expires_at", sa.DateTime(timezone=True), nullable=True),
        )
    # Грубый обратный backfill: кто в ленте (не hidden/NULL) → is_searching.
    op.execute(
        """
        UPDATE teammate_profiles
        SET is_searching = TRUE,
            search_expires_at = NOW() + INTERVAL '3 hours'
        WHERE status IN ('ready_now', 'looking_regular', 'looking_casual')
        """
    )
    if "status" in cols:
        op.drop_index("ix_teammate_profiles_status", table_name="teammate_profiles")
        op.drop_column("teammate_profiles", "status")
