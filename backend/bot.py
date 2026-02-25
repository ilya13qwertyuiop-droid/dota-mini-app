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
# CDN для иконок героев — тот же, что использует фронтенд (hero-images.js).
# Переопределяется через .env: HERO_IMAGE_BASE_URL=https://your-cdn/heroes
# Дефолт указывает на официальный Dota 2 CDN Valve.
HERO_IMAGE_BASE_URL: str = os.environ.get(
    "HERO_IMAGE_BASE_URL",
    "https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes",
)

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


# Перевод отображаемых имён героев в CDN-слаги.
# Скопировано из window.dotaHeroImages в hero-images.js — герои с нестандартными
# слагами (Anti-Mage→antimage, Shadow Fiend→nevermore и т.д.).
_HERO_SLUG_OVERRIDES: dict[str, str] = {
    "Anti-Mage":          "antimage",
    "Nature's Prophet":   "furion",
    "Shadow Fiend":       "nevermore",
    "Necrophos":          "necrolyte",
    "Wraith King":        "skeleton_king",
    "Clockwerk":          "rattletrap",
    "Lifestealer":        "life_stealer",
    "Doom":               "doom_bringer",
    "Outworld Destroyer": "obsidian_destroyer",
    "Outworld Devourer":  "obsidian_destroyer",
    "Treant Protector":   "treant",
    "Io":                 "wisp",
    "Magnus":             "magnataur",
    "Timbersaw":          "shredder",
    "Underlord":          "abyssal_underlord",
    "Windranger":         "windrunner",
    "Zeus":               "zuus",
    "Queen of Pain":      "queenofpain",
    "Vengeful Spirit":    "vengefulspirit",
}


