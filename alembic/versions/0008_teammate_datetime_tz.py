"""Make all teammate-module datetime columns timezone-aware.

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-13

КОРЕНЬ БАГА. До этой миграции 6 datetime-колонок были `DateTime` без TZ:

  teammate_profiles.search_expires_at
  teammate_profiles.created_at
  teammate_profiles.updated_at
  teammate_requests.created_at
  teammate_requests.accepted_at
  teammate_reviews.created_at

На PostgreSQL с session_tz ≠ UTC это давало silent-corruption:

  • Когда Python пишет `datetime.now(timezone.utc)` (tz-aware) в naive-колонку,
    psycopg2 конвертирует tz-aware → session_tz → strip tzinfo. В БД оседает
    wall-clock-local-time без какой-либо tz-метки. 5 колонок из 6 затронуты
    (всё кроме search_expires_at — он специально писался naive-UTC).
  • Когда .isoformat() сериализует naive-значение, фронт получает строку без
    TZ-маркера. JS парсит её как локальное время — для МСК-юзера сдвиг на -3ч.
    Это давало UI-баг с поиском: profile показывал «Искать пати», но в БД
    is_searching=True → юзер ВИДЕЛ в чужих лентах.

Фикс — конвертация в `TIMESTAMP WITH TIME ZONE` (timestamptz) + согласование
существующих значений:

  • search_expires_at: писалось naive-UTC → USING ... AT TIME ZONE 'UTC'
  • остальные 5: писались как naive-session-tz (через psycopg2 implicit) →
    USING ... AT TIME ZONE current_setting('TIMEZONE')

Caveat: если PG session_tz менялся между запусками сервера, существующие
значения 5 колонок могут оказаться в смешанных tz. На практике session_tz
обычно стабилен на протяжении деплоя — миграция корректна для типичных
сценариев.

На SQLite (dev-окружение) `ALTER COLUMN ... TYPE ... USING ...` не поддерживается.
Используем `op.batch_alter_table`, который пересоздаёт таблицу через
copy-rename. Значения уже хранятся как ISO-строки — SQLAlchemy после миграции
будет интерпретировать их с учётом timezone=True (для строк без TZ-маркера
вернёт naive datetime — приложение обязано трактовать их как UTC; такие
значения остаются только от dev-данных, и достаточно их перезаписать,
зайдя в раздел «Тиммейты» и нажав «Сохранить профиль»).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Колонка → как трактовать существующее naive-значение перед конвертацией.
# Только эта колонка писалась чистым UTC через datetime.utcnow().
_UTC_COLUMNS = {
    ("teammate_profiles", "search_expires_at"),
}

# Остальные колонки писались tz-aware через datetime.now(timezone.utc),
# psycopg2 их конвертировал в session_tz перед записью в naive-колонку.
# Значит существующие значения — это wall-clock в session_tz.
_SESSION_TZ_COLUMNS = [
    ("teammate_profiles", "created_at"),
    ("teammate_profiles", "updated_at"),
    ("teammate_requests", "created_at"),
    ("teammate_requests", "accepted_at"),
    ("teammate_reviews",  "created_at"),
]


def _pg_alter_to_tz(table: str, column: str, source_tz_expr: str) -> None:
    """ALTER COLUMN ... TYPE timestamptz USING ... AT TIME ZONE <expr>."""
    op.execute(
        f"ALTER TABLE {table} "
        f"ALTER COLUMN {column} TYPE TIMESTAMP WITH TIME ZONE "
        f"USING {column} AT TIME ZONE {source_tz_expr}"
    )


def _pg_alter_to_naive(table: str, column: str) -> None:
    """Обратная конвертация: timestamptz → naive, при этом значение конвертируется
    в UTC и tz-метка отбрасывается. Для consistency с pre-migration состоянием."""
    op.execute(
        f"ALTER TABLE {table} "
        f"ALTER COLUMN {column} TYPE TIMESTAMP "
        f"USING {column} AT TIME ZONE 'UTC'"
    )


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        # UTC-колонки — трактуем существующее naive как UTC.
        for table, column in _UTC_COLUMNS:
            _pg_alter_to_tz(table, column, "'UTC'")
        # Session-tz колонки — трактуем существующее naive как локальное
        # время сессии (то, что было применено psycopg2 при INSERT-е).
        for table, column in _SESSION_TZ_COLUMNS:
            _pg_alter_to_tz(table, column, "current_setting('TIMEZONE')")
    else:
        # SQLite (или другой backend без native ALTER TYPE): через batch_alter_table.
        # ISO-строки в БД остаются как есть; интерпретация ложится на код приложения.
        all_cols_by_table: dict[str, list[str]] = {}
        for table, column in list(_UTC_COLUMNS) + _SESSION_TZ_COLUMNS:
            all_cols_by_table.setdefault(table, []).append(column)
        for table, columns in all_cols_by_table.items():
            with op.batch_alter_table(table) as batch_op:
                for column in columns:
                    batch_op.alter_column(
                        column,
                        existing_type=sa.DateTime(),
                        type_=sa.DateTime(timezone=True),
                        existing_nullable=None,  # сохранить текущее nullable
                    )


def downgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "postgresql":
        for table, column in list(_UTC_COLUMNS) + _SESSION_TZ_COLUMNS:
            _pg_alter_to_naive(table, column)
    else:
        all_cols_by_table: dict[str, list[str]] = {}
        for table, column in list(_UTC_COLUMNS) + _SESSION_TZ_COLUMNS:
            all_cols_by_table.setdefault(table, []).append(column)
        for table, columns in all_cols_by_table.items():
            with op.batch_alter_table(table) as batch_op:
                for column in columns:
                    batch_op.alter_column(
                        column,
                        existing_type=sa.DateTime(timezone=True),
                        type_=sa.DateTime(),
                        existing_nullable=None,
                    )
