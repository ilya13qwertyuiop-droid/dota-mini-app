import asyncio
import functools
import html
import logging
import os
import re
import time
from collections import deque
from io import BytesIO
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# RPS counter — кольцевой буфер меток времени за последние 60 секунд
# ---------------------------------------------------------------------------
_rps_window: deque[float] = deque()  # timestamps запросов


def _record_request() -> float:
    """Записывает факт запроса и возвращает текущий RPS (за последние 60 с)."""
    now = time.monotonic()
    _rps_window.append(now)
    cutoff = now - 60.0
    while _rps_window and _rps_window[0] < cutoff:
        _rps_window.popleft()
    return len(_rps_window) / 60.0


def timed_handler(cmd: str):
    """Декоратор для хендлеров: логирует BEGIN/OK/ERROR с user_id, duration, RPS."""
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            uid: int | str = "?"
            try:
                if update.effective_user:
                    uid = update.effective_user.id
            except Exception:
                pass
            t0 = time.monotonic()
            rps = _record_request()
            logger.info(
                "[%s] user=%s %s BEGIN rps=%.1f",
                datetime.now().strftime("%H:%M:%S.%f")[:-3], uid, cmd, rps,
            )
            try:
                result = await fn(update, context)
                logger.info(
                    "[%s] user=%s %s OK %.0fms",
                    datetime.now().strftime("%H:%M:%S.%f")[:-3], uid, cmd,
                    (time.monotonic() - t0) * 1000,
                )
                return result
            except Exception as exc:
                logger.error(
                    "[%s] user=%s %s ERROR %.0fms: %s",
                    datetime.now().strftime("%H:%M:%S.%f")[:-3], uid, cmd,
                    (time.monotonic() - t0) * 1000, exc, exc_info=True,
                )
                raise
        return wrapper
    return decorator


def logged_event(event: str):
    """Декоратор: пишет одно событие в analytics_events перед вызовом хендлера.

    Применяется поверх timed_handler в регистрации команд. Никогда не валит
    основной поток (log_event сам глотает ошибки записи)."""
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            try:
                uid = update.effective_user.id if update.effective_user else None
                log_event(event, uid)
            except Exception:
                pass
            return await fn(update, context)
        return wrapper
    return decorator


try:
    from PIL import Image, ImageDraw, ImageFont
    _PIL_OK = True
except ImportError:
    _PIL_OK = False

import httpx
from telegram import (
    Bot,
    BotCommand,
    MenuButtonCommands,
    Update,
    ReplyKeyboardRemove,
    WebAppInfo,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    filters, ContextTypes,
)
from telegram.error import RetryAfter, Forbidden, TelegramError
from db import (
    init_tokens_table,
    get_last_quiz_result,
    save_feedback,
    get_recent_feedback,
    get_feedback_stats,
    count_new_users_today,
    count_active_users_30d,
    count_matches_with_game_mode,
    get_top_drafters,
    get_user_profile_settings,
    upsert_user_profile_settings,
    toggle_notify_news,
    get_all_bot_user_ids,
    create_broadcast_job,
    update_broadcast_job,
    get_active_broadcast_job,
    ban_user,
    unban_user,
    find_user_id_by_username,
    log_event,
)
from avatar_store import delete_avatar, store_avatar_bytes
from security_logging import configure_secure_logging
from stats_db import get_teammate_stats, get_analytics_overview

# Optional: локальная статистика (stats_updater.py должен был уже наполнить БД).
# db.py при импорте добавляет корень проекта в sys.path, поэтому эти импорты
# безопасны, если они идут ПОСЛЕ `from db import ...`.
try:
    from stats_db import (
        get_hero_matchup_rows,
        get_hero_base_winrate_from_db,
        get_hero_synergy_rows,
        get_stats_mode,
        set_stats_mode,
    )
    _LOCAL_STATS_OK = True
except ImportError as _local_import_err:
    logger.warning("[bot] stats_db не загружен: %s", _local_import_err)
    _LOCAL_STATS_OK = False

try:
    from hero_matchups_service import get_hero_matchups_cached, build_matchup_groups
    from hero_stats_service import get_hero_base_winrate as _get_od_base_winrate
    _OD_SERVICES_OK = True
except ImportError as _od_import_err:
    logger.warning("[bot] OpenDota-сервисы не загружены: %s", _od_import_err)
    _OD_SERVICES_OK = False

# Единый источник контрпиков/синергий с мини-апом (hero_matchups.json, Stratz).
try:
    from hero_pairs import get_hero_counters as _get_hero_counters, get_hero_synergy as _get_hero_synergy
    _HERO_PAIRS_OK = True
except ImportError as _hp_import_err:
    logger.warning("[bot] hero_pairs не загружен: %s", _hp_import_err)
    _HERO_PAIRS_OK = False


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
SPONSOR_CHAT_ID = os.environ.get("SPONSOR_CHAT_ID", "-1002005211472")  # chat_id канала спонсора

# user_id, для которых проверка подписки пропускается (список через запятую в SKIP_SUBSCRIPTION_CHECK_IDS)
SKIP_CHECK_USER_IDS: frozenset[int] = frozenset(
    int(x) for x in os.environ.get("SKIP_SUBSCRIPTION_CHECK_IDS", "").split(",") if x.strip().lstrip("-").isdigit()
)

# Отложенные товарищеские вызовы: неподписанный тапнул ссылку db_<КОД> →
# гейт отправил подписываться, а код из ссылки к повторному /start теряется
# (человек жмёт команду, не ссылку). Помним код на TTL комнаты и доигрываем
# после подписки. In-memory: бот однопроцессный, рестарат теряет — не страшно
# (вызов живёт 10 минут, друг может тапнуть ссылку повторно).
_PENDING_BATTLE_INVITES: dict[int, tuple[str, float]] = {}
_PENDING_BATTLE_TTL_SEC = 600

