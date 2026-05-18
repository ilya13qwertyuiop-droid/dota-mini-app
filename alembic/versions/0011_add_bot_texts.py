"""Add bot_texts table for admin-editable message templates.

Revision ID: 0011
Revises: 0010
Create Date: 2026-05-16

Adds:
  bot_texts — key/value таблица для текстов которые шлёт бот (push'и от
              миниапа + welcome). Двухуровневая модель: значение из БД
              имеет приоритет над DEFAULT_BOT_TEXTS в коде. Сброс к
              дефолту = DELETE FROM bot_texts WHERE key=...

Сделано в этом виде, чтобы:
  • можно было править тексты прямо из Telegram без редеплоя
  • кастомные эмодзи и форматирование Telegram сохранялись 1-в-1
    (entities_to_html в bot_texts.py)
  • дефолты в коде гарантировали работу пуст-БД (новый деплой, ошибка
    миграции, ручное удаление строки) — fallback всегда есть

Идемпотентность через inspector-check (как 0009/0010).
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _existing_tables(bind) -> set[str]:
    return set(sa.inspect(bind).get_table_names())


def upgrade() -> None:
    bind = op.get_bind()
    if "bot_texts" not in _existing_tables(bind):
        op.create_table(
            "bot_texts",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            # Стабильный идентификатор шаблона (например, "tm_push_new_request").
            # UNIQUE — на каждый key только одна override-запись.
            sa.Column("key", sa.String(64), nullable=False, unique=True),
            # HTML-текст готовый к отправке через parse_mode='HTML'. Содержит
            # плейсхолдеры формата {name}, заменяемые str.format в момент send.
            sa.Column("value", sa.Text(), nullable=False),
            # Человекочитаемое имя для админ-списка («Push о новом запросе»).
            sa.Column(
                "description", sa.String(256), nullable=False, server_default=""
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
        op.create_index("ix_bot_texts_key", "bot_texts", ["key"])


def downgrade() -> None:
    bind = op.get_bind()
    if "bot_texts" in _existing_tables(bind):
        op.drop_index("ix_bot_texts_key", table_name="bot_texts")
        op.drop_table("bot_texts")
