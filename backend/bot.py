import asyncio
import os
import re
import traceback
from io import BytesIO
from pathlib import Path
import secrets
from datetime import datetime, timedelta
from typing import Optional

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
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from db import init_tokens_table, create_token_for_user, get_user_id_by_token, get_last_quiz_result

# Optional: локальная статистика (stats_updater.py должен был уже наполнить БД).
# db.py при импорте добавляет корень проекта в sys.path, поэтому эти импорты
# безопасны, если они идут ПОСЛЕ `from db import ...`.
try:
    from stats_db import (
        get_hero_matchup_rows,
        get_hero_base_winrate_from_db,
        get_hero_synergy_rows,
    )
    _LOCAL_STATS_OK = True
except ImportError as _local_import_err:
    print(f"[bot] stats_db не загружен: {_local_import_err}")
    _LOCAL_STATS_OK = False

try:
    from hero_matchups_service import get_hero_matchups_cached, build_matchup_groups
    from hero_stats_service import get_hero_base_winrate as _get_od_base_winrate
    _OD_SERVICES_OK = True
except ImportError as _od_import_err:
    print(f"[bot] OpenDota-сервисы не загружены: {_od_import_err}")
    _OD_SERVICES_OK = False


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
            "photo_url": photo_url,
        }
    except Exception as e:
        print("Failed to build Telegram user payload:", e)
        payload = None

    subscribed = await is_subscriber(context.bot, user_id)

    if not subscribed:
        kb = InlineKeyboardMarkup(
            [[InlineKeyboardButton("📢 Подписаться на канал", url="https://t.me/kasumi_tt")]]
        )
        await update.message.reply_text(
            "⛔ Чтобы пользоваться ботом, подпишись на канал создателя.\n\n"
            "После подписки нажми /start ещё раз — и появится кнопка для открытия мини‑приложения.",
            reply_markup=kb,
        )
        try:
            await update.message.reply_reply_markup(reply_markup=ReplyKeyboardRemove())
        except Exception as e:
            print("Failed to remove old keyboard:", e)
        return

    token = create_token_for_user(user_id)
    mini_app_url_with_token = f"{MINI_APP_URL}?token={token}&tgWebAppDebug=1"

    if payload is not None:
        payload["token"] = token
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                r = await client.post(f"{API_BASE_URL}/api/save_telegram_data", json=payload)
            print("SAVE_TG_DATA status:", r.status_code, "resp:", r.text)
        except Exception as e:
            print("Failed to call save_telegram_data:", e)

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

_EXTRA_POS_LABELS: dict[str, str] = {
    "pos1": "Pos 1 — Керри",
    "pos2": "Pos 2 — Мид",
    "pos3": "Pos 3 — Оффлейн",
    "pos4": "Pos 4 — Роумер",
    "pos5": "Pos 5 — Саппорт",
}


def _fmt_date(dt: datetime | None) -> str:
    if dt is None:
        return "?"
    try:
        return dt.strftime("%d.%m.%Y")
    except Exception:
        return str(dt)[:10]


def _parse_position_quiz(result: dict, updated_at: datetime | None) -> dict | None:
    if "position_quiz" in result:
        pq = result["position_quiz"]
        return {
            "position":      pq.get("position", "?"),
            "positionIndex": pq.get("positionIndex"),
            "date":          pq.get("date") or _fmt_date(updated_at),
            "isPure":        bool(pq.get("isPure")),
            "extraPos":      pq.get("extraPos"),
        }
    if result.get("type") == "position_quiz":
        return {
            "position":      result.get("position", "?"),
            "positionIndex": result.get("positionIndex"),
            "date":          _fmt_date(updated_at),
            "isPure":        False,
            "extraPos":      None,
        }
    return None


def _parse_hero_quiz(result: dict, pos_index: int | None) -> list[dict]:
    if "hero_quiz_by_position" in result:
        hqbp: dict = result["hero_quiz_by_position"]
        key = str(pos_index) if pos_index is not None else None
        entry = hqbp.get(key) if key is not None else None
        if entry is None and hqbp:
            entry = next(iter(hqbp.values()))
        if entry:
            return entry.get("topHeroes", [])
    elif "hero_quiz" in result:
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
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


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
    """Конвертирует имя героя в PNG-файл для CDN (аналог логики в hero-images.js)."""
    slug = _HERO_SLUG_OVERRIDES.get(name)
    if slug is None:
        slug = name.strip().lower()
        slug = re.sub(r"['\u2019]", "", slug)
        slug = re.sub(r"\s+", "_", slug)
        slug = re.sub(r"[^a-z0-9_\-]", "", slug)
    return slug + ".png"