# Telegram user_id administrators. Never grant admin authority from source-code
# defaults: deployment configuration is the only trust source.
ADMIN_IDS: frozenset[int] = frozenset(
    int(x)
    for x in os.environ.get("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
)
if not ADMIN_IDS:
    logger.warning("ADMIN_IDS is empty; all administrative bot commands are disabled")
API_BASE_URL = "https://dotaquiz.blog"
# CDN для иконок героев — тот же, что использует фронтенд (hero-images.js).
# Переопределяется через .env: HERO_IMAGE_BASE_URL=https://your-cdn/heroes
# Дефолт указывает на официальный Dota 2 CDN Valve.
HERO_IMAGE_BASE_URL: str = os.environ.get(
    "HERO_IMAGE_BASE_URL",
    "https://cdn.cloudflare.steamstatic.com/apps/dota2/images/dota_react/heroes",
)

async def is_subscriber(bot: Bot, user_id: int) -> bool:
    """Проверяет подписку пользователя на оба канала: CHECK_CHAT_ID и SPONSOR_CHAT_ID.

    Каждый вызов делает свежий запрос getChatMember к Telegram API.
    При любой ошибке возвращает False и не падает.
    """
    if user_id in SKIP_CHECK_USER_IDS:
        return True
    if not CHECK_CHAT_ID:
        return False
    try:
        member = await bot.get_chat_member(chat_id=CHECK_CHAT_ID, user_id=user_id)
        if member.status not in ("member", "administrator", "creator"):
            return False
    except Exception as e:
        logger.warning("[is_subscriber] error for user %s (main channel): %s", user_id, e)
        return False
    if SPONSOR_CHAT_ID:
        try:
            sponsor_member = await bot.get_chat_member(chat_id=SPONSOR_CHAT_ID, user_id=user_id)
            if sponsor_member.status not in ("member", "administrator", "creator"):
                return False
        except Exception as e:
            logger.warning("[is_subscriber] error for user %s (sponsor channel): %s", user_id, e)
            return False
    return True


# -------- handlers --------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не найден. Проверь файл .env")
    if not MINI_APP_URL:
        raise RuntimeError("MINI_APP_URL не найден. Проверь файл .env")
    if not CHECK_CHAT_ID:
        raise RuntimeError("CHECK_CHAT_ID не найден. Проверь файл .env")

    user_id = update.effective_user.id

    user = update.effective_user

    # Атрибуция источника перехода: payload из deep-link (t.me/<bot>?start=<payload>).
    # Напр. "hl_share" — пришёл с шеринга мини-игры «Выше/Ниже».
    _start_payload = (context.args[0] if getattr(context, "args", None) else None)
    if _start_payload:
        logger.info("[start] deep-link payload=%s user=%s", _start_payload, user_id)

    # Получаем байты фото на сервере. Telegram file URL содержит BOT_TOKEN и
    # поэтому никогда не сохраняется и не возвращается клиенту.
    avatar_state = "error"
    avatar_bytes = None
    avatar_file_unique_id = None
    try:
        photos = await context.bot.get_user_profile_photos(user.id, limit=1)
        if photos.total_count > 0:
            photo = photos.photos[0][-1]
            telegram_file = await context.bot.get_file(photo.file_id)
            avatar_bytes = await telegram_file.download_as_bytearray()
            avatar_file_unique_id = photo.file_unique_id
            avatar_state = "ready"
        else:
            avatar_state = "missing"
    except Exception as e:
        logger.warning("Failed to fetch user photo for %s: %s", user_id, e)

    subscribed = await is_subscriber(context.bot, user_id)

    if not subscribed:
        # Вызов друга у неподписанного: код из ссылки потеряется к моменту
        # повторного /start (человек жмёт команду, не ссылку) — запоминаем
        # на TTL комнаты и доиграем после подписки.
        if _start_payload and _start_payload.startswith("db_"):
            _PENDING_BATTLE_INVITES[user_id] = (_start_payload[3:][:12], time.time())
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📢 Канал создателя", url="https://t.me/kasumi_tt"),
                InlineKeyboardButton("📢 Канал спонсора", url="https://t.me/+NtPbXaoKbeo2YjEy"),
            ]
        ])
        await update.message.reply_text(
            "⛔ Бот доступен подписчикам наших каналов.\n\n"
            "Подпишись на оба канала и нажми /start ещё раз."
            + ("\n\n⚔️ Вызов друга не потеряется — после подписки "
               "пришлю кнопку боя." if user_id in _PENDING_BATTLE_INVITES else ""),
            reply_markup=kb,
        )
        return

    # Never embed an API session in a Telegram button. The WebApp obtains a
    # short-lived session from signed Telegram initData after it opens.
    _mini_parts = urlsplit(MINI_APP_URL)
    mini_app_url = urlunsplit((
        _mini_parts.scheme,
        _mini_parts.netloc,
        _mini_parts.path,
        _mini_parts.query,
        "",
    ))

    # Товарищеский вызов («Сыграть с другом»): deep-link db_<КОД> из шаринга.
    # Гейт подписок выше УЖЕ пройден — неподписанный друг сперва подпишется
    # (это осознанно: вызовы не должны обходить обязательные каналы).
    # Код берём из payload ИЛИ из отложенного вызова: после подписки человек
    # жмёт /start без payload — доигрываем сохранённый код.
    _battle_code = None
    if _start_payload and _start_payload.startswith("db_"):
        _battle_code = _start_payload[3:][:12]
    else:
        _pending = _PENDING_BATTLE_INVITES.pop(user_id, None)
        if _pending and time.time() - _pending[1] <= _PENDING_BATTLE_TTL_SEC:
            _battle_code = _pending[0]
    if _battle_code:
        _battle_query = parse_qsl(_mini_parts.query, keep_blank_values=True)
        _battle_query.append(("battle", _battle_code))
        battle_url = urlunsplit((
            _mini_parts.scheme,
            _mini_parts.netloc,
            _mini_parts.path,
            urlencode(_battle_query),
            "",
        ))
        await update.message.reply_text(
            "⚔️ Тебя вызвали на битву драфтов!\n"
            "Товарищеский матч — рейтинг не на кону, только гордость.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "⚔️ Принять вызов",
                    web_app=WebAppInfo(url=battle_url),
                )
            ]]),
        )

    # Пишем данные профиля напрямую в БД — без HTTP-запроса к самому себе.
    # Старый token-bearing photo_url удаляется при любом успешном /start.
    try:
        current_settings = await asyncio.to_thread(get_user_profile_settings, user_id)
        old_avatar_key = current_settings.get("avatar_key")
        settings_patch = {
            "username": user.username,
            "first_name": user.first_name,
            "last_name": getattr(user, "last_name", None),
        }
        remove_keys = ["photo_url"]

        if avatar_state == "ready" and avatar_bytes is not None:
            avatar_key = await asyncio.to_thread(
                store_avatar_bytes, avatar_bytes, old_avatar_key
            )
            settings_patch.update({
                "avatar_key": avatar_key,
                "avatar_file_unique_id": avatar_file_unique_id,
            })
        elif avatar_state == "missing":
            await asyncio.to_thread(delete_avatar, old_avatar_key)
            remove_keys.extend(("avatar_key", "avatar_file_unique_id"))

        await asyncio.to_thread(
            upsert_user_profile_settings,
            user_id,
            settings_patch,
            remove_keys=tuple(remove_keys),
        )
    except Exception as e:
        logger.warning("Failed to upsert profile settings for user %s: %s", user_id, e)

    # A reply-keyboard WebApp opens a Telegram "simple WebView" without
    # signed user initData.  The former token-bearing URL hid that limitation.
    # Inline WebApp buttons receive signed initData, so the browser can obtain
    # its short-lived API session without putting credentials in the URL.
    open_markup = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            text="Открыть D2Helper",
            web_app=WebAppInfo(url=mini_app_url),
        )
    ]])

    # Welcome admin-редактируется через /admin_text welcome.
    # Дефолт см. backend/bot_texts.py:DEFAULT_BOT_TEXTS["welcome"].
    from backend.bot_texts import get_text as _get_bot_text
    await update.message.reply_text(
        _get_bot_text("welcome"),
        # Remove the legacy reply keyboard already stored by Telegram clients.
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML",
    )
    await update.message.reply_text(
        "Открыть мини-приложение 👇\n\n"
        "⚠️ Mini App не грузится? Попробуй зайти с VPN!",
        reply_markup=open_markup,
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
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📢 Канал создателя", url="https://t.me/kasumi_tt"),
                InlineKeyboardButton("📢 Канал спонсора", url="https://t.me/+NtPbXaoKbeo2YjEy"),
            ]
        ])
        await update.message.reply_text(
            "⛔ Бот доступен подписчикам наших каналов.\n\n"
            "Подпишись на оба канала и нажми /start ещё раз.",
            reply_markup=kb,
        )
        return

    row = await asyncio.to_thread(get_last_quiz_result, user_id)
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
        logger.exception("Failed to read quiz result")
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
            logger.debug("[hero icon] fetch failed for '%s': %s", name, e)
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
                logger.debug("[render] icon paste failed for '%s': %s", name, e)

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
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📢 Канал создателя", url="https://t.me/kasumi_tt"),
                InlineKeyboardButton("📢 Канал спонсора", url="https://t.me/+NtPbXaoKbeo2YjEy"),
            ]
        ])
        await update.message.reply_text(
            "⛔ Бот доступен подписчикам наших каналов.\n\n"
            "Подпишись на оба канала и нажми /start ещё раз.",
            reply_markup=kb,
        )
        return

    row = await asyncio.to_thread(get_last_quiz_result, user_id)
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
                buf   = await asyncio.to_thread(render_hero_quiz_card, pos_label, top, icons)

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
                logger.exception("Failed to send quiz result image")

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
        logger.exception("Failed to read hero quiz result")
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

    # Токены нового аппа (styles.css :root). Без золота и градиент-фона.
    C_BG      = (10,  10,  15)   # --bg-base
    C_CARD    = (17,  17,  19)   # --bg-surface
    C_BORDER  = (38,  38,  44)
    C_TEXT    = (237, 237, 240)  # --text-primary
    C_MUTED   = (139, 139, 149)  # --text-secondary
    C_BAR_BG  = (25,  25,  30)
    C_ICON_BG = (25,  25,  30)   # --bg-elevated

    img  = Image.new("RGB", (W, H), C_BG)   # плоский фон, без градиента
    draw = ImageDraw.Draw(img)

    # Шрифты Geist (как в шеринге); fallback на системный, если ассета нет.
    from pathlib import Path as _FontPath
    _fd = _FontPath(__file__).resolve().parent.parent / "assets" / "fonts"
    def _gf(nm: str, sz: int):
        try:
            return ImageFont.truetype(str(_fd / nm), sz)
        except Exception:
            return _load_font(sz, bold=("Bold" in nm or "SemiBold" in nm))
    f_title   = _gf("Geist-SemiBold.ttf", 26)
    f_sub     = _gf("Geist-Regular.ttf", 17)
    f_section = _gf("Geist-SemiBold.ttf", 19)
    f_hero    = _gf("Geist-Medium.ttf", 19)
    f_pct     = _gf("Geist-SemiBold.ttf", 17)

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
                logger.debug("[render2sec] icon paste failed: %s", e)

        name_y = y + 12
        draw.text((TEXT_X, name_y), hero["name"], font=f_hero, fill=C_TEXT)

        wr_pct = hero.get("wr_pct", 50.0)
        pct_str = f"{wr_pct:.1f}%"
        try:
            bb    = draw.textbbox((0, 0), pct_str, font=f_pct)
            pct_w = bb[2] - bb[0]
        except AttributeError:
            pct_w = len(pct_str) * 10
        draw.text((PCT_RIGHT - pct_w, name_y + 2), pct_str, font=f_pct, fill=bar_a)

        bar_y  = y + CARD_H - 14
        ratio  = min(max(wr_pct, 0.0), 100.0) / 100.0
        filled = int((BAR_X2 - BAR_X1) * ratio)
        # Обычные прямоугольники — равномерная толщина. rounded_rectangle с
        # большим radius на полосе 4px давал сужающиеся/«рваные» края.
        draw.rectangle([BAR_X1, bar_y, BAR_X2, bar_y + BAR_H], fill=C_BAR_BG)
        if filled > 0:
            draw.rectangle([BAR_X1, bar_y, BAR_X1 + filled, bar_y + BAR_H], fill=bar_a)

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
        sec1_bar_a=(61, 184, 122),
        sec1_bar_b=(61, 184, 122),
        sec1_label_color=(61, 184, 122),
        sec2_title="Сложно против:",
        sec2_heroes=weak_against,
        sec2_icons=icons_weak,
        sec2_bar_a=(229, 83, 75),
        sec2_bar_b=(229, 83, 75),
        sec2_label_color=(229, 83, 75),
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
        sec1_bar_a=(61, 184, 122),
        sec1_bar_b=(61, 184, 122),
        sec1_label_color=(61, 184, 122),
        sec2_title="Худшие союзники:",
        sec2_heroes=worst_allies,
        sec2_icons=icons_worst,
        sec2_bar_a=(229, 83, 75),
        sec2_bar_b=(229, 83, 75),
        sec2_label_color=(229, 83, 75),
    )