def hero_name_to_filename(name: str) -> str:
    """Конвертирует имя героя в PNG-файл для CDN (аналог логики в hero-images.js).

    Сначала ищет в _HERO_SLUG_OVERRIDES (герои с нестандартными слагами).
    Fallback: lower-case + убрать апострофы + пробелы → подчёркивания.

    "Anti-Mage"        → "antimage.png"         (override)
    "Outworld Destroyer"→ "obsidian_destroyer.png" (override)
    "Templar Assassin" → "templar_assassin.png"  (fallback)
    "Crystal Maiden"   → "crystal_maiden.png"    (fallback)
    """
    slug = _HERO_SLUG_OVERRIDES.get(name)
    if slug is None:
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
    """Рисует карточку с топ-героями в стиле мини-апа и возвращает PNG в памяти.

    Палитра точно соответствует styles.css:
      --bg-main #050509 · --glass-bg rgb(15,15,20) · --text-main #f5f5f7
      --text-muted #9b9ba1 · .match-fill gradient #ff9f1c→#ffd75a
      .hero-card--gold/silver/bronze border colors
    """
    n = min(len(heroes), 5)

    # ── размеры ──────────────────────────────────────────────────────────────
    W         = 800
    OUTER_PAD = 28    # отступ холста до карточки (px)
    INNER_PAD = 14    # внутренний padding карточки (CSS: 16–18px)
    CARD_H    = 82    # высота карточки героя
    CARD_GAP  = 10    # зазор между карточками
    ROW_H     = CARD_H + CARD_GAP
    ICON_W    = 120   # ширина иконки (panoramic 16:9, как в Dota 2 CDN)
    ICON_H    = 68    # высота иконки
    BORDER_R  = 14    # border-radius карточки (CSS: 16px)
    BAR_H     = 4     # высота полоски совпадения (CSS .match-bar: height 4px)
    HEADER_H  = 130   # высота блока заголовка

    H = HEADER_H + n * ROW_H + 30

    # ── палитра (точные hex-значения из styles.css) ───────────────────────────
    C_BG      = (5,   5,   9)    # --bg-main: #050509
    C_CARD    = (15,  15,  20)   # --glass-bg: rgba(15,15,20,0.9) → solid
    C_BORDER  = (35,  35,  46)   # --glass-border: rgba(255,255,255,0.06) на тёмном
    C_TEXT    = (245, 245, 247)  # --text-main: #f5f5f7
    C_MUTED   = (155, 155, 161)  # --text-muted: #9b9ba1
    C_GOLD_A  = (255, 159,  28)  # #ff9f1c — старт .match-fill gradient
    C_GOLD_B  = (255, 215,  90)  # #ffd75a — финиш .match-fill gradient
    C_BAR_BG  = (30,  30,  40)   # .match-bar background: rgba(30,30,40,1)
    C_ICON_BG = (22,  25,  38)   # placeholder иконки

    # Ранговые бордеры (CSS .hero-card--gold / --silver / --bronze)
    _RANK_BORDER: list = [
        (255, 215,  90),   # gold   #ffd75a
        (210, 218, 255),   # silver
        (224, 169, 109),   # bronze #e0a96d
        None,
        None,
    ]

    img  = Image.new("RGB", (W, H), C_BG)
    draw = ImageDraw.Draw(img)

    # ── фон: мягкий вертикальный градиент #050509 → #050510 ──────────────────
    for sy in range(H):
        bv = int(9 + 7 * sy / H)   # blue: 9 → 16
        draw.line([(0, sy), (W, sy)], fill=(5, 5, bv))

    # ── шрифты (размеры масштабированы под PNG-разрешение 800px) ─────────────
    f_title = _load_font(28, bold=True)   # h1: font-size 22px / weight 700 в CSS
    f_sub   = _load_font(18)              # подзаголовок, --text-muted
    f_hero  = _load_font(22, bold=True)   # .hero-name: font-weight 600
    f_pct   = _load_font(18)              # процент

    # ── заголовок ─────────────────────────────────────────────────────────────
    draw.text((OUTER_PAD, 32), "Рекомендованные герои", font=f_title, fill=C_TEXT)
    draw.text((OUTER_PAD, 78), f"Позиция: {position_name}", font=f_sub, fill=C_MUTED)
    # разделительная линия (имитирует border-bottom)
    draw.line([(OUTER_PAD, 114), (W - OUTER_PAD, 114)], fill=C_BORDER, width=1)

    # ── производные x-координаты ──────────────────────────────────────────────
    TEXT_X    = OUTER_PAD + INNER_PAD + ICON_W + 12  # x начала текста/полоски
    PCT_RIGHT = W - OUTER_PAD - INNER_PAD             # правый край для pct
    BAR_X1    = TEXT_X
    BAR_X2    = PCT_RIGHT - 52                        # место для "100%"

    _icons = list(icons or []) + [None] * n  # гарантируем длину ≥ n

    for i in range(n):
        hero     = heroes[i]
        icon_img = _icons[i]
        name     = hero.get("name", "?")
        pct      = hero.get("matchPercent")

        card_y     = HEADER_H + i * ROW_H
        border_col = _RANK_BORDER[i] if _RANK_BORDER[i] is not None else C_BORDER

        # ── карточка (.hero-card: border-radius 16px, bg rgba(15,15,20)) ──────
        try:
            draw.rounded_rectangle(
                [OUTER_PAD, card_y, W - OUTER_PAD, card_y + CARD_H],
                radius=BORDER_R, fill=C_CARD, outline=border_col, width=1,
            )
        except AttributeError:   # Pillow < 8.2 fallback
            draw.rectangle(
                [OUTER_PAD, card_y, W - OUTER_PAD, card_y + CARD_H],
                fill=C_CARD, outline=border_col,
            )

        # ── иконка (.hero-icon: border-radius 6px из CSS) ────────────────────
        ix = OUTER_PAD + INNER_PAD
        iy = card_y + (CARD_H - ICON_H) // 2
        try:
            draw.rounded_rectangle(
                [ix, iy, ix + ICON_W, iy + ICON_H], radius=6, fill=C_ICON_BG
            )
        except AttributeError:
            draw.rectangle([ix, iy, ix + ICON_W, iy + ICON_H], fill=C_ICON_BG)

        if icon_img is not None:
            try:
                thumb = icon_img.copy()
                thumb.thumbnail((ICON_W, ICON_H), Image.LANCZOS)
                ox = ix + (ICON_W - thumb.width)  // 2
                oy = iy + (ICON_H - thumb.height) // 2
                if "A" in thumb.getbands():
                    img.paste(thumb, (ox, oy), thumb)
                else:
                    img.paste(thumb, (ox, oy))
            except Exception as e:
                print(f"[render] icon paste failed for '{name}': {e}")

        # ── имя героя (.hero-name: font-weight 600, --text-main) ─────────────
        name_y = card_y + 16
        draw.text((TEXT_X, name_y), name, font=f_hero, fill=C_TEXT)

        # ── процент совпадения (правый край, цвет #ffd75a) ────────────────────
        if pct is not None:
            pct_str = f"{pct}%"
            try:
                bb    = draw.textbbox((0, 0), pct_str, font=f_pct)
                pct_w = bb[2] - bb[0]
            except AttributeError:
                pct_w = len(pct_str) * 11
            draw.text(
                (PCT_RIGHT - pct_w, name_y + 2),
                pct_str, font=f_pct, fill=C_GOLD_B,
            )

        # ── полоска совпадения (.match-bar/.match-fill) ───────────────────────
        if pct is not None:
            bar_y  = card_y + CARD_H - 18
            ratio  = min(max(int(pct), 0), 100) / 100
            filled = int((BAR_X2 - BAR_X1) * ratio)

            # фон полоски (.match-bar)
            try:
                draw.rounded_rectangle(
                    [BAR_X1, bar_y, BAR_X2, bar_y + BAR_H],
                    radius=999, fill=C_BAR_BG,
                )
            except AttributeError:
                draw.rectangle([BAR_X1, bar_y, BAR_X2, bar_y + BAR_H], fill=C_BAR_BG)

            # заполненная часть: градиент #ff9f1c → #ffd75a (.match-fill)
            if filled > 0:
                for dx in range(filled):
                    t  = dx / max(filled - 1, 1)
                    gr = int(C_GOLD_A[0] + (C_GOLD_B[0] - C_GOLD_A[0]) * t)
                    gg = int(C_GOLD_A[1] + (C_GOLD_B[1] - C_GOLD_A[1]) * t)
                    gb = int(C_GOLD_A[2] + (C_GOLD_B[2] - C_GOLD_A[2]) * t)
                    draw.line(
                        [(BAR_X1 + dx, bar_y), (BAR_X1 + dx, bar_y + BAR_H)],
                        fill=(gr, gg, gb),
                    )

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
                icons = await _fetch_hero_icons(top)
                buf   = render_hero_quiz_card(pos_label, top, icons)

                # Извлекаем только человекочитаемую часть после «—»
                if "—" in pos_label:
                    position_short = pos_label.split("—", 1)[1].strip()
                else:
                    position_short = pos_label

                caption = (
                    "🧙 <b>Рекомендованные герои</b>\n"
                    "\n"
                    f"🎯 <b>Позиция:</b> {position_short}\n"
                    "\n"
                    "📌 Подборка на основе твоего последнего квиза по позициям."
                )
                await update.message.reply_photo(photo=buf, caption=caption, parse_mode="HTML")
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


