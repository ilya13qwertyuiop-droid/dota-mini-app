"""bot_admin_texts.py — admin-команды для редактирования bot_texts через Telegram.

Поток (PTB ConversationHandler):
  /admin_text <key>     → бот шлёт текущее значение и инструкцию
                          → ждёт ответ-сообщение с форматированием
                          → конвертит entities → HTML, валидирует
                          плейсхолдеры, save в БД, шлёт preview

Дополнительно (single-shot команды без conversation):
  /admin_texts          → список всех редактируемых ключей со статусом
  /admin_text_reset <k> → удалить override (вернуть дефолт)

Защита: admin-проверка по ADMIN_IDS (передаётся из bot.py при register).
"""

from __future__ import annotations

import html
import logging
import re
from typing import Iterable

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ConversationHandler, ContextTypes, MessageHandler,
    filters,
)

from backend.bot_texts import (
    DEFAULT_BOT_TEXTS,
    EDITABLE_TEXTS,
    delete_text,
    entities_to_html,
    get_all_overrides,
    set_text,
)

logger = logging.getLogger(__name__)


# Conversation state — ждём от админа новое содержимое для key, который
# сохраняется в context.user_data['admin_editing_key'].
WAITING_FOR_NEW_TEXT = 1


def _is_admin(user_id: int, admin_ids: frozenset[int]) -> bool:
    return user_id in admin_ids


def _placeholders(text: str) -> set[str]:
    """Извлекает {var}-плейсхолдеры из строки. Используется для валидации
    что админ не забыл required-плейсхолдеры из дефолта."""
    return set(re.findall(r"\{(\w+)\}", text))


async def _send_with_html_safe(
    update: Update, text: str, parse_mode: str | None = "HTML",
) -> None:
    """sendMessage с защитой от 400 при битом HTML. Если parse_mode='HTML'
    ломается (Telegram не парсит наши теги — например <ой>), повторяем без
    parse_mode чтобы хоть что-то отправить."""
    try:
        await update.message.reply_text(text, parse_mode=parse_mode)
    except Exception as e:
        logger.warning("admin_texts: parse_mode='%s' failed: %s. Retry plain.",
                       parse_mode, e)
        try:
            await update.message.reply_text(text)
        except Exception as e2:
            logger.warning("admin_texts: plain send also failed: %s", e2)


# ─── /admin_texts — список ─────────────────────────────────────────────────

def make_admin_texts_command(admin_ids: frozenset[int]):
    """Factory: возвращает handler-функцию, закрытую над admin_ids."""

    async def admin_texts_command(update: Update, _ctx: ContextTypes.DEFAULT_TYPE):
        if not _is_admin(update.effective_user.id, admin_ids):
            return
        overrides = get_all_overrides()
        lines = ["<b>Редактируемые тексты:</b>", ""]
        for key, (label, hint) in EDITABLE_TEXTS.items():
            status = "✏️" if key in overrides else "·"
            lines.append(f"{status} <code>{html.escape(key)}</code> — {html.escape(label)}")
        lines.append("")
        lines.append("Редактировать:  <code>/admin_text КЛЮЧ</code>")
        lines.append("Сбросить:       <code>/admin_text_reset КЛЮЧ</code>")
        await _send_with_html_safe(update, "\n".join(lines))

    return admin_texts_command


# ─── /admin_text <key> — entry point conversation ──────────────────────────

def make_admin_text_command(admin_ids: frozenset[int]):
    """Factory для /admin_text — entry point ConversationHandler'а."""

    async def admin_text_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
        if not _is_admin(update.effective_user.id, admin_ids):
            return ConversationHandler.END
        args = ctx.args or []
        if not args:
            await update.message.reply_text(
                "Использование: /admin_text КЛЮЧ\n\n"
                "Список ключей: /admin_texts"
            )
            return ConversationHandler.END

        key = args[0].strip()
        if key not in EDITABLE_TEXTS:
            await update.message.reply_text(
                f"Неизвестный ключ: {key}\n\nДоступные: /admin_texts"
            )
            return ConversationHandler.END

        label, hint = EDITABLE_TEXTS[key]
        default_value = DEFAULT_BOT_TEXTS.get(key, "")
        overrides = get_all_overrides()
        current_value = overrides.get(key, default_value)

        # Сохраняем выбранный ключ в user-scoped state для следующего шага.
        ctx.user_data["admin_editing_key"] = key

        # Инструкция (HTML — экранируем имена/подсказку чтобы не сломать парсер).
        intro = (
            f"<b>Редактирую:</b> {html.escape(label)}\n"
            f"<b>Ключ:</b> <code>{html.escape(key)}</code>\n"
            f"<b>Плейсхолдеры:</b> {html.escape(hint)}\n\n"
            "Отправь следующим сообщением новый текст. Используй обычное "
            "Telegram-форматирование (жирный, курсив, ссылки, кастомные эмодзи, "
            "цитаты — всё что умеет твой клиент).\n\n"
            "Чтобы отменить — /cancel"
        )
        await _send_with_html_safe(update, intro)

        # Шлём текущее значение СЫРЫМ (без parse_mode) — чтобы админ мог
        # скопировать и подправить. Это plain-text вью того что лежит в БД.
        await update.message.reply_text(
            f"📋 Текущий текст (raw):\n\n{current_value}",
            disable_web_page_preview=True,
        )
        return WAITING_FOR_NEW_TEXT

    return admin_text_command