async def _fetch_hero_icons(heroes: list[dict]) -> list:
    """Параллельно скачивает иконки для каждого героя из HERO_IMAGE_BASE_URL."""
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
    """Рисует карточку с топ-героями в стиле мини-апа и возвращает PNG в памяти."""
    n = min(len(heroes), 5)

    W         = 800
    OUTER_PAD = 28
    INNER_PAD = 14
    CARD_H    = 82
    CARD_GAP  = 10
    ROW_H     = CARD_H + CARD_GAP
    ICON_W    = 120
    ICON_H    = 68
    BORDER_R  = 14
    BAR_H     = 4
    HEADER_H  = 130

    H = HEADER_H + n * ROW_H + 30

    C_BG      = (5,   5,   9)
    C_CARD    = (15,  15,  20)
    C_BORDER  = (35,  35,  46)
    C_TEXT    = (245, 245, 247)
    C_MUTED   = (155, 155, 161)
    C_GOLD_A  = (255, 159,  28)
    C_GOLD_B  = (255, 215,  90)
    C_BAR_BG  = (30,  30,  40)
    C_ICON_BG = (22,  25,  38)

    _RANK_BORDER: list = [
        (255, 215,  90),
        (210, 218, 255),
        (224, 169, 109),
        None,
        None,
    ]

    img  = Image.new("RGB", (W, H), C_BG)
    draw = ImageDraw.Draw(img)

    for sy in range(H):
        bv = int(9 + 7 * sy / H)
        draw.line([(0, sy), (W, sy)], fill=(5, 5, bv))

    f_title = _load_font(28, bold=True)
    f_sub   = _load_font(18)
    f_hero  = _load_font(22, bold=True)
    f_pct   = _load_font(18)

    draw.text((OUTER_PAD, 32), "Рекомендованные герои", font=f_title, fill=C_TEXT)
    draw.text((OUTER_PAD, 78), f"Позиция: {position_name}", font=f_sub, fill=C_MUTED)
    draw.line([(OUTER_PAD, 114), (W - OUTER_PAD, 114)], fill=C_BORDER, width=1)

    TEXT_X    = OUTER_PAD + INNER_PAD + ICON_W + 12
    PCT_RIGHT = W - OUTER_PAD - INNER_PAD
    BAR_X1    = TEXT_X
    BAR_X2    = PCT_RIGHT - 52

    _icons = list(icons or []) + [None] * n

    for i in range(n):
        hero     = heroes[i]
        icon_img = _icons[i]
        name     = hero.get("name", "?")
        pct      = hero.get("matchPercent")

        card_y     = HEADER_H + i * ROW_H
        border_col = _RANK_BORDER[i] if _RANK_BORDER[i] is not None else C_BORDER

        try:
            draw.rounded_rectangle(
                [OUTER_PAD, card_y, W - OUTER_PAD, card_y + CARD_H],
                radius=BORDER_R, fill=C_CARD, outline=border_col, width=1,
            )
        except AttributeError:
            draw.rectangle(
                [OUTER_PAD, card_y, W - OUTER_PAD, card_y + CARD_H],
                fill=C_CARD, outline=border_col,
            )

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

        name_y = card_y + 16
        draw.text((TEXT_X, name_y), name, font=f_hero, fill=C_TEXT)

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

        if pct is not None:
            bar_y  = card_y + CARD_H - 18
            ratio  = min(max(int(pct), 0), 100) / 100
            filled = int((BAR_X2 - BAR_X1) * ratio)

            try:
                draw.rounded_rectangle(
                    [BAR_X1, bar_y, BAR_X2, bar_y + BAR_H],
                    radius=999, fill=C_BAR_BG,
                )
            except AttributeError:
                draw.rectangle([BAR_X1, bar_y, BAR_X2, bar_y + BAR_H], fill=C_BAR_BG)

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

        if _PIL_OK:
            try:
                icons = await _fetch_hero_icons(top)
                buf   = render_hero_quiz_card(pos_label, top, icons)

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


# ============================================================
#  Поиск героя по тексту + карточки /counters и /synergy
# ============================================================

