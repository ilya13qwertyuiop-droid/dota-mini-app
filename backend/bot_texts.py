"""bot_texts.py — admin-editable message templates с двухуровневой моделью.

Архитектура «дефолт → DB override»:
  • Дефолты живут в DEFAULT_BOT_TEXTS (этот файл) — рабочая база. При пустой
    БД / ошибке миграции бот всё равно работает.
  • Кастомизации админа кладутся в таблицу bot_texts (см. модель BotText).
  • get_text(key) сначала смотрит DB-cache, потом fallback'ит на DEFAULT.

Кэш — простой in-memory dict с TTL 60 секунд. Не нужен Redis: тексты
читаются на каждый send, но 60s достаточно чтобы не дрюкать БД. Когда
админ ставит новое значение через set_text() — кэш-запись сразу
invalidate'ится в ЭТОМ процессе. Другие процессы (api.py, notifier.py
если bot.py редактирует) подтянут свежее значение в течение TTL.

Также модуль экспортирует entities_to_html — конвертер Telegram
message-entities в HTML с поддержкой UTF-16 offsets (без него любая
emoji за BMP «уезжает» в смещениях). Используется в admin-handler'е
чтобы конвертировать форматированное сообщение админа в HTML для save.
"""

from __future__ import annotations

import html
import logging
import time
from typing import Iterable, Optional

from sqlalchemy.exc import SQLAlchemyError

from backend.database import SessionLocal
from backend.models import BotText as DBBotText

logger = logging.getLogger(__name__)


# ─── DEFAULTS ──────────────────────────────────────────────────────────────
#
# Шаблоны с плейсхолдерами вида {name}, заменяются через str.format в момент
# отправки. parse_mode='HTML' предполагается на стороне sender'а — потому
# тут уже можно использовать <b>, <i>, <a href>, <tg-emoji>, etc.
#
# При изменении ключей здесь — обнови также EDITABLE_TEXTS ниже, иначе
# админ-список не покажет новый ключ.

DEFAULT_BOT_TEXTS: dict[str, str] = {
    # ── Welcome (/start), показывается каждому новому юзеру ──────────
    "welcome": (
        "👋 Привет! Я бот-помощник по Dota 2!\n\n"
        "Я помогу тебе найти идеального героя для твоего стиля игры.\n\n"
        "Нажми на кнопку ниже, чтобы начать опрос 👇"
    ),

    # ── Teammate push'и (отправляются из api.py / notifier.py) ───────

    # Новый запрос от X — приходит получателю в Telegram-чат с ботом.
    # Placeholders: {sender_name}
    "tm_push_new_request": (
        "👋 <b>{sender_name}</b> хочет играть с тобой.\n\n"
        "Открой раздел тиммейтов, чтобы посмотреть запрос."
    ),

    # Запрос принят — push отправителю.
    # Placeholders: {receiver_name}, {receiver_link}, {receiver_handle}
    "tm_push_accepted_to_sender": (
        "✅ <b>{receiver_name}</b> принял твой запрос.\n\n"
        "Напиши: {receiver_link}{receiver_handle}"
    ),

    # Запрос принят — push получателю (confirmation).
    # Placeholders: {sender_name}, {sender_link}, {sender_handle}
    "tm_push_accepted_to_receiver": (
        "✅ Ты принял запрос от <b>{sender_name}</b>.\n\n"
        "Напиши: {sender_link}{sender_handle}"
    ),

    # Напоминание оставить отзыв (задержка настраивается, см.
    # TM_REVIEW_DELAY_MINUTES). Текст нейтральный: «принял запрос» теперь
    # значит «законтачили», а не «сыграли» — для постоянки/не срочно игра
    # могла ещё не случиться. Placeholders: {name} — имя второго игрока.
    "tm_push_review_reminder": (
        "👋 Получилось поиграть с <b>{name}</b>? Оцени напарника — "
        "это помогает другим выбирать, с кем играть.\n\n"
        "Ещё не играли? Тогда позже — отзыв всегда можно оставить "
        "в разделе «Пати», на вкладке «История»."
    ),
}


