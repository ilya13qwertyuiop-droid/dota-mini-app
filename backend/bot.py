import os
import traceback
from pathlib import Path
import secrets
from datetime import datetime, timedelta

import httpx
from telegram import (
    Bot,
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import Application, CommandHandler, ContextTypes
from db import init_tokens_table, create_token_for_user, get_user_id_by_token, get_last_quiz_result


# -------- загрузка переменных из .env --------
def load_env():
    env_path = Path(__file__).with_name(".env")
    if not env_path.exists():
        return
    with env_path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


load_env()

BOT_TOKEN = os.environ.get("BOT_TOKEN")
MINI_APP_URL = os.environ.get("MINI_APP_URL")
CHECK_CHAT_ID = os.environ.get("CHECK_CHAT_ID")  # chat_id канала для проверки
API_BASE_URL = "https://dotaquiz.blog"

async def is_subscriber(bot: Bot, user_id: int) -> bool:
    """Проверяет подписку пользователя на канал CHECK_CHAT_ID.

    Использует нативный метод bot.get_chat_member вместо сырых HTTP-запросов.
    При любой ошибке Telegram API возвращает False и не падает.
    """
    if not CHECK_CHAT_ID:
        return False
    try:
        member = await bot.get_chat_member(chat_id=CHECK_CHAT_ID, user_id=user_id)
        status = member.status
        print(f"[is_subscriber] user={user_id} status={status}")
        return status in ("member", "administrator", "creator")
    except Exception as e:
        print(f"[is_subscriber] error for user {user_id}: {e}")
        return False


# -------- handlers --------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не найден. Проверь файл .env")
    if not MINI_APP_URL:
        raise RuntimeError("MINI_APP_URL не найден. Проверь файл .env")
    if not CHECK_CHAT_ID:
        raise RuntimeError("CHECK_CHAT_ID не найден. Проверь файл .env")

    user_id = update.effective_user.id
    print("DEBUG start called for user", user_id)

    # Сохраняем данные пользователя в backend для профиля
    try:
        user = update.effective_user

        photo_url = None
        try:
            photos = await context.bot.get_user_profile_photos(user.id, limit=1)
            if photos.total_count > 0:
                file_id = photos.photos[0][0].file_id
                file = await context.bot.get_file(file_id)
                photo_url = file.file_path
        except Exception as e:
            print("Failed to fetch user photo:", e)
            photo_url = None

        payload = {
            "token": None,  # заполним позже
            "first_name": user.first_name,
            "last_name": getattr(user, "last_name", None),
            "username": user.username,
            "photo_url": photo_url,  # ✅ БАГ-ФИХ: добавляем аватар
        }
    except Exception as e:
        print("Failed to build Telegram user payload:", e)
        payload = None

    subscribed = await is_subscriber(context.bot, user_id)

    if not subscribed:
        # Сообщение с просьбой подписаться
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("📢 Подписаться на канал", url="https://t.me/kasumi_tt")]]
        )
        await update.message.reply_text(
            "⛔ Чтобы пользоваться ботом, подпишись на канал создателя.\n\n"
            "После подписки нажми /start ещё раз — и появится кнопка для открытия мини‑приложения.",
            reply_markup=kb,
        )
        # Убираем старую клавиатуру с кнопкой мини-апа, если она была
        try:
            await update.message.reply_reply_markup(reply_markup=ReplyKeyboardRemove())
        except Exception as e:
            print("Failed to remove old keyboard:", e)
        return

    # Пользователь подписан – выдаём токен и прокидываем в URL мини‑апа
    token = create_token_for_user(user_id)
    # tgWebAppDebug=1 включает DevTools в Telegram Desktop: Ctrl+Shift+I внутри окна WebApp.
    # Убрать этот параметр перед релизом или вынести в env-флаг DEBUG_WEBAPP.
    mini_app_url_with_token = f"{MINI_APP_URL}?token={token}&tgWebAppDebug=1"

    # --- отправляем данные пользователя на backend ---
    if payload is not None:
        payload["token"] = token
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.post(f"{API_BASE_URL}/api/save_telegram_data", json=payload)
            print("SAVE_TG_DATA status:", r.status_code, "resp:", r.text)
        except Exception as e:
            print("Failed to call save_telegram_data:", e)
    # --- конец отправки данных ---

    keyboard = [
        [
            KeyboardButton(
                text="Найди своего героя",
                web_app=WebAppInfo(url=mini_app_url_with_token),
            )
        ]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        "👋 Привет! Я бот-помощник по Dota 2!\n\n"
        "Я помогу тебе найти идеального героя для твоего стиля игры.\n\n"
        "Нажми на кнопку ниже, чтобы начать опрос 👇",
        reply_markup=reply_markup,
    )


# -------- вспомогательные функции для разбора результатов квиза --------

# Человекочитаемые метки для поля extraPos ("pos1" … "pos5")
_EXTRA_POS_LABELS: dict[str, str] = {
    "pos1": "Pos 1 — Керри",
    "pos2": "Pos 2 — Мид",
    "pos3": "Pos 3 — Оффлейн",
    "pos4": "Pos 4 — Роумер",
    "pos5": "Pos 5 — Саппорт",
}


def _fmt_date(dt: datetime | None) -> str:
    """Форматирует datetime в строку ДД.ММ.ГГГГ; возвращает '?' при None."""
    if dt is None:
        return "?"
    try:
        return dt.strftime("%d.%m.%Y")
    except Exception:
        return str(dt)[:10]


