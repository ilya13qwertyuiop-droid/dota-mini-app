import asyncio
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Замени на свой токен от BotFather
BOT_TOKEN = "REMOVED_REVOKED_TELEGRAM_BOT_TOKEN"

# Временный URL для Mini App (пока заглушка, скоро заменим на настоящий)
MINI_APP_URL = "https://ilya13qwertyuiop-droid.github.io/dota-mini-app/"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отвечает на команду /start и показывает кнопку"""
    
    # Создаём кнопку с Mini App
    keyboard = [
        [KeyboardButton(
            text="🔮 Найти своего героя",
            web_app=WebAppInfo(url=MINI_APP_URL)
        )]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "👋 Привет! Я бот-помощник по Dota 2!\n\n"
        "Я помогу тебе найти идеального героя для твоего стиля игры.\n\n"
        "Нажми на кнопку ниже, чтобы начать опрос 👇",
        reply_markup=reply_markup
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отвечает на команду /help"""
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
    """Запуск бота"""
    print("🤖 Бот запускается...")
    
    # Создаём приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрируем команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    print("✅ Бот запущен! Открой Telegram и напиши боту /start")
    print("Для остановки нажми Ctrl+C")
    
    # Запускаем бота
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