# Реестр редактируемых ключей с описанием для админ-UI.
# (label, hint о доступных плейсхолдерах)
EDITABLE_TEXTS: dict[str, tuple[str, str]] = {
    "welcome": (
        "Приветствие /start",
        "Без плейсхолдеров.",
    ),
    "tm_push_new_request": (
        "Push: новый запрос на дуо",
        "Плейсхолдеры: {sender_name}",
    ),
    "tm_push_accepted_to_sender": (
        "Push: запрос принят (отправителю)",
        "Плейсхолдеры: {receiver_name}, {receiver_link}, {receiver_handle}",
    ),
    "tm_push_accepted_to_receiver": (
        "Push: запрос принят (получателю)",
        "Плейсхолдеры: {sender_name}, {sender_link}, {sender_handle}",
    ),
    "tm_push_review_reminder": (
        "Push: напоминание оставить отзыв",
        "Плейсхолдеры: {name} — имя второго игрока.",
    ),
}


# ─── CACHE ────────────────────────────────────────────────────────────────

# key → (value_from_db_or_None, fetched_at_unix). None означает «нет
# override'а в БД» — fallback на DEFAULT. Это позволяет кэшировать ОТСУТСТВИЕ
# записи (negative cache) тем же механизмом — иначе на каждый дефолт-текст
# полез бы SELECT.
_cache: dict[str, tuple[Optional[str], float]] = {}
_CACHE_TTL_SEC: float = 60.0


def _cache_get(key: str) -> Optional[Optional[str]]:
    """Вернуть закэшированное значение если свежее. Иначе None.

    None результат означает «cache miss / expired». Записанное None значение
    означает «в БД нет override'а» — это разные вещи, обе осмысленны.
    Возвращаемый тип: Optional[Optional[str]] = None (miss) | (None,) (db-miss)
    | (str,) (db-hit). Я разруливаю через двойную обёртку.
    """
    entry = _cache.get(key)
    if entry is None:
        return None
    value, fetched_at = entry
    if time.time() - fetched_at > _CACHE_TTL_SEC:
        return None
    # Возвращаем кортеж-обёртку чтобы различить «None в кэше» (= no override)
    # от «cache miss».
    return (value,)


def _cache_put(key: str, value: Optional[str]) -> None:
    _cache[key] = (value, time.time())


def _cache_invalidate(key: str) -> None:
    _cache.pop(key, None)


# ─── PUBLIC API ───────────────────────────────────────────────────────────

def get_text(key: str, **kwargs) -> str:
    """Возвращает финальный готовый-к-отправке текст для данного key.

    1. Смотрит в БД-cache (TTL 60s).
    2. На miss — лезет в БД, кладёт result в кэш (включая «нет такой записи»).
    3. Если в БД override'а нет — fallback на DEFAULT_BOT_TEXTS[key].
    4. Если в DEFAULT тоже нет — возвращает f'[{key}]' плейсхолдер
       (видимо в чате, явно сигнализирует проблему).
    5. Форматирует через str.format(**kwargs). Невалидный плейсхолдер
       возвращается as-is (не падаем).
    """
    # Шаг 1: попытка достать из кэша
    cached = _cache_get(key)
    if cached is None:
        # Cache miss — лезем в БД
        db_value: Optional[str] = None
        try:
            with SessionLocal() as session:
                row = (
                    session.query(DBBotText)
                    .filter(DBBotText.key == key)
                    .first()
                )
                db_value = row.value if row is not None else None
        except SQLAlchemyError as e:
            logger.warning("bot_texts: DB error reading key=%s: %s", key, e)
            # На ошибке БД не кэшируем — следующий вызов попробует ещё раз
        else:
            _cache_put(key, db_value)
        raw = db_value
    else:
        raw = cached[0]

    # Шаг 2: fallback на дефолт если в БД override'а нет
    if raw is None:
        raw = DEFAULT_BOT_TEXTS.get(key)
    if raw is None:
        # Шаг 3: ключа нет ни в БД ни в дефолтах — explicit-плейсхолдер,
        # сразу видим что-то не так в логах/чате
        logger.warning("bot_texts: unknown key requested: %s", key)
        return f"[{key}]"

    # Шаг 4: подставляем плейсхолдеры
    if kwargs:
        try:
            return raw.format(**kwargs)
        except (KeyError, IndexError, ValueError) as e:
            # Шаблон с placeholder'ом которого нет в kwargs — возвращаем
            # raw чтобы хотя бы что-то отправить, не падать целиком.
            logger.warning("bot_texts: format error for key=%s: %s", key, e)
            return raw
    return raw


def set_text(key: str, value: str, description: str = "") -> None:
    """Upsert override для текста. Атомарно invalidate'ит локальный кэш.

    Используется из admin-handler в bot.py после конвертации Telegram
    entities → HTML. value уже должен быть готовым HTML.
    """
    from datetime import datetime, timezone as _tz
    with SessionLocal() as session:
        row = session.query(DBBotText).filter(DBBotText.key == key).first()
        if row is None:
            row = DBBotText(
                key=key, value=value, description=description,
                updated_at=datetime.now(_tz.utc),
            )
            session.add(row)
        else:
            row.value = value
            if description:
                row.description = description
            row.updated_at = datetime.now(_tz.utc)
        session.commit()
    _cache_invalidate(key)