# Полный список героев: отображаемое имя → OpenDota hero_id.
# Источник: window.dotaHeroIds в hero-images.js (корень проекта).
HERO_NAME_TO_ID: dict[str, int] = {
    "Anti-Mage": 1,       "Axe": 2,             "Bane": 3,
    "Bloodseeker": 4,     "Crystal Maiden": 5,  "Drow Ranger": 6,
    "Earthshaker": 7,     "Juggernaut": 8,       "Mirana": 9,
    "Morphling": 10,      "Shadow Fiend": 11,    "Phantom Lancer": 12,
    "Puck": 13,           "Pudge": 14,           "Razor": 15,
    "Sand King": 16,      "Storm Spirit": 17,    "Sven": 18,
    "Tiny": 19,           "Vengeful Spirit": 20, "Windranger": 21,
    "Zeus": 22,           "Kunkka": 23,          "Lina": 25,
    "Lion": 26,           "Shadow Shaman": 27,   "Slardar": 28,
    "Tidehunter": 29,     "Witch Doctor": 30,    "Lich": 31,
    "Riki": 32,           "Enigma": 33,          "Tinker": 34,
    "Sniper": 35,         "Necrophos": 36,       "Warlock": 37,
    "Beastmaster": 38,    "Queen of Pain": 39,   "Venomancer": 40,
    "Faceless Void": 41,  "Wraith King": 42,     "Death Prophet": 43,
    "Phantom Assassin": 44, "Pugna": 45,         "Templar Assassin": 46,
    "Viper": 47,          "Luna": 48,            "Dragon Knight": 49,
    "Dazzle": 50,         "Clockwerk": 51,       "Leshrac": 52,
    "Nature's Prophet": 53, "Lifestealer": 54,   "Dark Seer": 55,
    "Clinkz": 56,         "Omniknight": 57,      "Enchantress": 58,
    "Huskar": 59,         "Night Stalker": 60,   "Broodmother": 61,
    "Bounty Hunter": 62,  "Weaver": 63,          "Jakiro": 64,
    "Batrider": 65,       "Chen": 66,            "Spectre": 67,
    "Ancient Apparition": 68, "Doom": 69,        "Ursa": 70,
    "Spirit Breaker": 71, "Gyrocopter": 72,      "Alchemist": 73,
    "Invoker": 74,        "Silencer": 75,        "Outworld Destroyer": 76,
    "Outworld Devourer": 76, "Lycan": 77,        "Brewmaster": 78,
    "Shadow Demon": 79,   "Lone Druid": 80,      "Chaos Knight": 81,
    "Meepo": 82,          "Treant Protector": 83, "Ogre Magi": 84,
    "Undying": 85,        "Rubick": 86,          "Disruptor": 87,
    "Nyx Assassin": 88,   "Naga Siren": 89,      "Keeper of the Light": 90,
    "Io": 91,             "Visage": 92,          "Slark": 93,
    "Medusa": 94,         "Troll Warlord": 95,   "Centaur Warrunner": 96,
    "Magnus": 97,         "Timbersaw": 98,       "Bristleback": 99,
    "Tusk": 100,          "Skywrath Mage": 101,  "Abaddon": 102,
    "Elder Titan": 103,   "Legion Commander": 104, "Techies": 105,
    "Ember Spirit": 106,  "Earth Spirit": 107,   "Underlord": 108,
    "Terrorblade": 109,   "Phoenix": 110,        "Oracle": 111,
    "Winter Wyvern": 112, "Arc Warden": 113,     "Monkey King": 114,
    "Dark Willow": 119,   "Pangolier": 120,      "Grimstroke": 121,
    "Hoodwink": 123,      "Void Spirit": 126,    "Snapfire": 128,
    "Mars": 129,          "Dawnbreaker": 135,    "Marci": 136,
    "Primal Beast": 137,  "Muerta": 138,         "Kez": 145,
    "Largo": 155,
}

# Обратный маппинг: hero_id → каноническое отображаемое имя (первое вхождение).
HERO_ID_TO_NAME: dict[int, str] = {}
for _n, _hid in HERO_NAME_TO_ID.items():
    if _hid not in HERO_ID_TO_NAME:
        HERO_ID_TO_NAME[_hid] = _n

# Состояние ожидания ввода: user_id → тип ожидания.
_user_state: dict[int, str] = {}