# -------- /counters --------

async def counters_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправляет инструкцию и ждёт имени героя для показа контрпиков."""
    user_id = update.effective_user.id

    if not await is_subscriber(context.bot, user_id):
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📢 Канал создателя", url="https://t.me/kasumi_tt"),
                InlineKeyboardButton("📢 Канал спонсора", url="https://t.me/+NtPbXaoKbeo2YjEy"),
            ]
        ])
        await update.message.reply_text(
            "⛔ Бот доступен подписчикам наших каналов.\n\n"
            "Подпишись на оба канала и нажми /start ещё раз.",
            reply_markup=kb,
        )
        return

    _user_state[user_id] = "awaiting_counters_hero"

    await update.message.reply_text(
        "⚔️ <b>Поиск контрпиков</b>\n"
        "\n"
        "Напиши имя героя на английском в формате, как в мини‑апе:\n"
        "\n"
        "• Первые буквы заглавные/прописные: <code>Juggernaut</code>, <code>luna</code>\n"
        "• Когда несколько слов — с пробелом или нижним подчёркиванием:\n"
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
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📢 Канал создателя", url="https://t.me/kasumi_tt"),
                InlineKeyboardButton("📢 Канал спонсора", url="https://t.me/+NtPbXaoKbeo2YjEy"),
            ]
        ])
        await update.message.reply_text(
            "⛔ Бот доступен подписчикам наших каналов.\n\n"
            "Подпишись на оба канала и нажми /start ещё раз.",
            reply_markup=kb,
        )
        return

    _user_state[user_id] = "awaiting_synergy_hero"

    await update.message.reply_text(
        "🤝 <b>Синергия союзников</b>\n"
        "\n"
        "Напиши имя героя на английском в формате, как в мини‑апе:\n"
        "\n"
        "• Первые буквы заглавные/прописные: <code>Invoker</code>, <code>crystal maiden</code>\n"
        "• Когда несколько слов — с пробелом или нижним подчёркиванием:\n"
        "  <code>Dark Willow</code> или <code>Dark_Willow</code>\n"
        "• Можно часть имени: <code>troll</code>, <code>arc</code>, <code>night</code>\n"
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
        # Единый источник с мини-апом — hero_pairs (hero_matchups.json/Stratz).
        # victims = «Силён против», counters = «Сложно против». Числа 1-в-1 с аппом.
        if _HERO_PAIRS_OK:
            data = await asyncio.to_thread(_get_hero_counters, hero_id, 5, 50)
            strong = [
                {"name": HERO_ID_TO_NAME.get(e["hero_id"], f"Hero #{e['hero_id']}"),
                 "wr_pct": round(e["wr_vs"] * 100, 1)}
                for e in (data.get("victims") or [])[:5]
            ]
            weak = [
                {"name": HERO_ID_TO_NAME.get(e["hero_id"], f"Hero #{e['hero_id']}"),
                 "wr_pct": round(e["wr_vs"] * 100, 1)}
                for e in (data.get("counters") or [])[:5]
            ]
            logger.info("[counters] hero=%s strong=%d weak=%d (hero_pairs)", hero_name, len(strong), len(weak))

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
                buf = await asyncio.to_thread(render_counters_card, hero_name, strong, weak, icons_strong, icons_weak)
                await update.message.reply_photo(photo=buf, caption=caption, parse_mode="HTML")
                return
            except Exception:
                logger.exception("Failed to send counter image")
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
        logger.exception("Failed to load counter data")
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
        # Единый источник с мини-апом — hero_pairs (hero_matchups.json, ключ "with").
        if _HERO_PAIRS_OK:
            data = await asyncio.to_thread(_get_hero_synergy, hero_id, 5, 50)
            best = [
                {"name": HERO_ID_TO_NAME.get(e["hero_id"], f"Hero #{e['hero_id']}"),
                 "wr_pct": round(e["wr_vs"] * 100, 1)}
                for e in (data.get("best_allies") or [])[:5]
            ]
            worst = [
                {"name": HERO_ID_TO_NAME.get(e["hero_id"], f"Hero #{e['hero_id']}"),
                 "wr_pct": round(e["wr_vs"] * 100, 1)}
                for e in (data.get("worst_allies") or [])[:5]
            ]
            logger.info("[synergy] hero=%s best=%d worst=%d (hero_pairs)", hero_name, len(best), len(worst))

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
                buf = await asyncio.to_thread(render_synergy_card, hero_name, best, worst, icons_best, icons_worst)
                await update.message.reply_photo(photo=buf, caption=caption, parse_mode="HTML")
                return
            except Exception:
                logger.exception("Failed to send synergy image")

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
        logger.exception("Failed to load synergy data")
        await update.message.reply_text(
            "Произошла ошибка при получении данных. Попробуй позже."
        )


# -------- /news --------

async def news_command(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Переключает подписку на новости Dota 2 (notify_news toggle)."""
    user_id = update.effective_user.id
    new_value = await asyncio.to_thread(toggle_notify_news, user_id)
    if new_value:
        text = "✅ Уведомления о новостях Dota 2 включены"
    else:
        text = "🔕 Уведомления о новостях Dota 2 отключены"
    await update.message.reply_text(text)