def delete_text(key: str) -> None:
    """Удаляет override (вернуться к DEFAULT). Идемпотентно."""
    with SessionLocal() as session:
        session.query(DBBotText).filter(DBBotText.key == key).delete()
        session.commit()
    _cache_invalidate(key)


def get_all_overrides() -> dict[str, str]:
    """Возвращает {key: value} ВСЕХ override'ов в БД. Для admin /list-команды.
    Не кэшируется — админская операция, дёргается редко."""
    try:
        with SessionLocal() as session:
            rows = session.query(DBBotText).all()
            return {r.key: r.value for r in rows}
    except SQLAlchemyError as e:
        logger.warning("bot_texts: DB error in get_all_overrides: %s", e)
        return {}


# ─── ENTITIES → HTML CONVERTER ────────────────────────────────────────────
#
# Когда админ присылает форматированное сообщение в Telegram, MessageEntity'и
# даются в UTF-16 code units, а не Python-символах. Emoji за BMP занимает
# 2 code unit'а — без правильной кодировки смещения сдвигаются. Поэтому
# работаем через utf-16-le байты.
#
# Поддерживаемые типы entity:
#   bold, italic, underline, strikethrough, spoiler, code, pre (с language),
#   text_link, custom_emoji, blockquote, expandable_blockquote.


_OPEN_TAG: dict[str, str] = {
    "bold":                  "<b>",
    "italic":                "<i>",
    "underline":             "<u>",
    "strikethrough":         "<s>",
    "spoiler":               "<tg-spoiler>",
    "code":                  "<code>",
    "blockquote":            "<blockquote>",
    "expandable_blockquote": "<blockquote expandable>",
}
_CLOSE_TAG: dict[str, str] = {
    "bold":                  "</b>",
    "italic":                "</i>",
    "underline":             "</u>",
    "strikethrough":         "</s>",
    "spoiler":               "</tg-spoiler>",
    "code":                  "</code>",
    "blockquote":            "</blockquote>",
    "expandable_blockquote": "</blockquote>",
}


def _utf16_units(s: str) -> bytes:
    """str → UTF-16 LE байты, по 2 байта на code unit."""
    return s.encode("utf-16-le")


def _from_utf16(b: bytes) -> str:
    return b.decode("utf-16-le")