def find_hero_by_name(query: str) -> Optional[tuple[str, int]]:
    """Ищет героя по тексту. Возвращает (display_name, hero_id) или None.

    Алгоритм:
    1. Точное совпадение (без учёта регистра).
    2. Подстрочный поиск — выбирается герой с наиболее ранним вхождением запроса.
    """
    q = query.strip().lower().replace("_", " ")
    if not q:
        return None

    # 1. Точное совпадение
    for name, hero_id in HERO_NAME_TO_ID.items():
        if name.lower() == q:
            return name, hero_id

    # 2. Подстрочный поиск
    matches: list[tuple[int, str, int]] = []
    for name, hero_id in HERO_NAME_TO_ID.items():
        name_lower = name.lower()
        idx = name_lower.find(q)
        if idx >= 0:
            matches.append((idx, name, hero_id))

    if not matches:
        return None

    # Сортируем: чем раньше совпадение — тем лучше, затем алфавитно
    matches.sort(key=lambda x: (x[0], x[1]))
    _, best_name, best_id = matches[0]
    return best_name, best_id


# -------- рендеринг двухсекционной карточки (counters / synergy) --------

def _render_two_section_card(
    main_title: str,
    hero_name: str,
    sec1_title: str,
    sec1_heroes: list[dict],
    sec1_icons: list | None,
    sec1_bar_a: tuple,
    sec1_bar_b: tuple,
    sec1_label_color: tuple,
    sec2_title: str,
    sec2_heroes: list[dict],
    sec2_icons: list | None,
    sec2_bar_a: tuple,
    sec2_bar_b: tuple,
    sec2_label_color: tuple,
) -> BytesIO:
    """Общая функция рендера карточки с двумя секциями героев.

    Каждый герой в списке: {"name": str, "wr_pct": float}  (wr_pct = 0..100).
    """
    n1 = min(len(sec1_heroes), 5)
    n2 = min(len(sec2_heroes), 5)

    W         = 800
    OUTER_PAD = 28
    INNER_PAD = 14
    CARD_H    = 72
    CARD_GAP  = 8
    ROW_H     = CARD_H + CARD_GAP
    ICON_W    = 100
    ICON_H    = 56
    BORDER_R  = 12
    BAR_H     = 4
    HEADER_H  = 110
    SECTION_H = 44
    EMPTY_H   = 36   # высота строки «Нет данных»
    BOT_PAD   = 24

    sec1_content_h = n1 * ROW_H if n1 > 0 else EMPTY_H
    sec2_content_h = n2 * ROW_H if n2 > 0 else EMPTY_H
    H = HEADER_H + SECTION_H + sec1_content_h + SECTION_H + sec2_content_h + BOT_PAD

    C_BG      = (5,   5,   9)
    C_CARD    = (15,  15,  20)
    C_BORDER  = (35,  35,  46)
    C_TEXT    = (245, 245, 247)
    C_MUTED   = (155, 155, 161)
    C_GOLD_B  = (255, 215,  90)
    C_BAR_BG  = (30,  30,  40)
    C_ICON_BG = (22,  25,  38)

    img  = Image.new("RGB", (W, H), C_BG)
    draw = ImageDraw.Draw(img)

    # фоновый градиент
    for sy in range(H):
        bv = int(9 + 7 * sy / H)
        draw.line([(0, sy), (W, sy)], fill=(5, 5, bv))

    f_title   = _load_font(26, bold=True)
    f_sub     = _load_font(17)
    f_section = _load_font(19, bold=True)
    f_hero    = _load_font(19, bold=True)
    f_pct     = _load_font(16)

    # ── заголовок ──────────────────────────────────────────────────────────
    draw.text((OUTER_PAD, 26), main_title, font=f_title, fill=C_TEXT)
    draw.text((OUTER_PAD, 66), f"Герой: {hero_name}", font=f_sub, fill=C_MUTED)
    draw.line([(OUTER_PAD, 98), (W - OUTER_PAD, 98)], fill=C_BORDER, width=1)

    TEXT_X    = OUTER_PAD + INNER_PAD + ICON_W + 12
    PCT_RIGHT = W - OUTER_PAD - INNER_PAD
    BAR_X1    = TEXT_X
    BAR_X2    = PCT_RIGHT - 56

    def _draw_hero_row(y: int, hero: dict, icon_img, bar_a: tuple, bar_b: tuple) -> None:
        try:
            draw.rounded_rectangle(
                [OUTER_PAD, y, W - OUTER_PAD, y + CARD_H],
                radius=BORDER_R, fill=C_CARD, outline=C_BORDER, width=1,
            )
        except AttributeError:
            draw.rectangle([OUTER_PAD, y, W - OUTER_PAD, y + CARD_H], fill=C_CARD, outline=C_BORDER)

        ix = OUTER_PAD + INNER_PAD
        iy = y + (CARD_H - ICON_H) // 2
        try:
            draw.rounded_rectangle([ix, iy, ix + ICON_W, iy + ICON_H], radius=6, fill=C_ICON_BG)
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
                print(f"[render2sec] icon paste failed: {e}")

        name_y = y + 12
        draw.text((TEXT_X, name_y), hero["name"], font=f_hero, fill=C_TEXT)

        wr_pct = hero.get("wr_pct", 50.0)
        pct_str = f"{wr_pct:.1f}%"
        try:
            bb    = draw.textbbox((0, 0), pct_str, font=f_pct)
            pct_w = bb[2] - bb[0]
        except AttributeError:
            pct_w = len(pct_str) * 10
        draw.text((PCT_RIGHT - pct_w, name_y + 2), pct_str, font=f_pct, fill=C_GOLD_B)

        bar_y  = y + CARD_H - 14
        ratio  = min(max(wr_pct, 0.0), 100.0) / 100.0
        filled = int((BAR_X2 - BAR_X1) * ratio)
        try:
            draw.rounded_rectangle([BAR_X1, bar_y, BAR_X2, bar_y + BAR_H], radius=999, fill=C_BAR_BG)
        except AttributeError:
            draw.rectangle([BAR_X1, bar_y, BAR_X2, bar_y + BAR_H], fill=C_BAR_BG)

        if filled > 0:
            for dx in range(filled):
                t  = dx / max(filled - 1, 1)
                r_ = int(bar_a[0] + (bar_b[0] - bar_a[0]) * t)
                g_ = int(bar_a[1] + (bar_b[1] - bar_a[1]) * t)
                b_ = int(bar_a[2] + (bar_b[2] - bar_a[2]) * t)
                draw.line([(BAR_X1 + dx, bar_y), (BAR_X1 + dx, bar_y + BAR_H)], fill=(r_, g_, b_))

    cur_y = HEADER_H

    # ── секция 1 ──────────────────────────────────────────────────────────
    draw.text((OUTER_PAD, cur_y + 12), sec1_title, font=f_section, fill=sec1_label_color)
    cur_y += SECTION_H

    if n1 == 0:
        draw.text((OUTER_PAD + 16, cur_y + 8), "Нет данных", font=f_sub, fill=C_MUTED)
        cur_y += EMPTY_H
    else:
        _ic1 = list(sec1_icons or []) + [None] * n1
        for i in range(n1):
            _draw_hero_row(cur_y, sec1_heroes[i], _ic1[i], sec1_bar_a, sec1_bar_b)
            cur_y += ROW_H

    # ── секция 2 ──────────────────────────────────────────────────────────
    draw.text((OUTER_PAD, cur_y + 12), sec2_title, font=f_section, fill=sec2_label_color)
    cur_y += SECTION_H

    if n2 == 0:
        draw.text((OUTER_PAD + 16, cur_y + 8), "Нет данных", font=f_sub, fill=C_MUTED)
    else:
        _ic2 = list(sec2_icons or []) + [None] * n2
        for i in range(n2):
            _draw_hero_row(cur_y, sec2_heroes[i], _ic2[i], sec2_bar_a, sec2_bar_b)
            cur_y += ROW_H

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf


def render_counters_card(
    hero_name: str,
    strong_against: list[dict],
    weak_against: list[dict],
    icons_strong: list | None = None,
    icons_weak: list | None = None,
) -> BytesIO:
    """Карточка контрпиков: 'Силён против' (зелёный) и 'Сложно против' (красный)."""
    return _render_two_section_card(
        main_title="Контрпики",
        hero_name=hero_name,
        sec1_title="Силён против:",
        sec1_heroes=strong_against,
        sec1_icons=icons_strong,
        sec1_bar_a=(52, 194, 122),
        sec1_bar_b=(35, 165,  90),
        sec1_label_color=(52, 194, 122),
        sec2_title="Сложно против:",
        sec2_heroes=weak_against,
        sec2_icons=icons_weak,
        sec2_bar_a=(220, 70, 70),
        sec2_bar_b=(180, 40, 40),
        sec2_label_color=(220, 70, 70),
    )


def render_synergy_card(
    hero_name: str,
    best_allies: list[dict],
    worst_allies: list[dict],
    icons_best: list | None = None,
    icons_worst: list | None = None,
) -> BytesIO:
    """Карточка синергий: 'Лучшие союзники' (зелёный) и 'Худшие союзники' (красный)."""
    return _render_two_section_card(
        main_title="Синергия",
        hero_name=hero_name,
        sec1_title="Лучшие союзники:",
        sec1_heroes=best_allies,
        sec1_icons=icons_best,
        sec1_bar_a=(52, 194, 122),
        sec1_bar_b=(35, 165,  90),
        sec1_label_color=(52, 194, 122),
        sec2_title="Худшие союзники:",
        sec2_heroes=worst_allies,
        sec2_icons=icons_worst,
        sec2_bar_a=(220, 70, 70),
        sec2_bar_b=(180, 40, 40),
        sec2_label_color=(220, 70, 70),
    )


