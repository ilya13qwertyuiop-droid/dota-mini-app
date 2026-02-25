import asyncio
import os
import re
import traceback
from io import BytesIO
from pathlib import Path
import secrets
from datetime import datetime, timedelta

try:
    from PIL import Image, ImageDraw, ImageFont
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

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
# Базовый URL статики с иконками героев.
# Подставь реальный путь: картинка должна лежать по адресу
#   <HERO_IMAGE_BASE_URL>/<hero_name_to_filename(name)>
# Пример: "https://dotaquiz.blog/hero-images/"
# Пустая строка → иконки не загружаются, рисуются серые placeholder'ы.
HERO_IMAGE_BASE_URL: str = os.environ.get("HERO_IMAGE_BASE_URL", "")

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


# -------- генерация карточки для /hero_quiz --------

def _load_font(size: int, bold: bool = False):
    """Пытается загрузить TTF-шрифт нужного размера; fallback — встроенный PIL."""
    candidates = (
        [
            "C:/Windows/Fonts/arialbd.ttf",
            "C:/Windows/Fonts/verdanab.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        ]
        if bold
        else [
            "C:/Windows/Fonts/arial.ttf",
            "C:/Windows/Fonts/verdana.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
    )
    for path in candidates:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    # Pillow ≥ 10 поддерживает size=; старые версии — нет
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def hero_name_to_filename(name: str) -> str:
    """Преобразует имя героя в имя PNG-файла (те же правила, что в hero-images.js).

    "Templar Assassin" → "templar_assassin.png"
    "Nature's Prophet" → "natures_prophet.png"
    "Anti-Mage"        → "anti-mage.png"
    """
    slug = name.strip().lower()
    slug = re.sub(r"['\u2019]", "", slug)       # убираем апострофы
    slug = re.sub(r"\s+", "_", slug)            # пробелы → _
    slug = re.sub(r"[^a-z0-9_\-]", "", slug)   # только безопасные символы
    return slug + ".png"


async def _fetch_hero_icons(heroes: list[dict]) -> list:
    """Параллельно скачивает иконки для каждого героя из HERO_IMAGE_BASE_URL.

    Возвращает list[PIL.Image | None] — None там, где загрузка не удалась.
    Любые сетевые/парсинговые ошибки подавляются; иконка просто пропускается.
    """
    if not _PIL_OK or not HERO_IMAGE_BASE_URL:
        return [None] * len(heroes)

    async def _one(client: httpx.AsyncClient, name: str):
        try:
            url = HERO_IMAGE_BASE_URL.rstrip("/") + "/" + hero_name_to_filename(name)
            resp = await client.get(url, follow_redirects=True)
            if resp.status_code == 200:
                return Image.open(BytesIO(resp.content)).convert("RGBA")
        except Exception as e:
            print(f"[hero icon] fetch failed for '{name}': {e}")
        return None

    async with httpx.AsyncClient(timeout=3.0) as client:
        results = await asyncio.gather(
            *[_one(client, h.get("name", "")) for h in heroes]
        )
    return list(results)


def render_hero_quiz_card(
    position_name: str,
    heroes: list[dict],
    icons: list | None = None,
) -> BytesIO:
    """Рисует карточку с топ-героями и возвращает PNG-изображение в памяти.

    position_name — строка вроде "Pos 1 — Керри"
    heroes        — list[{"name": str, "matchPercent": int|None}]
    icons         — list[PIL.Image | None], по одной на каждый элемент heroes
                    (None → серый placeholder; если не передано — все None)
    """
    n  = min(len(heroes), 5)
    MX = 44           # горизонтальный отступ

    HEADER_H = 138    # высота блока заголовка
    ROW_H    = 108    # высота одной строки героя
    BOTTOM   = 32     # нижний отступ

    W = 800
    H = HEADER_H + n * ROW_H + BOTTOM

    # ── палитра ──────────────────────────────────────────────────────────────
    C_BG_TOP   = (14,  20,  34)    # верх градиента
    C_BG_BOT   = (22,  30,  50)    # низ градиента
    C_GOLD     = (200, 169, 110)   # золото (акцент)
    C_WHITE    = (255, 255, 255)
    C_ROW_EVEN = (28,  36,  58)    # фон чётных строк
    C_ROW_ODD  = (22,  30,  48)    # фон нечётных строк
    C_BAR_BG   = (48,  58,  82)    # пустая часть полоски
    C_ICON_BG  = (36,  46,  70)    # placeholder иконки
    C_PCT      = (220, 195, 145)   # цвет текста процента

    img  = Image.new("RGB", (W, H), C_BG_TOP)
    draw = ImageDraw.Draw(img)

    # ── градиент фона (построчно) ─────────────────────────────────────────────
    for sy in range(H):
        t = sy / H
        r = int(C_BG_TOP[0] + (C_BG_BOT[0] - C_BG_TOP[0]) * t)
        g = int(C_BG_TOP[1] + (C_BG_BOT[1] - C_BG_TOP[1]) * t)
        b = int(C_BG_TOP[2] + (C_BG_BOT[2] - C_BG_TOP[2]) * t)
        draw.line([(0, sy), (W, sy)], fill=(r, g, b))

    # вертикальная золотая полоса слева (4 px)
    draw.rectangle([0, 0, 3, H], fill=C_GOLD)

    # ── шрифты ───────────────────────────────────────────────────────────────
    f_title = _load_font(34, bold=True)
    f_pos   = _load_font(20)
    f_hero  = _load_font(24, bold=True)
    f_pct   = _load_font(20)

    # ── заголовок ────────────────────────────────────────────────────────────
    draw.text((MX, 36), "Рекомендованные герои", font=f_title, fill=C_WHITE)
    draw.text((MX, 86), f"Позиция: {position_name}", font=f_pos,  fill=C_GOLD)
    draw.line([(MX, 120), (W - MX, 120)], fill=C_GOLD, width=1)

    # ── строки героев ─────────────────────────────────────────────────────────
    ICON_SIZE = 72
    ICON_X    = MX + 12                       # x левого края иконки
    TEXT_X    = ICON_X + ICON_SIZE + 14       # x начала текста/полоски
    BAR_END   = W - MX - 68                   # x правого края полоски
    BAR_W_MAX = BAR_END - TEXT_X              # максимальная ширина полоски
    BAR_H     = 10
    PCT_X     = BAR_END + 8                   # x текста процента

    _icons = list(icons or []) + [None] * n   # гарантируем длину ≥ n

    for i in range(n):
        hero     = heroes[i]
        icon_img = _icons[i]
        name     = hero.get("name", "?")
        pct      = hero.get("matchPercent")

        row_y = HEADER_H + i * ROW_H

        # фон строки (чередующийся)
        draw.rectangle(
            [MX, row_y + 4, W - MX, row_y + ROW_H - 4],
            fill=C_ROW_EVEN if i % 2 == 0 else C_ROW_ODD,
        )
        # тонкий золотой левый борт строки
        draw.rectangle([MX, row_y + 4, MX + 3, row_y + ROW_H - 4], fill=C_GOLD)

        # ── иконка ───────────────────────────────────────────────────────────
        iy = row_y + (ROW_H - ICON_SIZE) // 2
        draw.rectangle([ICON_X, iy, ICON_X + ICON_SIZE, iy + ICON_SIZE], fill=C_ICON_BG)
        if icon_img is not None:
            try:
                thumb = icon_img.copy()
                thumb.thumbnail((ICON_SIZE, ICON_SIZE), Image.LANCZOS)
                ox = ICON_X + (ICON_SIZE - thumb.width)  // 2
                oy = iy      + (ICON_SIZE - thumb.height) // 2
                if "A" in thumb.getbands():
                    img.paste(thumb, (ox, oy), thumb)
                else:
                    img.paste(thumb, (ox, oy))
            except Exception as e:
                print(f"[render] icon paste failed for '{name}': {e}")

        # ── имя и полоска прогресса ───────────────────────────────────────────
        cy = row_y + ROW_H // 2
        draw.text((TEXT_X, cy - 22), name, font=f_hero, fill=C_WHITE)

        if pct is not None:
            ratio  = min(max(int(pct), 0), 100) / 100
            filled = int(BAR_W_MAX * ratio)
            bar_y  = cy + 8

            draw.rectangle([TEXT_X, bar_y, BAR_END, bar_y + BAR_H], fill=C_BAR_BG)
            if filled > 0:
                draw.rectangle(
                    [TEXT_X, bar_y, TEXT_X + filled, bar_y + BAR_H], fill=C_GOLD
                )
            draw.text((PCT_X, cy + 4), f"{pct}%", font=f_pct, fill=C_PCT)

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


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

        top = heroes[:5]

        # ── попытка отправить карточку-изображение ────────────────────────────
        if _PIL_OK:
            try:
                icons   = await _fetch_hero_icons(top)
                buf     = render_hero_quiz_card(pos_label, top, icons)
                caption = f"Рекомендованные герои\nПозиция: {pos_label}"
                await update.message.reply_photo(photo=buf, caption=caption)
                return
            except Exception:
                traceback.print_exc()
                # продолжаем — ниже отправим текстовый вариант

        # ── текстовый fallback (PIL недоступен или упал) ──────────────────────
        lines = [
            "🧙 <b>Рекомендованные герои</b>",
            f"Позиция: <b>{pos_label}</b>",
            "",
        ]
        for i, hero in enumerate(top, start=1):
            name = hero.get("name", "?")
            pct  = hero.get("matchPercent")
            lines.append(f"{i}) {name} — совпадение {pct}%" if pct is not None else f"{i}) {name}")

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