def entities_to_html(text: str, entities: Optional[Iterable]) -> str:
    """Конвертирует Telegram message.text + message.entities в HTML.

    entities ожидается как iterable из объектов с атрибутами:
      type, offset, length, url, custom_emoji_id, language.

    Возвращает HTML-строку готовую к отправке с parse_mode='HTML'.
    Обычный текст экранируется через html.escape.
    """
    if not text:
        return ""
    if not entities:
        return html.escape(text, quote=False)

    # Работаем в UTF-16 единицах, потому что Telegram даёт offset/length в них.
    src = _utf16_units(text)

    # Строим список «событий» (позиция, открыть/закрыть, entity-данные).
    # Каждая entity = два события: на offset (open) и offset+length (close).
    events: list[tuple[int, int, dict]] = []  # (pos_units, kind, info)
    for idx, ent in enumerate(entities):
        ent_type = getattr(ent, "type", None)
        # aiogram возвращает enum-like; PTB строкой. Приводим к строке.
        if ent_type is not None and not isinstance(ent_type, str):
            ent_type = str(ent_type).split(".")[-1].lower()
        if ent_type is None:
            continue
        offset = int(getattr(ent, "offset", 0))
        length = int(getattr(ent, "length", 0))
        if length <= 0:
            continue
        info = {
            "type": ent_type,
            "offset": offset,
            "length": length,
            "url": getattr(ent, "url", None),
            "custom_emoji_id": getattr(ent, "custom_emoji_id", None),
            "language": getattr(ent, "language", None),
            "_idx": idx,  # tie-breaker для стабильной сортировки
        }
        # Open event приоритет 0, close — 1, чтобы при равных позициях
        # вначале закрылись «предыдущие» теги а потом открылись «новые».
        events.append((offset, 1, info))                # close-приоритет (на end)
        events.append((offset + length, 1, info))       # close
        events.append((offset, 0, info))                # open
    # Дубликаты event'ов выше — это просто опечатка; нормальная конструкция:
    events = []
    for idx, ent in enumerate(entities):
        ent_type = getattr(ent, "type", None)
        if ent_type is not None and not isinstance(ent_type, str):
            ent_type = str(ent_type).split(".")[-1].lower()
        if ent_type is None:
            continue
        offset = int(getattr(ent, "offset", 0))
        length = int(getattr(ent, "length", 0))
        if length <= 0:
            continue
        info = {
            "type": ent_type,
            "offset": offset,
            "length": length,
            "url": getattr(ent, "url", None),
            "custom_emoji_id": getattr(ent, "custom_emoji_id", None),
            "language": getattr(ent, "language", None),
            "_idx": idx,
        }
        events.append((offset, 0, info))                 # open
        events.append((offset + length, 1, info))        # close

    # Сортируем: по позиции; при равной — сначала close (1), потом open (0)…
    # нет, наоборот: при равной позиции МЫ хотим сначала ЗАКРЫТЬ tag который
    # тут заканчивается, потом ОТКРЫТЬ новый. Поэтому close (1) идёт ДО open
    # (0)? Нет, у нас 0=open, 1=close. Хотим close BEFORE open: значит close
    # должен сортироваться раньше. Меняем: open=1, close=0.
    # Перепишу проще: используем (pos, is_open) где close=0 < open=1.
    events_sorted: list[tuple[int, int, dict]] = []
    for pos, kind, info in events:
        # Перекодируем: 0 → 1 (open идёт ПОСЛЕ), 1 → 0 (close идёт ПЕРЕД)
        events_sorted.append((pos, 1 if kind == 0 else 0, info))
    events_sorted.sort(key=lambda e: (e[0], e[1], e[2]["_idx"]))

    # Идём по тексту, на каждом event'е выводим accumulated-фрагмент + тег.
    out_parts: list[str] = []
    cursor = 0
    # Стек открытых tag'ов (для правильной вложенности — если открыт <b>
    # а сейчас приходит open <i> то <i> должен оказаться ВНУТРИ; close
    # должен закрывать ровно тот тег который был открыт последним —
    # XML-style).
    # Для Telegram entity-пар это естественно работает потому что entity'и
    # не пересекаются «крест-накрест» (Telegram гарантирует proper nesting).

    open_stack: list[dict] = []

    def _flush_text(end_units: int) -> None:
        """Append экранированный текст от cursor до end_units."""
        nonlocal cursor
        if end_units > cursor:
            chunk = _from_utf16(src[cursor * 2: end_units * 2])
            out_parts.append(html.escape(chunk, quote=False))
            cursor = end_units

    for pos, sort_kind, info in events_sorted:
        # sort_kind=0 → close, =1 → open (из-за нашего перекодирования)
        _flush_text(pos)
        ent_type = info["type"]
        if sort_kind == 1:
            # OPEN
            if ent_type == "pre":
                lang = info.get("language") or ""
                if lang:
                    out_parts.append(
                        f'<pre><code class="language-{html.escape(lang, quote=True)}">'
                    )
                else:
                    out_parts.append("<pre>")
            elif ent_type == "text_link":
                url = info.get("url") or ""
                out_parts.append(f'<a href="{html.escape(url, quote=True)}">')
            elif ent_type == "custom_emoji":
                emoji_id = info.get("custom_emoji_id") or ""
                out_parts.append(
                    f'<tg-emoji emoji-id="{html.escape(str(emoji_id), quote=True)}">'
                )
            else:
                tag = _OPEN_TAG.get(ent_type)
                if tag:
                    out_parts.append(tag)
                else:
                    # Неподдерживаемая entity — игнорируем (текст останется без оформления)
                    open_stack.append({"type": "_skip"})
                    continue
            open_stack.append(info)
        else:
            # CLOSE
            if ent_type == "pre":
                lang = info.get("language") or ""
                out_parts.append("</code></pre>" if lang else "</pre>")
            elif ent_type == "text_link":
                out_parts.append("</a>")
            elif ent_type == "custom_emoji":
                out_parts.append("</tg-emoji>")
            else:
                tag = _CLOSE_TAG.get(ent_type)
                if tag:
                    out_parts.append(tag)
            # Снимаем со стека (best-effort — стек используется только для
            # отладки; ошибок порядка не лечим — полагаемся на корректность
            # entity'й от Telegram).
            if open_stack:
                open_stack.pop()

    # Дописываем остаток текста
    _flush_text(len(src) // 2)
    return "".join(out_parts)