# -------- /counters --------

async def counters_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет инструкцию и ждёт имени героя для показа контрпиков."""
    user_id = update.effective_user.id

    if not await is_subscriber(context.bot, user_id):
        await update.message.reply_text(
            "Чтобы пользоваться ботом, подпишись на канал @kasumi_tt и потом вернись сюда.\n"
            "После подписки нажми /start или повтори команду."
        )
        return

    _user_state[user_id] = "awaiting_counters_hero"

    await update.message.reply_text(
        "⚔️ <b>Поиск контрпиков</b>\n"
        "\n"
        "Напиши имя героя на английском в формате, как в мини‑апе:\n"
        "\n"
        "• Первые буквы заглавные: <code>Juggernaut</code>, <code>Luna</code>\n"
        "• Несколько слов — пробел или нижнее подчёркивание:\n"
        "  <code>Templar Assassin</code> или <code>Templar_Assassin</code>\n"
        "• Можно часть имени: <code>ember</code>, <code>void</code>, <code>luna</code>\n"
        "\n"
        "<i>Следующее твоё сообщение будет воспринято как имя героя.</i>",
        parse_mode="HTML",
    )


# -------- /synergy --------

async def synergy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет инструкцию и ждёт имени героя для показа синергий."""
    user_id = update.effective_user.id

    if not await is_subscriber(context.bot, user_id):
        await update.message.reply_text(
            "Чтобы пользоваться ботом, подпишись на канал @kasumi_tt и потом вернись сюда.\n"
            "После подписки нажми /start или повтори команду."
        )
        return

    _user_state[user_id] = "awaiting_synergy_hero"

    await update.message.reply_text(
        "🤝 <b>Синергия союзников</b>\n"
        "\n"
        "Напиши имя героя на английском в формате, как в мини‑апе:\n"
        "\n"
        "• Первые буквы заглавные: <code>Invoker</code>, <code>Crystal Maiden</code>\n"
        "• Несколько слов — пробел или нижнее подчёркивание:\n"
        "  <code>Dark Willow</code> или <code>Dark_Willow</code>\n"
        "• Можно часть имени: <code>invoker</code>, <code>cm</code>, <code>lion</code>\n"
        "\n"
        "<i>Следующее твоё сообщение будет воспринято как имя героя.</i>",
        parse_mode="HTML",
    )


# -------- логика обработки имени героя для /counters --------