# ─── State: ждём новый текст ──────────────────────────────────────────────

async def _receive_new_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    key = ctx.user_data.get("admin_editing_key")
    if not key:
        return ConversationHandler.END

    msg = update.message
    raw_text = msg.text or msg.caption or ""
    entities = msg.entities or msg.caption_entities or []

    # Конвертируем Telegram entities → HTML (нужно для bold/italic/custom_emoji
    # и правильных UTF-16 offsets).
    new_html = entities_to_html(raw_text, entities)

    # Валидация плейсхолдеров: если в DEFAULT есть {sender_name}, а в новом
    # тексте его нет — предупреждаем (но даём сохранить, юзер мог сознательно
    # убрать). Пока simple-warn, без confirmation-step.
    default_ph = _placeholders(DEFAULT_BOT_TEXTS.get(key, ""))
    new_ph = _placeholders(new_html)
    missing = default_ph - new_ph
    warning = ""
    if missing:
        warning = (
            "\n\n⚠️ <b>Внимание:</b> в новом тексте нет плейсхолдеров: "
            + ", ".join(f"<code>{html.escape(p)}</code>" for p in sorted(missing))
            + ". Push будет работать, но без подстановки этих значений."
        )

    # Сохраняем
    label = EDITABLE_TEXTS.get(key, ("", ""))[0]
    try:
        set_text(key, new_html, description=label)
    except Exception as e:
        logger.exception("admin_texts: set_text failed for %s", key)
        await update.message.reply_text(f"❌ Ошибка сохранения: {e}")
        return ConversationHandler.END

    # Конфирм + preview (рендер с parse_mode=HTML, чтобы увидеть финальный
    # вид). Для preview подставляем dummy-значения вместо плейсхолдеров —
    # иначе str.format упадёт KeyError'ом.
    dummy_kwargs = {p: f"⟨{p}⟩" for p in new_ph}
    try:
        preview = new_html.format(**dummy_kwargs)
    except Exception:
        preview = new_html

    await _send_with_html_safe(
        update,
        f"✅ Сохранено: <code>{html.escape(key)}</code>{warning}\n\n"
        f"<b>Preview:</b>\n\n{preview}",
    )

    ctx.user_data.pop("admin_editing_key", None)
    return ConversationHandler.END


async def _cancel_edit(update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> int:
    ctx.user_data.pop("admin_editing_key", None)
    await update.message.reply_text("Отменено.")
    return ConversationHandler.END


# ─── /admin_text_reset <key> — single-shot ────────────────────────────────

def make_admin_text_reset_command(admin_ids: frozenset[int]):

    async def admin_text_reset_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
        if not _is_admin(update.effective_user.id, admin_ids):
            return
        args = ctx.args or []
        if not args:
            await update.message.reply_text("Использование: /admin_text_reset КЛЮЧ")
            return
        key = args[0].strip()
        if key not in EDITABLE_TEXTS:
            await update.message.reply_text(f"Неизвестный ключ: {key}")
            return
        try:
            delete_text(key)
        except Exception as e:
            logger.exception("admin_texts: delete_text failed for %s", key)
            await update.message.reply_text(f"❌ Ошибка: {e}")
            return
        await update.message.reply_text(
            f"✅ Сброшен к дефолту: {key}"
        )

    return admin_text_reset_command


# ─── Регистрация handler'ов ───────────────────────────────────────────────

def register_admin_text_handlers(application: Application, admin_ids: frozenset[int]) -> None:
    """Регистрирует ConversationHandler + side-команды.

    Вызывается из bot.py main() ПОСЛЕ создания application но ПЕРЕД
    общим MessageHandler (filters.TEXT) чтобы не перехватывался catch-all'ом.
    """
    application.add_handler(CommandHandler("admin_texts", make_admin_texts_command(admin_ids)))
    application.add_handler(CommandHandler("admin_text_reset", make_admin_text_reset_command(admin_ids)))

    conv = ConversationHandler(
        entry_points=[CommandHandler("admin_text", make_admin_text_command(admin_ids))],
        states={
            WAITING_FOR_NEW_TEXT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, _receive_new_text),
            ],
        },
        fallbacks=[CommandHandler("cancel", _cancel_edit)],
        # per_user: один админ — одна conversation, не путаемся между чатами
        per_user=True,
        per_chat=False,
    )
    application.add_handler(conv)