# -------- /feedback --------

async def feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Принимает отзыв о мини‑аппе прямо через бота."""
    user_id = update.effective_user.id

    if not await is_subscriber(context.bot, user_id):
        kb = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📢 Канал создателя", url="https://t.me/kasumi_tt"),
                InlineKeyboardButton("📢 Канал спонсора", url="https://t.me/+NtPbXaoKbeo2YjEy"),
            ]
        ])
        await update.message.reply_text(
            "⛔ Бот доступен подписчикам наших каналов.\n\n"
            "Подпишись на оба канала и нажми /start ещё раз.",
            reply_markup=kb,
        )
        return

    _user_state[user_id] = "awaiting_feedback_message"

    await update.message.reply_text(
        "💬 <b>Предложить улучшения</b>\n"
        "\n"
        "Напиши одним сообщением, что тебе понравилось / не понравилось "
        "в мини‑аппе, и какие фичи хочешь видеть дальше.\n"
        "\n"
        "Я читаю все отзывы лично.",
        parse_mode="HTML",
    )


async def _handle_feedback_message(
    update: Update,
    _context: ContextTypes.DEFAULT_TYPE,
    text: str,
) -> None:
    user_id = update.effective_user.id
    username: str | None = update.effective_user.username
    try:
        await asyncio.to_thread(
            save_feedback,
            user_id=user_id,
            rating=None,
            tags=["bot"],
            message=text,
            source="bot",
            username=username,
        )
    except Exception:
        logger.exception("Failed to save bot feedback")
        await update.message.reply_text(
            "Не удалось сохранить отзыв. Попробуй позже."
        )
        return

    await update.message.reply_text(
        "✅ <b>Спасибо за отзыв!</b>\n"
        "\n"
        "Я читаю всё, что вы пишете, и буду дальше докручивать мини‑апп.",
        parse_mode="HTML",
    )


# -------- /stats_mode (скрытая команда для администраторов) --------

async def stats_mode_command(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Переключает режим статистики (normal ↔ strict). Только для администраторов."""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        return  # тихо игнорируем

    if not _LOCAL_STATS_OK:
        await update.message.reply_text("stats_db недоступен — переключение невозможно.")
        return

    try:
        current = get_stats_mode()
        new_mode = "strict" if current == "normal" else "normal"
        set_stats_mode(new_mode)
    except Exception:
        logger.exception("Failed to change statistics mode")
        await update.message.reply_text("Не удалось переключить режим статистики.")
        return

    if new_mode == "strict":
        msg = (
            "🔒 <b>Строгий режим включён</b>\n\n"
            "Статистика (контрпики, синергии, винрейт) считается только "
            "по ранговым матчам (<code>game_mode = 22</code>, "
            "<code>lobby_type = 7</code>) длительностью ≥ 20 мин.\n\n"
            "Данных меньше, но они качественнее."
        )
    else:
        msg = (
            "🔓 <b>Обычный режим включён</b>\n\n"
            "Статистика считается по всем спаршенным матчам "
            "(агрегатные таблицы <code>hero_stats</code> / "
            "<code>hero_matchups</code> / <code>hero_synergy</code>).\n\n"
            "Максимальное покрытие данных."
        )

    await update.message.reply_text(msg, parse_mode="HTML")


# -------- /admin_feedback (скрытая команда для администраторов) --------