async def _handle_counters_hero(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,  # noqa: ARG001
    query: str,
) -> None:
    found = find_hero_by_name(query)

    if found is None:
        await update.message.reply_text(
            "Я не нашёл такого героя. Попробуй написать имя на английском, как в мини‑апе.\n\n"
            "Примеры:\n"
            "• <code>Juggernaut</code>\n"
            "• <code>Luna</code>\n"
            "• <code>Templar Assassin</code> / <code>Templar_Assassin</code>\n\n"
            "Используй /counters, чтобы попробовать снова.",
            parse_mode="HTML",
        )
        return

    hero_name, hero_id = found
    strong: list[dict] = []
    weak:   list[dict] = []

    try:
        # ── 1. Локальные данные (stats_db) ────────────────────────────────
        if _LOCAL_STATS_OK:
            local_rows = get_hero_matchup_rows(hero_id, min_games=50)
            if local_rows:
                base_wr = get_hero_base_winrate_from_db(hero_id) or 0.5
                enriched = [
                    {**r, "adv": round(r["wr_vs"] - base_wr, 4)}
                    for r in local_rows
                    if r["games"] >= 50
                ]
                victims = sorted(
                    [e for e in enriched if e["adv"] > 0],
                    key=lambda x: x["adv"], reverse=True,
                )[:5]
                counters_list = sorted(
                    [e for e in enriched if e["adv"] <= 0],
                    key=lambda x: x["adv"],
                )[:5]
                strong = [
                    {"name": HERO_ID_TO_NAME.get(e["hero_id"], f"Hero #{e['hero_id']}"),
                     "wr_pct": round(e["wr_vs"] * 100, 1)}
                    for e in victims
                ]
                weak = [
                    {"name": HERO_ID_TO_NAME.get(e["hero_id"], f"Hero #{e['hero_id']}"),
                     "wr_pct": round(e["wr_vs"] * 100, 1)}
                    for e in counters_list
                ]
                print(f"[counters] local DB: hero={hero_name} strong={len(strong)} weak={len(weak)}")

        # ── 2. OpenDota (fallback, если локальных данных нет) ─────────────
        if not strong and not weak and _OD_SERVICES_OK:
            try:
                od_matchups = await get_hero_matchups_cached(hero_id)
                if od_matchups:
                    od_base_wr = await _get_od_base_winrate(hero_id)
                    groups = build_matchup_groups(od_matchups, od_base_wr)
                    strong = [
                        {"name": HERO_ID_TO_NAME.get(e["opponent_hero_id"],
                                                       f"Hero #{e['opponent_hero_id']}"),
                         "wr_pct": round(e["winrate"] * 100, 1)}
                        for e in groups["strong_against"][:5]
                    ]
                    weak = [
                        {"name": HERO_ID_TO_NAME.get(e["opponent_hero_id"],
                                                       f"Hero #{e['opponent_hero_id']}"),
                         "wr_pct": round(e["winrate"] * 100, 1)}
                        for e in groups["weak_against"][:5]
                    ]
                    print(f"[counters] OpenDota: hero={hero_name} strong={len(strong)} weak={len(weak)}")
            except Exception as od_err:
                print(f"[counters] OpenDota fallback error for {hero_name}: {od_err}")

        if not strong and not weak:
            await update.message.reply_text(
                f"Не удалось найти данные по контрпикам для <b>{hero_name}</b>.\n\n"
                "Возможно, статистика ещё не накоплена. Попробуй позже или проверь мини‑апп.",
                parse_mode="HTML",
            )
            return

        caption = (
            f"⚔️ <b>Контрпики для: {hero_name}</b>\n"
            "\n"
            "📊 На основе статистики матчапов из мини‑апа."
        )

        # ── Рендер карточки ───────────────────────────────────────────────
        if _PIL_OK:
            try:
                icons_all = await _fetch_hero_icons(
                    [{"name": h["name"]} for h in strong + weak]
                )
                icons_strong = icons_all[:len(strong)]
                icons_weak   = icons_all[len(strong):]
                buf = render_counters_card(hero_name, strong, weak, icons_strong, icons_weak)
                await update.message.reply_photo(photo=buf, caption=caption, parse_mode="HTML")
                return
            except Exception:
                traceback.print_exc()
                # продолжаем → текстовый fallback

        # ── Текстовый fallback ────────────────────────────────────────────
        lines = [f"⚔️ <b>Контрпики для: {hero_name}</b>", ""]
        if strong:
            lines.append("✅ <b>Силён против:</b>")
            for i, h in enumerate(strong, 1):
                lines.append(f"{i}. {h['name']} — {h['wr_pct']}%")
            lines.append("")
        if weak:
            lines.append("❌ <b>Сложно против:</b>")
            for i, h in enumerate(weak, 1):
                lines.append(f"{i}. {h['name']} — {h['wr_pct']}%")
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")

    except Exception:
        traceback.print_exc()
        await update.message.reply_text(
            "Произошла ошибка при получении данных. Попробуй позже."
        )


# -------- логика обработки имени героя для /synergy --------