def _parse_position_quiz(result: dict, updated_at: datetime | None) -> dict | None:
    """Извлекает данные о позиции из результата квиза (оба формата).

    Новый формат: result содержит ключ "position_quiz".
    Старый формат: result["type"] == "position_quiz".

    Возвращает нормализованный dict или None, если формат не распознан.
    """
    if "position_quiz" in result:
        # Новый формат
        pq = result["position_quiz"]
        return {
            "position":      pq.get("position", "?"),
            "positionIndex": pq.get("positionIndex"),
            "date":          pq.get("date") or _fmt_date(updated_at),
            "isPure":        bool(pq.get("isPure")),
            "extraPos":      pq.get("extraPos"),   # напр. "pos2", может быть None
        }
    if result.get("type") == "position_quiz":
        # Старый формат
        return {
            "position":      result.get("position", "?"),
            "positionIndex": result.get("positionIndex"),
            "date":          _fmt_date(updated_at),
            "isPure":        False,
            "extraPos":      None,
        }
    return None


def _parse_hero_quiz(result: dict, pos_index: int | None) -> list[dict]:
    """Извлекает список topHeroes из результата квиза (оба формата).

    Новый формат: result["hero_quiz_by_position"][str(pos_index)]["topHeroes"].
    Старый формат: result["hero_quiz"]["topHeroes"].

    Возвращает список hero-dict'ов (может быть пустым).
    """
    if "hero_quiz_by_position" in result:
        hqbp: dict = result["hero_quiz_by_position"]
        # Ищем запись по индексу позиции; если нет — берём первую доступную
        key = str(pos_index) if pos_index is not None else None
        entry = hqbp.get(key) if key is not None else None
        if entry is None and hqbp:
            entry = next(iter(hqbp.values()))
        if entry:
            return entry.get("topHeroes", [])
    elif "hero_quiz" in result:
        # Старый формат
        return result["hero_quiz"].get("topHeroes", [])
    return []


async def last_quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает последний сохранённый результат квиза по позициям."""
    user_id = update.effective_user.id

    if not await is_subscriber(context.bot, user_id):
        await update.message.reply_text(
            "Чтобы пользоваться ботом, подпишись на канал @kasumi_tt и потом вернись сюда.\n"
            "После подписки нажми /start или повтори команду."
        )
        return

    row = get_last_quiz_result(user_id)
    if row is None:
        await update.message.reply_text(
            "У тебя пока нет сохранённых результатов квиза. "
            "Пройди квиз в мини‑аппе, а потом попробуй снова."
        )
        return

    result_dict, updated_at = row
    try:
        pos = _parse_position_quiz(result_dict, updated_at)
        if pos is None:
            await update.message.reply_text(
                "Не удалось разобрать сохранённый результат квиза. "
                "Попробуй пройти квиз заново."
            )
            return

        lines = [
            "🎯 <b>Последний квиз по позициям</b>",
            f"Дата: <code>{pos['date']}</code>",
            f"Позиция: <b>{pos['position']}</b>",
        ]
        if pos.get("extraPos"):
            label = _EXTRA_POS_LABELS.get(pos["extraPos"], pos["extraPos"])
            lines.append(f"Доп. позиция: {label}")
        if pos.get("isPure"):
            lines.append("Тип: <b>чистая позиция</b>")

        await update.message.reply_text("\n".join(lines), parse_mode="HTML")

    except Exception:
        traceback.print_exc()
        await update.message.reply_text(
            "Произошла ошибка при чтении результатов. Попробуй позже."
        )


async def hero_quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает рекомендованных героев из последнего квиза по героям."""
    user_id = update.effective_user.id

    if not await is_subscriber(context.bot, user_id):
        await update.message.reply_text(
            "Чтобы пользоваться ботом, подпишись на канал @kasumi_tt и потом вернись сюда.\n"
            "После подписки нажми /start или повтори команду."
        )
        return

    row = get_last_quiz_result(user_id)
    if row is None:
        await update.message.reply_text(
            "У тебя пока нет сохранённых результатов квиза. "
            "Пройди квиз в мини‑аппе, а потом попробуй снова."
        )
        return

    result_dict, updated_at = row
    try:
        pos = _parse_position_quiz(result_dict, updated_at)
        pos_index = pos["positionIndex"] if pos else None
        pos_label = pos["position"] if pos else "?"

        heroes = _parse_hero_quiz(result_dict, pos_index)
        if not heroes:
            await update.message.reply_text(
                "Квиз по позиции найден, но героев ещё нет. "
                "Пройди квиз по героям в мини‑аппе."
            )
            return

        lines = [
            "🧙 <b>Рекомендованные герои</b>",
            f"Позиция: <b>{pos_label}</b>",
            "",
        ]
        for i, hero in enumerate(heroes[:5], start=1):
            name = hero.get("name", "?")
            pct = hero.get("matchPercent")
            if pct is not None:
                lines.append(f"{i}) {name} — совпадение {pct}%")
            else:
                lines.append(f"{i}) {name}")

        await update.message.reply_text("\n".join(lines), parse_mode="HTML")

    except Exception:
        traceback.print_exc()
        await update.message.reply_text(
            "Произошла ошибка при чтении результатов. Попробуй позже."
        )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎮 Как пользоваться ботом:\n\n"
        "1️⃣ Нажми кнопку '🔮 Найти своего героя'\n"
        "2️⃣ Ответь на несколько вопросов\n"
        "3️⃣ Получи рекомендацию по герою и позиции\n\n"
        "Команды:\n"
        "/start — Начать заново\n"
        "/last_quiz — Последний результат квиза по позициям\n"
        "/hero_quiz — Рекомендованные герои из последнего квиза\n"
        "/help — Показать это сообщение"
    )


def main():
    init_tokens_table()
    print("🤖 Бот запускается...")

    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не найден. Проверь файл .env")

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("last_quiz", last_quiz_command))
    application.add_handler(CommandHandler("hero_quiz", hero_quiz_command))

    print("✅ Бот запущен! Открой Telegram и напиши боту /start")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()


