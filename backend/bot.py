import os
from pathlib import Path
import secrets
from datetime import datetime, timedelta

import httpx
from telegram import (
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup,
    WebAppInfo,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardRemove,
)
from telegram.ext import Application, CommandHandler, ContextTypes


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

print("[BOT DEBUG] BOT_TOKEN =", BOT_TOKEN)

# -------- простое хранилище токенов --------
TOKEN_STORE: dict[str, dict] = {}  # token -> {"user_id": int, "expires_at": datetime}


def create_token_for_user(user_id: int) -> str:
    token = secrets.token_urlsafe(16)
    TOKEN_STORE[token] = {
        "user_id": user_id,
        "expires_at": datetime.utcnow() + timedelta(hours=1),
    }
    return token


def get_user_id_by_token(token: str) -> int | None:
    data = TOKEN_STORE.get(token)
    if not data:
        return None
    if data["expires_at"] < datetime.utcnow():
        del TOKEN_STORE[token]
        return None
    return data["user_id"]


async def _is_subscribed(user_id: int) -> bool:
    if not BOT_TOKEN or not CHECK_CHAT_ID:
        return False

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember"
    params = {"chat_id": CHECK_CHAT_ID, "user_id": user_id}

    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url, params=params)

    if r.status_code != 200:
        print("CHECK_SUB ERROR", user_id, "status_code:", r.status_code, "raw:", r.text)
        return False

    data = r.json()
    status = (data.get("result") or {}).get("status")
    print("CHECK_SUB", user_id, "status:", status, "raw:", data)

    return status in {"member", "administrator", "creator"}


# -------- handlers --------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не найден. Проверь файл .env")
    if not MINI_APP_URL:
        raise RuntimeError("MINI_APP_URL не найден. Проверь файл .env")
    if not CHECK_CHAT_ID:
        raise RuntimeError("CHECK_CHAT_ID не найден. Проверь файл .env")

    user_id = update.effective_user.id
    subscribed = await _is_subscribed(user_id)

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
    mini_app_url_with_token = f"{MINI_APP_URL}?token={token}"

    keyboard = [
        [
            KeyboardButton(
                text="🔮 Найти своего героя",
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


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎮 Как пользоваться ботом:\n\n"
        "1️⃣ Нажми кнопку '🔮 Найти своего героя'\n"
        "2️⃣ Ответь на несколько вопросов\n"
        "3️⃣ Получи рекомендацию по герою и позиции\n\n"
        "Команды:\n"
        "/start - Начать заново\n"
        "/help - Показать это сообщение"
    )


def main():
    print("🤖 Бот запускается...")

    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не найден. Проверь файл .env")

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    print("[BOT DEBUG] starting polling...")

    print("✅ Бот запущен! Открой Telegram и напиши боту /start")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()