async def _handle_synergy_hero(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    query: str,
) -> None:
    found = find_hero_by_name(query)

    if found is None:
        await update.message.reply_text(
            "Я не нашёл такого героя. Попробуй написать имя на английском, как в мини‑апе.\n\n"
            "Примеры:\n"
            "• <code>Invoker</code>\n"
            "• <code>Crystal Maiden</code>\n"
            "• <code>Dark Willow</code> / <code>Dark_Willow</code>\n\n"
            "Используй /synergy, чтобы попробовать снова.",
            parse_mode="HTML",
        )
        return

    hero_name, hero_id = found
    best:  list[dict] = []
    worst: list[dict] = []

    try:
        if _LOCAL_STATS_OK:
            syn_rows = get_hero_synergy_rows(hero_id, min_games=50)
            if syn_rows:
                base_wr = get_hero_base_winrate_from_db(hero_id) or 0.5
                enriched = [
                    {**r, "delta": round(r["wr_vs"] - base_wr, 4)}
                    for r in syn_rows
                    if r["games"] >= 50
                ]
                best = [
                    {"name": HERO_ID_TO_NAME.get(e["hero_id"], f"Hero #{e['hero_id']}"),
                     "wr_pct": round(e["wr_vs"] * 100, 1)}
                    for e in sorted(
                        [e for e in enriched if e["delta"] >= 0],
                        key=lambda x: x["delta"], reverse=True,
                    )[:5]
                ]
                worst = [
                    {"name": HERO_ID_TO_NAME.get(e["hero_id"], f"Hero #{e['hero_id']}"),
                     "wr_pct": round(e["wr_vs"] * 100, 1)}
                    for e in sorted(
                        [e for e in enriched if e["delta"] < 0],
                        key=lambda x: x["delta"],
                    )[:5]
                ]
                print(f"[synergy] local DB: hero={hero_name} best={len(best)} worst={len(worst)}")

        if not best and not worst:
            await update.message.reply_text(
                f"🤝 <b>Синергия для: {hero_name}</b>\n"
                "\n"
                "Данные по синергиям пока в разработке или недостаточно матчей в базе.\n\n"
                "Используй мини‑апп для детальной статистики.",
                parse_mode="HTML",
            )
            return

        caption = (
            f"🤝 <b>Синергия для: {hero_name}</b>\n"
            "\n"
            "📊 На основе статистики из мини‑апа."
        )

        if _PIL_OK:
            try:
                icons_all = await _fetch_hero_icons(
                    [{"name": h["name"]} for h in best + worst]
                )
                icons_best  = icons_all[:len(best)]
                icons_worst = icons_all[len(best):]
                buf = render_synergy_card(hero_name, best, worst, icons_best, icons_worst)
                await update.message.reply_photo(photo=buf, caption=caption, parse_mode="HTML")
                return
            except Exception:
                traceback.print_exc()

        lines = [f"🤝 <b>Синергия для: {hero_name}</b>", ""]
        if best:
            lines.append("✅ <b>Лучшие союзники:</b>")
            for i, h in enumerate(best, 1):
                lines.append(f"{i}. {h['name']} — {h['wr_pct']}%")
            lines.append("")
        if worst:
            lines.append("❌ <b>Худшие союзники:</b>")
            for i, h in enumerate(worst, 1):
                lines.append(f"{i}. {h['name']} — {h['wr_pct']}%")
        await update.message.reply_text("\n".join(lines), parse_mode="HTML")

    except Exception:
        traceback.print_exc()
        await update.message.reply_text(
            "Произошла ошибка при получении данных. Попробуй позже."
        )


# -------- обработчик текстовых сообщений (диспетчер состояний) --------

async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Перехватывает текстовые сообщения, когда бот ждёт имя героя."""
    user_id = update.effective_user.id
    state   = _user_state.get(user_id)

    if state is None:
        # Нет активного состояния — игнорируем
        return

    # Сбрасываем состояние до обработки (чтобы ошибка внутри не "застряла")
    del _user_state[user_id]

    text = (update.message.text or "").strip()
    if not text:
        return

    if state == "awaiting_counters_hero":
        await _handle_counters_hero(update, context, text)
    elif state == "awaiting_synergy_hero":
        await _handle_synergy_hero(update, context, text)


# -------- /help --------

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎮 <b>Как пользоваться ботом:</b>\n\n"
        "1️⃣ Нажми кнопку «Найди своего героя»\n"
        "2️⃣ Ответь на несколько вопросов\n"
        "3️⃣ Получи рекомендацию по герою и позиции\n\n"
        "<b>Команды:</b>\n"
        "/start — Начать заново\n"
        "/last_quiz — Последний результат квиза по позициям\n"
        "/hero_quiz — Рекомендованные герои из последнего квиза\n"
        "/counters — Контрпики для любого героя\n"
        "/synergy — Синергии союзников для любого героя\n"
        "/help — Показать это сообщение",
        parse_mode="HTML",
    )


def main():
    init_tokens_table()
    print("🤖 Бот запускается...")

    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не найден. Проверь файл .env")

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start",      start))
    application.add_handler(CommandHandler("help",       help_command))
    application.add_handler(CommandHandler("last_quiz",  last_quiz_command))
    application.add_handler(CommandHandler("hero_quiz",  hero_quiz_command))
    application.add_handler(CommandHandler("counters",   counters_command))
    application.add_handler(CommandHandler("synergy",    synergy_command))

    # Текстовые сообщения — должны идти ПОСЛЕ команд (меньший приоритет)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message)
    )

    print("✅ Бот запущен! Открой Telegram и напиши боту /start")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