async def admin_feedback_command(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Показывает последние 20 отзывов. Доступно только администраторам."""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        return  # тихо игнорируем

    try:
        stats, entries = await asyncio.gather(
            asyncio.to_thread(get_feedback_stats),
            asyncio.to_thread(get_recent_feedback, limit=20),
        )
    except Exception:
        logger.exception("Failed to load admin feedback")
        await update.message.reply_text("Не удалось получить отзывы.")
        return

    avg_str = f"{stats['avg_rating']:.2f} ★" if stats["avg_rating"] is not None else "—"
    header = (
        f"<b>📋 Отзывы</b>\n"
        f"Всего в БД: <b>{stats['total']}</b> · Средний рейтинг: <b>{avg_str}</b>\n"
        f"Показываю последние {len(entries)}\n"
    )

    if not entries:
        await update.message.reply_text(header + "\nОтзывов пока нет.", parse_mode="HTML")
        return

    def build_entry(e: dict) -> str:
        stars = "★" * (e["rating"] or 0) + "☆" * (4 - (e["rating"] or 0)) if e["rating"] else "—"
        # ВАЖНО: текст отзыва, username и теги — пользовательские; экранируем
        # под parse_mode="HTML", иначе символы < > & ломают парсинг → Telegram
        # отдаёт 400 и команда падает без ответа.
        uname = (
            f'<a href="tg://user?id={e["user_id"]}">@{html.escape(e["username"])}</a>'
            if e["username"]
            else (f'user {e["user_id"]}' if e["user_id"] else "аноним")
        )
        tags_str = " ".join(f"#{html.escape(str(t))}" for t in e["tags"]) if e["tags"] else ""
        date_str = e["created_at"].strftime("%d.%m %H:%M") if e["created_at"] else "?"
        source_icon = "📱" if e["source"] == "mini_app" else "🤖"
        return (
            f"<b>#{e['id']}</b> {source_icon} {stars} · {uname} · {date_str}\n"
            + (f"{tags_str}\n" if tags_str else "")
            + f"{html.escape(e['message'] or '')}"
        )

    # Разбиваем по 10 отзывов на сообщение; первое сообщение содержит header
    CHUNK = 10
    for chunk_idx, start in enumerate(range(0, len(entries), CHUNK)):
        chunk = entries[start : start + CHUNK]
        parts: list[str] = []
        if chunk_idx == 0:
            parts.append(header)
        parts.extend(build_entry(e) for e in chunk)
        text = "\n\n".join(parts)
        # Safety: если вдруг один отзыв огромный — обрезаем до лимита
        if len(text) > 4096:
            text = text[:4090] + "\n…"
        # Отправку оборачиваем: один битый блок не должен ронять всю команду
        # без ответа. На сбое HTML-парсинга шлём как plain-text (теги станут
        # видны, но сообщение хотя бы дойдёт).
        try:
            await update.message.reply_text(text, parse_mode="HTML", disable_web_page_preview=True)
        except Exception:
            logger.exception("Failed to send formatted admin feedback")
            try:
                await update.message.reply_text(text, disable_web_page_preview=True)
            except Exception:
                logger.exception("Failed to send plain admin feedback")


# -------- /admin_users (скрытая команда для администраторов) --------

async def admin_users_command(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Показывает статистику по пользователям. Только для администраторов."""
    if update.effective_user.id not in ADMIN_IDS:
        return

    try:
        new_today = count_new_users_today()
        active_30d = count_active_users_30d()
    except Exception:
        logger.exception("Failed to load admin user statistics")
        await update.message.reply_text("Не удалось получить статистику пользователей.")
        return

    await update.message.reply_text(
        f"👤 Новых пользователей сегодня: {new_today}\n"
        f"📅 Уникальных пользователей за 30 дней: {active_30d}"
    )


# -------- /admin_matches (скрытая команда для администраторов) --------

async def admin_matches_command(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Показывает количество матчей с заполненным game_mode. Только для администраторов."""
    if update.effective_user.id not in ADMIN_IDS:
        return

    try:
        count = count_matches_with_game_mode()
    except Exception:
        logger.exception("Failed to load admin match statistics")
        await update.message.reply_text("Не удалось получить статистику матчей.")
        return

    await update.message.reply_text(f"🧩 Матчей с заполненным game_mode: {count}")


# -------- /tm_stats (сводка по разделу «Пати», только для администраторов) --------

async def tm_stats_command(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Сводка по поиску тиммейтов: профили, статусы, запросы, отзывы."""
    if update.effective_user.id not in ADMIN_IDS:
        return

    try:
        s = get_teammate_stats()
    except Exception:
        logger.exception("Failed to load teammate statistics")
        await update.message.reply_text("Не удалось получить статистику раздела «Пати».")
        return

    status_labels = {
        "ready_now":       "Готов сейчас",
        "looking_regular": "Постоянка",
        "looking_casual":  "Не срочно",
        "hidden":          "Скрыт",
        "none":            "Без статуса",
    }
    by_status = s.get("by_status", {})
    status_lines = "\n".join(
        f"  • {status_labels.get(k, k)}: {by_status[k]}"
        for k in ["ready_now", "looking_regular", "looking_casual", "hidden", "none"]
        if by_status.get(k)
    ) or "  • —"

    reqs = s.get("requests", {})
    accept_rate = s.get("accept_rate")
    accept_str = f"{accept_rate}%" if accept_rate is not None else "—"

    await update.message.reply_text(
        "📊 Раздел «Пати»\n\n"
        f"👥 Профилей: {s.get('profiles_total', 0)}\n"
        f"🟢 Активны за 24ч: {s.get('active_24h', 0)}\n"
        f"🚀 Первопроходцев: {s.get('founders', 0)}\n\n"
        "Статусы:\n"
        f"{status_lines}\n\n"
        "Запросы:\n"
        f"  • ожидают: {reqs.get('pending', 0)}\n"
        f"  • принято: {reqs.get('accepted', 0)}\n"
        f"  • отклонено: {reqs.get('declined', 0)}\n"
        f"  • отменено: {reqs.get('cancelled', 0)}\n"
        f"  • % принятия: {accept_str}\n\n"
        f"⭐ Отзывов оставлено: {s.get('reviews_total', 0)}"
    )


# -------- /analytics (общая аналитика, только для администраторов) --------

# Лейблы для имён событий — чтобы в дайджесте было читаемо, а не «page_drafter».
_ANALYTICS_EVENT_LABELS = {
    "bot_start":             "/start",
    "bot_help":              "/help",
    "bot_quiz_last":         "/last_quiz",
    "bot_quiz_hero":         "/hero_quiz",
    "bot_counters":          "/counters",
    "bot_synergy":           "/synergy",
    "bot_news":              "/news",
    "bot_feedback":          "/feedback",
    "page_home":             "Главная",
    "page_drafter":          "Драфтер",
    "page_quiz":             "Квизы",
    "page_database":         "База героев",
    "page_profile":          "Профиль",
    "page_teammates":        "Пати",
    "page_teammate_review":  "Экран отзыва",
    "page_donate":           "Поддержка",
    "page_feedback":         "Фидбек",
    "page_news":             "Новости",
    "support_click":         "Поддержать — кликов",
    # Битва драфтов — воронка (battle_queue → battle_start → battle_finish).
    "page_draft_battle":     "Битва драфтов — открыт экран",
    "battle_queue":          "Битва — встал в очередь",
    "battle_start":          "Битва — началась",
    "battle_vs_bot":         "Битва — против бота",
    "battle_finish":         "Битва — доиграна",
    "battle_forfeit":        "Битва — сдался",
}


async def analytics_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сводка по активности и использованию — для админа. По умолчанию окно 7 дней;
    можно указать аргументом: /analytics 14."""
    if update.effective_user.id not in ADMIN_IDS:
        return

    # Парсим окно из аргумента (опц.).
    days = 7
    try:
        if context.args:
            n = int(context.args[0])
            if 1 <= n <= 60:
                days = n
    except (ValueError, IndexError):
        pass

    try:
        a = await asyncio.to_thread(get_analytics_overview, days=days)
    except Exception:
        logger.exception("Failed to load analytics")
        await update.message.reply_text("Не удалось получить аналитику.")
        return

    # 1) Дневная разбивка
    daily = a.get("daily", [])
    total_dau = sum(d["dau"] for d in daily)
    total_new = sum(d["new"] for d in daily)
    avg_dau = round(total_dau / len(daily)) if daily else 0
    daily_lines = "\n".join(
        f"  • {d['day']} — DAU {d['dau']} (нов: {d['new']} · верн: {d['returning']})"
        for d in daily
    ) or "  • —"

    # 2) Использование по фичам — сортировано по opens
    feats = a.get("features", [])
    feat_lines = "\n".join(
        f"  • {_ANALYTICS_EVENT_LABELS.get(f['event'], f['event'])}: "
        f"{f['opens']} откр · {f['users']} юзеров"
        for f in feats
    ) or "  • —"

    # 3) Retention
    d1 = a.get("retention_d1") or {}
    d7 = a.get("retention_d7") or {}
    def _ret_line(label, r):
        pct = r.get("avg_pct")
        cohorts = r.get("cohorts", 0)
        if pct is None:
            return f"  • {label}: — (нет данных)"
        return f"  • {label}: {pct}% (по {cohorts} cohort'ам)"

    await update.message.reply_text(
        f"📊 Аналитика D2Helper (окно {days} дн.)\n\n"
        f"📅 По дням:\n{daily_lines}\n\n"
        f"📈 Итого за окно: новых {total_new} · средний DAU ≈ {avg_dau}\n\n"
        f"💖 Поддержать — кликов: {a.get('support_clicks', 0)}\n\n"
        f"🔧 Использование по фичам:\n{feat_lines}\n\n"
        f"♻ Retention:\n"
        f"{_ret_line('D1', d1)}\n"
        f"{_ret_line('D7', d7)}"
    )


# -------- /topdraft (скрытая команда для администраторов) --------

async def topdraft_command(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Топ-3 драфтеров за текущий месяц. Только для администраторов."""
    if update.effective_user.id not in ADMIN_IDS:
        return

    now = datetime.now(timezone.utc)
    month_names = {
        1: "январь", 2: "февраль", 3: "март", 4: "апрель",
        5: "май", 6: "июнь", 7: "июль", 8: "август",
        9: "сентябрь", 10: "октябрь", 11: "ноябрь", 12: "декабрь",
    }
    month_label = f"{month_names[now.month]} {now.year}"

    try:
        top = get_top_drafters(month=now.month, year=now.year)
    except Exception:
        logger.exception("Failed to load draft leaderboard")
        await update.message.reply_text("❌ Не удалось получить топ драфтеров.")
        return

    if not top:
        await update.message.reply_text(
            f"🏆 Топ-3 драфтеров за {month_label}\n\nПока нет участников."
        )
        return

    medals = {1: "1.", 2: "2.", 3: "3."}
    lines = [f"🏆 Топ-3 драфтеров за {month_label}\n"]
    for r in top:
        uname = f"@{r['username']}" if r["username"] else r["first_name"]
        name = r["first_name"]
        display = f"{uname} ({name})" if r["username"] else name
        lines.append(
            f"{medals[r['rank']]} {display} — топ-5 сумма: {r['top5_sum']} / {r['draft_count']} драфтов\n"
            f"   user_id: {r['user_id']}"
        )

    await update.message.reply_text("\n".join(lines))


def _parse_ban_target(args: list[str]) -> tuple[int | None, str | None]:
    """Parses /ban or /unban args. Returns (user_id, error_message).

    First positional arg is either a numeric user_id or @username.
    @username is resolved via user_profiles.settings.username.
    """
    if not args:
        return None, "Использование: /ban [user_id или @username] [причина]"
    target = args[0].strip()
    if not target:
        return None, "Использование: /ban [user_id или @username] [причина]"
    if target.startswith("@") or not target.lstrip("-").isdigit():
        resolved = find_user_id_by_username(target)
        if resolved is None:
            return None, f"Пользователь {target} не найден в user_profiles."
        return resolved, None
    try:
        return int(target), None
    except ValueError:
        return None, f"Некорректный user_id: {target}"


async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Банит пользователя из лидерборда. Только для администраторов."""
    admin_id = update.effective_user.id
    if admin_id not in ADMIN_IDS:
        return

    args = context.args or []
    target_id, err = _parse_ban_target(args)
    if err:
        await update.message.reply_text(err)
        return

    reason = " ".join(args[1:]).strip() or None
    try:
        newly_banned = await asyncio.to_thread(ban_user, target_id, admin_id, reason)
    except Exception:
        logger.exception("Failed to ban user")
        await update.message.reply_text("❌ Не удалось применить бан.")
        return

    if newly_banned:
        suffix = f" · причина: {reason}" if reason else ""
        await update.message.reply_text(f"🚫 Пользователь {target_id} забанен в лидерборде.{suffix}")
    else:
        await update.message.reply_text(f"Пользователь {target_id} уже забанен.")


async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Снимает бан лидерборда с пользователя. Только для администраторов."""
    if update.effective_user.id not in ADMIN_IDS:
        return

    args = context.args or []
    target_id, err = _parse_ban_target(args)
    if err:
        await update.message.reply_text(err.replace("/ban", "/unban"))
        return

    try:
        removed = await asyncio.to_thread(unban_user, target_id)
    except Exception:
        logger.exception("Failed to unban user")
        await update.message.reply_text("❌ Не удалось снять бан.")
        return

    if removed:
        await update.message.reply_text(f"✅ Бан снят с пользователя {target_id}.")
    else:
        await update.message.reply_text(f"Пользователь {target_id} не был забанен.")


async def force_update_builds_command(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Принудительно запускает обновление кеша сборок. Только для администраторов."""
    if update.effective_user.id not in ADMIN_IDS:
        return
    try:
        from backend.stats_db import set_app_setting
        set_app_setting("force_builds_update", "1")
        await update.message.reply_text(
            "✅ Флаг force_builds_update установлен.\n"
            "Воркер обновит кеш сборок в течение нескольких минут."
        )
    except Exception as exc:
        logger.error("[force_update_builds] error: %s", exc)
        await update.message.reply_text("❌ Ошибка при установке флага обновления.")


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
    elif state == "awaiting_feedback_message":
        await _handle_feedback_message(update, context, text)


# -------- /help --------

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎮 <b>Как пользоваться ботом:</b>\n\n"
        "1️⃣ Нажми кнопку «Найди своего героя»\n"
        "2️⃣ Ответь на несколько вопросов\n"
        "3️⃣ Получи рекомендацию по герою и позиции\n\n"
        "<b>Команды:</b>\n"
        "/start — Начать заново\n"
        "/news — Уведомления об обновлениях Dota 2\n"
        "/last_quiz — Последний результат квиза по позициям\n"
        "/hero_quiz — Рекомендованные герои из последнего квиза\n"
        "/counters — Контрпики для любого героя\n"
        "/synergy — Синергии союзников для любого героя\n"
        "/feedback — Предложить улучшения мини‑аппа\n"
        "/help — Показать это сообщение",
        parse_mode="HTML",
    )


# -------- error handler --------

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Глобальный обработчик ошибок: пишет traceback в лог с user_id."""
    user_id = "?"
    try:
        if isinstance(update, Update) and update.effective_user:
            user_id = update.effective_user.id
    except Exception:
        pass

    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    logger.error(
        "[%s] ERROR user=%s %s",
        ts,
        user_id,
        context.error,
        exc_info=context.error,
    )


# ---------------------------------------------------------------------------
# /broadcast — рассылка поста из канала всем пользователям бота (только админ)
#
# Поток: админ ПЕРЕСЫЛАЕТ боту пост из своего канала → бот сохраняет ссылку на
# это сообщение и показывает кнопки [проверить на себе / разослать всем / отмена].
# Рассылка = forward_message того же сообщения каждому пользователю: картинка,
# форматирование, кастом-эмодзи и плашка «Переслано из канала» (со ссылкой на
# пост для реакций/комментов) сохраняются 1-в-1.
# ---------------------------------------------------------------------------

# admin_id -> {"chat_id", "message_id", "sending"}
_BROADCAST_PENDING: dict[int, dict] = {}

# Скорость: шлём ПАРАЛЛЕЛЬНО (перекрываем сетевую задержку), но глобально не
# выше _BROADCAST_RATE сообщений/сек — потолок Telegram ~30/сек, держимся под ним.
# Всё через env, чтобы крутить на проде без правки кода.
_BROADCAST_RATE = float(os.getenv("BROADCAST_RATE", "25"))          # сообщений/сек
_BROADCAST_CONCURRENCY = int(os.getenv("BROADCAST_CONCURRENCY", "25"))  # одновременных
_BROADCAST_CHUNK = int(os.getenv("BROADCAST_CHUNK", "500"))         # чекпоинт каждые N
# Сколько ждать максимум на одной flood-паузе (страховка от гигантского retry_after)
_BROADCAST_MAX_WAIT = float(os.getenv("BROADCAST_MAX_WAIT", "120"))
# Не зацикливаемся на одном юзере вечно: ограничиваем число flood-повторов
_BROADCAST_MAX_RETRIES = 5


async def _broadcast_send_one(bot, uid: int, src_chat_id: int, src_msg_id: int,
                              pacer, counters: dict) -> None:
    """Одна пересылка: пейсинг → forward → учёт ошибок и flood-повторов."""
    for attempt in range(_BROADCAST_MAX_RETRIES + 1):
        await pacer()  # глобальный лимитер скорости
        try:
            await bot.forward_message(chat_id=uid, from_chat_id=src_chat_id,
                                      message_id=src_msg_id)
            counters["ok"] += 1
            return
        except RetryAfter as e:
            wait = float(getattr(e, "retry_after", 5))
            # Логируем — раньше flood-паузы были невидимы (отсюда «двое суток»)
            logger.warning("[broadcast] RetryAfter %.1fs (uid=%s, attempt=%d)",
                           wait, uid, attempt + 1)
            counters["flood_waits"] += 1
            counters["flood_secs"] += wait
            if attempt >= _BROADCAST_MAX_RETRIES:
                counters["failed"] += 1
                return
            await asyncio.sleep(min(wait, _BROADCAST_MAX_WAIT) + 0.5)
            # повторяем
        except Forbidden:
            counters["blocked"] += 1  # заблокировал бота / не стартовал
            return
        except TelegramError:
            counters["failed"] += 1
            return
        except Exception:
            counters["failed"] += 1
            return


async def _do_broadcast(context, job_id: int, src_chat_id: int, src_msg_id: int,
                        user_ids: list[int], start_cursor: int, status_msg,
                        base_ok: int = 0, base_blocked: int = 0,
                        base_failed: int = 0) -> None:
    """Параллельно (с глобальным лимитером ~_BROADCAST_RATE/сек) пересылает пост
    всем user_ids начиная с start_cursor; чекпоинтит прогресс в БД каждый чанк.
    base_* — уже накопленные счётчики из прерванного прогона (для resume).
    """
    bot = context.bot
    total = len(user_ids)
    counters = {"ok": 0, "blocked": 0, "failed": 0, "flood_waits": 0, "flood_secs": 0.0}

    # --- глобальный token-bucket: не более _BROADCAST_RATE отправок/сек ---
    interval = 1.0 / _BROADCAST_RATE if _BROADCAST_RATE > 0 else 0.0
    next_slot = [time.monotonic()]
    pace_lock = asyncio.Lock()

    async def pacer():
        async with pace_lock:
            now = time.monotonic()
            t = next_slot[0] if next_slot[0] > now else now
            next_slot[0] = t + interval
        delay = t - time.monotonic()
        if delay > 0:
            await asyncio.sleep(delay)

    sem = asyncio.Semaphore(_BROADCAST_CONCURRENCY)

    async def worker(uid: int):
        async with sem:
            await _broadcast_send_one(bot, uid, src_chat_id, src_msg_id, pacer, counters)

    start_time = time.monotonic()

    async def render(done_count: int, final: bool = False):
        ok = counters["ok"] + base_ok
        bl = counters["blocked"] + base_blocked
        fl = counters["failed"] + base_failed
        elapsed = time.monotonic() - start_time
        processed_now = counters["ok"] + counters["blocked"] + counters["failed"]
        rate = processed_now / elapsed if elapsed > 0 else 0.0
        if final:
            txt = (
                "✅ <b>Рассылка завершена</b>\n\n"
                f"Всего: {total}\n"
                f"Доставлено: <b>{ok}</b>\n"
                f"Заблокировали бота: {bl}\n"
                f"Ошибки: {fl}\n"
                f"Скорость: {rate:.1f}/сек · flood-пауз: {counters['flood_waits']}"
            )
        else:
            eta = (total - done_count) / rate if rate > 0 else 0
            txt = (
                f"⏳ Рассылка… {done_count}/{total}\n"
                f"✅ {ok} · 🚫 {bl} · ⚠️ {fl}\n"
                f"~{rate:.1f}/сек · осталось ~{int(eta // 60)} мин"
            )
        try:
            await status_msg.edit_text(txt, parse_mode="HTML" if final else None)
        except Exception:
            pass

    # Идём чанками: внутри чанка — параллельно; после чанка — чекпоинт в БД.
    cursor = start_cursor
    for chunk_start in range(start_cursor, total, _BROADCAST_CHUNK):
        batch = user_ids[chunk_start:chunk_start + _BROADCAST_CHUNK]
        await asyncio.gather(*(worker(uid) for uid in batch))
        cursor = chunk_start + len(batch)
        try:
            await asyncio.to_thread(
                update_broadcast_job, job_id,
                cursor=cursor,
                sent=base_ok + counters["ok"],
                blocked=base_blocked + counters["blocked"],
                failed=base_failed + counters["failed"],
            )
        except Exception:
            logger.exception("Failed to checkpoint broadcast")
        await render(cursor)

    try:
        await asyncio.to_thread(
            update_broadcast_job, job_id,
            cursor=cursor, sent=base_ok + counters["ok"],
            blocked=base_blocked + counters["blocked"],
            failed=base_failed + counters["failed"],
            status="done",
        )
    except Exception:
        logger.exception("Failed to mark broadcast complete")
    await render(cursor, final=True)
    logger.info("[broadcast] done job=%s ok=%d blocked=%d failed=%d flood=%d/%.0fs",
                job_id, counters["ok"], counters["blocked"], counters["failed"],
                counters["flood_waits"], counters["flood_secs"])


async def broadcast_receive(update: Update, _context: ContextTypes.DEFAULT_TYPE):
    """Админ переслал боту пост — предлагаем разослать."""
    admin_id = update.effective_user.id
    if admin_id not in ADMIN_IDS:
        return
    msg = update.effective_message
    _BROADCAST_PENDING[admin_id] = {
        "chat_id": update.effective_chat.id,
        "message_id": msg.message_id,
        "sending": False,
    }
    try:
        n = len(await asyncio.to_thread(get_all_bot_user_ids))
        n_str = str(n)
    except Exception:
        logger.exception("Failed to count broadcast recipients")
        n_str = "?"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🧪 Проверить на себе", callback_data="bc:test")],
        [InlineKeyboardButton(f"📢 Разослать всем ({n_str})", callback_data="bc:send")],
        [InlineKeyboardButton("❌ Отмена", callback_data="bc:cancel")],
    ])
    await msg.reply_text(
        "📨 <b>Пост получен для рассылки.</b>\n\n"
        f"Аудитория: <b>{n_str}</b> пользователей.\n"
        "Перешлётся 1-в-1: картинка, форматирование, эмодзи и ссылка на канал "
        "(плашка «Переслано из…»).\n\n"
        "⚠️ Действие необратимо. Сначала проверь на себе.",
        parse_mode="HTML",
        reply_markup=kb,
    )


async def broadcast_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Кнопки подтверждения рассылки (bc:test / bc:send / bc:cancel)."""
    q = update.callback_query
    admin_id = q.from_user.id
    if admin_id not in ADMIN_IDS:
        await q.answer("Нет доступа", show_alert=True)
        return

    pending = _BROADCAST_PENDING.get(admin_id)
    if not pending:
        await q.answer("Пост устарел — перешли его боту заново.", show_alert=True)
        try:
            await q.edit_message_reply_markup(reply_markup=None)
        except Exception:
            pass
        return

    action = (q.data or "bc:").split(":", 1)[1]

    if action == "cancel":
        _BROADCAST_PENDING.pop(admin_id, None)
        await q.answer("Отменено")
        try:
            await q.edit_message_text("❌ Рассылка отменена.")
        except Exception:
            pass
        return

    if action == "test":
        await q.answer("Отправляю тебе…")
        try:
            await context.bot.forward_message(
                chat_id=admin_id,
                from_chat_id=pending["chat_id"],
                message_id=pending["message_id"],
            )
        except Exception as e:
            await context.bot.send_message(admin_id, f"Не удалось переслать: {e}")
        return

    if action == "send":
        if pending.get("sending"):
            await q.answer("Рассылка уже идёт", show_alert=True)
            return
        pending["sending"] = True
        await q.answer("Запускаю рассылку")
        try:
            user_ids = await asyncio.to_thread(get_all_bot_user_ids)
        except Exception as e:
            logger.exception("Failed to load broadcast recipients")
            _BROADCAST_PENDING.pop(admin_id, None)
            try:
                await q.edit_message_text(f"Не удалось получить список пользователей: {e}")
            except Exception:
                pass
            return

        # Создаём запись job (для чекпоинта/resume) и фиксируем координаты
        # сообщения с прогрессом, чтобы /broadcast_resume мог его редактировать.
        status_msg = q.message
        try:
            job_id = await asyncio.to_thread(
                create_broadcast_job, admin_id,
                pending["chat_id"], pending["message_id"], len(user_ids),
            )
            await asyncio.to_thread(
                update_broadcast_job, job_id, cursor=0, sent=0, blocked=0, failed=0,
                status_chat_id=status_msg.chat_id, status_message_id=status_msg.message_id,
            )
        except Exception as e:
            logger.exception("Failed to create broadcast job")
            await q.edit_message_text(f"Не удалось создать задачу рассылки: {e}")
            _BROADCAST_PENDING.pop(admin_id, None)
            return

        try:
            await status_msg.edit_text(
                f"⏳ Рассылка запущена для {len(user_ids)} пользователей…\n"
                f"~{_BROADCAST_RATE:.0f}/сек · ETA ~{int(len(user_ids) / max(_BROADCAST_RATE,1) // 60)} мин"
            )
        except Exception:
            pass

        _BROADCAST_PENDING.pop(admin_id, None)
        await _do_broadcast(context, job_id, pending["chat_id"], pending["message_id"],
                            user_ids, 0, status_msg)
        return


async def broadcast_resume_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Возобновляет прерванную рассылку с места чекпоинта (только админ)."""
    admin_id = update.effective_user.id
    if admin_id not in ADMIN_IDS:
        return

    job = await asyncio.to_thread(get_active_broadcast_job)
    if not job:
        await update.message.reply_text("Нет прерванной рассылки для возобновления.")
        return

    try:
        user_ids = await asyncio.to_thread(get_all_bot_user_ids)
    except Exception as e:
        logger.exception("Failed to resume broadcast recipients")
        await update.message.reply_text(f"Не удалось получить список пользователей: {e}")
        return

    start_cursor = min(max(job["cursor"], 0), len(user_ids))
    remaining = len(user_ids) - start_cursor
    if remaining <= 0:
        await asyncio.to_thread(update_broadcast_job, job["id"],
                                cursor=start_cursor, sent=job["sent"],
                                blocked=job["blocked"], failed=job["failed"],
                                status="done")
        await update.message.reply_text("Рассылка уже была завершена.")
        return

    status_msg = await update.message.reply_text(
        f"▶️ Возобновляю: обработано {start_cursor}/{len(user_ids)}, "
        f"осталось {remaining}…"
    )
    try:
        await asyncio.to_thread(
            update_broadcast_job, job["id"], cursor=start_cursor,
            sent=job["sent"], blocked=job["blocked"], failed=job["failed"],
            status="running", status_chat_id=status_msg.chat_id,
            status_message_id=status_msg.message_id,
        )
    except Exception:
        logger.exception("Failed to update resumed broadcast")

    await _do_broadcast(
        context, job["id"], job["src_chat_id"], job["src_message_id"],
        user_ids, start_cursor, status_msg,
        base_ok=job["sent"], base_blocked=job["blocked"], base_failed=job["failed"],
    )


async def _notify_interrupted_broadcast(application: Application) -> None:
    """При старте: если осталась незавершённая рассылка — пингуем админов."""
    try:
        job = await asyncio.to_thread(get_active_broadcast_job)
    except Exception:
        return
    if not job:
        return
    done = job["cursor"]
    total = job["total"] or 0
    msg = (
        "⚠️ <b>Найдена прерванная рассылка</b>\n\n"
        f"Обработано: {done}/{total}\n"
        f"✅ {job['sent']} · 🚫 {job['blocked']} · ⚠️ {job['failed']}\n\n"
        "Отправь /broadcast_resume чтобы продолжить с этого места."
    )
    for aid in ADMIN_IDS:
        try:
            await application.bot.send_message(chat_id=aid, text=msg, parse_mode="HTML")
        except Exception:
            pass


async def _on_startup(application: Application) -> None:
    """post_init: меню команд + пинг админам, если осталась прерванная рассылка."""
    await _set_commands(application)
    await _notify_interrupted_broadcast(application)


async def _set_commands(application: Application) -> None:
    """Registers the visible command menu shown when the user types / in Telegram."""
    # Keep the persistent chat menu as a command list. A WebApp menu button
    # opens the app without passing through /start and therefore bypasses the
    # two-channel subscription gate. Setting this explicitly also replaces
    # any attacker-controlled menu left after a bot-token compromise.
    await application.bot.set_chat_menu_button(
        menu_button=MenuButtonCommands()
    )
    await application.bot.set_my_commands([
        BotCommand("start",      "Открыть мини‑приложение"),
        BotCommand("news",       "Уведомления об обновлениях Dota 2"),
        BotCommand("counters",   "Контрпики для любого героя"),
        BotCommand("synergy",    "Синергии союзников для любого героя"),
        BotCommand("last_quiz",  "Последний результат квиза по позициям"),
        BotCommand("hero_quiz",  "Рекомендованные герои из последнего квиза"),
        BotCommand("feedback",   "Предложить улучшения мини‑аппа"),
        BotCommand("help",       "Показать список команд"),
    ])


def main():
    logging.basicConfig(
        format="%(asctime)s.%(msecs)03d %(levelname)-8s %(name)s %(message)s",
        datefmt="%H:%M:%S",
        level=logging.INFO,
    )
    configure_secure_logging(BOT_TOKEN, os.environ.get("DATABASE_URL"))
    init_tokens_table()
    print("🤖 Бот запускается...")

    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN не найден. Проверь файл .env")

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .concurrent_updates(True)
        .post_init(_on_startup)
        .build()
    )

    application.add_handler(CommandHandler("start",      logged_event("bot_start")(timed_handler("/start")(start))))
    application.add_handler(CommandHandler("help",       logged_event("bot_help")(timed_handler("/help")(help_command))))
    application.add_handler(CommandHandler("last_quiz",  logged_event("bot_quiz_last")(timed_handler("/last_quiz")(last_quiz_command))))
    application.add_handler(CommandHandler("hero_quiz",  logged_event("bot_quiz_hero")(timed_handler("/hero_quiz")(hero_quiz_command))))
    application.add_handler(CommandHandler("counters",   logged_event("bot_counters")(timed_handler("/counters")(counters_command))))
    application.add_handler(CommandHandler("synergy",    logged_event("bot_synergy")(timed_handler("/synergy")(synergy_command))))
    application.add_handler(CommandHandler("news",            logged_event("bot_news")(timed_handler("/news")(news_command))))
    application.add_handler(CommandHandler("feedback",       logged_event("bot_feedback")(timed_handler("/feedback")(feedback_command))))
    application.add_handler(CommandHandler("admin_feedback", timed_handler("/admin_feedback")(admin_feedback_command)))
    application.add_handler(CommandHandler("admin_users",    timed_handler("/admin_users")(admin_users_command)))
    application.add_handler(CommandHandler("admin_matches",  timed_handler("/admin_matches")(admin_matches_command)))
    application.add_handler(CommandHandler("tm_stats",       timed_handler("/tm_stats")(tm_stats_command)))
    application.add_handler(CommandHandler("analytics",      timed_handler("/analytics")(analytics_command)))
    application.add_handler(CommandHandler("stats_mode",          timed_handler("/stats_mode")(stats_mode_command)))
    application.add_handler(CommandHandler("force_update_builds", timed_handler("/force_update_builds")(force_update_builds_command)))
    application.add_handler(CommandHandler("topdraft",            timed_handler("/topdraft")(topdraft_command)))
    application.add_handler(CommandHandler("ban",                 timed_handler("/ban")(ban_command)))
    application.add_handler(CommandHandler("unban",               timed_handler("/unban")(unban_command)))
    application.add_handler(CommandHandler("broadcast_resume",    timed_handler("/broadcast_resume")(broadcast_resume_command)))

    # Рассылка: админ пересылает боту пост из канала → подтверждение → forward
    # всем. Регистрируем ПЕРЕД admin-text и catch-all, чтобы пересланный пост
    # (в т.ч. текстовый) ловился именно здесь.
    application.add_handler(
        MessageHandler(
            filters.FORWARDED & filters.ChatType.PRIVATE
            & filters.User(user_id=list(ADMIN_IDS)),
            timed_handler("broadcast_receive")(broadcast_receive),
        )
    )
    application.add_handler(CallbackQueryHandler(broadcast_callback, pattern=r"^bc:"))

    # Admin-команды редактирования текстов бота — ConversationHandler +
    # side-команды. Регистрируется ПЕРЕД общим MessageHandler ниже, чтобы
    # ответы в conversation-state ловились раньше catch-all'а.
    from backend.bot_admin_texts import register_admin_text_handlers
    register_admin_text_handlers(application, ADMIN_IDS)

    # Текстовые сообщения — должны идти ПОСЛЕ команд (меньший приоритет)
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, timed_handler("text")(handle_text_message))
    )

    application.add_error_handler(error_handler)

    print("✅ Бот запущен! Открой Telegram и напиши боту /start")
    application.run_polling(
        allowed_updates=Update.ALL_TYPES,
        # A stolen token can be used to install an attacker-controlled webhook.
        # Polling deletes it during bootstrap; queued updates from the compromise
        # window must not execute after token rotation.
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()
