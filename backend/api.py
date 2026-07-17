import asyncio
import hashlib
import hmac
import json
import logging
import os
import random
import threading
import time
import httpx
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qsl

logger = logging.getLogger(__name__)

# ── In-memory caches ──────────────────────────────────────────────────────────
# /api/meta result — recomputed at most once per hour
META_CACHE_TTL = 3600
_meta_cache: dict | None = None
_meta_cache_time: float = 0

# dota_builds.json raw content — file is large; read once per process lifetime
_dota_builds_file_cache: dict | None = None

# hero_matchups.json — read once per process lifetime
_hero_matchups_file_cache: dict | None = None

# hero_matchups.json — raw JSON bytes, used by /api/draft/matchups_all to avoid
# re-serializing the 2.4 MB dict on every request (jsonable_encoder + json.dumps
# on this blob takes ~4 s per call). The endpoint just proxies the file as-is,
# so we serve the raw bytes directly.
_hero_matchups_json_bytes: bytes | None = None

# draft_matches.json — read once per process lifetime
_draft_matches_file_cache: list | None = None

# /api/hero/{hero_id}/build — full response per hero, TTL 30 min
# Stores pre-serialized JSON strings (not dicts) to skip jsonable_encoder +
# json.dumps on every cache hit (~3.5 s per call on this payload).
BUILD_CACHE_TTL = 1800
_build_cache: dict[int, tuple[float, str]] = {}  # {hero_id: (timestamp, json_str)}

# /api/draft/leaderboard — TTL 5 min
_leaderboard_cache: list | None = None
_leaderboard_cache_ts: float = 0.0

# /api/draft/evaluate — rate limiting: max 30 requests per 10 min per user_id
# Uses SQLite (shared across all uvicorn workers) instead of in-memory dict.
_EVALUATE_RL_WINDOW = 600   # seconds
_EVALUATE_RL_LIMIT  = 30


def _init_rl_table() -> None:
    """Create rate_limit_evaluate table if it doesn't exist."""
    from sqlalchemy import text as _text
    with engine.begin() as conn:
        conn.execute(_text("""
            CREATE TABLE IF NOT EXISTS rate_limit_evaluate (
                user_id   INTEGER NOT NULL,
                ts        REAL    NOT NULL
            )
        """))
        conn.execute(_text(
            "CREATE INDEX IF NOT EXISTS idx_rle_user_ts ON rate_limit_evaluate(user_id, ts)"
        ))


def _rl_check_and_record(user_id: int) -> tuple[bool, int]:
    """Returns (allowed, current_count).

    Uses SQLite as shared store so all uvicorn workers see the same counters.
    Deletes expired rows for this user, counts remaining, inserts new row.
    All in one BEGIN…COMMIT so concurrent workers don't race.
    """
    from sqlalchemy import text as _text
    now = time.time()
    window_start = now - _EVALUATE_RL_WINDOW
    with engine.begin() as conn:
        # Clean up expired rows for this user
        conn.execute(_text(
            "DELETE FROM rate_limit_evaluate WHERE user_id = :uid AND ts <= :ws"
        ), {"uid": user_id, "ws": window_start})
        # Count remaining rows in window
        row = conn.execute(_text(
            "SELECT COUNT(*) FROM rate_limit_evaluate WHERE user_id = :uid"
        ), {"uid": user_id}).fetchone()
        count = row[0] if row else 0
        if count >= _EVALUATE_RL_LIMIT:
            return False, count
        # Record this request
        conn.execute(_text(
            "INSERT INTO rate_limit_evaluate (user_id, ts) VALUES (:uid, :ts)"
        ), {"uid": user_id, "ts": now})
        return True, count + 1

# /api/check-subscription — TTL 600s per user_id
_subscription_cache: dict[int, float] = {}


def _load_dota_builds_file() -> dict | None:
    """Return parsed dota_builds.json, caching the result in memory."""
    global _dota_builds_file_cache
    if _dota_builds_file_cache is not None:
        return _dota_builds_file_cache
    builds_path = Path(__file__).resolve().parent.parent / "dota_builds.json"
    if not builds_path.exists():
        return None
    try:
        with open(builds_path, encoding="utf-8") as f:
            _dota_builds_file_cache = json.load(f)
    except Exception as e:
        logger.warning("[dota_builds] Failed to read dota_builds.json: %s", e)
        return None
    return _dota_builds_file_cache


def _load_hero_matchups_file() -> dict | None:
    """Return parsed hero_matchups.json, caching the result in memory."""
    global _hero_matchups_file_cache
    if _hero_matchups_file_cache is not None:
        return _hero_matchups_file_cache
    path = Path(__file__).resolve().parent.parent / "hero_matchups.json"
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            _hero_matchups_file_cache = json.load(f)
    except Exception as e:
        logger.warning("[hero_matchups] Failed to read hero_matchups.json: %s", e)
        return None
    return _hero_matchups_file_cache


def _load_hero_matchups_bytes() -> bytes | None:
    """Return raw hero_matchups.json bytes for endpoints that proxy the file as-is."""
    global _hero_matchups_json_bytes
    if _hero_matchups_json_bytes is not None:
        return _hero_matchups_json_bytes
    path = Path(__file__).resolve().parent.parent / "hero_matchups.json"
    if not path.exists():
        return None
    try:
        _hero_matchups_json_bytes = path.read_bytes()
    except Exception as e:
        logger.warning("[hero_matchups] Failed to read hero_matchups.json bytes: %s", e)
        return None
    return _hero_matchups_json_bytes


def _load_draft_matches_file() -> list | None:
    """Return parsed draft_matches.json, caching the result in memory."""
    global _draft_matches_file_cache
    if _draft_matches_file_cache is not None:
        return _draft_matches_file_cache
    path = Path(__file__).resolve().parent.parent / "draft_matches.json"
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as f:
            _draft_matches_file_cache = json.load(f)
    except Exception as e:
        logger.warning("[draft_matches] Failed to read draft_matches.json: %s", e)
        return None
    return _draft_matches_file_cache

# ─────────────────────────────────────────────────────────────────────────────


from fastapi import FastAPI, HTTPException, Depends, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from pydantic import BaseModel


from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified


# --- Shared DB layer (единая точка подключения) ---
from backend.database import get_db, create_all_tables, engine
from backend.models import BannedUser as DBBannedUser, UserProfile as DBUserProfile, QuizResult as DBQuizResult, DraftResult as DBDraftResult
from backend.db import get_user_id_by_token, create_token_for_user, init_tokens_table, init_hero_matchups_cache_table, save_feedback, get_latest_news_guids, is_user_banned, get_banned_user_ids
from backend.hero_matchups_service import get_hero_matchups_cached, build_matchup_groups
from backend.hero_stats_service import get_hero_base_winrate
from backend.stats_db import (
    init_stats_tables,
    get_hero_matchup_rows,
    get_hero_synergy_rows,
    get_hero_base_winrate_from_db,
    get_hero_total_games,
    get_stats_mode,
    get_hero_ability_build,
    get_hero_talent_builds,
    get_hero_build_cache,
    get_app_cache_value,
    set_hero_build_cache,
    get_latest_match_patch,
)
from backend.config import BAYESIAN_SMOOTHING_C


BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHECK_CHAT_ID = os.environ.get("CHECK_CHAT_ID")  # chat_id канала для проверки


if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")
if not CHECK_CHAT_ID:
    raise RuntimeError("CHECK_CHAT_ID is not set")


# --- DB init (idempotent; Alembic is the authoritative source for PostgreSQL) ---
# Раньше тут было два вызова: create_all_tables() явно + init_stats_tables(),
# который сам внутри зовёт create_all_tables(). При 4 uvicorn-воркерах это
# давало 8 одновременных проходов startup-миграций → на PostgreSQL мы регулярно
# ловили дедлоки на user_profiles (см. database.py:create_all_tables).
# Оставлен только init_stats_tables — он гарантированно зовёт create_all_tables
# первым шагом, плюс делает свои миграции по stats-таблицам.
init_stats_tables()
_init_rl_table()          # rate limiting table for /api/draft/evaluate
# --- DB init end ---

# Warm up file-backed caches so the first request to each worker doesn't pay the
# cold-start cost (file read + parse). Each uvicorn worker runs this once.
_load_hero_matchups_bytes()
_load_hero_matchups_file()


# Production: uvicorn backend.api:app --workers 4 --timeout-keep-alive 30
app = FastAPI(title="Dota Mini App Backend")


# CORS нужен, чтобы фронтенд (мини-ап) мог вызывать этот API из браузера.
# Для продакшена лучше сузить allow_origins до домена мини-апа.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# GZip не должен трогать image-ответы: фетчер Telegram при отправке inline-фото
# не разжимает gzip и сохраняет битые байты (чёрный квадрат, фото не доходит).
# Starlette исключает типы из DEFAULT_EXCLUDED_CONTENT_TYPES (читается из модуля
# в момент ответа) — расширяем его на image/*, чтобы картинки шли БЕЗ сжатия и
# без нестандартного заголовка Content-Encoding.
import starlette.middleware.gzip as _gzip_mod
if "image/" not in _gzip_mod.DEFAULT_EXCLUDED_CONTENT_TYPES:
    _gzip_mod.DEFAULT_EXCLUDED_CONTENT_TYPES = (
        _gzip_mod.DEFAULT_EXCLUDED_CONTENT_TYPES + ("image/",)
    )

app.add_middleware(GZipMiddleware, minimum_size=1024)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Логирует каждый HTTP-запрос: метод, путь, статус, время выполнения."""
    t0 = time.monotonic()
    response = await call_next(request)
    ms = (time.monotonic() - t0) * 1000
    logger.info(
        "[%s] %s %s %d %.0fms",
        datetime.now().strftime("%H:%M:%S.%f")[:-3],
        request.method,
        request.url.path,
        response.status_code,
        ms,
    )
    return response



# ========== Pydantic Models ==========

class CheckRequest(BaseModel):
    token: str  # одноразовый токен из URL мини-апа


class CheckResponse(BaseModel):
    allowed: bool


class SaveResultRequest(BaseModel):
    token: str
    result: dict


class SaveResultResponse(BaseModel):
    success: bool


class GetResultResponse(BaseModel):
    result: dict | None


class Profile(BaseModel):
    user_id: int
    favorite_heroes: list[str] = []
    settings: dict = {}


class UserStats(BaseModel):
    """Статистика пользователя для профиля"""
    user_id: int
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    photo_url: str | None = None
    total_quizzes: int = 0
    last_quiz_date: str | None = None
    quiz_history: list[dict] = []  # последние 5-10 квизов


class TelegramUserData(BaseModel):
    """Данные пользователя из Telegram Web App"""
    token: str
    username: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    photo_url: str | None = None


class RefreshTokenRequest(BaseModel):
    """Silent token refresh через валидный Telegram WebApp initData."""
    init_data: str


class RefreshTokenResponse(BaseModel):
    token: str


# ── Telegram WebApp initData validation ───────────────────────────────────
# Максимальный возраст auth_date в initData (защита от replay).
_INIT_DATA_MAX_AGE_SECONDS = 86400  # 24 часа


def _validate_telegram_init_data(init_data: str, bot_token: str) -> dict | None:
    """Проверяет HMAC-подпись initData по схеме из документации Telegram.
    Возвращает словарь параметров при успехе или None при ошибке."""
    if not init_data:
        return None
    try:
        pairs = parse_qsl(init_data, keep_blank_values=True)
    except ValueError:
        return None

    params = dict(pairs)
    received_hash = params.pop("hash", None)
    if not received_hash:
        return None

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(params.items()))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    computed_hash = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        return None

    try:
        auth_date = int(params.get("auth_date", "0"))
    except ValueError:
        return None
    if auth_date <= 0 or (time.time() - auth_date) > _INIT_DATA_MAX_AGE_SECONDS:
        return None

    return params



# ========== API Endpoints ==========

@app.post("/api/refresh_token", response_model=RefreshTokenResponse)
async def refresh_token(data: RefreshTokenRequest):
    """Выдаёт новый токен по валидному Telegram WebApp initData.
    Нужен для silent refresh когда старый токен истёк (24ч),
    чтобы пользователю не приходилось заново нажимать /start в боте."""
    params = _validate_telegram_init_data(data.init_data, BOT_TOKEN)
    if params is None:
        raise HTTPException(status_code=401, detail="Invalid initData signature")

    user_json = params.get("user")
    if not user_json:
        raise HTTPException(status_code=401, detail="No user in initData")

    try:
        user_payload = json.loads(user_json)
        user_id = int(user_payload["id"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid user payload")

    new_token = await asyncio.to_thread(create_token_for_user, user_id)
    return RefreshTokenResponse(token=new_token)


@app.post("/api/check-subscription", response_model=CheckResponse)
async def check_subscription(data: CheckRequest):
    """Проверяет подписку пользователя на канал"""
    global _subscription_cache

    # 1. по токену достаём user_id
    user_id = get_user_id_by_token(data.token)
    if not user_id:
        return CheckResponse(allowed=False)

    # 2. кеш: если подписка уже подтверждена менее 600 сек назад — не идём в Telegram
    cached_ts = _subscription_cache.get(user_id)
    if cached_ts is not None and time.time() - cached_ts < 600:
        return CheckResponse(allowed=True)

    # 3. проверяем подписку через getChatMember
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember"
    params = {"chat_id": CHECK_CHAT_ID, "user_id": user_id}

    async with httpx.AsyncClient() as client:
        r = await client.get(url, params=params)

    if r.status_code != 200:
        raise HTTPException(status_code=500, detail="Telegram API error")

    result = r.json().get("result", {})
    status = result.get("status")

    allowed_statuses = {"member", "administrator", "creator"}
    allowed = status in allowed_statuses

    if allowed:
        _subscription_cache[user_id] = time.time()
    else:
        _subscription_cache.pop(user_id, None)

    return CheckResponse(allowed=allowed)


@app.post("/api/save_telegram_data")
def save_telegram_data(data: TelegramUserData, db: Session = Depends(get_db)):
    """Сохраняет данные пользователя из Telegram (имя, username, фото)"""
    user_id = get_user_id_by_token(data.token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Обновляем профиль
    db_profile = db.query(DBUserProfile).filter(DBUserProfile.user_id == user_id).first()
    if not db_profile:
        db_profile = DBUserProfile(
            user_id=user_id,
            favorite_heroes=[],
            settings={}
        )
        db.add(db_profile)

    # Сохраняем данные Telegram в settings
    if not db_profile.settings:
        db_profile.settings = {}

    # НЕ затираем существующие значения пустыми: Telegram WebApp не всегда
    # отдаёт username/фото в initDataUnsafe (приватность/клиент) — раньше
    # приходящий null стирал валидный username, сохранённый на /start, и
    # пуши «Пати» уходили без контакта.
    if data.username:
        db_profile.settings["username"] = data.username
    if data.first_name:
        db_profile.settings["first_name"] = data.first_name
    if data.last_name:
        db_profile.settings["last_name"] = data.last_name
    if data.photo_url:
        db_profile.settings["photo_url"] = data.photo_url
    flag_modified(db_profile, "settings")

    db.commit()
    return {"success": True}


@app.get("/api/profile_full", response_model=UserStats)
def get_profile_full(token: str, db: Session = Depends(get_db)):
    """Получает полный профиль пользователя с историей квизов"""
    # 1. Проверяем токен
    user_id = get_user_id_by_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    # 2. Получаем профиль из БД
    db_profile = db.query(DBUserProfile).filter(DBUserProfile.user_id == user_id).first()
    if not db_profile:
        db_profile = DBUserProfile(
            user_id=user_id,
            favorite_heroes=[],
            settings={}
        )
        db.add(db_profile)
        db.commit()
        db.refresh(db_profile)
    
    # 3. Получаем историю квизов
    quiz_results = db.query(DBQuizResult)\
        .filter(DBQuizResult.user_id == user_id)\
        .order_by(DBQuizResult.updated_at.desc())\
        .limit(10)\
        .all()
    
    # 4. Формируем историю (НОВЫЙ формат)
    quiz_history = []
    for quiz in quiz_results:
        base_date = quiz.updated_at.isoformat() if quiz.updated_at else None
        res = quiz.result or {}

        if isinstance(res, dict):
            # Новый формат: position_quiz + hero_quiz_by_position
            combined_result = {}

            position_res = res.get("position_quiz")
            if position_res:
                combined_result["position_quiz"] = position_res

            # Новый формат: hero_quiz_by_position (словарь по позициям)
            hero_by_pos = res.get("hero_quiz_by_position")
            if hero_by_pos:
                combined_result["hero_quiz_by_position"] = hero_by_pos

            # Legacy fallback (will disappear after full migration)
            if not combined_result:
                # Старый формат — просто один объект с type в корне
                if "type" in res:
                    combined_result = res

            if combined_result:
                quiz_history.append({
                    "date": base_date,
                    "result": combined_result
                })

    # 5. Извлекаем данные Telegram из settings
    settings = db_profile.settings or {}

    return UserStats(
        user_id=user_id,
        username=settings.get("username"),
        first_name=settings.get("first_name"),
        last_name=settings.get("last_name"),
        photo_url=settings.get("photo_url"),
        total_quizzes=len(quiz_results),
        last_quiz_date=quiz_results[0].updated_at.isoformat() if quiz_results and quiz_results[0].updated_at else None,
        quiz_history=quiz_history
    )


@app.post("/api/save_result", response_model=SaveResultResponse)
def save_result(data: SaveResultRequest, db: Session = Depends(get_db)):
    """Сохраняет результат квиза (позиции и герои в одном JSON)"""
    user_id = get_user_id_by_token(data.token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Профиль для FK
    db_user_profile = db.query(DBUserProfile).filter(DBUserProfile.user_id == user_id).first()
    if not db_user_profile:
        db_user_profile = DBUserProfile(
            user_id=user_id,
            favorite_heroes=[],
            settings={}
        )
        db.add(db_user_profile)
        db.commit()
        db.refresh(db_user_profile)

    # Определяем тип квиза
    result_type = None
    if isinstance(data.result, dict):
        result_type = data.result.get("type")

    # Достаём существующий агрегированный результат.
    # with_for_update() ставит row-level lock на PostgreSQL: конкурентный запрос
    # от того же юзера заблокируется до коммита текущей транзакции и прочитает
    # уже обновлённые данные. На SQLite игнорируется (dev-only).
    db_quiz_result = (
        db.query(DBQuizResult)
        .filter(DBQuizResult.user_id == user_id)
        .with_for_update()
        .first()
    )

    if db_quiz_result and isinstance(db_quiz_result.result, dict):
        combined_result = dict(db_quiz_result.result)
    else:
        combined_result = {}

    # Обновляем только нужную часть в НОВОМ формате
    if result_type == "position_quiz":
        combined_result["position_quiz"] = data.result
        # Чистим legacy верхнеуровневые ключи
        for legacy_key in ["type", "position", "posShort", "positionIndex", "date", "isPure", "extraPos"]:
            combined_result.pop(legacy_key, None)

    elif result_type == "hero_quiz":
        hero_position_index = data.result.get("heroPositionIndex")
        if hero_position_index is not None:
            if "hero_quiz_by_position" not in combined_result:
                combined_result["hero_quiz_by_position"] = {}
            combined_result["hero_quiz_by_position"][str(hero_position_index)] = data.result
            # Чистим legacy hero_quiz (если был)
            combined_result.pop("hero_quiz", None)
        else:
            logger.warning("[save_result] hero_quiz without heroPositionIndex for user %s", user_id)
    else:
        # Неизвестный тип — не трогаем данные
        logger.warning("[save_result] unknown result.type=%r for user %s", result_type, user_id)
        return SaveResultResponse(success=True)

    if db_quiz_result:
        db_quiz_result.result = combined_result
        db_quiz_result.updated_at = datetime.now(timezone.utc)
        flag_modified(db_quiz_result, "result")
    else:
        db_quiz_result = DBQuizResult(
            user_id=user_id,
            result=combined_result,
            updated_at=datetime.now(timezone.utc)
        )
        db.add(db_quiz_result)

    # Обновляем favorite_heroes для профиля, если это геройский квиз
    try:
        if result_type == "hero_quiz":
            top_heroes = data.result.get("topHeroes") or []
            hero_names = [
                h.get("name") if isinstance(h, dict) else h
                for h in top_heroes
                if h
            ]
            if hero_names:
                db_user_profile.favorite_heroes = hero_names
                flag_modified(db_user_profile, "favorite_heroes")
    except Exception as e:
        logger.warning("[save_result] failed to update favorite_heroes for user %s: %s", user_id, e)

    db.commit()
    db.refresh(db_quiz_result)

    return SaveResultResponse(success=True)


@app.get("/api/get_result", response_model=GetResultResponse)
def get_result(token: str, db: Session = Depends(get_db)):
    """Получает результат квиза по токену"""
    user_id = get_user_id_by_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    db_quiz_result = db.query(DBQuizResult).filter(DBQuizResult.user_id == user_id).first()
    if db_quiz_result:
        return GetResultResponse(result=db_quiz_result.result)
    return GetResultResponse(result=None)

# ========== Hero Matchups ==========

@app.get("/api/hero_matchups")
async def api_hero_matchups(hero_id: int):
    """Возвращает матчапы героя, сгруппированные по strong_against / weak_against.

    Формат ответа:
    {
      "hero_id": 1,
      "strong_against": [{"opponent_hero_id": 18, "games": 560, "wins": 350, "winrate": 0.625, "updated_at": "..."}],
      "weak_against":   [{"opponent_hero_id": 33, "games": 530, "wins": 100, "winrate": 0.1886, "updated_at": "..."}]
    }

    TODO: Consider migrating callers to /api/hero/{hero_id}/counters, which uses
    our own match data instead of OpenDota aggregates and produces more reliable results.
    """
    if hero_id <= 0:
        raise HTTPException(status_code=400, detail="hero_id must be a positive integer")

    try:
        matchups = await get_hero_matchups_cached(hero_id)
    except Exception as e:
        logger.warning("[matchups] Failed for hero_id=%s: %s", hero_id, e)
        raise HTTPException(status_code=502, detail="Failed to fetch hero matchups")

    base_wr = await get_hero_base_winrate(hero_id)
    groups = build_matchup_groups(matchups, base_wr)
    logger.info(
        "[matchups api] hero_id=%s strong=%d weak=%d",
        hero_id,
        len(groups.get("strong_against", [])),
        len(groups.get("weak_against", [])),
    )
    return {
        "hero_id": hero_id,
        "strong_against": groups["strong_against"],
        "weak_against": groups["weak_against"],
    }


# ========== Custom Stats: counters from our own match data ==========

@app.get("/api/hero/{hero_id}/counters")
def api_hero_counters(
    hero_id: int,
    limit: int = Query(default=20, ge=1, le=200, description="Max entries in counters/victims lists"),
    min_games: int = Query(default=50, ge=1, description="Minimum games for a pair to be included"),
):
    """Returns hero counters and victims computed from our own match database.

    Unlike /api/hero_matchups (which proxies OpenDota aggregates), this endpoint
    uses matches collected by stats_updater.py and stored locally.

    Response format:
    {
      "hero_id": 1,
      "base_winrate": 0.51,
      "data_games": 15000,        // total games this hero appears in our DB
      "counters": [               // heroes that beat this hero (advantage < 0)
        { "hero_id": 99, "games": 320, "wr_vs": 0.40, "advantage": -0.11 },
        ...                       // sorted ascending by advantage (worst first)
      ],
      "victims": [                // heroes this hero beats (advantage > 0)
        { "hero_id": 53, "games": 280, "wr_vs": 0.62, "advantage": 0.11 },
        ...                       // sorted descending by advantage (best first)
      ]
    }

    Data source: hero_matchups.json (Stratz aggregates), key "vs".
    """
    if hero_id <= 0:
        raise HTTPException(status_code=400, detail="hero_id must be a positive integer")
    # Единый источник с ботом /counters — backend/hero_pairs.py (та же логика).
    from backend.hero_pairs import get_hero_counters
    return get_hero_counters(hero_id, limit=limit, min_games=min_games)


# ========== Custom Stats: ally synergy from our own match data ==========

@app.get("/api/hero/{hero_id}/synergy")
def api_hero_synergy(
    hero_id: int,
    limit: int = Query(default=20, ge=1, le=200, description="Max entries in best/worst allies lists"),
    min_games: int = Query(default=50, ge=1, description="Minimum shared games for a pair to be included"),
):
    """Returns best and worst allies for a hero computed from our own match database.

    Response format:
    {
      "hero_id": 1,
      "base_winrate": 0.51,
      "data_games": 15000,
      "best_allies": [
        { "hero_id": 42, "games": 280, "wins": 199, "wr_vs": 0.71, "delta": 0.20 },
        ...   // sorted descending by delta
      ],
      "worst_allies": [
        { "hero_id": 17, "games": 260, "wins": 113, "wr_vs": 0.43, "delta": -0.08 },
        ...   // sorted ascending by delta (worst first)
      ]
    }

    delta = wr_vs - base_winrate (in fraction, e.g. 0.12 means +12 pp).
    Data source: hero_matchups.json (Stratz aggregates), key "with".
    """
    if hero_id <= 0:
        raise HTTPException(status_code=400, detail="hero_id must be a positive integer")
    # Единый источник с ботом /synergy — backend/hero_pairs.py (та же логика).
    from backend.hero_pairs import get_hero_synergy
    return get_hero_synergy(hero_id, limit=limit, min_games=min_games)


# ========== Hero Build ==========

_STRATZ_TO_DOTA_POS: dict[str, str] = {
    "POSITION_1": "pos%201",
    "POSITION_2": "pos%202",
    "POSITION_3": "pos%203",
    "POSITION_4": "pos%204",
    "POSITION_5": "pos%205",
}
_DOTA_TO_STRATZ_POS: dict[str, str] = {v: k for k, v in _STRATZ_TO_DOTA_POS.items()}


def _dota_builds_positions(dota_builds: dict) -> list[dict]:
    """Return positions sorted by num_matches desc.

    Each entry: {"position": "POSITION_N", "matchCount": <int>,
                 "num_matches": <int>, "num_wins": <int>, "win_rate": <float>}.
    Uses position-level num_matches when present, falls back to summing sixslot.
    """
    result = []
    for dota_key, pos_data in dota_builds.items():
        stratz_key = _DOTA_TO_STRATZ_POS.get(dota_key)
        if not stratz_key:
            continue
        num_matches = pos_data.get("num_matches")
        if num_matches is None:
            num_matches = sum(e.get("num_matches", 0) for e in (pos_data.get("sixslot") or []))
        result.append({
            "position":    stratz_key,
            "matchCount":  num_matches,
            "num_matches": num_matches,
            "num_wins":    pos_data.get("num_wins"),
            "win_rate":    pos_data.get("win_rate"),
        })
    result.sort(key=lambda x: x["matchCount"], reverse=True)
    return result


def _resolve_dota_builds(
    dota_builds: dict,
    top_position: str | None,
    items_db: dict,
) -> tuple[list[str], list[dict], list[dict], list[dict]]:
    """Return (ability_build, talents, core_items, start_game_items) from dota_builds data.

    Returns four empty lists when top_position is unknown or data is missing.
    """
    dota_pos_key = _STRATZ_TO_DOTA_POS.get(top_position or "") if top_position else None
    pos_data = dota_builds.get(dota_pos_key) if dota_pos_key else None
    if not pos_data:
        return [], [], [], []

    # Ability build — exclude talents (isTalent=True)
    ability_build: list[str] = [
        a["name"]
        for a in (pos_data.get("abilities") or [])
        if not a.get("isTalent", False) and a.get("name")
    ]

    # Talents — normalized format
    talents: list[dict] = [
        {
            "level":         t.get("lvl"),
            "left_ability":  (t.get("left") or {}).get("name", ""),
            "left_display":  (t.get("left") or {}).get("displayName", ""),
            "right_ability": (t.get("right") or {}).get("name", ""),
            "right_display": (t.get("right") or {}).get("displayName", ""),
            "choice":        t.get("choice", ""),
        }
        for t in (pos_data.get("talents") or [])
    ]

    # Core items — sixslot top-6 by pick_rate
    def _resolve_item(item_id: int) -> dict:
        info = items_db.get(str(item_id)) or {}
        return {"id": item_id, "dname": info.get("dname"), "img": info.get("img")}

    sixslot = sorted(
        pos_data.get("sixslot") or [],
        key=lambda x: x.get("pick_rate", 0),
        reverse=True,
    )[:6]
    core_items: list[dict] = [_resolve_item(e["item_id"]) for e in sixslot if "item_id" in e]

    # Start game items — first (most popular) starting set
    start_game_items: list[dict] = []
    starting = pos_data.get("starting_items") or []
    if starting:
        first_set = starting[0]
        if first_set and isinstance(first_set[0], list):
            start_game_items = [_resolve_item(iid) for iid in first_set[0]]

    return ability_build, talents, core_items, start_game_items


@app.get("/api/hero/{hero_id}/build")
def api_hero_build(hero_id: int):
    """Returns all data for the Build tab: facets, ability build, talents, items.

    When dota_builds is present in the cache (imported via import_dota_builds.py),
    ability_build / talents / items are sourced from dota2protracker data for the
    hero's most popular position (determined from stratz.ALL.positions).
    Falls back to the old logic (stratz + live DB) otherwise.
    """
    if hero_id <= 0:
        raise HTTPException(status_code=400, detail="hero_id must be a positive integer")

    # ── In-memory build cache ─────────────────────────────────────────────
    _cached_entry = _build_cache.get(hero_id)
    if _cached_entry is not None and (time.time() - _cached_entry[0]) < BUILD_CACHE_TTL:
        return Response(content=_cached_entry[1], media_type="application/json")

    # ── Static data from pre-built cache ─────────────────────────────────
    cached = get_hero_build_cache(hero_id)
    if cached is None:
        raise HTTPException(
            status_code=503,
            detail=(
                "Build data not yet available. "
                "The builds_updater will populate it on first run."
            ),
        )

    facets = cached.get("facets", [])
    items_db = get_app_cache_value("items_by_id") or {}

    # ── Determine most popular position ───────────────────────────────────
    dota_builds = cached.get("dota_builds")
    if not dota_builds:
        raw_file = _load_dota_builds_file()
        if raw_file:
            dota_builds = raw_file.get(str(hero_id))
    top_position: str | None = None
    if dota_builds:
        sorted_pos = _dota_builds_positions(dota_builds)
        top_position = sorted_pos[0]["position"] if sorted_pos else None
    else:
        stratz_raw = cached.get("stratz") or {}
        all_positions = (stratz_raw.get("ALL") or {}).get("positions") or []
        if all_positions:
            top_pos = max(all_positions, key=lambda p: p.get("matchCount", 0))
            top_position = top_pos.get("position")

    # ── dota_builds path (dota2protracker data) ───────────────────────────
    if dota_builds:
        ability_build, talents, core_items, start_game_items = _resolve_dota_builds(
            dota_builds, top_position, items_db
        )
        # Sorted list of dota-format position keys (pos%20N) by num_matches desc.
        # Included so the frontend doesn't have to derive order from dota_builds keys.
        dota_keys_sorted: list[str] = sorted(
            dota_builds.keys(),
            key=lambda k: (
                dota_builds[k].get("num_matches")
                or sum(e.get("num_matches", 0) for e in (dota_builds[k].get("sixslot") or []))
            ),
            reverse=True,
        )
        logger.info(
            "[build] hero_id=%s source=dota_builds top_pos=%s "
            "ability_build=%d talents=%d core_items=%d start_items=%d positions=%s",
            hero_id, top_position,
            len(ability_build), len(talents), len(core_items), len(start_game_items),
            dota_keys_sorted,
        )
        _response = {
            "facets":       facets,
            "ability_build": ability_build,
            "ability_id_to_name": {},
            "talents":      talents,
            "talents_valve": cached.get("talents", []),
            "talent_picks": {},
            "items": {
                "start_game_items": start_game_items,
                "core_items":       core_items,
            },
            "positions":   dota_keys_sorted,
            "dota_builds": dota_builds,
        }
        _serialized = json.dumps(_response)
        _build_cache[hero_id] = (time.time(), _serialized)
        return Response(content=_serialized, media_type="application/json")

    # ── Fallback: old stratz + live DB logic ──────────────────────────────
    raw_map = get_app_cache_value("ability_id_to_name") or {}
    ability_id_to_name: dict[int, str] = {int(k): v for k, v in raw_map.items()}

    ability_build_fb: list[str] = []
    db_build = get_hero_ability_build(hero_id)
    if db_build and db_build.get("ability_ids"):
        for aid in db_build["ability_ids"]:
            aname = ability_id_to_name.get(int(aid))
            if aname:
                ability_build_fb.append(aname)

    core_items_fb: list[dict] = [
        {"id": item.get("id"), "dname": item.get("dname"), "img": item.get("img")}
        for item in (cached.get("core_items") or [])
    ]

    talent_picks_raw = get_hero_talent_builds(hero_id)
    talent_picks_fb: dict[str, list] = {}
    for level, picks in talent_picks_raw.items():
        level_picks = []
        for pick in picks:
            aname = ability_id_to_name.get(pick["ability_id"])
            if aname and aname.startswith("special_bonus_"):
                level_picks.append({**pick, "ability_name": aname})
        if level_picks:
            talent_picks_fb[str(level)] = level_picks

    talents_fb = cached.get("talents", [])
    start_game_items_fb = cached.get("start_game_items", [])

    logger.info(
        "[build] hero_id=%s source=fallback facets=%d talents=%d ability_build=%d "
        "start_items=%d core_items=%d talent_picks_levels=%d",
        hero_id, len(facets), len(talents_fb), len(ability_build_fb),
        len(start_game_items_fb), len(core_items_fb), len(talent_picks_fb),
    )

    _response = {
        "facets":             facets,
        "ability_build":      ability_build_fb,
        "ability_id_to_name": raw_map,
        "talents":            talents_fb,
        "talent_picks":       talent_picks_fb,
        "items": {
            "start_game_items": start_game_items_fb,
            "core_items":       core_items_fb,
        },
    }
    _serialized = json.dumps(_response)
    _build_cache[hero_id] = (time.time(), _serialized)
    return Response(content=_serialized, media_type="application/json")


# ========== Hero Positions ==========

@app.get("/api/hero/{hero_id}/positions")
def api_hero_positions(hero_id: int):
    """Returns positions for a hero sorted by popularity.

    When dota_builds is present in the cache, uses total sixslot num_matches
    per position. Falls back to Stratz ALL.positions matchCount otherwise.
    """
    if hero_id <= 0:
        raise HTTPException(status_code=400, detail="hero_id must be a positive integer")

    cached = get_hero_build_cache(hero_id)
    if cached is None:
        raise HTTPException(status_code=503, detail="Build data not yet available.")

    dota_builds = cached.get("dota_builds")
    if not dota_builds:
        raw_file = _load_dota_builds_file()
        if raw_file:
            dota_builds = raw_file.get(str(hero_id))
    if dota_builds:
        positions_sorted = _dota_builds_positions(dota_builds)
        return {"hero_id": hero_id, "positions": positions_sorted}

    # Fallback: stratz
    stratz = cached.get("stratz")
    if not stratz:
        raise HTTPException(status_code=404, detail="No position data available.")

    all_data = stratz.get("ALL") or {}
    positions = all_data.get("positions") or []
    positions_sorted = sorted(positions, key=lambda p: p.get("matchCount", 0), reverse=True)
    return {"hero_id": hero_id, "positions": positions_sorted}


# ========== Items DB ==========

from fastapi.responses import JSONResponse

@app.get("/api/items_db")
def api_items_db():
    """Returns items_by_id dict (shared across all heroes).

    Cached in-memory server-side; clients should treat it as immutable
    for the session (Cache-Control: public, max-age=3600).
    """
    data = get_app_cache_value("items_by_id") or {}
    return JSONResponse(content=data, headers={"Cache-Control": "public, max-age=3600"})


# ========== Feedback ==========

@app.get("/api/meta")
def api_meta():
    """Returns top-5 meta heroes per position from dota_builds.json.

    Primary position = the position with max num_matches for a hero.
    Only heroes where the primary position matches AND num_matches >= 200.
    Top 5 by win_rate per position.

    Response format:
    {
      "patch": "7.41",
      "positions": {
        "POSITION_1": [{"hero_id": 54, "win_rate": 0.59, "num_matches": 2545}],
        ...
      }
    }
    """
    global _meta_cache, _meta_cache_time
    if _meta_cache is not None and (time.time() - _meta_cache_time) < META_CACHE_TTL:
        return _meta_cache

    raw = _load_dota_builds_file()
    if raw is None:
        raise HTTPException(status_code=503, detail="dota_builds.json not found")

    patch = raw.get("patch") or ""
    if not patch:
        fallback_patch = get_latest_match_patch()
        if fallback_patch:
            patch = fallback_patch
            logger.info("[meta] patch from matches table: %s", patch)
        else:
            logger.info("[meta] patch unavailable (neither dota_builds nor matches)")
    else:
        logger.info("[meta] patch from dota_builds.json: %s", patch)

    pos_keys = ["pos%201", "pos%202", "pos%203", "pos%204", "pos%205"]
    # _DOTA_TO_STRATZ_POS: "pos%20N" -> "POSITION_N"
    stratz_positions = ["POSITION_1", "POSITION_2", "POSITION_3", "POSITION_4", "POSITION_5"]
    buckets: dict[str, list] = {p: [] for p in stratz_positions}

    for hero_id_str, positions in raw.items():
        if hero_id_str == "patch":
            continue
        if not isinstance(positions, dict):
            continue
        try:
            hero_id = int(hero_id_str)
        except ValueError:
            continue

        # Find primary position (max num_matches)
        best_pos_key: str | None = None
        best_matches = -1
        for pk in pos_keys:
            pos_data = positions.get(pk)
            if not isinstance(pos_data, dict):
                continue
            nm = pos_data.get("num_matches") or 0
            if nm > best_matches:
                best_matches = nm
                best_pos_key = pk

        if best_pos_key is None:
            continue

        stratz_pos = _DOTA_TO_STRATZ_POS.get(best_pos_key)
        if not stratz_pos:
            continue

        pos_data = positions[best_pos_key]
        nm = pos_data.get("num_matches") or 0
        wr = pos_data.get("win_rate")

        if nm >= 200 and wr is not None:
            buckets[stratz_pos].append({
                "hero_id": hero_id,
                "win_rate": round(float(wr), 4),
                "num_matches": nm,
            })

    result_positions: dict[str, list] = {}
    for pos in stratz_positions:
        heroes = sorted(buckets[pos], key=lambda h: h["win_rate"], reverse=True)
        result_positions[pos] = heroes[:5]

    _meta_cache = {"patch": patch, "positions": result_positions}
    _meta_cache_time = time.time()
    return _meta_cache


@app.get("/api/news")
async def api_news():
    """Returns the most recent Dota 2 news item from the dota_news table.

    Response: {"title": str, "link": str, "published_at": str|null} or {} when empty.
    """
    rows = await asyncio.to_thread(get_latest_news_guids, 1)
    if not rows:
        return {}
    row = rows[0]
    published = row.get("published_at")
    return {
        "title": row.get("title") or "",
        "link": row.get("link") or "",
        "published_at": published.isoformat() if published is not None else None,
    }


class FeedbackRequest(BaseModel):
    token: str
    rating: int | None = None
    tags: list[str] = []
    message: str


@app.post("/api/feedback")
def submit_feedback(data: FeedbackRequest, db: Session = Depends(get_db)):
    """Сохраняет отзыв пользователя из мини‑аппа."""
    user_id = get_user_id_by_token(data.token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if data.rating is not None and data.rating not in (1, 2, 3, 4):
        raise HTTPException(status_code=422, detail="rating must be 1, 2, 3 or 4")

    if not data.message.strip():
        raise HTTPException(status_code=422, detail="message must not be empty")

    # Пробуем достать username из сохранённого профиля
    username: str | None = None
    try:
        db_profile = db.query(DBUserProfile).filter(DBUserProfile.user_id == user_id).first()
        if db_profile and db_profile.settings:
            username = db_profile.settings.get("username")
    except Exception as e:
        logger.warning("[feedback] Failed to fetch username for user %s: %s", user_id, e)

    save_feedback(
        user_id=user_id,
        rating=data.rating,
        tags=data.tags,
        message=data.message.strip(),
        source="mini_app",
        username=username,
    )
    return {"success": True}


# ========== Drafter ==========

_DOTA_POS_URL_TO_NUM: dict[str, int] = {
    "pos%201": 1, "pos%202": 2, "pos%203": 3, "pos%204": 4, "pos%205": 5,
}


def _hero_valid_pos_nums(hero_id: int, threshold: float = 0.15) -> set[int]:
    """Return set of valid position numbers (1-5) for a hero from dota_builds.json.

    A position is valid if the hero plays >= threshold fraction of their matches there.
    Returns empty set if no data is available.
    """
    raw = _load_dota_builds_file()
    if not raw:
        return set()
    hero_data = raw.get(str(hero_id))
    if not isinstance(hero_data, dict):
        return set()

    pos_matches: dict[int, int] = {}
    for pk, pos_num in _DOTA_POS_URL_TO_NUM.items():
        pos_data = hero_data.get(pk)
        if not isinstance(pos_data, dict):
            continue
        nm = pos_data.get("num_matches") or 0
        if nm > 0:
            pos_matches[pos_num] = nm

    total = sum(pos_matches.values())
    if total == 0:
        return set()

    return {pos_num for pos_num, nm in pos_matches.items() if nm / total >= threshold}



# Hero pools per position — hero_id lists derived from
# heroes-carry.js / heroes-mid.js / heroes-offlane.js / heroes-pos45.js
_DRAFT_POOL_POS1 = [
    102, 73, 1, 4, 61, 81, 56, 49, 6, 41, 72, 8, 145, 54, 48, 136, 94, 114,
    10, 89, 53, 57, 44, 12, 15, 32, 11, 93, 35, 67, 18, 46, 109, 95, 70, 63,
    21, 42,
]
_DRAFT_POOL_POS2 = [
    107, 7, 59, 49, 137, 28, 98, 19, 61, 56, 145, 80, 82, 114, 10, 32, 11,
    35, 46, 47, 74, 90, 52, 25, 36, 113, 38, 43, 97, 136, 53, 88, 16, 126,
    92, 13, 39, 86, 101, 17, 34, 22,
]
_DRAFT_POOL_POS3 = [
    73, 2, 99, 96, 81, 135, 69, 49, 107, 7, 103, 59, 23, 155, 104, 77, 129,
    60, 57, 110, 137, 14, 28, 71, 29, 98, 19, 108, 85, 42, 61, 15, 47, 55,
    36, 102, 38, 65, 78, 43, 33, 97, 136, 16, 120, 92, 21,
]
_DRAFT_POOL_POS4 = [
    26, 27, 31, 123, 20, 64, 30, 84, 100, 14, 37, 5, 50, 101, 68, 86, 105,
    75, 40, 91, 83, 128, 85, 111, 112, 121, 22, 131, 119, 21, 74, 79, 45,
    51, 63, 35, 97, 3, 9, 57, 53, 71, 110, 102, 136, 62, 88, 58, 66, 7, 19,
    107, 90, 65, 103, 87, 155,
]
_DRAFT_POOL_POS5 = [
    26, 30, 27, 64, 5, 31, 84, 37, 40, 101, 75, 105, 68, 22, 50, 21, 20,
    123, 85, 128, 112, 119, 83, 121, 100, 91, 53, 51, 45, 131, 79, 3, 102,
    57, 58, 87, 155, 111,
]

_DRAFT_POOLS_BY_POS = {
    1: _DRAFT_POOL_POS1,
    2: _DRAFT_POOL_POS2,
    3: _DRAFT_POOL_POS3,
    4: _DRAFT_POOL_POS4,
    5: _DRAFT_POOL_POS5,
}


@app.get("/api/draft/random")
def api_draft_random():
    """Returns a random enemy draft generated from per-position hero pools."""
    enemy = []
    used_ids: set[int] = set()
    for pos in (1, 2, 3, 4, 5):
        candidates = [hid for hid in _DRAFT_POOLS_BY_POS[pos] if hid not in used_ids]
        hero_id = random.choice(candidates)
        used_ids.add(hero_id)
        enemy.append({"hero_id": hero_id, "position": f"pos {pos}"})

    return {"match_id": 0, "enemy": enemy}


# Cache for popularity payload — derived from dota_builds.json once per process.
_draft_popularity_cache: dict[str, dict] | None = None


@app.get("/api/draft/matchups_all")
def api_draft_matchups_all():
    """Returns full hero_matchups.json blob.

    Used by the frontend "Анализ" mode of the Drafter to compute live recommendations
    on the client without round-trips. ~2.4 MB; raw bytes are cached at startup and
    served directly to skip jsonable_encoder + json.dumps (~4 s on this blob).
    GZipMiddleware handles compression on the wire.
    """
    data = _load_hero_matchups_bytes()
    if data is None:
        raise HTTPException(status_code=503, detail="Matchups data not available")
    return Response(content=data, media_type="application/json")


@app.get("/api/draft/popularity")
def api_draft_popularity():
    """Returns popularity data per hero with per-position breakdown.

    Schema:
        {
          "<hero_id>": {
            "total": <sum of num_matches across all positions>,
            "positions": {
              "<pos_num 1..5>": {"matches": <int>, "win_rate": <float | null>},
              ...
            }
          },
          ...
        }

    Source — dota_builds.json. Position keys там URL-encoded ("pos%201"..."pos%205");
    номер извлекается через _pos_str_to_num. win_rate = num_wins / num_matches,
    или null если num_matches == 0. Позиции, у которых нет валидного num_matches
    в исходных данных, в ответе не присутствуют.

    Used by the frontend "Анализ" mode for default ordering, tiebreakers, and
    per-position popularity/winrate context.
    """
    global _draft_popularity_cache
    if _draft_popularity_cache is not None:
        return _draft_popularity_cache

    builds = _load_dota_builds_file()
    if builds is None:
        raise HTTPException(status_code=503, detail="Builds data not available")

    out: dict[str, dict] = {}
    for hero_key, positions in builds.items():
        if not isinstance(positions, dict):
            continue
        per_pos: dict[str, dict] = {}
        total = 0
        for raw_pos_key, pos_data in positions.items():
            if not isinstance(pos_data, dict):
                continue
            pos_num = _pos_str_to_num(raw_pos_key)
            if pos_num is None:
                continue
            matches_raw = pos_data.get("num_matches")
            if not isinstance(matches_raw, (int, float)):
                continue
            matches = int(matches_raw)
            total += matches
            wins_raw = pos_data.get("num_wins")
            win_rate: float | None = None
            if isinstance(wins_raw, (int, float)) and matches > 0:
                win_rate = float(wins_raw) / matches
            per_pos[str(pos_num)] = {"matches": matches, "win_rate": win_rate}
        out[str(hero_key)] = {"total": total, "positions": per_pos}

    _draft_popularity_cache = out
    return out


class DraftHeroEntry(BaseModel):
    hero_id: int
    position: str = ""


class DraftEvaluateRequest(BaseModel):
    enemy: list[DraftHeroEntry] = []
    ally: list[DraftHeroEntry] = []
    token: str | None = None


def _pos_str_to_num(pos) -> int | None:
    """Convert position to 1..5. Accepts None.

    Supported formats: '1'..'5', 'pos 1'..'pos 5', 'pos%201'..'pos%205'.
    """
    if not pos:
        return None
    s = str(pos).strip().replace("%20", " ").lower()
    for i in range(1, 6):
        if s == str(i) or s == f"pos {i}":
            return i
    return None


def compute_draft_score(ally_entries, enemy_entries, synergy_scale: float = 50.0) -> dict:
    """Чистая оценка драфта — без HTTP-контекста (токенов, rate-limit, БД).

    ally_entries / enemy_entries — последовательности объектов с атрибутами
    .hero_id и .position (Pydantic DraftHeroEntry или любой совместимый объект).

    Единственный источник правды для счёта: /api/draft/evaluate просто
    оборачивает эту функцию, и финализация «Битвы драфтов» (этап 1) обязана
    считать итоги обеих сторон ИМЕННО ею — тогда числа гарантированно
    совпадают с сольным драфтером.

    synergy_scale — потолок синергия-компонента. Дефолт 50 (Тренировка,
    исторические лидерборды draft_results несопоставимы с другой шкалой).
    Битва передаёт 25 (счёт v2, 2026-07-16): контрпик — главный навык,
    синергия — второй план; ред-тим показал, что при равных весах заученная
    связка с потолочной синергией фармит 97% поля вслепую.
    """
    matchups = _load_hero_matchups_file() or {}

    ally_ids = [h.hero_id for h in ally_entries]
    enemy_ids = [h.hero_id for h in enemy_entries]

    # ── Компонент 1: Синергия команды (0-50) — 10 пар союзников ─────────────
    # Усредняем обе стороны, чтобы результат не зависел от порядка ввода героев:
    # поле "with" асимметрично (дельта от базового WR у каждого героя своя).
    synergy_pairs: list[tuple[int, int, float]] = []
    for i in range(len(ally_ids)):
        for j in range(i + 1, len(ally_ids)):
            a, b = ally_ids[i], ally_ids[j]
            v1 = (matchups.get(str(a)) or {}).get("with", {}).get(str(b), {}).get("synergy", 0.0)
            v2 = (matchups.get(str(b)) or {}).get("with", {}).get(str(a), {}).get("synergy", 0.0)
            val = (float(v1) + float(v2)) / 2
            synergy_pairs.append((a, b, val))

    avg_synergy = sum(v for _, _, v in synergy_pairs) / (len(synergy_pairs) or 1)
    synergy_component = max(0.0, min(synergy_scale, (avg_synergy + 1.5) / 3.0 * synergy_scale))

    # ── Компонент 2: Матчап против врагов (0-50) — 25 пар наш vs вражеский ──
    # СИММЕТРИЗОВАНО: val = (v_ae − v_ea) / 2, где v_ea — тот же матчап
    # глазами противника. Поле "vs" в данных Stratz асимметрично (дельта от
    # собственного base WR каждого героя), и одностороннее чтение давало
    # смещение в пользу стороны с более полным словарём. После симметризации
    # пары антисимметричны: matchup(A,B) = −matchup(B,A), сумма сырых
    # матчап-баллов двух команд — строго ноль. Критично для PvP («Битва
    # драфтов»): у кого плюс — тот в преимуществе, парадокс «обе команды в
    # минусе из-за дыр в данных» исключён.
    matchup_pairs: list[tuple[int, int, float]] = []
    for a in ally_ids:
        for e in enemy_ids:
            v_ae = (matchups.get(str(a)) or {}).get("vs", {}).get(str(e), {}).get("synergy", 0.0)
            v_ea = (matchups.get(str(e)) or {}).get("vs", {}).get(str(a), {}).get("synergy", 0.0)
            val = (float(v_ae) - float(v_ea)) / 2
            matchup_pairs.append((a, e, val))

    matchup_score = sum(v for _, _, v in matchup_pairs) / (len(matchup_pairs) or 1)
    matchup_component = max(0.0, min(50.0, (matchup_score + 1.5) / 3.0 * 50.0))

    # ── Позиции — не влияют на total_score, только comments ─────────────────
    pos_scores: list[tuple[int, bool]] = []
    for h in ally_entries:
        chosen = _pos_str_to_num(h.position)
        valid_positions = _hero_valid_pos_nums(h.hero_id)
        on_valid = chosen is not None and chosen in valid_positions
        pos_scores.append((h.hero_id, on_valid))

    position_component = 0.0

    # ── total_score = 2 компонента, макс 100 ────────────────────────────────
    total_score = synergy_component + matchup_component

    # ── comments ──────────────────────────────────────────────────────────
    comments: list[dict] = []

    # Top-2 best synergy pairs → "good"
    best_syn = sorted(synergy_pairs, key=lambda x: x[2], reverse=True)[:2]
    for a, b, v in best_syn:
        if len(comments) >= 5:
            break
        comments.append({
            "type": "good",
            "kind": "synergy",
            "hero_id1": a,
            "hero_id2": b,
            "value": round(v, 2),
        })

    # Top-2 worst matchups → "bad"
    worst_mu = sorted(matchup_pairs, key=lambda x: x[2])[:2]
    for a, e, v in worst_mu:
        if len(comments) >= 5:
            break
        comments.append({
            "type": "bad",
            "kind": "matchup",
            "ally_hero_id": a,
            "enemy_hero_id": e,
            "value": round(v, 2),
        })

    # Heroes on atypical positions → single consolidated "warn"
    atypical_ids = [hero_id for hero_id, on_primary in pos_scores if not on_primary]
    if atypical_ids:
        comments.append({
            "type": "warn",
            "kind": "position",
            "hero_ids": atypical_ids,
            "count": len(atypical_ids),
        })

    return {
        "total_score": round(total_score, 1),
        "synergy_score": round(synergy_component, 2),
        "matchup_score": round(matchup_component, 2),
        "position_score": round(position_component, 2),
        "ally_ids": ally_ids,
        "synergy_pairs": [
            {"hero_id1": a, "hero_id2": b, "value": round(v, 2)}
            for a, b, v in synergy_pairs
        ],
        "matchup_pairs": [
            {"ally_id": a, "enemy_id": e, "value": round(v, 2)}
            for a, e, v in matchup_pairs
        ],
        "enemy_ids": enemy_ids,
        "comments": comments,
    }


@app.post("/api/draft/evaluate")
def api_draft_evaluate(data: DraftEvaluateRequest, db: Session = Depends(get_db)):
    """Evaluates a draft based on synergy, matchups, and position fit.

    Счёт целиком в compute_draft_score (чистая функция выше); здесь только
    HTTP-обвязка: rate-limit, токен, сохранение результата в draft_results.
    """
    # ── Анти-чит: во время активной битвы драфтов оценка недоступна ─────────
    # «Тренировка»/«Анализ» считают той же формулой, которой судится битва, —
    # открытый evaluate в бою = идеальная подсказка. Fail-open: любая ошибка
    # проверки открывает доступ (хуже запереть честного, чем пропустить чит).
    rl_user_id = get_user_id_by_token(data.token) if data.token else None
    if rl_user_id:
        try:
            if _bt_draft_locked(db, rl_user_id):
                raise HTTPException(
                    status_code=409,
                    detail="Идёт битва драфтов — анализ откроется после её завершения.",
                )
        except HTTPException:
            raise
        except Exception:
            logger.exception("[battle] draft-lock check failed, failing open")

    # ── Rate limiting: 30 req / 10 min per authenticated user ───────────────
    # Uses SQLite so all uvicorn workers share the same counters.
    if rl_user_id:
        allowed, count = _rl_check_and_record(rl_user_id)
        logger.info("[rate_limit] user_id=%s window_count=%d allowed=%s", rl_user_id, count, allowed)
        if not allowed:
            raise HTTPException(status_code=429, detail="Слишком много запросов. Подождите немного.")

    result = compute_draft_score(data.ally, data.enemy)

    # ── Сохраняем результат если передан токен ───────────────────────────────
    uid = get_user_id_by_token(data.token) if data.token else None
    if uid:
        db.add(DBDraftResult(
            user_id=uid,
            total_score=result["total_score"],
            ally_heroes=result["ally_ids"],
            enemy_heroes=result["enemy_ids"],
        ))
        db.commit()

    return result


def _normalize_ally_heroes(raw):
    """Парсит ally_heroes из сырой строки SQL.

    SQLite возвращает JSON как str, PostgreSQL JSONB — как list. Нормализуем
    к list[int] или None.
    """
    if raw is None:
        return None
    if isinstance(raw, list):
        return raw
    if isinstance(raw, str):
        try:
            v = json.loads(raw)
            return v if isinstance(v, list) else None
        except (ValueError, TypeError):
            return None
    return None


def _compute_top5_sums_per_user(db_rows) -> dict[int, tuple[float, int]]:
    """Применяет правило «максимум 2 результата на уникальный союзный состав».

    Для каждого пользователя:
    1. Группируем результаты по отсортированному кортежу ally_heroes.
       Если ally_heroes NULL/пустой — каждый результат считается уникальным
       составом (исторические записи без сохранённого состава не дедупятся).
    2. Внутри группы оставляем 2 наивысших total_score.
    3. Из общего пула берём топ-5 и суммируем.

    Args:
        db_rows: iterable объектов с .user_id, .total_score, .ally_heroes.
    Returns:
        {user_id: (top5_sum, draft_count)}.
    """
    per_user: dict[int, list[tuple[float, tuple]]] = {}
    counts: dict[int, int] = {}
    for idx, r in enumerate(db_rows):
        uid = r.user_id
        ally = _normalize_ally_heroes(r.ally_heroes)
        if ally:
            try:
                key = tuple(sorted(int(h) for h in ally))
            except (ValueError, TypeError):
                key = ("__row__", idx)
        else:
            key = ("__row__", idx)  # NULL/пустой состав — каждая запись уникальна
        per_user.setdefault(uid, []).append((float(r.total_score), key))
        counts[uid] = counts.get(uid, 0) + 1

    result: dict[int, tuple[float, int]] = {}
    for uid, rows in per_user.items():
        by_comp: dict[tuple, list[float]] = {}
        for score, key in rows:
            by_comp.setdefault(key, []).append(score)
        pool: list[float] = []
        for scores in by_comp.values():
            scores.sort(reverse=True)
            pool.extend(scores[:2])
        pool.sort(reverse=True)
        top5_sum = sum(pool[:5])
        result[uid] = (top5_sum, counts[uid])
    return result


def _current_month_start_utc() -> datetime:
    """Начало текущего календарного месяца в UTC. Используется как нижняя
    граница для месячного лидерборда — каждый 1-е число рейтинг обнуляется."""
    now = datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


@app.get("/api/draft/leaderboard")
def api_draft_leaderboard(db: Session = Depends(get_db)):
    """Топ-25 пользователей по сумме топ-5 результатов за текущий месяц.

    Правило: на уникальный союзный состав (sorted ally_heroes) засчитываются
    максимум 2 лучших результата. Считаются только драфты текущего календарного
    месяца — рейтинг обнуляется 1-го числа каждого месяца.
    """
    global _leaderboard_cache, _leaderboard_cache_ts

    if _leaderboard_cache is not None and time.time() - _leaderboard_cache_ts < 300:
        return _leaderboard_cache

    from sqlalchemy import text

    rows = db.execute(text("""
        SELECT user_id, total_score, ally_heroes
        FROM draft_results
        WHERE user_id NOT IN (SELECT user_id FROM banned_users)
          AND created_at >= :month_start
    """), {"month_start": _current_month_start_utc()}).fetchall()

    per_user = _compute_top5_sums_per_user(rows)
    ranked = sorted(per_user.items(), key=lambda kv: kv[1][0], reverse=True)
    top25 = ranked[:25]

    user_ids = [uid for uid, _ in top25]
    profiles = {
        p.user_id: p
        for p in db.query(DBUserProfile).filter(DBUserProfile.user_id.in_(user_ids)).all()
    }

    result = []
    for rank, (uid, (top5_sum, draft_count)) in enumerate(top25, 1):
        profile = profiles.get(uid)
        settings = (profile.settings if profile else None) or {}
        username = settings.get("first_name") or settings.get("username") or f"Игрок {uid}"
        photo_url = settings.get("photo_url") or None
        result.append({
            "rank": rank,
            "user_id": uid,
            "username": username,
            "photo_url": photo_url,
            "top5_sum": round(top5_sum, 1),
            "draft_count": draft_count,
        })

    _leaderboard_cache = result
    _leaderboard_cache_ts = time.time()
    return result


@app.get("/api/draft/leaderboard/me")
def api_draft_leaderboard_me(token: str = "", db: Session = Depends(get_db)):
    """Место и счёт текущего пользователя среди всех участников за текущий месяц.

    Использует то же правило дедупа по союзному составу и тот же месячный
    фильтр, что и /leaderboard.
    """
    if not token:
        return {"rank": None, "top5_sum": None}
    user_id = get_user_id_by_token(token)
    if not user_id:
        return {"rank": None, "top5_sum": None}

    if is_user_banned(user_id):
        return {"banned": True, "rank": None, "top5_sum": None}

    from sqlalchemy import text

    rows = db.execute(text("""
        SELECT user_id, total_score, ally_heroes
        FROM draft_results
        WHERE user_id NOT IN (SELECT user_id FROM banned_users)
          AND created_at >= :month_start
    """), {"month_start": _current_month_start_utc()}).fetchall()

    per_user = _compute_top5_sums_per_user(rows)
    my = per_user.get(user_id)
    if not my or my[0] == 0.0:
        return {"rank": None, "top5_sum": None}

    my_sum = my[0]
    better_count = sum(1 for v in per_user.values() if v[0] > my_sum)
    return {"rank": better_count + 1, "top5_sum": round(my_sum, 1)}


@app.get("/api/draft/history")
def api_draft_history(token: str, db: Session = Depends(get_db)):
    """Последние 10 драфтов пользователя."""
    user_id = get_user_id_by_token(token) if token else None
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    rows = (
        db.query(DBDraftResult)
        .filter(DBDraftResult.user_id == user_id)
        .order_by(DBDraftResult.created_at.desc())
        .limit(10)
        .all()
    )
    def _score_rank(score: float) -> str:
        if score >= 85: return "SSS"
        if score >= 80: return "S"
        if score >= 65: return "A"
        if score >= 50: return "B"
        return "C"

    return [
        {
            "total_score": r.total_score,
            "rank": _score_rank(r.total_score),
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "ally_heroes": r.ally_heroes,
            "enemy_heroes": r.enemy_heroes,
        }
        for r in rows
    ]


# ========== Фэнтези TI (данные собирает переписанный stats_updater.py) ======

@app.get("/api/fantasy/players")
def api_fantasy_players(db: Session = Depends(get_db)):
    """Игроки TI-команд со средними фэнтези-показателями за все турниры.

    Витрина этапа 1 (проверка данных + фундамент UX этапа 2). Сырые средние —
    очки компендиума посчитает этап 2, когда Valve опубликует механику."""
    try:
        rows = db.execute(text("""
            SELECT p.account_id, p.name, p.team_name, p.position,
                   COUNT(s.match_id)      AS matches_count,
                   AVG(s.kills)           AS avg_kills,
                   AVG(s.deaths)          AS avg_deaths,
                   AVG(s.assists)         AS avg_assists,
                   AVG(s.last_hits)       AS avg_last_hits,
                   AVG(s.gold_per_min)    AS avg_gpm,
                   AVG(s.xp_per_min)      AS avg_xpm,
                   AVG(s.stuns)           AS avg_stuns,
                   AVG(s.obs_placed)      AS avg_obs,
                   AVG(s.camps_stacked)   AS avg_camps,
                   AVG(s.tower_kills)     AS avg_tower_kills,
                   AVG(s.roshan_kills)    AS avg_roshan_kills
            FROM fantasy_players p
            JOIN fantasy_player_stats s ON s.account_id = p.account_id
            GROUP BY p.account_id, p.name, p.team_name, p.position
            ORDER BY p.team_name, p.name
        """)).mappings().all()
    except Exception as e:
        # Таблиц ещё нет (воркер не запускался) — пустой список, не 500.
        logger.warning("[fantasy] players query failed: %s", e)
        return {"players": []}

    def _r1(v):
        return round(float(v), 1) if v is not None else 0.0

    return {"players": [
        {
            "account_id": r["account_id"],
            "name": r["name"],
            "team_name": r["team_name"],
            "position": r["position"],
            "matches_count": r["matches_count"],
            "avg_kills": _r1(r["avg_kills"]),
            "avg_deaths": _r1(r["avg_deaths"]),
            "avg_assists": _r1(r["avg_assists"]),
            "avg_last_hits": _r1(r["avg_last_hits"]),
            "avg_gpm": _r1(r["avg_gpm"]),
            "avg_xpm": _r1(r["avg_xpm"]),
            "avg_stuns": _r1(r["avg_stuns"]),
            "avg_obs": _r1(r["avg_obs"]),
            "avg_camps": _r1(r["avg_camps"]),
            "avg_tower_kills": _r1(r["avg_tower_kills"]),
            "avg_roshan_kills": _r1(r["avg_roshan_kills"]),
        }
        for r in rows
    ]}


# ========== Analytics ==========
#
# Один эндпоинт для записи событий миниаппа в analytics_events. Фронт зовёт
# из switchPage на каждое открытие страницы. События с бота пишутся напрямую
# из bot.py через db.log_event. Просмотр — admin-команда /analytics в боте.

# Аллоулист событий миниаппа: жёстко зафиксирован, чтобы клиент не мог
# засорять таблицу произвольными строками. Расширяется по мере появления
# новых страниц.
_ANALYTICS_ALLOWED_EVENTS: frozenset[str] = frozenset({
    "page_home",
    "page_drafter",
    "page_quiz",
    "page_database",
    "page_profile",
    "page_teammates",
    "page_teammate_review",
    "page_donate",
    "page_feedback",
    "page_news",
    # Хабы из нового floating dock (см. styles.css `.dock-pill`).
    "page_hub_play",
    "page_hub_tools",
    # Мини-игры.
    "page_minigame_hl",
    # PvP-драфтер «Битва драфтов».
    "page_draft_battle",
    # Клик по кнопке «Поддержать» на главном экране (goToDonate в script.js).
    "support_click",
})


class AnalyticsEventBody(BaseModel):
    token: str
    event: str


@app.post("/api/analytics/event")
def api_analytics_event(data: AnalyticsEventBody):
    """Принимает событие с миниаппа. Жёсткий аллоулист по имени; невалидные
    игнорируются с 422, чтобы клиент не пихал произвольный мусор."""
    if data.event not in _ANALYTICS_ALLOWED_EVENTS:
        raise HTTPException(status_code=422, detail="unknown event")
    user_id = get_user_id_by_token(data.token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    # log_event сам глотает любые ошибки записи — endpoint всегда возвращает ok.
    from backend.db import log_event as _log_event
    _log_event(data.event, user_id)
    return {"ok": True}


# ========== Мини-игры ==========
#
# «Выше/Ниже»: пул героев с агрегатами (популярность/длительность/ранг) +
# хранение личного рекорда стрика в user_profiles.settings.minigame_best.

class MinigameScore(BaseModel):
    token: str
    game: str          # идентификатор игры, напр. "hl"
    streak: int


@app.get("/api/minigames/hl/pool")
async def api_minigame_hl_pool(token: str):
    """Пул героев для «Выше/Ниже». Пары/раунды собирает фронт из этого пула.
    Тяжёлый пересчёт кэшируется на 12ч — гоняем в threadpool, чтобы не блокировать loop."""
    if get_user_id_by_token(token) is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    from backend.stats_db import get_minigame_hl_pool
    pool = await asyncio.to_thread(get_minigame_hl_pool)
    return {"heroes": pool}


@app.get("/api/minigames/best")
def api_minigame_best(token: str, game: str, db: Session = Depends(get_db)):
    """Личный рекорд стрика по игре (из user_profiles.settings.minigame_best)."""
    user_id = get_user_id_by_token(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    row = db.get(DBUserProfile, user_id)
    best = ((row.settings if row else None) or {}).get("minigame_best") or {}
    return {"best": int(best.get(game) or 0)}


@app.get("/api/minigames/leaderboard")
async def api_minigame_leaderboard(token: str, game: str = "hl", db: Session = Depends(get_db)):
    """Топ игроков по рекордной серии + ранг/перцентиль текущего юзера."""
    user_id = get_user_id_by_token(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    from backend.stats_db import get_minigame_leaderboard
    data = await asyncio.to_thread(get_minigame_leaderboard, game)

    row = db.get(DBUserProfile, user_id)
    ub = 0
    try:
        ub = int((((row.settings if row else None) or {}).get("minigame_best") or {}).get(game) or 0)
    except (TypeError, ValueError):
        ub = 0

    scores = data.get("scores") or []     # отсортировано по ВОЗРАСТАНИЮ (для bisect)
    total = data.get("total") or 0
    you = {"user_id": user_id, "best": ub, "rank": None, "percentile": None}
    if ub > 0 and total > 0:
        import bisect
        le = bisect.bisect_right(scores, ub)   # сколько результатов <= твоего — O(log n)
        greater = total - le                   # строго больше твоего
        rank = greater + 1
        you["rank"] = rank
        you["percentile"] = round(100 * (total - rank) / total) if total > 1 else 100
    return {"top": data.get("top", []), "total": total, "you": you}


@app.post("/api/minigames/score")
def api_minigame_score(data: MinigameScore, db: Session = Depends(get_db)):
    """Сохраняет результат: обновляет личный рекорд, если стрик выше прошлого."""
    user_id = get_user_id_by_token(data.token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    if not isinstance(data.streak, int) or data.streak < 0 or data.streak > 100000:
        raise HTTPException(status_code=422, detail="invalid streak")

    row = db.get(DBUserProfile, user_id)
    best = dict(((row.settings if row else None) or {}).get("minigame_best") or {})
    new_best = max(int(best.get(data.game) or 0), int(data.streak))
    best[data.game] = new_best
    from backend.db import upsert_user_profile_settings
    upsert_user_profile_settings(user_id, {"minigame_best": best})
    return {"ok": True, "best": new_best}


# ── Шеринг результата: карточка-картинка + prepared inline message ──
# Картинку рисует Pillow (backend/share_card.py), доставку делает
# save_prepared_inline_message (фото + подпись + url-кнопка «Играть» на бота —
# кнопка ведёт в /start, чтобы НЕ обходить гейт подписки).

_MGHL_MODES_SET = {"pop", "kills", "deaths"}


def _normalize_mode(mode: str) -> str | None:
    """Канонический ключ режима. Принимает и короткую форму («deaths»), и
    game-id («hl_deaths») — фронт исторически слал то одно, то другое.
    Возвращает «pop»/«kills»/«deaths» или None, если режим неизвестен."""
    m = (mode or "").strip()
    if m.startswith("hl_"):
        m = m[3:]
    return m if m in _MGHL_MODES_SET else None


def _public_base() -> str:
    """Базовый публичный URL мини-аппа из MINI_APP_URL — С УЧЁТОМ пути-префикса.

    Раньше брали только scheme://host и теряли префикс (на staging API живёт под
    «/staging/api», а photo_url уходил на «/api» → 404, и Telegram не качал фото →
    shareMessage callback=false). Теперь сохраняем путь:
      "https://dotaquiz.blog/staging/"           → "https://dotaquiz.blog/staging"
      "https://dotaquiz.blog/staging/index.html" → "https://dotaquiz.blog/staging"
      "https://dotaquiz.blog/"                    → "https://dotaquiz.blog"
    Возвращает без хвостового слэша; "" если URL невалиден.
    """
    from urllib.parse import urlsplit
    p = urlsplit((os.environ.get("MINI_APP_URL") or "").strip())
    if not (p.scheme and p.netloc):
        return ""
    path = p.path or ""
    # отбрасываем имя файла (последний сегмент с точкой, напр. index.html)
    if path and "." in path.rsplit("/", 1)[-1]:
        path = path.rsplit("/", 1)[0]
    return f"{p.scheme}://{p.netloc}{path.rstrip('/')}"


# Один инициализированный Bot на процесс для prepared-сообщений: иначе на КАЖДЫЙ
# шер поднимался новый http-клиент и делался лишний get_me. Telegram-Bot можно
# безопасно шарить между конкурентными запросами (свой пул соединений).
_share_bot = None
_share_bot_lock = asyncio.Lock()


async def _get_share_bot():
    global _share_bot
    if _share_bot is not None:
        return _share_bot
    async with _share_bot_lock:
        if _share_bot is None:
            from telegram import Bot
            b = Bot(BOT_TOKEN)
            await b.initialize()              # заполняет username, поднимает request-клиент
            _share_bot = b
    return _share_bot


@app.get("/api/minigames/share-image")
async def api_minigame_share_image(
    mode: str, streak: int,
    h1: str = "", n1: str = "", v1: str = "",
    h2: str = "", n2: str = "", v2: str = "",
):
    """JPEG-карточка результата. Без токена — Telegram тянет её как photo_url.
    Контент детерминирован параметрами, поэтому агрессивно кэшируется."""
    mode = _normalize_mode(mode)
    if mode is None:
        raise HTTPException(status_code=400, detail="bad mode")
    streak = max(0, min(int(streak), 100000))

    def _slug(s: str) -> str:
        return "".join(c for c in (s or "") if c.isalnum() or c in "_-")[:40]

    def _nm(s: str) -> str:
        return ((s or "").strip()[:24]) or "?"

    def _val(s: str):
        try:
            return float(s)
        except (TypeError, ValueError):
            return None

    heroes = [(_slug(h1), _nm(n1), _val(v1)), (_slug(h2), _nm(n2), _val(v2))]
    from backend.share_card import render_share_card
    jpg = await asyncio.to_thread(render_share_card, mode, streak, heroes)
    # GZip для image/* отключён глобально (см. DEFAULT_EXCLUDED_CONTENT_TYPES выше),
    # поэтому JPEG уходит как есть — без сжатия и без Content-Encoding-заголовка,
    # который строгий фетчер Telegram мог не разжать.
    return Response(
        content=jpg, media_type="image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )


class MinigameShareReq(BaseModel):
    token: str
    mode: str
    streak: int
    h1: str = ""
    n1: str = ""
    v1: float | None = None
    h2: str = ""
    n2: str = ""
    v2: float | None = None


@app.post("/api/minigames/share")
async def api_minigame_share(data: MinigameShareReq):
    """Готовит inline-сообщение с карточкой и возвращает его id для
    Telegram.WebApp.shareMessage(id) на фронте."""
    user_id = get_user_id_by_token(data.token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="unauthorized")
    mode = _normalize_mode(data.mode)   # принимает и «deaths», и «hl_deaths»
    if mode is None:
        raise HTTPException(status_code=400, detail="bad mode")
    base = _public_base()
    if not base:
        logger.warning("[minigame_share] MINI_APP_URL не задаёт публичный URL")
        raise HTTPException(status_code=503, detail="share unavailable")

    streak = max(0, min(int(data.streak), 100000))
    from urllib.parse import urlencode
    qs = urlencode({
        "mode": mode, "streak": streak,
        "h1": data.h1, "n1": data.n1, "v1": "" if data.v1 is None else data.v1,
        "h2": data.h2, "n2": data.n2, "v2": "" if data.v2 is None else data.v2,
    })
    img_url = f"{base}/api/minigames/share-image?{qs}"

    from backend.share_card import _MODE_LABEL
    mode_name = _MODE_LABEL.get(mode, "")
    caption = (
        f"Я выбил серию {streak} в режиме «{mode_name}» "
        f"в мини-игре «Больше / Меньше». Побьёшь?"
    )

    import secrets
    from telegram import (
        InlineQueryResultPhoto, InlineKeyboardMarkup, InlineKeyboardButton,
    )
    try:
        bot = await _get_share_bot()          # один инициализированный Bot на процесс
        play_url = f"https://t.me/{bot.username}?start=hl_share"
        result = InlineQueryResultPhoto(
            id=secrets.token_hex(8),           # уникальный id на каждый шер
            photo_url=img_url,
            thumbnail_url=img_url,
            photo_width=1200,
            photo_height=630,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(
                [[InlineKeyboardButton("🎮 Играть", url=play_url)]]
            ),
        )
        # Все типы чатов разрешены явно — иначе Telegram отклоняет отправку
        # (callback=false) после выбора получателя для неразрешённого типа.
        prepared = await bot.save_prepared_inline_message(
            int(user_id), result,
            allow_user_chats=True,
            allow_bot_chats=True,
            allow_group_chats=True,
            allow_channel_chats=True,
        )
        logger.info(
            "[minigame_share] prepared id=%s for user=%s (bot=@%s)",
            prepared.id, user_id, bot.username,
        )
        return {"id": prepared.id}
    except Exception as e:
        logger.warning("[minigame_share] prepared message failed: %s", e)
        raise HTTPException(status_code=502, detail="share failed")


# ========== Teammate finder ==========
#
# Профиль игрока для поиска тиммейтов + входящие/исходящие запросы + отзывы.
# Авторизация — существующий get_user_id_by_token (401 при невалидном токене).
# Логирование запросов — middleware log_requests выше; ничего дополнительно
# делать не надо.

from datetime import timedelta as _tm_timedelta  # noqa: E402  (локально, чтобы не трогать top-level imports)

from backend.models import (  # noqa: E402
    TeammateProfile as DBTeammateProfile,
    TeammateRequest as DBTeammateRequest,
    TeammateReview as DBTeammateReview,
    TeammateTag as DBTeammateTag,
    TeammateReport as DBTeammateReport,
    TeammateLobby as DBTeammateLobby,
    TeammateLobbySlot as DBTeammateLobbySlot,
)


_TM_VALID_RANKS = frozenset({
    "Калибровка",  # тир 0 — игрок на калибровке / без ранга
    "Рекрут", "Страж", "Рыцарь", "Герой", "Легенда", "Властелин", "Божество", "Титан",
})
_TM_VALID_GAME_MODES = frozenset({"ranked", "normal", "turbo"})
_TM_POSITIVE_TAGS = frozenset({"Бустер", "Душа компании", "Командный", "No tilted", "1x9"})
_TM_NEGATIVE_TAGS = frozenset({"Токсик", "Фидер", "AFK", "Фотограф", "Агент Габена"})
_TM_VALID_TAGS = _TM_POSITIVE_TAGS | _TM_NEGATIVE_TAGS
# Жалобы: фиксированные причины (упрощают триаж на стороне админа).
_TM_REPORT_REASONS = frozenset({
    "Токсичность", "Саботаж / фид", "Читы", "Другое",
})

# Статус видимости в ленте (заменил is_searching+TTL, миграция 0012).
_TM_VALID_STATUSES = frozenset({
    "ready_now", "looking_regular", "looking_casual", "hidden",
})
# Статусы, при которых профиль показывается в ленте (hidden и NULL — нет).
# Без приоритезации между ними — статус это фильтр-намерение, не ранжирование.
_TM_FEED_STATUSES = ("ready_now", "looking_regular", "looking_casual")

_TM_ABOUT_MAX_LEN = 200
_TM_MAX_FAVORITE_HEROES = 3
# «Первопроходец» — первым N юзерам, заполнившим профиль, выдаётся
# founder_number (см. миграцию 0014). Янтарная метка на карточке + счётчик
# «осталось N мест» на экране заполнения. Сам номер наружу не отдаём.
_TM_FOUNDER_CAP = 1000
# Админы (модерация профилей из миниапа). Зеркалит ADMIN_IDS в bot.py —
# держать в синхроне. Можно переопределить через env TM_ADMIN_IDS="id1,id2".
_TM_ADMIN_IDS: frozenset[int] = frozenset(
    int(x) for x in os.environ.get("TM_ADMIN_IDS", "556944111").split(",") if x.strip()
)
# Замок «раньше игры быть не могло»: нельзя оставить отзыв раньше, чем
# проходит партия. Турбо ~20 мин, обычная ~40 — 30 мин это безопасный порог,
# отсекающий «оценку по переписке» сразу после принятия, почти не задевая
# честный кейс (реальную игру за меньшее время вместе не сыграть).
_TM_REVIEW_MIN_MINUTES = 30
_TM_HOURS_MAX = 100000
# Soft-лимит на параллельные исходящие запросы. Защита от шотгана:
# новичок не должен иметь возможность тапнуть «Позвать» на 50 карточках подряд.
_TM_MAX_OUTGOING_PENDING = 10

# Party-finder («Лобби»)
_TM_LOBBY_TTL_MINUTES = 30
_TM_VALID_PARTY_SIZES = frozenset({3, 4, 5})
# Ранкед-валв-правила: разрешены party 1/2/3/5 (4-стак запрещён). У нас 1-2
# покрывает обычный 1-на-1 search, поэтому лобби для ranked = 3 или 5.
_TM_VALID_PARTY_SIZES_RANKED = frozenset({3, 5})

# Используется в inline-кнопке "Открыть" под уведомлением о новом запросе.
# Если переменная не задана — уведомление всё равно уйдёт, но без кнопки.
_TM_MINI_APP_URL = os.environ.get("MINI_APP_URL")

# Троттлинг записи last_active_at: не чаще раза в N секунд на юзера.
# Срезает write-amplification (одно открытие миниаппа = несколько auth-вызовов).
_TM_BUMP_THROTTLE_SEC = 60


def _tm_bump_last_active(db: Session, user_id: int) -> None:
    """Обновляет teammate_profiles.last_active_at = now для данного юзера.

    Best-effort: если у юзера нет teammate_profile (новый юзер, не заполнил
    форму) — UPDATE с WHERE просто no-op'ит, rowcount=0. Не валим вызов.

    Семантика «last_active»: значение обновляется на authenticated teammate-
    endpoint'е, но НЕ чаще раза в _TM_BUMP_THROTTLE_SEC (по умолчанию 60с).
    Троттлинг: одно открытие миниаппа = несколько авторизованных вызовов
    (profile/me + feed + входящие + исходящие), и без него каждый из них писал
    бы в БД. WHERE-условие `last_active_at < cutoff` отсекает повторы на уровне
    одного UPDATE — без лишнего SELECT. Для «в сети / был N мин назад» точность
    до минуты избыточна, так что 60с-гранулярность не вредит UX.
    """
    try:
        now = datetime.now(timezone.utc)
        cutoff = now - _tm_timedelta(seconds=_TM_BUMP_THROTTLE_SEC)
        db.execute(
            text(
                """
                UPDATE teammate_profiles
                SET last_active_at = :now
                WHERE user_id = :uid
                  AND (last_active_at IS NULL OR last_active_at < :cutoff)
                """
            ),
            {"now": now, "cutoff": cutoff, "uid": user_id},
        )
        db.commit()
    except Exception:
        # last_active не критичен — если UPDATE упал (deadlock / лок etc),
        # просто пропускаем, чтобы не валить основной endpoint.
        try: db.rollback()
        except Exception: pass


def _tm_authenticate(token: str, db: Session) -> int:
    """Validate token + bump last_active_at. Use в качестве auth-точки во
    ВСЕХ teammate-endpoint'ах вместо голого _tm_require_user — это даёт
    автоматический трекинг активности юзера (см. _tm_bump_last_active)."""
    uid = _tm_require_user(token=token)
    _tm_bump_last_active(db, uid)
    return uid


def _tm_require_user(token: str) -> int:
    """Validates token and returns user_id, or raises 401."""
    uid = get_user_id_by_token(token)
    if not uid:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return uid


def _tm_serialize_profile(p: DBTeammateProfile, settings: dict | None = None) -> dict:
    """Base profile payload — fields shared between /me, /feed, /{user_id}.

    `settings` — содержимое user_profiles.settings для данного user_id (если есть).
    Оттуда подтягиваются telegram-данные (имя/фото/username), чтобы карточка
    игрока могла показать аватар и ник, а не голый user_id.
    """
    s = settings or {}
    return {
        "user_id":         p.user_id,
        "rank":            p.rank,
        "hours":           p.hours,
        "positions":       list(p.positions or []),
        "game_modes":      list(p.game_modes or []),
        "microphone":      bool(p.microphone),
        "discord":         bool(p.discord),
        "favorite_heroes": list(p.favorite_heroes or []),
        "about":           p.about or "",
        # Статус видимости/намерения (заменил is_searching). NULL = не выбран.
        "status":          p.status,
        # Когда юзер последний раз делал что-то в miniapp (см. _tm_bump_last_active).
        # Фронт рендерит «🟢 в сети» / «был N мин назад» в meta-row карточки.
        "last_active_at":  p.last_active_at.isoformat() if p.last_active_at else None,
        # Первопроходец — янтарная метка на карточке. Сам номер не светим.
        "is_founder":      p.founder_number is not None,
        # Telegram identity (из user_profiles.settings)
        "first_name":      s.get("first_name"),
        "last_name":       s.get("last_name"),
        "username":        s.get("username"),
        "photo_url":       s.get("photo_url"),
    }


def _tm_load_user_settings(db: Session, user_ids: list[int]) -> dict[int, dict]:
    """Returns {user_id: settings dict} for the given users; empty dict if no row."""
    if not user_ids:
        return {}
    rows = (
        db.query(DBUserProfile)
        .filter(DBUserProfile.user_id.in_(user_ids))
        .all()
    )
    return {r.user_id: (r.settings or {}) for r in rows}


def _tm_html_safe(value: str | None) -> str:
    """HTML-escape для безопасной интерполяции в parse_mode=HTML тексты.

    First_name / username приходят из Telegram (валидируется на стороне TG),
    но всё равно могут содержать `<`, `&`, `"` — без escape'а сообщение
    отлетит с 400 от Bot API.
    """
    import html as _html
    return _html.escape(value or "", quote=False)


async def _tm_fetch_fresh_tg(user_id: int) -> dict | None:
    """Живые данные юзера из Telegram (getChat): актуальный username/имя.

    Кэш в user_profiles.settings протухает (username пишется только на /start
    и может быть затёрт клиентом без username в initDataUnsafe) — а пуш
    «запрос принят» без контакта бесполезен. getChat работает для любого, кто
    стартовал бота (оба участника — стартовали, иначе пуш не дошёл бы).
    Best-effort: любая ошибка → None, зовущий падает на кэш из БД."""
    if not BOT_TOKEN:
        return None
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            r = await client.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getChat",
                params={"chat_id": user_id},
            )
        if r.status_code != 200:
            return None
        result = (r.json() or {}).get("result") or {}
        return {
            "username": (result.get("username") or "").strip(),
            "first_name": (result.get("first_name") or "").strip(),
        }
    except Exception as e:
        logger.warning("[tm_notify] getChat %s failed: %s", user_id, e)
        return None


async def _tm_send_bot_message(
    chat_id: int,
    text: str,
    with_open_button: bool = False,
    open_button_url: str | None = None,
    parse_mode: str | None = None,
) -> None:
    """Шлёт сообщение пользователю через Bot API. Fire-and-forget: любая ошибка
    логируется, исключения наружу не выбрасываются — отправка нотификации
    никогда не должна валить основной запрос.

    Использует тот же raw-httpx-подход, что и /check-subscription выше (минуя
    python-telegram-bot Application, который живёт в отдельном процессе bot.py).

    `open_button_url` — кастомный URL для кнопки "Открыть" (например, с
    query-параметром для deep-link'а внутри миниапа). Если не задан и
    `with_open_button=True`, используется _TM_MINI_APP_URL как есть.
    """
    if not BOT_TOKEN:
        logger.warning("[tm_notify] BOT_TOKEN missing; skip chat_id=%s", chat_id)
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload: dict = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": True,
    }
    if parse_mode:
        payload["parse_mode"] = parse_mode
    if with_open_button:
        btn_url = open_button_url or _TM_MINI_APP_URL
        if btn_url:
            payload["reply_markup"] = {
                "inline_keyboard": [[
                    {"text": "Открыть", "web_app": {"url": btn_url}},
                ]],
            }
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.post(url, json=payload)
        if r.status_code != 200:
            logger.warning(
                "[tm_notify] sendMessage chat_id=%s failed: %d %s",
                chat_id, r.status_code, (r.text or "")[:200],
            )
    except Exception as e:
        logger.warning("[tm_notify] sendMessage chat_id=%s error: %s", chat_id, e)


def _tm_load_tags_grouped(db: Session, user_ids: list[int]) -> dict[int, list[dict]]:
    """Returns {user_id: [{tag, count, is_positive}, ...]} for the given ids.

    Только ПОЛОЖИТЕЛЬНЫЕ теги (Вариант A): публичная репутация — эндорсменты.
    Негативные метки субъективны и несправедливо «клеймят» — для плохого опыта
    есть приватные блок/жалоба. Фильтр скрывает и старые негативные теги из БД."""
    if not user_ids:
        return {}
    rows = (
        db.query(DBTeammateTag)
        .filter(DBTeammateTag.user_id.in_(user_ids))
        .filter(DBTeammateTag.is_positive.is_(True))
        .all()
    )
    out: dict[int, list[dict]] = {uid: [] for uid in user_ids}
    for r in rows:
        out.setdefault(r.user_id, []).append({
            "tag":         r.tag,
            "count":       r.count,
            "is_positive": bool(r.is_positive),
        })
    return out


# ── Pydantic models ─────────────────────────────────────────────────────────

class TeammateProfileUpsert(BaseModel):
    token: str
    rank: str
    hours: int
    positions: list[int]
    game_modes: list[str]
    microphone: bool
    discord: bool
    favorite_heroes: list[int] = []
    about: str = ""


class TeammateTokenOnly(BaseModel):
    token: str


class TeammateRequestCreate(BaseModel):
    token: str
    to_user_id: int


class TeammateRequestRespond(BaseModel):
    token: str
    request_id: int
    accept: bool


class TeammateReviewSubmit(BaseModel):
    token: str
    request_id: int
    tags: list[str]


class TeammateRequestCancel(BaseModel):
    token: str
    request_id: int


class TeammateStatusUpdate(BaseModel):
    token: str
    status: str  # ready_now / looking_regular / looking_casual / hidden


class TeammateAdminDelete(BaseModel):
    token: str
    target_user_id: int


# ── Party-finder («Лобби») Pydantic models ──────────────────────────────────

class TeammateLobbyCreate(BaseModel):
    token: str
    party_size: int                       # 3 / 4 / 5 (4 запрещён при mode='ranked')
    mode: str                             # ranked / normal / turbo
    host_position: int                    # 1..5 — позиция host'а
    needed_positions: list[int]           # позиции, которые ищем (без host'а)
    rank_filter: list[str] | None = None  # обязателен для ranked


class TeammateLobbyJoin(BaseModel):
    token: str
    position: int


class TeammateLobbyAction(BaseModel):
    """Используется для leave / disband — body всех action-endpoint'ов одинаков."""
    token: str


# ── 1. POST /api/teammates/profile — upsert ─────────────────────────────────

@app.post("/api/teammates/profile")
def api_teammates_profile_upsert(
    data: TeammateProfileUpsert, db: Session = Depends(get_db),
):
    """Создаёт или обновляет профиль текущего пользователя для поиска тиммейтов."""
    user_id = _tm_authenticate(data.token, db)

    if data.rank not in _TM_VALID_RANKS:
        raise HTTPException(status_code=422, detail="invalid rank")
    if not isinstance(data.hours, int) or data.hours < 0 or data.hours > _TM_HOURS_MAX:
        raise HTTPException(status_code=422, detail="hours out of range")

    positions = sorted({int(p) for p in data.positions if int(p) in (1, 2, 3, 4, 5)})
    if not positions:
        raise HTTPException(status_code=422, detail="positions must contain at least one of 1..5")

    game_modes = sorted({m for m in data.game_modes if m in _TM_VALID_GAME_MODES})
    if not game_modes:
        raise HTTPException(status_code=422, detail="game_modes must contain at least one valid mode")

    # Дедуп и обрезка до лимита, чтобы не доверять клиенту слепо.
    favorite_heroes = list(dict.fromkeys(int(h) for h in (data.favorite_heroes or [])))[:_TM_MAX_FAVORITE_HEROES]
    about = (data.about or "").strip()[:_TM_ABOUT_MAX_LEN]

    now = datetime.now(timezone.utc)
    try:
        profile = db.get(DBTeammateProfile, user_id)
        if profile is None:
            # Первопроходец: пока выдано меньше _TM_FOUNDER_CAP номеров, новый
            # профиль получает следующий. Номер = (выдано) + 1. Гонка двух
            # параллельных создателей в худшем случае выдаст одинаковый номер —
            # не страшно, наружу номер не светим, важен только факт is_founder,
            # а перелёт за cap отсекается ниже.
            founder_number = None
            taken = (
                db.query(DBTeammateProfile)
                .filter(DBTeammateProfile.founder_number.isnot(None))
                .count()
            )
            if taken < _TM_FOUNDER_CAP:
                founder_number = taken + 1
            profile = DBTeammateProfile(
                user_id=user_id,
                rank=data.rank,
                hours=data.hours,
                positions=positions,
                game_modes=game_modes,
                microphone=bool(data.microphone),
                discord=bool(data.discord),
                favorite_heroes=favorite_heroes,
                about=about,
                # status НЕ задаём — остаётся NULL, чтобы юзер прошёл обязательный
                # экран выбора статуса в ленте. Профиль и статус — два разных шага.
                founder_number=founder_number,
                created_at=now,
                updated_at=now,
            )
            db.add(profile)
        else:
            profile.rank = data.rank
            profile.hours = data.hours
            profile.positions = positions
            profile.game_modes = game_modes
            profile.microphone = bool(data.microphone)
            profile.discord = bool(data.discord)
            profile.favorite_heroes = favorite_heroes
            profile.about = about
            profile.updated_at = now
        db.commit()
    except Exception:
        # Детали (тип исключения, текст БД) пишем в серверный лог, наружу —
        # generic-текст. Раньше отдавали exc-детали клиенту: это утечка
        # внутренностей (схема БД, SQL) и непонятно для пользователя.
        logger.exception("[tm/profile] UNCAUGHT upsert user_id=%s", user_id)
        try: db.rollback()
        except Exception: pass
        raise HTTPException(
            status_code=500,
            detail="Не удалось сохранить профиль. Попробуй ещё раз.",
        )
    return {"ok": True}


# ── 2. GET /api/teammates/profile/me ─────────────────────────────────────────
# ВАЖНО: объявлен ДО /profile/{user_id}, иначе FastAPI попытается распарсить
# "me" как int и вернёт 422.

@app.get("/api/teammates/profile/me")
def api_teammates_profile_me(token: str, db: Session = Depends(get_db)):
    """Возвращает свой профиль (со статусом и тегами) или null.

    Поле status: ready_now / looking_regular / looking_casual / hidden / null.
    null = статус ещё не выбран → фронт покажет обязательный экран выбора.
    """
    user_id = _tm_authenticate(token, db)
    try:
        profile = db.get(DBTeammateProfile, user_id)
        if profile is None:
            return None

        user_row = db.get(DBUserProfile, user_id)
        settings = (user_row.settings if user_row else None) or {}
        out = _tm_serialize_profile(profile, settings)  # уже включает status
        out["tags"] = _tm_load_tags_grouped(db, [user_id]).get(user_id, [])
        # Флаг админа — фронт по нему показывает кнопку модерации на карточках.
        out["is_admin"] = user_id in _TM_ADMIN_IDS
        return out
    except Exception:
        logger.exception("[tm/profile/me] UNCAUGHT user_id=%s", user_id)
        raise HTTPException(
            status_code=500,
            detail="Не удалось загрузить профиль. Попробуй ещё раз.",
        )


# ── 2b. GET /api/teammates/founders — счётчик «первопроходцев» ───────────────

@app.get("/api/teammates/founders")
def api_teammates_founders(db: Session = Depends(get_db)):
    """Сколько мест «первопроходца» выдано и сколько осталось.

    Не требует токена — это публичный счётчик для экрана заполнения профиля
    («осталось N мест»). Номера наружу не отдаём, только агрегаты.
    """
    taken = (
        db.query(DBTeammateProfile)
        .filter(DBTeammateProfile.founder_number.isnot(None))
        .count()
    )
    return {
        "cap": _TM_FOUNDER_CAP,
        "taken": taken,
        "remaining": max(0, _TM_FOUNDER_CAP - taken),
    }


# ── 2c. POST /api/teammates/admin/delete_profile — модерация (только админ) ──

@app.post("/api/teammates/admin/delete_profile")
def api_teammates_admin_delete_profile(
    data: TeammateAdminDelete, db: Session = Depends(get_db),
):
    """Удаляет teammate-профиль игрока. Только для админов (_TM_ADMIN_IDS).

    Модерация: убирает плохой профиль из ленты/просмотров. Чистим сам профиль
    + накопленные на нём теги-репутацию, а его pending-запросы переводим в
    cancelled (чтобы не висели у получателей). Отзывы/история не трогаем —
    они ссылаются на user_id и безвредны без профиля."""
    user_id = _tm_authenticate(data.token, db)
    if user_id not in _TM_ADMIN_IDS:
        raise HTTPException(status_code=403, detail="admin only")

    target = data.target_user_id
    profile = db.get(DBTeammateProfile, target)
    if profile is None:
        raise HTTPException(status_code=404, detail="profile not found")

    # Pending-запросы игрока (входящие и исходящие) → cancelled.
    db.query(DBTeammateRequest).filter(
        ((DBTeammateRequest.from_user_id == target) |
         (DBTeammateRequest.to_user_id == target)),
        DBTeammateRequest.status == "pending",
    ).update({DBTeammateRequest.status: "cancelled"}, synchronize_session=False)

    # Накопленные на игроке теги (его репутация в ленте).
    db.query(DBTeammateTag).filter(DBTeammateTag.user_id == target).delete(
        synchronize_session=False
    )

    db.delete(profile)
    db.commit()
    logger.info("[tm/admin] profile %s deleted by admin %s", target, user_id)
    return {"ok": True}


# ── 3. POST /api/teammates/status — установить статус видимости ──────────────

@app.post("/api/teammates/status")
def api_teammates_status_set(
    data: TeammateStatusUpdate, db: Session = Depends(get_db),
):
    """Ставит статус профиля. Используется и обязательным экраном выбора при
    первом заходе, и быстрым переключателем сверху ленты.

    Заменил пару search/start + search/stop из старой TTL-модели."""
    user_id = _tm_authenticate(data.token, db)
    if data.status not in _TM_VALID_STATUSES:
        raise HTTPException(status_code=422, detail="invalid status")

    profile = db.get(DBTeammateProfile, user_id)
    if profile is None:
        raise HTTPException(
            status_code=400,
            detail="profile not found — fill in profile first",
        )
    profile.status = data.status
    profile.updated_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True, "status": data.status}


# ── 5. GET /api/teammates/feed ──────────────────────────────────────────────

@app.get("/api/teammates/feed")
def api_teammates_feed(
    token: str,
    ranks: str | None = None,
    positions: str | None = None,
    game_modes: str | None = None,
    statuses: str | None = None,
    microphone: bool | None = None,
    discord: bool | None = None,
    limit: int = Query(default=20, ge=1, le=50),
    cursor: int | None = None,
    db: Session = Depends(get_db),
):
    """Лента игроков по статусу видимости.

    Модель статуса (миграция 0012, заменила is_searching+TTL):
      • показываем только status IN (ready_now, looking_regular, looking_casual)
        — hidden и NULL не в ленте.
      • БЕЗ приоритезации по статусу — все статусы равны. Сортировка чисто по
        свежести активности (last_active_at desc) = «по мере появления».
        Статус — это фильтр-намерение, а не ранжирующий фактор.
      • опциональный фильтр `statuses` (comma-separated) — показать только
        выбранные статусы (например, только тех кто «готов сейчас»).

    Пагинация — offset-based (cursor = смещение). Пул активных невелик —
    грузим капнутый набор, режем по offset.

    Boolean-фильтры microphone/discord — True оставляет только тех у кого флаг
    тоже True; False = «нет фильтра».
    """
    user_id = _tm_authenticate(token, db)
    offset = int(cursor) if cursor is not None and cursor > 0 else 0

    # Какие статусы показывать. По умолчанию — все feed-статусы. Если задан
    # фильтр statuses — пересекаем с допустимыми (hidden/мусор отсекаются).
    status_set = set(_TM_FEED_STATUSES)
    if statuses:
        requested = {s.strip() for s in statuses.split(",") if s.strip()}
        status_set = requested & set(_TM_FEED_STATUSES)
        if not status_set:
            # Запросили только невалидные/hidden — пустая лента.
            return {"items": [], "next_cursor": None}

    q = (
        db.query(DBTeammateProfile)
        .filter(DBTeammateProfile.status.in_(status_set))
        .filter(DBTeammateProfile.user_id != user_id)
    )

    # Ranks — мультивыбор, comma-separated (как и positions / game_modes).
    if ranks:
        rank_set = {r.strip() for r in ranks.split(",") if r.strip()}
        invalid = rank_set - _TM_VALID_RANKS
        if invalid:
            raise HTTPException(status_code=422, detail="invalid rank value(s)")
        if rank_set:
            q = q.filter(DBTeammateProfile.rank.in_(rank_set))

    # Boolean column filters — SQL-side, чтобы не тащить лишние строки в Python.
    if microphone:
        q = q.filter(DBTeammateProfile.microphone == True)  # noqa: E712
    if discord:
        q = q.filter(DBTeammateProfile.discord == True)     # noqa: E712

    # Сортировка — по свежести активности (индекс). Никакой статус-приоритезации.
    _FEED_HARD_CAP = 500
    q = q.order_by(DBTeammateProfile.last_active_at.desc().nullslast())
    raw_rows = q.limit(_FEED_HARD_CAP).all()

    pos_filter: set[int] | None = None
    if positions:
        try:
            pos_filter = {int(x) for x in positions.split(",") if x.strip()}
        except ValueError:
            raise HTTPException(status_code=422, detail="positions must be comma-separated integers")
        pos_filter = {p for p in pos_filter if p in (1, 2, 3, 4, 5)} or None

    mode_filter: set[str] | None = None
    if game_modes:
        mode_filter = {m.strip() for m in game_modes.split(",") if m.strip()}
        mode_filter = (mode_filter & _TM_VALID_GAME_MODES) or None

    # JSON-фильтры позиций/режимов — в Python (JSON-операторы разнятся SQLite/PG).
    # raw_rows уже отсортирован по активности — порядок сохраняется.
    matched: list[DBTeammateProfile] = []
    for p in raw_rows:
        if pos_filter and not (set(p.positions or []) & pos_filter):
            continue
        if mode_filter and not (set(p.game_modes or []) & mode_filter):
            continue
        matched.append(p)

    # Offset-пагинация по уже отсортированному (по активности) списку.
    page = matched[offset: offset + limit]

    feed_ids = [p.user_id for p in page]
    tags_by_user = _tm_load_tags_grouped(db, feed_ids)
    settings_by_user = _tm_load_user_settings(db, feed_ids)
    items: list[dict] = []
    for p in page:
        item = _tm_serialize_profile(p, settings_by_user.get(p.user_id))
        item["tags"] = tags_by_user.get(p.user_id, [])
        items.append(item)

    next_offset = offset + limit
    next_cursor = next_offset if next_offset < len(matched) else None
    return {"items": items, "next_cursor": next_cursor}


# ── 6. POST /api/teammates/request — отправить запрос ───────────────────────

@app.post("/api/teammates/request")
async def api_teammates_request_create(
    data: TeammateRequestCreate, db: Session = Depends(get_db),
):
    """Создаёт pending-запрос от текущего пользователя к to_user_id."""
    user_id = _tm_authenticate(data.token, db)

    if data.to_user_id == user_id:
        raise HTTPException(status_code=422, detail="cannot request yourself")

    existing = (
        db.query(DBTeammateRequest)
        .filter(DBTeammateRequest.from_user_id == user_id)
        .filter(DBTeammateRequest.to_user_id == data.to_user_id)
        .filter(DBTeammateRequest.status == "pending")
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="request already exists")

    # Soft rate-limit на одновременные pending'и. Защита от ситуации, когда
    # юзер тапает «Позвать» на 30 карточках подряд из любопытства — каждая
    # генерит push, получатели не понимают что происходит.
    pending_count = (
        db.query(DBTeammateRequest)
        .filter(DBTeammateRequest.from_user_id == user_id)
        .filter(DBTeammateRequest.status == "pending")
        .count()
    )
    if pending_count >= _TM_MAX_OUTGOING_PENDING:
        raise HTTPException(
            status_code=429,
            detail=f"У тебя уже {pending_count} запросов в ожидании. Дождись ответа или отмени старые.",
        )

    req = DBTeammateRequest(
        from_user_id=user_id,
        to_user_id=data.to_user_id,
        status="pending",
        review_sent=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add(req)
    db.commit()
    db.refresh(req)

    # Достаём имя отправителя для персонализации push'а. «Иван хочет играть»
    # читается ощутимо лучше, чем «Кто-то хочет играть» — у получателя сразу
    # есть контекст «о, это конкретный человек, открою посмотрю».
    sender_row = db.get(DBUserProfile, user_id)
    sender_settings = (sender_row.settings if sender_row else None) or {}
    sender_name = (sender_settings.get("first_name") or "").strip() or "Игрок"

    incoming_url = (
        f"{_TM_MINI_APP_URL}?tm_incoming=1" if _TM_MINI_APP_URL else None
    )
    # Шаблон — admin-редактируемый через /admin_text tm_push_new_request.
    # Дефолт см. backend/bot_texts.py:DEFAULT_BOT_TEXTS. {sender_name}
    # экранируется через _tm_html_safe ДО форматирования — попадает в шаблон
    # как уже-HTML-safe значение.
    from backend.bot_texts import get_text as _get_bot_text
    push_text = _get_bot_text(
        "tm_push_new_request",
        sender_name=_tm_html_safe(sender_name),
    )
    await _tm_send_bot_message(
        chat_id=data.to_user_id,
        text=push_text,
        with_open_button=True,
        open_button_url=incoming_url,
        parse_mode="HTML",
    )

    return {"ok": True, "request_id": req.id}


# ── 7. POST /api/teammates/request/respond — accept/decline ─────────────────

@app.post("/api/teammates/request/respond")
async def api_teammates_request_respond(
    data: TeammateRequestRespond, db: Session = Depends(get_db),
):
    """Принять/отклонить входящий запрос."""
    user_id = _tm_authenticate(data.token, db)

    req = db.get(DBTeammateRequest, data.request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="request not found")
    if req.to_user_id != user_id:
        raise HTTPException(status_code=403, detail="not the recipient of this request")
    if req.status != "pending":
        raise HTTPException(status_code=409, detail="request already resolved")

    if data.accept:
        req.status = "accepted"
        req.accepted_at = datetime.now(timezone.utc)
    else:
        req.status = "declined"

    # Снимаем строки бэка с FK до сетевых вызовов — не держим транзакцию
    # открытой на время HTTP к Bot API.
    from_id = req.from_user_id
    to_id   = req.to_user_id
    accepted = (req.status == "accepted")
    db.commit()

    # Раньше тут был auto-stop поиска для обоих участников. В status-модели
    # (миграция 0012) статус постоянный и юзер сам им управляет — насильно
    # менять его на accept'е неправильно (человек может хотеть ещё поиграть).
    # Поэтому статус НЕ трогаем.

    if accepted:
        # Подтягиваем имена / usernames обоих участников. Кэш settings может
        # протухнуть или быть затёртым (см. save_telegram_data) — поэтому
        # СНАЧАЛА живой getChat из Telegram, кэш — фолбэк.
        settings_map = _tm_load_user_settings(db, [from_id, to_id])
        from_s = settings_map.get(from_id) or {}
        to_s   = settings_map.get(to_id)   or {}

        _fr, _to = await asyncio.gather(
            _tm_fetch_fresh_tg(from_id), _tm_fetch_fresh_tg(to_id)
        )
        fresh_from = _fr or {}
        fresh_to = _to or {}
        # Диагностика причин «пропавших username»: фиксируем расхождение
        # живых данных с кэшем — по логам видно, протухание это или затирание.
        for _uid, _fresh, _cached in (
            (from_id, fresh_from, from_s), (to_id, fresh_to, to_s),
        ):
            if _fresh and (_fresh.get("username") or "") != (_cached.get("username") or ""):
                logger.info(
                    "[tm_notify] stale username for %s: cached=%r fresh=%r",
                    _uid, _cached.get("username"), _fresh.get("username"),
                )

        from_name = (fresh_from.get("first_name") or from_s.get("first_name") or "").strip() or "тиммейт"
        to_name   = (fresh_to.get("first_name") or to_s.get("first_name") or "").strip() or "тиммейт"
        from_uname = (fresh_from.get("username") or from_s.get("username") or "").lstrip("@").strip()
        to_uname   = (fresh_to.get("username") or to_s.get("username") or "").lstrip("@").strip()

        # Self-heal кэша: свежие непустые значения — обратно в settings, чтобы
        # лента/карточки тоже показывали актуальный контакт.
        try:
            for uid_heal, fresh in ((from_id, fresh_from), (to_id, fresh_to)):
                if not fresh:
                    continue
                prof = db.query(DBUserProfile).filter(DBUserProfile.user_id == uid_heal).first()
                if not prof:
                    continue
                changed = False
                s = prof.settings or {}
                for k in ("username", "first_name"):
                    if fresh.get(k) and s.get(k) != fresh[k]:
                        s[k] = fresh[k]
                        changed = True
                if changed:
                    prof.settings = s
                    flag_modified(prof, "settings")
            db.commit()
        except Exception as e:
            logger.warning("[tm_notify] settings self-heal failed: %s", e)

        # Ключевое: tg://user?id=N открывает чат с пользователем НЕЗАВИСИМО
        # от наличия у него username. Раньше при отсутствии @ хвост вообще
        # пропадал — получатель видел «Напиши Иван — он ждёт» и не понимал
        # куда писать. Теперь имя — это clickable-ссылка в любом случае.
        from_link = f'<a href="tg://user?id={from_id}">{_tm_html_safe(from_name)}</a>'
        to_link   = f'<a href="tg://user?id={to_id}">{_tm_html_safe(to_name)}</a>'
        from_handle = f" (@{_tm_html_safe(from_uname)})" if from_uname else ""
        to_handle   = f" (@{_tm_html_safe(to_uname)})"   if to_uname   else ""

        # Шаблоны admin-редактируются через /admin_text tm_push_accepted_*.
        # Плейсхолдеры подставляются здесь — _tm_html_safe + готовые <a>-теги
        # уже HTML-safe и попадают в шаблон as-is.
        from backend.bot_texts import get_text as _get_bot_text
        await _tm_send_bot_message(
            chat_id=from_id,
            text=_get_bot_text(
                "tm_push_accepted_to_sender",
                receiver_name=_tm_html_safe(to_name),
                receiver_link=to_link,
                receiver_handle=to_handle,
            ),
            parse_mode="HTML",
        )
        await _tm_send_bot_message(
            chat_id=to_id,
            text=_get_bot_text(
                "tm_push_accepted_to_receiver",
                sender_name=_tm_html_safe(from_name),
                sender_link=from_link,
                sender_handle=from_handle,
            ),
            parse_mode="HTML",
        )

    return {"ok": True}


# ── 8. GET /api/teammates/requests/incoming ─────────────────────────────────

@app.get("/api/teammates/requests/incoming")
def api_teammates_requests_incoming(token: str, db: Session = Depends(get_db)):
    """Входящие pending-запросы с прикреплённым профилем отправителя."""
    user_id = _tm_authenticate(token, db)

    rows = (
        db.query(DBTeammateRequest)
        .filter(DBTeammateRequest.to_user_id == user_id)
        .filter(DBTeammateRequest.status == "pending")
        .order_by(DBTeammateRequest.created_at.desc())
        .all()
    )

    from_ids = [r.from_user_id for r in rows]
    profiles_map = {
        p.user_id: p
        for p in db.query(DBTeammateProfile)
        .filter(DBTeammateProfile.user_id.in_(from_ids))
        .all()
    }
    tags_by_user = _tm_load_tags_grouped(db, from_ids)
    settings_by_user = _tm_load_user_settings(db, from_ids)

    result: list[dict] = []
    for r in rows:
        profile = profiles_map.get(r.from_user_id)
        profile_payload = None
        if profile is not None:
            profile_payload = _tm_serialize_profile(profile, settings_by_user.get(r.from_user_id))
            profile_payload["tags"] = tags_by_user.get(r.from_user_id, [])
        result.append({
            "request_id":   r.id,
            "from_user_id": r.from_user_id,
            "created_at":   r.created_at.isoformat() if r.created_at else None,
            "profile":      profile_payload,
        })
    return result


# ── 9. POST /api/teammates/review — оставить отзыв ──────────────────────────

@app.post("/api/teammates/review")
def api_teammates_review_submit(
    data: TeammateReviewSubmit, db: Session = Depends(get_db),
):
    """Сохраняет отзыв (список тегов) и инкрементит счётчики в teammate_tags.

    Оставить отзыв может любой из участников accepted-запроса. Цель отзыва —
    другой участник. Повторный отзыв тем же пользователем по тому же
    request_id — 409.
    """
    user_id = _tm_authenticate(data.token, db)

    req = db.get(DBTeammateRequest, data.request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="request not found")
    if req.status != "accepted":
        raise HTTPException(status_code=409, detail="request is not in accepted status")
    if user_id != req.from_user_id and user_id != req.to_user_id:
        raise HTTPException(status_code=403, detail="not a participant of this request")

    target_user_id = req.to_user_id if user_id == req.from_user_id else req.from_user_id

    # Дедуп ПО ПАРЕ игроков (from→to), а не по request_id: один человек может
    # оставить другому ровно один отзыв навсегда — тегов сколько угодно, но
    # один раз. Иначе повторные коннекты тех же двоих позволяли бы накручивать
    # счётчики тегов в профиле. Направленно: A→B и B→A — разные отзывы.
    already = (
        db.query(DBTeammateReview)
        .filter(DBTeammateReview.from_user_id == user_id)
        .filter(DBTeammateReview.to_user_id == target_user_id)
        .first()
    )
    if already is not None:
        raise HTTPException(status_code=409, detail="Ты уже оставлял отзыв этому игроку")

    # Замок по длине катки: раньше _TM_REVIEW_MIN_MINUTES игры быть не могло,
    # значит это «оценка по переписке» — отклоняем. accepted_at выставлен при
    # accept'е; если вдруг None — замок пропускаем (не блокируем легитимный кейс).
    if req.accepted_at is not None:
        accepted_at = req.accepted_at
        if accepted_at.tzinfo is None:
            accepted_at = accepted_at.replace(tzinfo=timezone.utc)
        elapsed_min = (datetime.now(timezone.utc) - accepted_at).total_seconds() / 60.0
        if elapsed_min < _TM_REVIEW_MIN_MINUTES:
            raise HTTPException(
                status_code=409,
                detail="Оценить можно после игры — кнопка станет доступна чуть позже.",
            )

    # Дедуп + валидация. Принимаем ТОЛЬКО положительные теги (Вариант A):
    # негативные метки больше не собираются (даже если UI их пришлёт).
    raw_tags = list(dict.fromkeys((t or "").strip() for t in (data.tags or [])))
    valid_tags = [t for t in raw_tags if t in _TM_POSITIVE_TAGS]
    if not valid_tags:
        raise HTTPException(status_code=422, detail="no valid tags provided")

    now = datetime.now(timezone.utc)

    db.add(DBTeammateReview(
        from_user_id=user_id,
        to_user_id=target_user_id,
        request_id=data.request_id,
        tags=valid_tags,
        created_at=now,
    ))

    # Upsert teammate_tags (user_id, tag): создаём с count=1 или инкрементим.
    for tag in valid_tags:
        is_positive = tag in _TM_POSITIVE_TAGS
        row = db.get(DBTeammateTag, (target_user_id, tag))
        if row is None:
            db.add(DBTeammateTag(
                user_id=target_user_id,
                tag=tag,
                count=1,
                is_positive=is_positive,
            ))
        else:
            row.count = (row.count or 0) + 1

    db.commit()
    return {"ok": True}


# ── 9b. POST /api/teammates/report — пожаловаться на игрока ──────────────────

class TeammateReportSubmit(BaseModel):
    token: str
    request_id: int
    reason: str
    text: str = ""


async def _tm_notify_admins_report(reporter_id: int, reported_id: int,
                                   reason: str, text: str, db: Session) -> None:
    """Push жалобы админам в Telegram (best-effort, не валит запрос)."""
    def _name(uid: int) -> str:
        row = db.get(DBUserProfile, uid)
        s = (row.settings if row else None) or {}
        nm = ((s.get("first_name") or "") + " " + (s.get("last_name") or "")).strip()
        if not nm:
            nm = ("@" + s["username"]) if s.get("username") else ""
        return nm
    try:
        msg = (
            "🚩 Жалоба в Пати\n"
            f"От: {_name(reporter_id)} (id {reporter_id})\n"
            f"На: {_name(reported_id)} (id {reported_id})\n"
            f"Причина: {reason}"
        )
        if text:
            msg += f"\nКомментарий: {text}"
        bot = await _get_share_bot()
        for admin_id in _TM_ADMIN_IDS:
            try:
                await bot.send_message(chat_id=admin_id, text=msg)
            except Exception as e:
                logger.warning("[tm_report] notify admin %s failed: %s", admin_id, e)
    except Exception as e:
        logger.warning("[tm_report] notify build failed: %s", e)


@app.post("/api/teammates/report")
async def api_teammates_report_submit(
    data: TeammateReportSubmit, db: Session = Depends(get_db),
):
    """Жалоба на участника accepted-заявки. Приватная (отмеченный не видит,
    публичной метки нет). Сохраняется для разбора + push админам в Telegram.
    Гейт «только после игры» — тот же, что у отзыва (через request_id)."""
    user_id = _tm_authenticate(data.token, db)

    reason = (data.reason or "").strip()
    if reason not in _TM_REPORT_REASONS:
        raise HTTPException(status_code=422, detail="invalid reason")
    text = (data.text or "").strip()[:2000]

    req = db.get(DBTeammateRequest, data.request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="request not found")
    if req.status != "accepted":
        raise HTTPException(status_code=409, detail="request is not in accepted status")
    if user_id != req.from_user_id and user_id != req.to_user_id:
        raise HTTPException(status_code=403, detail="not a participant of this request")
    target_user_id = req.to_user_id if user_id == req.from_user_id else req.from_user_id

    # Один ОТКРЫТЫЙ репорт на пару (reporter→reported) — защита от спама.
    already = (
        db.query(DBTeammateReport)
        .filter(DBTeammateReport.reporter_id == user_id)
        .filter(DBTeammateReport.reported_user_id == target_user_id)
        .filter(DBTeammateReport.status == "open")
        .first()
    )
    if already is not None:
        raise HTTPException(status_code=409, detail="Жалоба на этого игрока уже отправлена")

    db.add(DBTeammateReport(
        reporter_id=user_id,
        reported_user_id=target_user_id,
        request_id=data.request_id,
        reason=reason,
        text=text or None,
        status="open",
        created_at=datetime.now(timezone.utc),
    ))
    db.commit()

    await _tm_notify_admins_report(user_id, target_user_id, reason, text, db)
    return {"ok": True}


# ── 10. GET /api/teammates/profile/{user_id} — публичный профиль ────────────
# Объявлен ПОСЛЕ /profile/me — иначе "me" попадёт в этот роут и упадёт на
# приведении к int.

@app.get("/api/teammates/profile/{user_id}")
def api_teammates_profile_public(
    user_id: int, token: str, db: Session = Depends(get_db),
):
    """Профиль игрока + накопленные теги. Требует валидный токен.

    Раньше эндпоинт был открыт без авторизации и отдавал Telegram-идентичность
    (имя, @username, фото) любого user_id. Так как user_id = Telegram ID и они
    перебираемы, это позволяло без входа собрать контакты всех зарегистрированных
    (в т.ч. со статусом hidden). Теперь нужен токен — как у /feed и остальных."""
    _tm_authenticate(token, db)
    profile = db.get(DBTeammateProfile, user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="profile not found")
    user_row = db.get(DBUserProfile, user_id)
    settings = (user_row.settings if user_row else None) or {}
    out = _tm_serialize_profile(profile, settings)
    out["tags"] = _tm_load_tags_grouped(db, [user_id]).get(user_id, [])
    return out


# ── 11. GET /api/teammates/requests/outgoing ────────────────────────────────

@app.get("/api/teammates/requests/outgoing")
def api_teammates_requests_outgoing(token: str, db: Session = Depends(get_db)):
    """Исходящие pending-запросы текущего пользователя с профилем получателя."""
    user_id = _tm_authenticate(token, db)

    rows = (
        db.query(DBTeammateRequest)
        .filter(DBTeammateRequest.from_user_id == user_id)
        .filter(DBTeammateRequest.status == "pending")
        .order_by(DBTeammateRequest.created_at.desc())
        .all()
    )

    to_ids = [r.to_user_id for r in rows]
    profiles_map = {
        p.user_id: p
        for p in db.query(DBTeammateProfile)
        .filter(DBTeammateProfile.user_id.in_(to_ids))
        .all()
    }
    tags_by_user = _tm_load_tags_grouped(db, to_ids)
    settings_by_user = _tm_load_user_settings(db, to_ids)

    result: list[dict] = []
    for r in rows:
        profile = profiles_map.get(r.to_user_id)
        profile_payload = None
        if profile is not None:
            profile_payload = _tm_serialize_profile(profile, settings_by_user.get(r.to_user_id))
            profile_payload["tags"] = tags_by_user.get(r.to_user_id, [])
        result.append({
            "request_id": r.id,
            "to_user_id": r.to_user_id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "profile":    profile_payload,
        })
    return result


# ── 12. GET /api/teammates/requests/history ─────────────────────────────────

@app.get("/api/teammates/requests/history")
def api_teammates_requests_history(
    token: str,
    limit: int = Query(default=20, ge=1, le=50),
    cursor: str | None = None,   # ISO-строка accepted_at последней показанной строки
    db: Session = Depends(get_db),
):
    """Принятые запросы, где пользователь — отправитель ИЛИ получатель.

    Курсор — ISO-формат `accepted_at` последней отданной строки. Сортировка
    accepted_at DESC; следующая страница — строки строго раньше курсора.
    """
    user_id = _tm_authenticate(token, db)

    q = (
        db.query(DBTeammateRequest)
        .filter(
            (DBTeammateRequest.from_user_id == user_id) |
            (DBTeammateRequest.to_user_id == user_id)
        )
        .filter(DBTeammateRequest.status == "accepted")
        .filter(DBTeammateRequest.accepted_at.isnot(None))
    )

    if cursor:
        try:
            cursor_dt = datetime.fromisoformat(cursor)
        except ValueError:
            raise HTTPException(status_code=422, detail="invalid cursor")
        # accepted_at теперь TIMESTAMPTZ (миграция 0008). Сравнение работает
        # с любым tz-aware значением напрямую. Naive-cursor подгоняем к UTC
        # для обратной совместимости с фронтом, который мог отдать строку
        # без TZ-маркера до прохождения миграции.
        if cursor_dt.tzinfo is None:
            cursor_dt = cursor_dt.replace(tzinfo=timezone.utc)
        q = q.filter(DBTeammateRequest.accepted_at < cursor_dt)

    rows = (
        q.order_by(DBTeammateRequest.accepted_at.desc())
         .limit(limit)
         .all()
    )

    # Определяем "другого" участника для каждой строки.
    other_ids = []
    for r in rows:
        other_ids.append(r.to_user_id if r.from_user_id == user_id else r.from_user_id)

    profiles_map = {
        p.user_id: p
        for p in db.query(DBTeammateProfile)
        .filter(DBTeammateProfile.user_id.in_(other_ids))
        .all()
    }
    tags_by_user = _tm_load_tags_grouped(db, other_ids)
    settings_by_user = _tm_load_user_settings(db, other_ids)

    # Оставил ли текущий юзер отзыв этому ЧЕЛОВЕКУ (по паре, не по request_id —
    # согласовано с дедупом в /review). Если да, все записи с этим игроком в
    # истории показываются как «отзыв оставлен», а не предлагают оценить снова.
    reviewed_user_ids: set[int] = set()
    if other_ids:
        review_rows = (
            db.query(DBTeammateReview.to_user_id)
            .filter(DBTeammateReview.from_user_id == user_id)
            .filter(DBTeammateReview.to_user_id.in_(other_ids))
            .all()
        )
        reviewed_user_ids = {row[0] for row in review_rows}

    items: list[dict] = []
    for r in rows:
        other_id = r.to_user_id if r.from_user_id == user_id else r.from_user_id
        profile = profiles_map.get(other_id)
        profile_payload = None
        if profile is not None:
            profile_payload = _tm_serialize_profile(profile, settings_by_user.get(other_id))
            profile_payload["tags"] = tags_by_user.get(other_id, [])
        items.append({
            "request_id":     r.id,
            "other_user_id":  other_id,
            "accepted_at":    r.accepted_at.isoformat() if r.accepted_at else None,
            "profile":        profile_payload,
            "my_review_left": other_id in reviewed_user_ids,
        })

    next_cursor = items[-1]["accepted_at"] if len(items) == limit and items else None
    return {"items": items, "next_cursor": next_cursor}


# ── 13. POST /api/teammates/request/cancel ──────────────────────────────────

@app.post("/api/teammates/request/cancel")
def api_teammates_request_cancel(
    data: TeammateRequestCancel, db: Session = Depends(get_db),
):
    """Отмена исходящего pending-запроса автором. Переводит status в 'cancelled'.

    Получатель не получает отдельного push'а: запрос просто исчезает у него
    из входящих при следующем рефреше. Это интенциональный low-touch:
    «передумал — убрал тихо». История запросов это значение не показывает
    (history фильтрует по status='accepted').
    """
    user_id = _tm_authenticate(data.token, db)

    req = db.get(DBTeammateRequest, data.request_id)
    if req is None:
        raise HTTPException(status_code=404, detail="request not found")
    if req.from_user_id != user_id:
        raise HTTPException(status_code=403, detail="not the sender of this request")
    if req.status != "pending":
        raise HTTPException(status_code=409, detail="request already resolved")

    req.status = "cancelled"
    db.commit()
    return {"ok": True}


# ─────────────────────────────────────────────────────────────────────────────
#  Party-finder («Лобби»)
# ─────────────────────────────────────────────────────────────────────────────


def _tm_user_active_lobby_id(db: Session, user_id: int) -> int | None:
    """Возвращает id активного лобби, в котором участвует user (host или slot),
    либо None. Активное = status='open' AND expires_at > now."""
    now = datetime.now(timezone.utc)
    # Host-membership: лобби со status='open' и я хост.
    host_lobby = (
        db.query(DBTeammateLobby.id)
        .filter(DBTeammateLobby.host_id == user_id)
        .filter(DBTeammateLobby.status == "open")
        .filter(DBTeammateLobby.expires_at > now)
        .first()
    )
    if host_lobby:
        return host_lobby[0]
    # Slot-membership: ищу слот с этим user_id в активном лобби.
    slot = (
        db.query(DBTeammateLobbySlot.lobby_id)
        .join(DBTeammateLobby, DBTeammateLobby.id == DBTeammateLobbySlot.lobby_id)
        .filter(DBTeammateLobbySlot.user_id == user_id)
        .filter(DBTeammateLobby.status == "open")
        .filter(DBTeammateLobby.expires_at > now)
        .first()
    )
    return slot[0] if slot else None


def _tm_serialize_lobby(
    db: Session,
    lobby: DBTeammateLobby,
    slots: list[DBTeammateLobbySlot] | None = None,
) -> dict:
    """Сериализует лобби с полным списком слотов (host'а + всех остальных).

    Каждый слот включает мини-профиль user'а (имя/аватар/ранг), если занят.
    slots — опциональная предзагрузка; если None, грузим внутри (для batch'а
    list-endpoint'а лучше предзагружать снаружи и передавать сюда).
    """
    if slots is None:
        slots = (
            db.query(DBTeammateLobbySlot)
            .filter(DBTeammateLobbySlot.lobby_id == lobby.id)
            .all()
        )

    # Загружаем профили + settings'ы участников одним batch'ем.
    user_ids = [s.user_id for s in slots if s.user_id is not None]
    if user_ids:
        profiles_map = {
            p.user_id: p
            for p in db.query(DBTeammateProfile)
            .filter(DBTeammateProfile.user_id.in_(user_ids))
            .all()
        }
        settings_by_user = _tm_load_user_settings(db, user_ids)
    else:
        profiles_map, settings_by_user = {}, {}

    def slot_payload(s: DBTeammateLobbySlot) -> dict:
        if s.user_id is None:
            return {"position": s.position, "user": None}
        prof = profiles_map.get(s.user_id)
        if prof is None:
            # Юзер существует в TG, но без teammate-профиля — редкий edge
            # (заполнил профиль host'а до миграции?). Возвращаем минимум.
            user_data = {
                "user_id": s.user_id,
                **(settings_by_user.get(s.user_id) or {}),
                "rank": None,
            }
        else:
            user_data = _tm_serialize_profile(prof, settings_by_user.get(s.user_id))
        return {
            "position": s.position,
            "user": user_data,
            "joined_at": s.joined_at.isoformat() if s.joined_at else None,
        }

    return {
        "lobby_id":          lobby.id,
        "host_id":           lobby.host_id,
        "host_position":     lobby.host_position,
        "party_size":        lobby.party_size,
        "mode":              lobby.mode,
        "rank_filter":       list(lobby.rank_filter or []) or None,
        "needed_positions":  list(lobby.needed_positions or []),
        "status":            lobby.status,
        "created_at":        lobby.created_at.isoformat() if lobby.created_at else None,
        "expires_at":        lobby.expires_at.isoformat() if lobby.expires_at else None,
        "filled_at":         lobby.filled_at.isoformat() if lobby.filled_at else None,
        "slots": sorted(
            [slot_payload(s) for s in slots],
            key=lambda x: x["position"],
        ),
    }


async def _tm_send_lobby_join_push(
    db: Session, lobby: DBTeammateLobby, joiner_id: int, position: int,
) -> None:
    """Host получает пуш «X присоединился на Pos N»."""
    settings_map = _tm_load_user_settings(db, [joiner_id])
    joiner_s = settings_map.get(joiner_id) or {}
    joiner_name = (joiner_s.get("first_name") or "").strip() or "Игрок"
    open_url = f"{_TM_MINI_APP_URL}?tm_lobby={lobby.id}" if _TM_MINI_APP_URL else None
    # NB: переменная называется message_text, не text — чтобы не shadow'ить
    # модульный `from sqlalchemy import text`. Если когда-нибудь добавишь
    # в эту функцию raw SQL — будет работать без сюрпризов.
    message_text = (
        f"➕ <b>{_tm_html_safe(joiner_name)}</b> присоединился на Pos {position}"
    )
    await _tm_send_bot_message(
        chat_id=lobby.host_id,
        text=message_text,
        with_open_button=True,
        open_button_url=open_url,
        parse_mode="HTML",
    )


async def _tm_send_lobby_filled_pushes(db: Session, lobby: DBTeammateLobby) -> None:
    """Когда последний слот занят: рассылаем ВСЕМ участникам список @ников
    с tg://-ссылками, чтобы каждый мог тапнуть и начать чат / собрать группу."""
    slots = (
        db.query(DBTeammateLobbySlot)
        .filter(DBTeammateLobbySlot.lobby_id == lobby.id)
        .all()
    )
    user_ids = [s.user_id for s in slots if s.user_id is not None]
    if not user_ids:
        return
    settings_map = _tm_load_user_settings(db, user_ids)

    # Строим список @юзернеймов с tg://-ссылками. Если у юзера нет username,
    # подставляем first_name (clickable через tg://user?id=).
    members_html_parts: list[str] = []
    for uid in user_ids:
        s = settings_map.get(uid) or {}
        name = (s.get("first_name") or "").strip() or "тиммейт"
        uname = (s.get("username") or "").lstrip("@").strip()
        if uname:
            members_html_parts.append(
                f'<a href="tg://user?id={uid}">{_tm_html_safe(name)}</a> '
                f'(@{_tm_html_safe(uname)})'
            )
        else:
            members_html_parts.append(
                f'<a href="tg://user?id={uid}">{_tm_html_safe(name)}</a>'
            )
    members_block = "\n".join(f"• {p}" for p in members_html_parts)

    # message_text вместо text — см. комментарий в _tm_send_lobby_join_push.
    message_text = (
        f"🎮 <b>Пати собрана!</b>\n\n"
        f"{members_block}\n\n"
        f"Создайте групповой чат и стартуйте."
    )

    # Шлём каждому участнику. Параллельная рассылка через httpx-клиент
    # внутри _tm_send_bot_message — приемлемо.
    for uid in user_ids:
        await _tm_send_bot_message(
            chat_id=uid,
            text=message_text,
            parse_mode="HTML",
        )


async def _tm_send_lobby_disband_pushes(
    db: Session, lobby: DBTeammateLobby, by_host: bool,
) -> None:
    """Host распустил → шлём всем members. by_host для текстовки."""
    slots = (
        db.query(DBTeammateLobbySlot)
        .filter(DBTeammateLobbySlot.lobby_id == lobby.id)
        .filter(DBTeammateLobbySlot.user_id.isnot(None))
        .filter(DBTeammateLobbySlot.user_id != lobby.host_id)
        .all()
    )
    if not slots:
        return
    text = "❌ Хост распустил лобби." if by_host else "❌ Лобби распущено."
    for s in slots:
        await _tm_send_bot_message(chat_id=s.user_id, text=text)


# ── L1. POST /api/teammates/lobby — create ──────────────────────────────────

@app.post("/api/teammates/lobby")
def api_teammates_lobby_create(
    data: TeammateLobbyCreate, db: Session = Depends(get_db),
):
    """Создаёт лобби. Host автоматически занимает свой слот."""
    user_id = _tm_authenticate(data.token, db)

    # Профиль обязателен — без него host не сможет показать ранг/позицию.
    profile = db.get(DBTeammateProfile, user_id)
    if profile is None:
        raise HTTPException(status_code=400, detail="profile not found — fill in profile first")

    # Не даём создать лобби, если юзер уже в активном лобби.
    if _tm_user_active_lobby_id(db, user_id) is not None:
        raise HTTPException(
            status_code=409,
            detail="Ты уже в активном лобби. Выйди из него, чтобы создать новое.",
        )

    # Валидация полей.
    if data.mode not in _TM_VALID_GAME_MODES:
        raise HTTPException(status_code=422, detail="invalid mode")
    if data.party_size not in _TM_VALID_PARTY_SIZES:
        raise HTTPException(status_code=422, detail="invalid party_size")
    if data.mode == "ranked" and data.party_size not in _TM_VALID_PARTY_SIZES_RANKED:
        raise HTTPException(
            status_code=422,
            detail="В рейтинге 4-стак запрещён правилами Доты",
        )

    if data.host_position not in (1, 2, 3, 4, 5):
        raise HTTPException(status_code=422, detail="invalid host_position")

    needed = list(data.needed_positions or [])
    if len(needed) != data.party_size - 1:
        raise HTTPException(
            status_code=422,
            detail="needed_positions должен содержать party_size - 1 значений",
        )
    if len(set(needed)) != len(needed):
        raise HTTPException(status_code=422, detail="duplicate needed_positions")
    for p in needed:
        if p not in (1, 2, 3, 4, 5):
            raise HTTPException(status_code=422, detail="invalid position in needed_positions")
    if data.host_position in needed:
        raise HTTPException(
            status_code=422,
            detail="host_position не должна быть в needed_positions",
        )

    # rank_filter обязателен для ranked.
    rank_filter: list[str] | None = None
    if data.rank_filter:
        invalid_ranks = [r for r in data.rank_filter if r not in _TM_VALID_RANKS]
        if invalid_ranks:
            raise HTTPException(status_code=422, detail="invalid rank_filter values")
        # Сохраняем как уникальный sorted список.
        rank_filter = sorted(set(data.rank_filter))
    if data.mode == "ranked" and not rank_filter:
        raise HTTPException(
            status_code=422,
            detail="Для ranked-режима укажи допустимые ранги",
        )

    now = datetime.now(timezone.utc)
    lobby = DBTeammateLobby(
        host_id=user_id,
        party_size=data.party_size,
        mode=data.mode,
        rank_filter=rank_filter,
        needed_positions=needed,
        host_position=data.host_position,
        status="open",
        created_at=now,
        expires_at=now + _tm_timedelta(minutes=_TM_LOBBY_TTL_MINUTES),
        filled_at=None,
    )
    db.add(lobby)
    db.flush()  # получить lobby.id до создания слотов

    # Создаём слоты. Host's слот сразу filled, остальные NULL.
    slots: list[DBTeammateLobbySlot] = []
    for pos in [data.host_position] + needed:
        slot = DBTeammateLobbySlot(
            lobby_id=lobby.id,
            position=pos,
            user_id=user_id if pos == data.host_position else None,
            joined_at=now if pos == data.host_position else None,
        )
        slots.append(slot)
        db.add(slot)
    db.commit()
    db.refresh(lobby)

    return _tm_serialize_lobby(db, lobby, slots)


# ── L2. GET /api/teammates/lobbies — list active ────────────────────────────

@app.get("/api/teammates/lobbies")
def api_teammates_lobbies_list(token: str, db: Session = Depends(get_db)):
    """Возвращает список активных лобби (status='open', expires_at > now).

    Сортировка: created_at DESC (новые сверху). UI рендерит их над одиночными
    игроками в ленте. Фронту передаём ВСЕ — фильтрацию по rank_filter тоже,
    клиент сам решит как подсветить «доступно мне / нет».
    """
    _tm_authenticate(token, db)
    now = datetime.now(timezone.utc)

    lobbies = (
        db.query(DBTeammateLobby)
        .filter(DBTeammateLobby.status == "open")
        .filter(DBTeammateLobby.expires_at > now)
        .order_by(DBTeammateLobby.created_at.desc())
        .limit(50)
        .all()
    )
    if not lobbies:
        return {"items": []}

    lobby_ids = [l.id for l in lobbies]
    all_slots = (
        db.query(DBTeammateLobbySlot)
        .filter(DBTeammateLobbySlot.lobby_id.in_(lobby_ids))
        .all()
    )
    slots_by_lobby: dict[int, list[DBTeammateLobbySlot]] = {}
    for s in all_slots:
        slots_by_lobby.setdefault(s.lobby_id, []).append(s)

    items = [
        _tm_serialize_lobby(db, l, slots_by_lobby.get(l.id, []))
        for l in lobbies
    ]
    return {"items": items}


# ── L3. POST /api/teammates/lobby/{id}/join ─────────────────────────────────

@app.post("/api/teammates/lobby/{lobby_id}/join")
async def api_teammates_lobby_join(
    lobby_id: int, data: TeammateLobbyJoin, db: Session = Depends(get_db),
):
    """Open-join: атомарно занимаем пустой слот в указанной position.

    Race-protection: UPDATE … SET user_id=:uid WHERE … AND user_id IS NULL —
    rowcount=0 значит «слот уже занят кем-то параллельно». Тогда возвращаем 409.

    Все uncaught-исключения логируются с traceback'ом — на staging юзер видит
    точную точку падения по `[tm/lobby/join]` в логах backend'а.
    """
    user_id = _tm_authenticate(data.token, db)
    logger.info(
        "[tm/lobby/join] user_id=%s lobby_id=%s position=%s",
        user_id, lobby_id, data.position,
    )
    try:
        lobby = db.get(DBTeammateLobby, lobby_id)
        if lobby is None:
            raise HTTPException(status_code=404, detail="lobby not found")
        if lobby.status != "open":
            raise HTTPException(status_code=409, detail="lobby is no longer open")

        now = datetime.now(timezone.utc)
        if lobby.expires_at <= now:
            raise HTTPException(status_code=409, detail="lobby has expired")

        # Не даём join'нуть если уже в каком-то активном лобби.
        existing = _tm_user_active_lobby_id(db, user_id)
        if existing is not None:
            if existing == lobby_id:
                raise HTTPException(status_code=409, detail="ты уже в этом лобби")
            raise HTTPException(
                status_code=409,
                detail="Ты уже в активном лобби. Выйди из него, чтобы вступить в другое.",
            )

        # Rank-filter: если есть — юзер должен быть в нём.
        if lobby.rank_filter:
            profile = db.get(DBTeammateProfile, user_id)
            if profile is None or profile.rank not in set(lobby.rank_filter):
                raise HTTPException(
                    status_code=403,
                    detail="Твой ранг не подходит под фильтр лобби",
                )

        # Атомарный claim слота. Возможные failure-modes:
        # 1) FK violation на user_id → user не зарегистрирован в user_profiles.
        # 2) Тип :now не совпадает с column-type — для timestamptz передаём
        #    tz-aware, что мы и делаем (datetime.now(timezone.utc)).
        result = db.execute(
            text(
                """
                UPDATE teammate_lobby_slots
                SET user_id = :uid, joined_at = :now
                WHERE lobby_id = :lid AND position = :pos AND user_id IS NULL
                """
            ),
            {"uid": user_id, "now": now, "lid": lobby_id, "pos": data.position},
        )
        if not result.rowcount:
            db.commit()
            raise HTTPException(
                status_code=409,
                detail="Этот слот только что заняли. Попробуй другую позицию.",
            )

        # Проверяем — последний ли это слот? Все остальные слоты лобби заняты?
        remaining_empty = (
            db.query(DBTeammateLobbySlot)
            .filter(DBTeammateLobbySlot.lobby_id == lobby_id)
            .filter(DBTeammateLobbySlot.user_id.is_(None))
            .count()
        )

        just_filled = False
        if remaining_empty == 0:
            # Лобби собрано — переводим в filled, фиксируем filled_at.
            lobby.status = "filled"
            lobby.filled_at = now
            just_filled = True

        db.commit()
        db.refresh(lobby)

        # Push'и:
        #   - если лобби только что заполнилось → рассылаем «пати собрана» ВСЕМ
        #     участникам (включая host'а).
        #   - иначе → host получает «X присоединился».
        if just_filled:
            await _tm_send_lobby_filled_pushes(db, lobby)
        else:
            await _tm_send_lobby_join_push(db, lobby, user_id, data.position)

        return _tm_serialize_lobby(db, lobby)

    except HTTPException:
        # Не логируем 4xx — это нормальные business-кейсы (заняли слот /
        # ранг не подходит / уже в лобби). 5xx внизу.
        raise
    except Exception as exc:
        logger.exception(
            "[tm/lobby/join] UNCAUGHT user_id=%s lobby_id=%s position=%s",
            user_id, lobby_id, data.position,
        )
        try: db.rollback()
        except Exception: pass
        raise HTTPException(
            status_code=500,
            detail=f"Внутренняя ошибка: {type(exc).__name__}: {str(exc)[:200]}",
        )


# ── L4. POST /api/teammates/lobby/{id}/leave ────────────────────────────────

@app.post("/api/teammates/lobby/{lobby_id}/leave")
async def api_teammates_lobby_leave(
    lobby_id: int, data: TeammateLobbyAction, db: Session = Depends(get_db),
):
    """Member выходит из своего слота. Если выходит host — это disband
    (но мы возвращаем 409 чтобы фронт явно вызвал /disband — UI там другой)."""
    user_id = _tm_authenticate(data.token, db)

    lobby = db.get(DBTeammateLobby, lobby_id)
    if lobby is None:
        raise HTTPException(status_code=404, detail="lobby not found")
    if lobby.status != "open":
        raise HTTPException(status_code=409, detail="lobby is no longer open")
    if lobby.host_id == user_id:
        raise HTTPException(
            status_code=409,
            detail="Host не может «выйти» — используй роспуск лобби.",
        )

    result = db.execute(
        text(
            """
            UPDATE teammate_lobby_slots
            SET user_id = NULL, joined_at = NULL
            WHERE lobby_id = :lid AND user_id = :uid
            """
        ),
        {"lid": lobby_id, "uid": user_id},
    )
    if not result.rowcount:
        db.commit()
        raise HTTPException(status_code=404, detail="ты не в этом лобби")

    db.commit()

    # Push'им host'у — «X вышел». Имя берём из user_profiles.settings.
    settings_map = _tm_load_user_settings(db, [user_id])
    leaver_s = settings_map.get(user_id) or {}
    leaver_name = (leaver_s.get("first_name") or "").strip() or "Игрок"
    open_url = f"{_TM_MINI_APP_URL}?tm_lobby={lobby.id}" if _TM_MINI_APP_URL else None
    await _tm_send_bot_message(
        chat_id=lobby.host_id,
        text=f"➖ <b>{_tm_html_safe(leaver_name)}</b> вышел из лобби",
        with_open_button=True,
        open_button_url=open_url,
        parse_mode="HTML",
    )

    return {"ok": True}


# ── L5. POST /api/teammates/lobby/{id}/disband ──────────────────────────────

@app.post("/api/teammates/lobby/{lobby_id}/disband")
async def api_teammates_lobby_disband(
    lobby_id: int, data: TeammateLobbyAction, db: Session = Depends(get_db),
):
    """Host распускает лобби. Members получают пуш."""
    user_id = _tm_authenticate(data.token, db)

    lobby = db.get(DBTeammateLobby, lobby_id)
    if lobby is None:
        raise HTTPException(status_code=404, detail="lobby not found")
    if lobby.host_id != user_id:
        raise HTTPException(status_code=403, detail="only host can disband")
    if lobby.status != "open":
        raise HTTPException(status_code=409, detail="lobby is no longer open")

    # Сначала push'им members (пока ещё видим состав), потом меняем status.
    await _tm_send_lobby_disband_pushes(db, lobby, by_host=True)

    lobby.status = "disbanded"
    db.commit()

    return {"ok": True}


# ── L6. GET /api/teammates/lobbies/history ──────────────────────────────────

@app.get("/api/teammates/lobbies/history")
def api_teammates_lobbies_history(
    token: str, db: Session = Depends(get_db),
):
    """История лобби, в которых юзер участвовал и которые ЗАПОЛНИЛИСЬ.

    Disbanded / expired не показываем — это «лобби не состоялось», а юзер
    хочет видеть «с кем играл». Без пагинации: hard cap 50 (на v1 этого
    хватит, плюс легко merge'ить с requests/history на фронте).
    """
    user_id = _tm_authenticate(token, db)

    # Берём id лобби в которых я участвовал (host ИЛИ занимал слот).
    my_lobby_ids_rows = db.execute(
        text(
            """
            SELECT DISTINCT l.id, l.filled_at
            FROM teammate_lobbies l
            LEFT JOIN teammate_lobby_slots s ON s.lobby_id = l.id
            WHERE l.status = 'filled'
              AND (l.host_id = :uid OR s.user_id = :uid)
            ORDER BY l.filled_at DESC
            LIMIT 50
            """
        ),
        {"uid": user_id},
    ).fetchall()

    lobby_ids = [r[0] for r in my_lobby_ids_rows]
    if not lobby_ids:
        return {"items": []}

    lobbies = (
        db.query(DBTeammateLobby)
        .filter(DBTeammateLobby.id.in_(lobby_ids))
        .all()
    )
    # Order according to my_lobby_ids_rows.
    lobby_by_id = {l.id: l for l in lobbies}

    # Batch slots.
    all_slots = (
        db.query(DBTeammateLobbySlot)
        .filter(DBTeammateLobbySlot.lobby_id.in_(lobby_ids))
        .all()
    )
    slots_by_lobby: dict[int, list[DBTeammateLobbySlot]] = {}
    for s in all_slots:
        slots_by_lobby.setdefault(s.lobby_id, []).append(s)

    items: list[dict] = []
    for lid, _filled_at in my_lobby_ids_rows:
        lobby = lobby_by_id.get(lid)
        if lobby is None:
            continue
        items.append(_tm_serialize_lobby(db, lobby, slots_by_lobby.get(lid, [])))
    return {"items": items}


# ═════════════════════════════════════════════════════════════════════════════
#  «Битва драфтов» — PvP-драфтер в реальном времени
# ═════════════════════════════════════════════════════════════════════════════
#
# Архитектура (анализ транспорта — в истории проекта):
#   • Состояние битвы только в PG (draft_battles + draft_battle_actions),
#     воркеры stateless — игроки могут попадать на разные воркеры.
#   • Доставка событий: long polling с версионным курсором (/battle/events)
#     + PG LISTEN/NOTIFY как межворкерная шина (backend/battle_bus.py).
#   • Время считает ТОЛЬКО сервер: deadline_at в БД; просрочка исполняется
#     ЛЕНИВО любым чтением/действием (висящие long-poll'ы сами будят таймауты
#     по дедлайну) — фоновый тикер не нужен.
#   • Мутации — def (threadpool, sync-сессии); /battle/events — async def
#     (реальные await шины), в БД ходит через asyncio.to_thread.

from types import SimpleNamespace as _BTEntry  # noqa: E402

from backend.database import SessionLocal  # noqa: E402
from backend.battle_bus import notify_battle_changed as _bt_notify  # noqa: E402
from backend.battle_bus import wait_for_change as _bt_wait  # noqa: E402
from backend.models import (  # noqa: E402
    DraftBattle as DBDraftBattle,
    DraftBattleAction as DBDraftBattleAction,
)

_BT_BAN_MS = 20_000          # основное время на бан
_BT_PICK_MS = 25_000         # основное время на пик
_BT_RESERVE_MS = 90_000      # доп. время на игрока на всю партию (как в CM; 120→90 2026-07-16)
_BT_ASSIGN_MS = 30_000       # общий таймер стадии расстановки позиций
# Стартовый отсчёт: таймер ПЕРВОГО хода начинает тикать через столько мс после
# матча — покрывает доставку матча второму игроку (его полл) + интерстишл.
_BT_START_COUNTDOWN_MS = 4_000
_BT_MAX_HOLD_SECONDS = 25.0  # удержание long-poll (< nginx proxy_read_timeout 60s)
# Протухание комнат в waiting/searching (env — тот же ключ, что раньше читал
# sweep в teammates_notifier; уборка теперь живёт здесь, см. _bt_sweep_loop).
_BT_WAITING_TTL_MIN = int(os.environ.get("BT_WAITING_TTL_MIN", "10"))
# drafting/assigning, чей дедлайн просрочен БОЛЕЕ чем на это — оба игрока ушли
# (активный поллинг исполняет просрочку максимум за один hold-цикл ~25с).
_BT_DEAD_GRACE_SEC = int(os.environ.get("BT_DEAD_GRACE_SEC", "120"))
_BT_SWEEP_INTERVAL_SEC = 60.0   # период фоновой уборки брошенных битв
_BT_MODES = ("cm", "ap")
# 'waiting' (легаси приватных комнат) исключён из активных: сервер такие
# строки больше не создаёт, а редкую древнюю добьёт sweep — она не должна
# блокировать «ты уже в активной битве». Ветки чтения ('waiting','searching')
# в timeouts/leave/sweep оставлены как дешёвая страховка чтения старых строк.
_BT_ACTIVE_STATUSES = ("searching", "drafting", "assigning")
# Позиционный штраф (счёт v2, 2026-07-16): доля матчей героя на назначенной
# позиции < 4% → «не позиция» (−12), < 12% → «редкий флекс» (−5), иначе 0.
# Источник долей — dota_builds (D2PT, обновляется юзером вручную). Пороги
# выверены глазами по всему ростеру (артефакт-ревизия): Abaddon-4 (14.5%)
# свободен, Viper-керри (4.4%) — мягкий, Medusa-4 (0%) — жёсткий.
# Лестница: штрафы сортируются по убыванию и умножаются на _BT_POS_LADDER —
# первая ошибка в полную цену, дальше с убыванием (решение юзера: −24 за две
# позиции «ломает окончательно»; максимум лестницы = −25 при пяти жёстких).
# Каждый шаг округляется до целого ОТДЕЛЬНО: по-геройные строки протокола
# обязаны сходиться с итогом штрафа один в один.
_BT_POS_HARD_SHARE = 0.04
_BT_POS_SOFT_SHARE = 0.12
_BT_POS_HARD_PENALTY = 12.0
_BT_POS_SOFT_PENALTY = 5.0
_BT_POS_LADDER = (1.0, 0.5, 0.25, 0.2, 0.15)
# Шкала синергии битвы (счёт v2): контрпик (0-50) — главный навык, синергия —
# второй план. Тренировка остаётся на 50 (сопоставимость лидерборда).
_BT_SYNERGY_SCALE = 25.0

# Последовательности ходов. Роли: 'F' — команда первого пика, 'S' — вторая.
# 'cm' — фазовая структура Captains Mode 7.34 (14 банов + 10 пиков; баны
# 3-2-2 у F / 4-1-2 у S, пики 1-3-1; S выбивает 4 героев до первого пика).
# Точный внутрифазовый порядок Valve не документирован — внутри фаз змейка,
# согласованная с этими свойствами. Правится в одном месте.
_BT_SEQ_CM: list[tuple[str, str]] = [
    # Ban phase 1 — F×3, S×4
    ("F", "ban"), ("S", "ban"), ("S", "ban"), ("F", "ban"),
    ("S", "ban"), ("S", "ban"), ("F", "ban"),
    # Pick phase 1 — 1-1
    ("F", "pick"), ("S", "pick"),
    # Ban phase 2 — S×1, F×2
    ("S", "ban"), ("F", "ban"), ("F", "ban"),
    # Pick phase 2 — 3-3 (продолжение змейки)
    ("S", "pick"), ("F", "pick"), ("F", "pick"),
    ("S", "pick"), ("S", "pick"), ("F", "pick"),
    # Ban phase 3 — 2-2
    ("F", "ban"), ("S", "ban"), ("F", "ban"), ("S", "ban"),
    # Pick phase 3 — 1-1
    ("F", "pick"), ("S", "pick"),
]
# 'ap' — без банов: 10 пиков чистой змейкой (та же пик-последовательность,
# что получается в 'cm', — оценки режимов сопоставимы).
_BT_SEQ_AP: list[tuple[str, str]] = [
    ("F", "pick"), ("S", "pick"), ("S", "pick"), ("F", "pick"), ("F", "pick"),
    ("S", "pick"), ("S", "pick"), ("F", "pick"), ("F", "pick"), ("S", "pick"),
]
# 'ap2' — этапный AP («как в рейтинговой Доте», 2026-07-16): очереди ходов
# НЕТ, оба пикают одновременно этапами 2-2-1, пики соперника в текущем этапе
# скрыты до вскрытия, коллизия = герой сгорает у обоих (kind='burn').
# Значение в _BT_SEQUENCES — только фолбэк для generic-мест (len и т.п.);
# вся логика ap2 идёт своими ветками (_bt_ap_*). Легаси-'ap' битвы,
# начатые до деплоя, доигрываются старым последовательным движком.
_BT_SEQUENCES = {"cm": _BT_SEQ_CM, "ap": _BT_SEQ_AP, "ap2": _BT_SEQ_AP}

_BT_AP2_MODE = "ap2"
_BT_AP_STAGES = (2, 2, 1)                      # пиков на игрока за этап
_BT_AP_STAGE_MS = (50_000, 50_000, 30_000)     # базовое время этапа
_BT_AP_REVEAL_MS = 2500                        # пауза-вскрытие между этапами
_BT_AP_BURN_GRACE_MS = 15_000                  # минимум времени на перепик после сгорания
# Рубильник: очередь 'ap' создаёт этапные битвы ap2 (фронт умеет с v309).
# BT_AP_STAGED=0 — аварийный откат на старый последовательный AP.
_BT_AP_STAGED = os.environ.get("BT_AP_STAGED", "1") == "1"

# Инвайт-код: без визуально похожих символов (0/O, 1/I/L).
_BT_CODE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"

# Объединённый мета-пул для авто-ходов по таймауту.
_BT_META_POOL: frozenset[int] = frozenset(
    h for pool in _DRAFT_POOLS_BY_POS.values() for h in pool
)

_bt_known_heroes_cache: "frozenset[int] | None" = None


def _bt_known_heroes() -> frozenset[int]:
    """Валидные hero_id = ключи hero_matchups.json (источник скоринга)."""
    global _bt_known_heroes_cache
    if _bt_known_heroes_cache is None:
        data = _load_hero_matchups_file() or {}
        ids = set()
        for k in data.keys():
            try:
                ids.add(int(k))
            except (TypeError, ValueError):
                continue
        _bt_known_heroes_cache = frozenset(ids) or _BT_META_POOL
    return _bt_known_heroes_cache


def _bt_now() -> datetime:
    return datetime.now(timezone.utc)


def _bt_log(event: str, *user_ids: int) -> None:
    """Серверная аналитика воронки битвы. Пишется на бэке (а не с фронта),
    чтобы события не терялись, когда игрок закрыл апп. log_event сам глотает
    ошибки (на dev-SQLite BigInteger PK не автоинкрементит — молча no-op,
    на PG — ок). Воронка: battle_queue → battle_start → battle_finish,
    battle_forfeit — отвал."""
    from backend.db import log_event as _log_event
    for uid in user_ids:
        if uid is not None:
            _log_event(event, uid)


def _bt_aware(dt):
    """SQLite (dev) возвращает naive datetime — нормализуем к UTC-aware,
    чтобы сравнения с _bt_now() работали кросс-БД."""
    if dt is not None and dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _bt_new_code(db: Session) -> str:
    import secrets as _secrets
    for _ in range(20):
        code = "".join(_secrets.choice(_BT_CODE_ALPHABET) for _ in range(6))
        exists = db.query(DBDraftBattle.id).filter(DBDraftBattle.code == code).first()
        if exists is None:
            return code
    raise HTTPException(status_code=500, detail="failed to allocate battle code")


def _bt_role(battle: DBDraftBattle, user_id: int):
    if battle.host_id == user_id:
        return "host"
    if battle.guest_id == user_id:
        return "guest"
    return None


def _bt_actor_of(battle: DBDraftBattle, idx: int) -> str:
    """Роль ('host'/'guest') актора хода idx по first_pick и последовательности."""
    seq = _BT_SEQUENCES[battle.mode]
    rel = seq[idx][0]   # 'F'/'S'
    if battle.first_pick == "host":
        return "host" if rel == "F" else "guest"
    return "guest" if rel == "F" else "host"


def _bt_base_ms(kind: str) -> int:
    return _BT_BAN_MS if kind == "ban" else _BT_PICK_MS


def _bt_reserve_ms(battle: DBDraftBattle, role: str) -> int:
    return battle.host_reserve_ms if role == "host" else battle.guest_reserve_ms


def _bt_set_reserve(battle: DBDraftBattle, role: str, value_ms: int) -> None:
    if role == "host":
        battle.host_reserve_ms = max(0, int(value_ms))
    else:
        battle.guest_reserve_ms = max(0, int(value_ms))


def _bt_start_turn(battle: DBDraftBattle, now: datetime, db: Session | None = None) -> None:
    """Старт хода turn_index: дедлайн = базовое время + остаток резерва актора.

    Резерв доступен С ПЕРВОГО хода (новичку сложно уложиться в базовые 25с —
    фидбек с прода). Но просрочка дедлайна = немедленное поражение актора
    (см. _bt_apply_timeouts) — бот больше НЕ драфтит за живого игрока.
    db не используется, оставлен в сигнатуре для совместимости вызовов.

    ap2: turn_index = номер ЭТАПА; дедлайн — ранний из персональных дедлайнов
    обоих игроков (оба пикают параллельно, у каждого свои часы)."""
    if battle.mode == _BT_AP2_MODE:
        battle.turn_started_at = now
        battle.deadline_at = now + _tm_timedelta(milliseconds=(
            _bt_ap_stage_base_ms(0)
            + min(battle.host_reserve_ms, battle.guest_reserve_ms)))
        return
    seq = _BT_SEQUENCES[battle.mode]
    if battle.turn_index >= len(seq):
        return
    actor = _bt_actor_of(battle, battle.turn_index)
    kind = seq[battle.turn_index][1]
    total_ms = _bt_base_ms(kind) + _bt_reserve_ms(battle, actor)
    battle.turn_started_at = now
    battle.deadline_at = now + _tm_timedelta(milliseconds=total_ms)


def _bt_taken_ids(db: Session, battle_id: int) -> set:
    rows = db.query(DBDraftBattleAction.hero_id).filter(
        DBDraftBattleAction.battle_id == battle_id
    ).all()
    return {r[0] for r in rows}


_bt_pos_shares_cache: "dict[int, dict[int, float]] | None" = None


def _bt_pos_shares() -> dict:
    """{hero_id: {pos: доля матчей героя на позиции}} из dota_builds.json."""
    global _bt_pos_shares_cache
    if _bt_pos_shares_cache is not None:
        return _bt_pos_shares_cache
    raw = _load_dota_builds_file() or {}
    out: dict[int, dict[int, float]] = {}
    for hid_str, positions in raw.items():
        if not isinstance(positions, dict):
            continue
        try:
            hid = int(hid_str)
        except ValueError:
            continue
        per_pos: dict[int, int] = {}
        for pk, pos_num in _DOTA_POS_URL_TO_NUM.items():
            pd = positions.get(pk)
            if isinstance(pd, dict):
                per_pos[pos_num] = int(pd.get("num_matches") or 0)
        total = sum(per_pos.values())
        if total > 0:
            out[hid] = {p: nm / total for p, nm in per_pos.items()}
    _bt_pos_shares_cache = out
    return out


def _bt_position_penalty_detail(positions: dict) -> tuple:
    """(суммарный штраф int <= 0, [{hero_id, pos, level, value}]) за
    несоответствие героев позициям.

    positions: {hero_id(int|str): pos(int)}. Герои без данных о позициях
    не штрафуются (бенефит сомнения — данные неполны, см. фидбек о флексах).
    Лестница _BT_POS_LADDER применяется к штрафам, отсортированным по
    убыванию; каждый шаг округляется отдельно (сумма строк = итог)."""
    shares = _bt_pos_shares()
    hits: list[dict] = []
    for hid, pos in (positions or {}).items():
        try:
            hid_i, pos_i = int(hid), int(pos)
        except (TypeError, ValueError):
            continue
        hero_shares = shares.get(hid_i)
        if not hero_shares:
            continue
        share = hero_shares.get(pos_i, 0.0)
        if share < _BT_POS_HARD_SHARE:
            hits.append({"hero_id": hid_i, "pos": pos_i, "level": "hard",
                         "base": _BT_POS_HARD_PENALTY, "share": share})
        elif share < _BT_POS_SOFT_SHARE:
            hits.append({"hero_id": hid_i, "pos": pos_i, "level": "soft",
                         "base": _BT_POS_SOFT_PENALTY, "share": share})
    hits.sort(key=lambda h: -h["base"])
    items = []
    total = 0
    for i, h in enumerate(hits):
        mult = _BT_POS_LADDER[i] if i < len(_BT_POS_LADDER) else _BT_POS_LADDER[-1]
        value = -int(h["base"] * mult + 0.5)
        total += value
        # share (в %) — для вкладки «Разбор»: «Medusa не играет 4 — 0% матчей».
        items.append({"hero_id": h["hero_id"], "pos": h["pos"],
                      "level": h["level"], "value": value,
                      "share": round(h["share"] * 100)})
    return total, items


def _bt_position_penalty(positions: dict) -> float:
    """Суммарный штраф (обратная совместимость: бот-пики/симуляции)."""
    return float(_bt_position_penalty_detail(positions)[0])


def _bt_pos_risk(pick_ids: list) -> dict:
    """{hero_id: {pos: 'soft'|'hard'}} — карта опасных позиций для пиков
    игрока (стадия расстановки, предупреждения на слотах). 'ok' опускается."""
    shares = _bt_pos_shares()
    out: dict[int, dict[int, str]] = {}
    for hid in pick_ids or []:
        hero_shares = shares.get(int(hid))
        if not hero_shares:
            continue
        risk = {}
        for pos in range(1, 6):
            share = hero_shares.get(pos, 0.0)
            if share < _BT_POS_HARD_SHARE:
                risk[pos] = "hard"
            elif share < _BT_POS_SOFT_SHARE:
                risk[pos] = "soft"
        if risk:
            out[int(hid)] = risk
    return out


# Мета-компонент УДАЛЁН из счёта (v2, 2026-07-16, решение юзера): вклад был
# крошечным (типично ±1–3, максимум ±8.4 идеальным стеком — проверено
# ред-тимом), а вопросов в протоколе вызывал много. Старые битвы хранят
# result.meta в payload — фронт рендерит строку условно, история не ломается.


def _bt_picks_of(db: Session, battle: DBDraftBattle, role: str) -> list:
    """Эффективные пики роли: сгоревшие в ap2 герои (kind='burn') — void."""
    rows = (
        db.query(DBDraftBattleAction)
        .filter(DBDraftBattleAction.battle_id == battle.id)
        .order_by(DBDraftBattleAction.idx)
        .all()
    )
    burned = {r.hero_id for r in rows if r.kind == "burn"}
    return [r.hero_id for r in rows
            if r.kind == "pick" and r.actor == role and r.hero_id not in burned]


def _bt_default_positions(pick_ids: list) -> dict:
    """Фолбэк для не успевших расставить: позиции в порядке пика.
    Нейтральный и предсказуемый (никакой «авто-меты» — решение игрока свято)."""
    return {str(h): i + 1 for i, h in enumerate(pick_ids[:5])}


def _bt_start_assign(battle: DBDraftBattle, now: datetime) -> None:
    """Драфт окончен → стадия расстановки: общий таймер _BT_ASSIGN_MS."""
    battle.status = "assigning"
    battle.turn_started_at = None
    battle.deadline_at = now + _tm_timedelta(milliseconds=_BT_ASSIGN_MS)
    battle.last_action_at = now


# ─────────────────────────────────────────────────────────────────────────────
#  Рейтинг «Битвы драфтов» — Elo с адаптивным K и поправкой на разгром.
#
#  Считается ТОЛЬКО за бои с живым соперником (is_bot=False). Бот-бои не двигают
#  рейтинг и не считаются в калибровку. Шкала намеренно крупная (дота-подобная):
#  начинаешь у _BT_RATING_BASE, пол — _BT_RATING_FLOOR, потолка нет (на практике
#  ограничен мастерством). Первые _BT_CALIBRATION_GAMES живых боёв — калибровка
#  (большой K → быстрый поиск своего уровня; ранг скрыт за бейджем «Калибровка»).
#
#  Все числа — в одной таблице ниже, чтобы крутить тюнинг без поиска по коду.
# ─────────────────────────────────────────────────────────────────────────────

_BT_RATING_BASE = 1000        # стартовый рейтинг (внутренний; скрыт на калибровке)
_BT_RATING_FLOOR = 0          # ниже не падает
_BT_ELO_DIVISOR = 1600.0      # насколько разрыв рейтинга влияет на шансы (≈9:1 на 1600)
_BT_K_CALIBRATION = 400       # K на калибровке — большие скачки
_BT_K_ESTABLISHED = 96        # K после калибровки — стабильно (~±50 за равный бой)
_BT_CALIBRATION_GAMES = 5     # сколько живых боёв длится калибровка (холодный старт; потом 10)
# Множитель за разгром (перекалиброван под целочисленный счёт v2 2026-07-17:
# тоталы 35-55, медианный отрыв ~10). Разрыв 10 → 1.0, потолок с 24, пол —
# сверхблизкие бои. Потолок опущен 1.5 → 1.35: в паре с Elo-асимметрией
# фаворита (окно подбора) 1.5 давал «−100 за поражение» на проде.
_BT_MARGIN_MIN = 0.7
_BT_MARGIN_MAX = 1.35
_BT_MARGIN_GAP_CENTER = 10    # отрыв в очках, при котором множитель = 1.0
_BT_MARGIN_GAP_SLOPE = 40     # +1 к множителю за каждые 40 очков отрыва
# Потолок сдвига за ОДИН бой: K=400 × разгром 1.5 при матче «любой с любым»
# (окно снято после 25с) теоретически даёт ±600 — один такой бой ломает
# доверие к числам. Клэмп держит худший случай в рамках здравого смысла.
_BT_RATING_DELTA_MAX = 350

# Ранги: (нижний порог рейтинга, ключ-ассет, отображаемое имя). По возрастанию.
# Пороги — гипотеза; подвинем по реальному распределению (один список — одна правка).
_BT_RANKS = [
    (0,    "pawn",      "Пешка"),
    (1000, "harbinger", "Предвестник"),
    (2200, "chosen",    "Избранный"),
    (3800, "overlord",  "Владыка"),
    (6000, "eternal",   "Вечный"),
]


def _bt_expected(rating_a: float, rating_b: float) -> float:
    """Ожидаемый счёт A против B по логистике Elo (0..1)."""
    return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / _BT_ELO_DIVISOR))


def _bt_k_factor(games_played: int) -> int:
    """K по числу УЖЕ сыгранных живых боёв: калибровка → большой, иначе обычный."""
    return _BT_K_CALIBRATION if games_played < _BT_CALIBRATION_GAMES else _BT_K_ESTABLISHED


def _bt_margin_mult(my_final, opp_final) -> float:
    """Множитель за разгром из счёта драфта. При форфейте (счёта нет) — 1.0.

    v2 (2026-07-17): по АБСОЛЮТНОМУ разрыву, не относительному. Старая формула
    |Δ|/сумма калибровалась под счета 60-80 на игрока; счёт v2 ужал тоталы до
    35-55 (и прибивает штрафами к нулю) — типичные бои стали «разгромными»
    (множитель 1.4-1.5 вместо ~1.1), и в паре с Elo-асимметрией фаворитов
    прод получил «+30 за победу / −100 за поражение». Абсолютный разрыв от
    целочисленного счёта стабилен: 10 очков → 1.0, 24+ → потолок."""
    if my_final is None or opp_final is None:
        return 1.0
    gap = abs((my_final or 0) - (opp_final or 0))
    m = 1.0 + (gap - _BT_MARGIN_GAP_CENTER) / _BT_MARGIN_GAP_SLOPE
    return max(_BT_MARGIN_MIN, min(_BT_MARGIN_MAX, m))


def _bt_rating_delta(my_rating, opp_rating, score: float, k: int, margin: float) -> int:
    """Изменение рейтинга за бой (клэмп ±_BT_RATING_DELTA_MAX).
    score: 1 победа / 0.5 ничья / 0 поражение."""
    expected = _bt_expected(my_rating, opp_rating)
    delta = round(k * margin * (score - expected))
    return max(-_BT_RATING_DELTA_MAX, min(_BT_RATING_DELTA_MAX, delta))


def _bt_apply_floor(rating: int) -> int:
    return max(_BT_RATING_FLOOR, rating)


def _bt_rank_for(rating: int) -> tuple:
    """(ключ-ассет, имя) ранга по рейтингу."""
    key, name = _BT_RANKS[0][1], _BT_RANKS[0][2]
    for threshold, k, n in _BT_RANKS:
        if rating >= threshold:
            key, name = k, n
        else:
            break
    return key, name


def _bt_is_calibrating(games_played: int) -> bool:
    return games_played < _BT_CALIBRATION_GAMES


def _bt_public_rank_key(rating, games_played) -> str:
    """Публичный ключ медали игрока: на калибровке настоящий ранг не палим."""
    if _bt_is_calibrating(games_played or 0):
        return "calibration"
    return _bt_rank_for(rating if rating is not None else _BT_RATING_BASE)[0]


# Подбор по рейтингу: окно расширяется по времени ожидания (чем дольше ждёт —
# тем шире берёт, чтобы никто не застрял в очереди навечно).
# Сужено 800/2000 → 400/1200 (2026-07-17): при выросшем онлайне и растянутой
# лестнице мгновенные пары «1450 vs 1050» стали нормой, а у фаворита Elo
# забирает за поражение вдвое-втрое больше, чем даёт за победу (прод-жалобы
# «+30/−100»). Узкое окно первых секунд — главный лечащий рычаг; после
# _BT_MATCH_WIDEN_2_SEC окно по-прежнему снимается совсем (никто не виснет).
_BT_MATCH_WINDOW_NEAR = 400    # свежий кандидат — только близкий по рейтингу
_BT_MATCH_WINDOW_MID = 1200    # подождал — окно шире
_BT_MATCH_WIDEN_1_SEC = 10
_BT_MATCH_WIDEN_2_SEC = 25
_BT_MATCH_SCAN_LIMIT = 20      # сколько кандидатов осматриваем за раз
# Тест-режим (staging): BT_MATCH_ANY=1 полностью выключает окно рейтинга —
# любые два игрока матчатся сразу. На проде НЕ ставить.
_BT_MATCH_ANY = os.environ.get("BT_MATCH_ANY", "0") == "1"


def _bt_match_window(wait_seconds: float):
    """Допустимый разрыв рейтинга для игрока, ждущего wait_seconds.
    None = любой (ждёт давно → берём кого угодно)."""
    if _BT_MATCH_ANY:
        return None
    if wait_seconds < _BT_MATCH_WIDEN_1_SEC:
        return _BT_MATCH_WINDOW_NEAR
    if wait_seconds < _BT_MATCH_WIDEN_2_SEC:
        return _BT_MATCH_WINDOW_MID
    return None


def _bt_player_rating(db: Session, user_id: int) -> int:
    """Текущий боевой рейтинг игрока (или база, если профиля/значения нет)."""
    r = (
        db.query(DBUserProfile.battle_rating)
        .filter(DBUserProfile.user_id == user_id)
        .scalar()
    )
    return r if r is not None else _BT_RATING_BASE


def _bt_apply_ratings(db: Session, battle: DBDraftBattle) -> None:
    """Пересчёт рейтинга обеих сторон по итогу боя. Пишет снимок в
    draft_battles.*_rating_before/after, обновляет user_profiles.battle_rating и
    battle_games_played. Идемпотентно (повторный вызов — no-op).

    Только живые бои: бот (is_bot) и бои без живого гостя рейтинг не трогают.
    Счёт сторон берётся из battle.winner (победа/ничья), разгром — из result.final
    (при форфейте final нет → нейтральный множитель). Каждый игрок калибруется
    независимо: K зависит от ЕГО battle_games_played до этого боя."""
    if battle.host_rating_after is not None:
        return   # уже применяли (двойная финализация/форфейт-гонка)
    if battle.is_bot or battle.guest_id is None:
        return   # бот/нет живого гостя — рейтинг не меняем
    if battle.is_friendly:
        return   # товарищеский матч: счёт настоящий, рейтинг не трогаем

    profiles = {
        p.user_id: p
        for p in db.query(DBUserProfile)
        .filter(DBUserProfile.user_id.in_([battle.host_id, battle.guest_id]))
        .with_for_update()
        .all()
    }
    host_p = profiles.get(battle.host_id)
    guest_p = profiles.get(battle.guest_id)
    if host_p is None or guest_p is None:
        return   # без обоих профилей рейтинг не считаем (страховка)

    host_r = host_p.battle_rating if host_p.battle_rating is not None else _BT_RATING_BASE
    guest_r = guest_p.battle_rating if guest_p.battle_rating is not None else _BT_RATING_BASE
    host_games = host_p.battle_games_played or 0
    guest_games = guest_p.battle_games_played or 0

    if battle.winner == "host":
        host_score, guest_score = 1.0, 0.0
    elif battle.winner == "guest":
        host_score, guest_score = 0.0, 1.0
    else:
        host_score, guest_score = 0.5, 0.5

    final = (battle.result or {}).get("final") or {}
    host_margin = _bt_margin_mult(final.get("host"), final.get("guest"))
    guest_margin = _bt_margin_mult(final.get("guest"), final.get("host"))

    host_delta = _bt_rating_delta(host_r, guest_r, host_score,
                                  _bt_k_factor(host_games), host_margin)
    guest_delta = _bt_rating_delta(guest_r, host_r, guest_score,
                                   _bt_k_factor(guest_games), guest_margin)

    host_new = _bt_apply_floor(host_r + host_delta)
    guest_new = _bt_apply_floor(guest_r + guest_delta)

    battle.host_rating_before, battle.host_rating_after = host_r, host_new
    battle.guest_rating_before, battle.guest_rating_after = guest_r, guest_new
    host_p.battle_rating = host_new
    guest_p.battle_rating = guest_new
    host_p.battle_games_played = host_games + 1
    guest_p.battle_games_played = guest_games + 1


def _bt_finalize(db: Session, battle: DBDraftBattle, now: datetime) -> None:
    """Обе раскладки готовы (или таймер стадии вышел): счёт через
    compute_draft_score (этап 0) + позиционный штраф каждой стороне."""
    host_picks = _bt_picks_of(db, battle, "host")
    guest_picks = _bt_picks_of(db, battle, "guest")

    host_pos = battle.host_positions or _bt_default_positions(host_picks)
    guest_pos = battle.guest_positions or _bt_default_positions(guest_picks)

    def _entries(ids, pos_map):
        return [
            _BTEntry(hero_id=h, position="pos " + str(pos_map.get(str(h), i + 1)))
            for i, h in enumerate(ids)
        ]

    # Счёт v2 (2026-07-16): контрпик — главный навык. Синергия 0–25 (шкала
    # sinergy_scale=25 против дефолтных 50 Тренировки), меты НЕТ (решение
    # юзера: крошечный вклад ±8, споры в протоколе), штрафы — лестницей.
    host_res = compute_draft_score(
        _entries(host_picks, host_pos), _entries(guest_picks, guest_pos),
        synergy_scale=_BT_SYNERGY_SCALE)
    guest_res = compute_draft_score(
        _entries(guest_picks, guest_pos), _entries(host_picks, host_pos),
        synergy_scale=_BT_SYNERGY_SCALE)

    host_pen, host_pen_items = _bt_position_penalty_detail(host_pos)
    guest_pen, guest_pen_items = _bt_position_penalty_detail(guest_pos)

    # ЦЕЛЫЕ ЧИСЛА на всех уровнях: каждый компонент округляется отдельно,
    # итог = сумма округлённых. Прод-жалобы: «синергия 10 + контрпики 10 +
    # мета 5 = 25, а на экране 24» — строки протокола обязаны сходиться
    # с итогом при сложении столбиком. Победитель — по этим же целым.
    host_syn, host_mu = round(host_res["synergy_score"]), round(host_res["matchup_score"])
    guest_syn, guest_mu = round(guest_res["synergy_score"]), round(guest_res["matchup_score"])
    host_final = max(0, host_syn + host_mu + host_pen)
    guest_final = max(0, guest_syn + guest_mu + guest_pen)

    if host_final > guest_final:
        battle.winner = "host"
    elif guest_final > host_final:
        battle.winner = "guest"
    else:
        battle.winner = "draw"
    battle.result = {
        "host": host_res,
        "guest": guest_res,
        # Целые компоненты для протокола (сходятся с final при сложении).
        "rows": {
            "host": {"synergy": host_syn, "matchup": host_mu, "penalty": host_pen},
            "guest": {"synergy": guest_syn, "matchup": guest_mu, "penalty": guest_pen},
        },
        "penalties": {"host": host_pen, "guest": guest_pen},
        # По-геройная расшифровка штрафа (лестница; сумма value = penalty).
        "penalty_items": {"host": host_pen_items, "guest": guest_pen_items},
        "final": {"host": host_final, "guest": guest_final},
        # Метаданные шкал: фронт подписывает «/25», «/50» и отличает v2
        # от старых битв (у тех есть result.meta и дробные компоненты).
        "scoring": {"v": 2, "synergy_max": int(_BT_SYNERGY_SCALE), "matchup_max": 50},
        # Раскладки вскрываются обоим только здесь, после финала.
        "positions": {"host": host_pos, "guest": guest_pos},
    }
    battle.status = "finished"
    battle.finished_at = now
    battle.deadline_at = None
    battle.turn_started_at = None
    # Рейтинг — до лога: пишет снимок в *_rating_*, двигает battle_rating
    # обоих (живой бой; бот — no-op). Идемпотентно по host_rating_after.
    _bt_apply_ratings(db, battle)
    # Один раз на битву: финализация ставит status='finished', повторные
    # _bt_apply_timeouts в эту ветку уже не входят.
    _bt_log("battle_finish", battle.host_id, battle.guest_id)


def _bt_insert_action(
    db: Session, battle: DBDraftBattle, actor: str, kind: str,
    hero_id: int, is_auto: bool, now: datetime,
) -> None:
    """Один ход: запись в журнал (PK (battle_id, idx) отсекает гонку двойного
    хода), продвижение указателя, старт следующего хода или финализация."""
    db.add(DBDraftBattleAction(
        battle_id=battle.id, idx=battle.turn_index,
        actor=actor, kind=kind, hero_id=hero_id,
        is_auto=is_auto, created_at=now,
    ))
    # flush ОБЯЗАТЕЛЕН (sessionmaker autoflush=False): дальше в этой же
    # транзакции ход должны видеть _bt_manual_moves/_bt_trailing_autos
    # (резерв следующего хода, AFK-детект). Гонка двойного idx всплывает
    # здесь же — ловится тем же except IntegrityError у бот-ходов.
    db.flush()
    battle.turn_index += 1
    battle.last_action_at = now
    battle.state_version += 1
    if battle.turn_index >= len(_BT_SEQUENCES[battle.mode]):
        # Драфт окончен — НЕ финализируем сразу: стадия расстановки позиций.
        _bt_start_assign(battle, now)
    else:
        _bt_start_turn(battle, now, db)


def _bt_auto_hero(db: Session, battle: DBDraftBattle) -> int:
    """Авто-ход по таймауту: случайный незанятый герой из мета-пула."""
    taken = _bt_taken_ids(db, battle.id)
    pool = list(_BT_META_POOL - taken) or list(_bt_known_heroes() - taken)
    return random.choice(pool)


def _bt_finish_timeout(db: Session, battle: DBDraftBattle, afk_role: str, now: datetime) -> None:
    """Завершение битвы по истёкшему времени актора: та же механика, что явная
    сдача (winner, рейтинг с нейтральным множителем), reason='timeout' для
    честного текста («время вышло», не обязательно AFK — мог и думать)."""
    battle.status = "finished"
    battle.winner = "guest" if afk_role == "host" else "host"
    battle.result = {"forfeit": afk_role, "reason": "timeout"}
    battle.finished_at = now
    battle.deadline_at = None
    battle.turn_started_at = None
    battle.state_version += 1   # разбудить long-poll соперника (ходов не было)
    _bt_apply_ratings(db, battle)
    _bt_log("battle_afk", battle.host_id if afk_role == "host" else battle.guest_id)


def _bt_apply_timeouts(db: Session, battle: DBDraftBattle, now: datetime) -> bool:
    """Ленивое исполнение просрочек. Возвращает True, если что-то изменилось.

    drafting: дедлайн хода включает базу + ВЕСЬ остаток резерва актора —
    просрочка значит «время игрока кончилось» → немедленное поражение
    (фидбек с прода: бот не должен драфтить за живого, а серия авто-ходов
    мучила соперника). Исключение — ход БОТА в бот-партии (догон, когда
    никто не поллил): исполняется авто-ходом, бот не может «проиграть по
    времени». waiting/searching: протухание комнаты по TTL.
    """
    changed = False
    if battle.status in ("waiting", "searching"):
        created = _bt_aware(battle.created_at)
        if created and now - created > _tm_timedelta(minutes=_BT_WAITING_TTL_MIN):
            battle.status = "abandoned"
            battle.state_version += 1
            changed = True
        return changed

    # Стадия расстановки: общий таймер вышел → не успевшие получают раскладку
    # «в порядке пика», финализируем.
    if battle.status == "assigning":
        if battle.deadline_at is not None and now >= _bt_aware(battle.deadline_at):
            _bt_finalize(db, battle, now)
            battle.state_version += 1
            changed = True
        return changed

    # Этапный драфт: своя логика просрочек (персональные дедлайны двоих).
    if battle.status == "drafting" and battle.mode == _BT_AP2_MODE:
        if (battle.deadline_at is not None
                and now >= _bt_aware(battle.deadline_at)):
            changed = _bt_ap_apply_timeouts(db, battle, now) or changed
        # Дальше — общий дожим assigning ниже.
    while (
        battle.status == "drafting"
        and battle.mode != _BT_AP2_MODE
        and battle.deadline_at is not None
        and now >= _bt_aware(battle.deadline_at)
    ):
        actor = _bt_actor_of(battle, battle.turn_index)
        moment = _bt_aware(battle.deadline_at)
        if battle.is_bot and actor == "guest":
            # Догон хода бота (никто не поллил): авто-ход, бот не «проигрывает
            # по времени». Момент — от истёкшего дедлайна, отсчёт честный.
            kind = _BT_SEQUENCES[battle.mode][battle.turn_index][1]
            _bt_set_reserve(battle, actor, 0)
            hero_id = _bt_auto_hero(db, battle)
            _bt_insert_action(db, battle, actor, kind, hero_id, True, moment)
            changed = True
            continue
        # Живой игрок: время (база + весь резерв) вышло → поражение сразу.
        _bt_set_reserve(battle, actor, 0)
        _bt_finish_timeout(db, battle, actor, moment)
        changed = True
        break

    # Авто-цепочка могла довести до стадии расстановки, чей дедлайн тоже уже
    # в прошлом (оба игрока отсутствовали) — дожимаем финализацию сразу.
    if (
        battle.status == "assigning"
        and battle.deadline_at is not None
        and now >= _bt_aware(battle.deadline_at)
    ):
        _bt_finalize(db, battle, now)
        battle.state_version += 1
        changed = True
    return changed


# ─────────────────────────────────────────────────────────────────────────────
#  Бот-соперник (подсаживается, когда живой не нашёлся за таймаут поиска).
#
#  Намеренно НЕ оптимальный: знает все числа из hero_matchups.json, но играет
#  «средне» — из подходящих по позиции кандидатов берёт не топ, а середину
#  (см. _BT_BOT_SKILL_*). Иначе обыграть бота невозможно и нет азарта. При этом
#  позиционно грамотен — пикает героев на их реальные позиции (не ловит штраф).
#  Роль бота всегда 'guest' (host = инициатор поиска, человек). Ходит лениво
#  на сервере: при чтении/поллинге, отстояв «думалку» _bt_think_ms.
# ─────────────────────────────────────────────────────────────────────────────

_BT_BOT_FALLBACK_SEC = 40        # сколько ищем живого, прежде чем подсадить бота
_BT_BOT_THINK_MIN_MS = 1200      # «думалка» бота на ход — нижняя граница
_BT_BOT_THINK_MAX_MS = 2800      # верхняя граница (детерминир. по ходу)
# Притупление: из кандидатов, отсортированных по силе убыв., бот берёт срез
# [SKILL_LO, SKILL_HI] перцентиля — т.е. крепкую середину, а не лучшее.
_BT_BOT_SKILL_LO = 0.30
_BT_BOT_SKILL_HI = 0.70
# Позиционная логика: кандидат на позицию — герой, играющий там не реже этого
# (та же планка, что soft-порог позиционного штрафа → бот штраф не ловит).
_BT_BOT_POS_MIN_SHARE = 0.15
# Порядок, в котором бот закрывает позиции (кор-роли раньше — их важнее
# застолбить, пока пул не разобран).
_BT_BOT_POS_ORDER = (2, 1, 3, 4, 5)

_bt_bot_pos_pool_cache: "dict[int, list[int]] | None" = None


def _bt_bot_pos_pool() -> dict:
    """{pos: [hero_id, ...]} — кто играбелен на позиции (share >= порога).
    Только известные герои (есть в hero_matchups.json → есть чем скорить)."""
    global _bt_bot_pos_pool_cache
    if _bt_bot_pos_pool_cache is not None:
        return _bt_bot_pos_pool_cache
    shares = _bt_pos_shares()
    known = _bt_known_heroes()
    out: dict[int, list[int]] = {p: [] for p in (1, 2, 3, 4, 5)}
    for hid, per_pos in shares.items():
        if hid not in known:
            continue
        for pos, share in per_pos.items():
            if share >= _BT_BOT_POS_MIN_SHARE:
                out[pos].append(hid)
    # Фолбэк для пустой позиции (нет данных) — мета-пул.
    for pos in out:
        if not out[pos]:
            out[pos] = [h for h in _BT_META_POOL if h in known] or list(known)
    _bt_bot_pos_pool_cache = out
    return out


def _bt_pair_val(matchups: dict, mapkey: str, a: int, b: int) -> float:
    return float((matchups.get(str(a)) or {}).get(mapkey, {})
                 .get(str(b), {}).get("synergy", 0.0))


def _bt_bot_cand_value(matchups: dict, cand: int,
                       ally: list, enemy: list) -> float:
    """Ценность кандидата для бота: синергия с союзниками (симметризовано) +
    матчап против врагов (антисимметрично) — та же арифметика, что
    compute_draft_score, но инкрементально по уже сделанным пикам."""
    val = 0.0
    for a in ally:
        val += (_bt_pair_val(matchups, "with", cand, a)
                + _bt_pair_val(matchups, "with", a, cand)) / 2
    for e in enemy:
        val += (_bt_pair_val(matchups, "vs", cand, e)
                - _bt_pair_val(matchups, "vs", e, cand)) / 2
    return val


def _bt_bot_picks_so_far(db: Session, battle: DBDraftBattle):
    """(ally=пики бота, enemy=пики человека, taken=все занятые id, bot_positions)."""
    actions = (
        db.query(DBDraftBattleAction)
        .filter(DBDraftBattleAction.battle_id == battle.id)
        .all()
    )
    taken = {a.hero_id for a in actions}
    ally = [a.hero_id for a in actions if a.kind == "pick" and a.actor == "guest"]
    enemy = [a.hero_id for a in actions if a.kind == "pick" and a.actor == "host"]
    return ally, enemy, taken


def _bt_bot_choose_pick(db: Session, battle: DBDraftBattle) -> tuple:
    """Возвращает (hero_id, pos): притуплённый выбор героя на ещё не закрытую
    ботом позицию. Бот = guest, его позиции копятся в guest_positions."""
    matchups = _load_hero_matchups_file() or {}
    ally, enemy, taken = _bt_bot_picks_so_far(db, battle)
    bot_pos = battle.guest_positions or {}
    used_positions = set(int(p) for p in bot_pos.values())

    pos_pool = _bt_bot_pos_pool()
    target_pos = next((p for p in _BT_BOT_POS_ORDER if p not in used_positions),
                      None)
    if target_pos is None:   # все 5 заняты (не должно случиться) — любой свободный
        target_pos = 1

    cands = [h for h in pos_pool.get(target_pos, []) if h not in taken]
    if not cands:   # позиция вычерпана банами — берём любого свободного известного
        cands = [h for h in _bt_known_heroes() if h not in taken]
    if not cands:
        cands = [h for h in _BT_META_POOL if h not in taken] or [next(iter(_bt_known_heroes()))]

    # Сортируем по ценности убыв. и берём из СРЕДНЕГО среза (притупление).
    scored = sorted(cands, key=lambda h: _bt_bot_cand_value(matchups, h, ally, enemy),
                    reverse=True)
    n = len(scored)
    lo = int(n * _BT_BOT_SKILL_LO)
    hi = max(lo + 1, int(n * _BT_BOT_SKILL_HI))
    mid_slice = scored[lo:hi] or scored
    return random.choice(mid_slice), target_pos


def _bt_bot_choose_ban(db: Session, battle: DBDraftBattle) -> int:
    """Бан бота — простой: случайный незанятый из мета-пула (бан-фаза слабо
    влияет на счёт, переусложнять незачем)."""
    _ally, _enemy, taken = _bt_bot_picks_so_far(db, battle)
    pool = [h for h in _BT_META_POOL if h not in taken] or \
           [h for h in _bt_known_heroes() if h not in taken]
    return random.choice(pool) if pool else next(iter(_bt_known_heroes()))


def _bt_think_ms(battle: DBDraftBattle, idx: int) -> int:
    """Детерминированная «думалка» бота на ход idx (стабильна между чтениями,
    иначе момент хода прыгал бы)."""
    h = (int(battle.id) * 131 + idx * 977) % 1000
    span = _BT_BOT_THINK_MAX_MS - _BT_BOT_THINK_MIN_MS
    return _BT_BOT_THINK_MIN_MS + h * span // 1000


def _bt_bot_due(battle: DBDraftBattle, now: datetime):
    """Если сейчас ход бота и он «надумал» — момент, когда ход должен исполниться
    (turn_started + думалка). Иначе None. Второй элемент — сколько ещё ждать (с)."""
    if not battle.is_bot or battle.status != "drafting":
        return None, None
    seq = _BT_SEQUENCES[battle.mode]
    if battle.turn_index >= len(seq):
        return None, None
    if _bt_actor_of(battle, battle.turn_index) != "guest":
        return None, None
    started = _bt_aware(battle.turn_started_at)
    if started is None:
        return None, None
    think = _bt_think_ms(battle, battle.turn_index)
    due_at = started + _tm_timedelta(milliseconds=think)
    if now >= due_at:
        return due_at, 0.0
    return None, (due_at - now).total_seconds()


def _bt_apply_bot_moves(db: Session, battle: DBDraftBattle, now: datetime) -> bool:
    """Лениво исполняет «надуманные» ходы бота (pick/ban). True, если сходил."""
    if not battle.is_bot:
        return False
    if battle.mode == _BT_AP2_MODE:
        return _bt_ap_bot_moves(db, battle, now)
    changed = False
    seq = _BT_SEQUENCES[battle.mode]
    while (
        battle.status == "drafting"
        and battle.turn_index < len(seq)
        and _bt_actor_of(battle, battle.turn_index) == "guest"
    ):
        due_at, _wait = _bt_bot_due(battle, now)
        if due_at is None:
            break   # бот ещё думает
        kind = seq[battle.turn_index][1]
        if kind == "pick":
            hero_id, pos = _bt_bot_choose_pick(db, battle)
        else:
            hero_id, pos = _bt_bot_choose_ban(db, battle), None
        try:
            # Ход стартует от момента «надумывания», не от now — честный отсчёт
            # при догоне цепочки ходов бота (напр. SS подряд).
            _bt_insert_action(db, battle, "guest", kind, hero_id, False, due_at)
        except IntegrityError:
            # Другой воркер уже сходил за бота на этот idx — откатываемся.
            db.rollback()
            return changed
        if kind == "pick":
            gp = dict(battle.guest_positions or {})
            gp[str(hero_id)] = pos
            battle.guest_positions = gp   # реассайн → SQLAlchemy увидит JSON-change
        changed = True
    return changed


# ─────────────────────────────────────────────────────────────────────────────
#  Этапный драфт ap2: оба игрока пикают ОДНОВРЕМЕННО этапами 2-2-1.
#
#  Модель: turn_index = номер этапа, turn_started_at = его старт (может быть
#  в будущем — пауза-вскрытие), deadline_at = ранний из персональных дедлайнов
#  незакончивших (персональный = старт + база этапа + остаток резерва игрока).
#  Пики соперника ТЕКУЩЕГО этапа скрыты (маскируются в сериализаторе) до
#  вскрытия. Коллизия (пикнул скрытого героя соперника) — герой СГОРАЕТ у
#  обоих: kind='burn' в журнале, пик жертвы становится void, обоим гарантия
#  минимум _BT_AP_BURN_GRACE_MS на перепик. Резерв списывается дельтой от
#  последнего своего действия этапа — двойное списание исключено.
# ─────────────────────────────────────────────────────────────────────────────

def _bt_ap_stage_base_ms(stage: int) -> int:
    return _BT_AP_STAGE_MS[min(stage, len(_BT_AP_STAGE_MS) - 1)]


def _bt_ap_cumq(stage: int) -> int:
    """Сколько эффективных пиков должно быть у игрока к КОНЦУ этапа stage."""
    return sum(_BT_AP_STAGES[:stage + 1])


def _bt_ap_view(db: Session, battle: DBDraftBattle) -> tuple:
    """(actions, burned:set, eff:{'host':[hero...],'guest':[...]}) — разбор
    журнала: сгоревшие герои и эффективные (не void) пики по ролям."""
    actions = (
        db.query(DBDraftBattleAction)
        .filter(DBDraftBattleAction.battle_id == battle.id)
        .order_by(DBDraftBattleAction.idx)
        .all()
    )
    burned = {a.hero_id for a in actions if a.kind == "burn"}
    eff = {"host": [], "guest": []}
    for a in actions:
        if a.kind == "pick" and a.hero_id not in burned:
            eff[a.actor].append(a.hero_id)
    return actions, burned, eff


def _bt_ap_personal_deadline(battle: DBDraftBattle, role: str, stage: int):
    started = _bt_aware(battle.turn_started_at)
    return started + _tm_timedelta(milliseconds=(
        _bt_ap_stage_base_ms(stage) + _bt_reserve_ms(battle, role)))


def _bt_ap_refresh_deadline(battle: DBDraftBattle, eff: dict) -> None:
    """deadline_at = ранний персональный дедлайн среди не закончивших этап."""
    stage = battle.turn_index
    need = _bt_ap_cumq(stage)
    pending = [r for r in ("host", "guest") if len(eff[r]) < need]
    if pending:
        battle.deadline_at = min(
            _bt_ap_personal_deadline(battle, r, stage) for r in pending)


def _bt_ap_insert(db: Session, battle: DBDraftBattle, actor: str, kind: str,
                  hero_id: int, now: datetime, n_actions: int) -> None:
    """Запись действия ap2 БЕЗ продвижения turn_index (этапом управляет
    _bt_ap_try_advance). idx = порядковый номер в журнале; гонка двух
    воркеров на один idx ловится PK (battle_id, idx)."""
    db.add(DBDraftBattleAction(
        battle_id=battle.id, idx=n_actions, actor=actor, kind=kind,
        hero_id=hero_id, is_auto=False, created_at=now,
    ))
    db.flush()
    battle.last_action_at = now
    battle.state_version += 1


def _bt_ap_charge_reserve(battle: DBDraftBattle, role: str, actions: list,
                          stage: int, now: datetime) -> None:
    """Списание резерва к моменту коммита: всё сверх базы этапа, ДЕЛЬТОЙ от
    последнего своего действия этого этапа (повторное списание исключено)."""
    started = _bt_aware(battle.turn_started_at)
    if started is None or now <= started:
        return
    base = _bt_ap_stage_base_ms(stage)
    elapsed = int((now - started).total_seconds() * 1000)
    prev = 0
    for a in actions:
        ts = _bt_aware(a.created_at)
        if a.actor == role and ts is not None and ts > started:
            prev = max(prev, int((ts - started).total_seconds() * 1000))
    charge = max(0, elapsed - base) - max(0, prev - base)
    if charge > 0:
        _bt_set_reserve(battle, role, _bt_reserve_ms(battle, role) - charge)


def _bt_ap_try_advance(db: Session, battle: DBDraftBattle, now: datetime,
                       eff: dict) -> None:
    """Оба закрыли квоту этапа → следующий этап (со вскрытием) или расстановка.
    Иначе — просто освежить deadline_at (мог закончить один из двоих)."""
    stage = battle.turn_index
    need = _bt_ap_cumq(stage)
    if len(eff["host"]) < need or len(eff["guest"]) < need:
        _bt_ap_refresh_deadline(battle, eff)
        return
    if stage + 1 >= len(_BT_AP_STAGES):
        _bt_start_assign(battle, now)
        return
    battle.turn_index = stage + 1
    battle.turn_started_at = now + _tm_timedelta(milliseconds=_BT_AP_REVEAL_MS)
    battle.state_version += 1
    _bt_ap_refresh_deadline(battle, eff)


def _bt_ap_action(db: Session, battle: DBDraftBattle, role: str,
                  hero_id: int, now: datetime) -> None:
    """Пик игрока в этапном драфте (вызов под FOR UPDATE из /battle/action)."""
    stage = battle.turn_index
    actions, burned, eff = _bt_ap_view(db, battle)
    started = _bt_aware(battle.turn_started_at)
    if started is None or now < started:
        raise HTTPException(status_code=409, detail="Этап ещё не начался.")
    if len(eff[role]) >= _bt_ap_cumq(stage):
        raise HTTPException(
            status_code=409, detail="Ты уже выбрал героев этапа — ждём соперника.")
    opp = "guest" if role == "host" else "host"
    prev_q = sum(_BT_AP_STAGES[:stage])
    opp_hidden = set(eff[opp][prev_q:])
    visible_taken = ({a.hero_id for a in actions} - opp_hidden)
    if hero_id in visible_taken:
        raise HTTPException(status_code=409, detail="Этот герой уже занят.")

    _bt_ap_charge_reserve(battle, role, actions, stage, now)

    if hero_id in opp_hidden:
        # Коллизия: оба выбрали одного героя — герой сгорает у обоих (как в
        # рейтинговой Доте). Пик соперника становится void, обоим — гарантия
        # времени на перепик (жертва могла «закончить» этап и уйти от экрана).
        _bt_ap_insert(db, battle, role, "burn", hero_id, now, len(actions))
        elapsed = int((now - started).total_seconds() * 1000)
        floor_reserve = elapsed - _bt_ap_stage_base_ms(stage) + _BT_AP_BURN_GRACE_MS
        for r in (role, opp):
            if _bt_reserve_ms(battle, r) < floor_reserve:
                _bt_set_reserve(battle, r, floor_reserve)
        # Бот-жертва: вернуть позицию сгоревшего в пул её ролей.
        if battle.is_bot and opp == "guest":
            gp = dict(battle.guest_positions or {})
            gp.pop(str(hero_id), None)
            battle.guest_positions = gp
        eff[opp] = [h for h in eff[opp] if h != hero_id]
        _bt_ap_refresh_deadline(battle, eff)
        return

    _bt_ap_insert(db, battle, role, "pick", hero_id, now, len(actions))
    eff[role].append(hero_id)
    _bt_ap_try_advance(db, battle, now, eff)


def _bt_ap_bot_moves(db: Session, battle: DBDraftBattle, now: datetime) -> bool:
    """Ленивые пики бота в этапном драфте: k-й пик этапа «надуман» после
    суммы думалок. True, если сходил."""
    if not battle.is_bot or battle.status != "drafting":
        return False
    changed = False
    for _ in range(6):
        if battle.status != "drafting":
            break
        stage = battle.turn_index
        actions, burned, eff = _bt_ap_view(db, battle)
        need = _bt_ap_cumq(stage)
        if len(eff["guest"]) >= need:
            break
        started = _bt_aware(battle.turn_started_at)
        if started is None:
            break
        prev_q = sum(_BT_AP_STAGES[:stage])
        k = len(eff["guest"]) - prev_q   # номер пика внутри этапа (0..)
        think = sum(_bt_think_ms(battle, prev_q + i) for i in range(k + 1))
        due = started + _tm_timedelta(milliseconds=think)
        if now < due:
            break
        try:
            hero_id, pos = _bt_bot_choose_pick(db, battle)
            _bt_ap_insert(db, battle, "guest", "pick", hero_id, due, len(actions))
        except IntegrityError:
            db.rollback()
            return changed
        gp = dict(battle.guest_positions or {})
        gp[str(hero_id)] = pos
        battle.guest_positions = gp
        eff["guest"].append(hero_id)
        _bt_ap_try_advance(db, battle, due, eff)
        changed = True
    return changed


def _bt_ap_bot_wait(db: Session, battle: DBDraftBattle, now: datetime):
    """Секунды до следующего «надуманного» пика бота в этапном драфте —
    будильник long-poll'а (иначе полл спит до дедлайна и ходы бота
    материализуются пачкой раз в hold-цикл). None — бот ходить не должен."""
    if not battle.is_bot or battle.status != "drafting":
        return None
    stage = battle.turn_index
    _actions, _burned, eff = _bt_ap_view(db, battle)
    if len(eff["guest"]) >= _bt_ap_cumq(stage):
        return None
    started = _bt_aware(battle.turn_started_at)
    if started is None:
        return None
    prev_q = sum(_BT_AP_STAGES[:stage])
    k = len(eff["guest"]) - prev_q
    think = sum(_bt_think_ms(battle, prev_q + i) for i in range(k + 1))
    due = started + _tm_timedelta(milliseconds=think)
    return max(0.05, (due - now).total_seconds())


def _bt_ap_apply_timeouts(db: Session, battle: DBDraftBattle, now: datetime) -> bool:
    """Просрочки этапного драфта: не закрыл квоту к персональному дедлайну →
    поражение (бот в бот-партии — добор авто-пиком, не проигрывает)."""
    changed = False
    for _ in range(8):
        if battle.status != "drafting":
            break
        stage = battle.turn_index
        actions, burned, eff = _bt_ap_view(db, battle)
        need = _bt_ap_cumq(stage)
        pending = [r for r in ("host", "guest") if len(eff[r]) < need]
        if not pending:
            # Оба готовы, но advance не случился (гонка/догон) — дожать.
            _bt_ap_try_advance(db, battle, now, eff)
            changed = True
            continue
        progressed = False
        # Просрочивший раньше — проигрывает первым (детерминизм).
        for role in sorted(pending,
                           key=lambda r: _bt_ap_personal_deadline(battle, r, stage)):
            deadline = _bt_ap_personal_deadline(battle, role, stage)
            if now < deadline:
                continue
            if battle.is_bot and role == "guest":
                hero_id, pos = _bt_bot_choose_pick(db, battle)
                _bt_ap_insert(db, battle, "guest", "pick", hero_id, deadline,
                              len(actions))
                gp = dict(battle.guest_positions or {})
                gp[str(hero_id)] = pos
                battle.guest_positions = gp
                eff["guest"].append(hero_id)
                _bt_ap_try_advance(db, battle, deadline, eff)
            else:
                _bt_set_reserve(battle, role, 0)
                _bt_finish_timeout(db, battle, role, deadline)
            changed = True
            progressed = True
            break
        if not progressed:
            break
    return changed


def _bt_tick_pending(battle: DBDraftBattle, now: datetime) -> bool:
    """Чистый предикат: «есть ли что исполнять в _bt_tick?» — зеркалит условия
    _bt_apply_timeouts + _bt_bot_due БЕЗ побочных эффектов и БЕЗ обращений к БД.

    Используется для double-checked locking в _bt_tick: сначала дешёвая проверка
    на нелоченном снимке (99% поллов — false, ни одного лока), и повторная —
    на свежей строке после FOR UPDATE. Пере-срабатывание безвредно (после лока
    решает настоящая логика), недо-срабатывание опасно (застрявшие таймауты) —
    поэтому условия тупо повторяют мутирующие ветки, без оптимизаций."""
    if battle.status in ("waiting", "searching"):
        created = _bt_aware(battle.created_at)
        return bool(
            created and now - created > _tm_timedelta(minutes=_BT_WAITING_TTL_MIN)
        )
    if battle.status in ("drafting", "assigning"):
        deadline = _bt_aware(battle.deadline_at)
        if deadline is not None and now >= deadline:
            return True
        # ap2: без БД не узнать, добрал ли бот квоту этапа — триггеримся всегда
        # после минимальной думалки (пере-срабатывание безвредно по контракту;
        # верхней границы нет — иначе догон бота после долгого сна не сработает).
        if battle.mode == _BT_AP2_MODE:
            if not battle.is_bot or battle.status != "drafting":
                return False
            started = _bt_aware(battle.turn_started_at)
            if started is None:
                return False
            return now >= started + _tm_timedelta(milliseconds=_BT_BOT_THINK_MIN_MS)
        due_at, _wait = _bt_bot_due(battle, now)
        return due_at is not None
    return False


def _bt_tick(db: Session, battle: DBDraftBattle, now: datetime) -> bool:
    """Единая «прокрутка» состояния: просрочки таймеров + ходы бота, до
    фикс-точки. Заменяет прямые вызовы _bt_apply_timeouts в эндпоинтах/поллинге.

    Гонко-безопасность (двойная финализация / lost-update): read-пути
    (/battle/events, /battle/state, /battle/active) читают битву обычным
    SELECT'ом. Мутировать на основе такого снимка нельзя — параллельный
    /battle/positions мог уже финализировать битву, и мы бы перезаписали его
    результат фолбэк-позициями и наложили второй Elo-сдвиг. Поэтому:
      1) дешёвый предикат на нелоченном снимке — обычно false, лока нет;
      2) сработал → db.refresh(with_for_update=True): ре-SELECT строки ПОД
         ЛОКОМ с перезаписью in-memory состояния (именно refresh — обычный
         query вернул бы тот же identity-mapped объект со старыми атрибутами);
      3) повторная проверка предиката на свежей строке — если другой воркер
         уже всё исполнил (finished), выходим без изменений.
    Пишущие эндпоинты и так держат FOR UPDATE — для них refresh это повторный
    SELECT в той же транзакции, дедлока нет."""
    if not _bt_tick_pending(battle, now):
        return False
    db.refresh(battle, with_for_update=True)
    if not _bt_tick_pending(battle, now):
        return False
    changed = False
    for _ in range(len(_BT_SEQUENCES[battle.mode]) + 2):
        c1 = _bt_apply_timeouts(db, battle, now)
        c2 = _bt_apply_bot_moves(db, battle, now)
        changed = changed or c1 or c2
        if not (c1 or c2):
            break
    return changed


def _bt_send_match_push_sync(host_id, guest_id, code: str) -> None:
    """Тело пуша «соперник найден» (sync httpx, до ~8с на два Telegram-вызова).
    Выполняется ТОЛЬКО в отдельном daemon-потоке — см. _bt_send_match_push."""
    if not BOT_TOKEN:
        return
    deep = f"{_TM_MINI_APP_URL}?battle={code}" if _TM_MINI_APP_URL else None
    payload_base = {
        "text": "⚔️ Соперник найден! Заходи в «Битву драфтов» — драфт уже идёт.",
        "disable_web_page_preview": True,
    }
    if deep:
        payload_base["reply_markup"] = {
            "inline_keyboard": [[{"text": "Открыть битву", "web_app": {"url": deep}}]]
        }
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    for chat_id in (host_id, guest_id):
        if chat_id is None:
            continue
        try:
            with httpx.Client(timeout=4.0) as client:
                client.post(url, json={**payload_base, "chat_id": chat_id})
        except Exception as e:
            logger.warning("[battle] match push to %s failed: %s", chat_id, e)


def _bt_send_match_push(host_id, guest_id, code: str) -> None:
    """Пуш «соперник найден» обоим участникам — fire-and-forget daemon-поток.

    Раньше sync httpx выполнялся прямо в вызывающем потоке: из /queue это
    блокировало воркер Starlette-threadpool'а, а из ленивого матчера
    (_bt_try_live_match ← _bt_poll_read ← asyncio.to_thread) — процесс-глобальный
    executor, общий для ВСЕХ to_thread-вызовов приложения. При деградации
    Telegram API (до ~8с на пару вызовов) это стопорило самый горячий путь
    (/battle/events). Отдельный короткоживущий поток изолирует пуш полностью;
    best-effort-семантика не меняется."""
    threading.Thread(
        target=_bt_send_match_push_sync,
        args=(host_id, guest_id, code),
        daemon=True,
        name="bt-match-push",
    ).start()


def _bt_start_battle_vs_bot(battle: DBDraftBattle, now: datetime) -> None:
    """Подсадка бота в зависшую searching-комнату. guest_id остаётся NULL.
    Стартовый отсчёт — как у живого матча (интерстишл не ест время игрока)."""
    battle.is_bot = True
    battle.status = "drafting"
    battle.first_pick = random.choice(("host", "guest"))
    battle.turn_index = 0
    battle.started_at = now
    battle.last_action_at = now
    battle.state_version += 1
    _bt_start_turn(battle, now + _tm_timedelta(milliseconds=_BT_START_COUNTDOWN_MS))
    _bt_log("battle_start", battle.host_id)
    _bt_log("battle_vs_bot", battle.host_id)


def _bt_serialize(db: Session, battle: DBDraftBattle, viewer_role, now: datetime) -> dict:
    seq = _BT_SEQUENCES[battle.mode]
    actions = (
        db.query(DBDraftBattleAction)
        .filter(DBDraftBattleAction.battle_id == battle.id)
        .order_by(DBDraftBattleAction.idx)
        .all()
    )

    ids = [battle.host_id] + ([battle.guest_id] if battle.guest_id else [])
    settings = _tm_load_user_settings(db, ids)
    # Ранг-медаль каждого игрока (на калибровке — 'calibration', ранг не палим).
    rank_rows = {
        r.user_id: (r.battle_rating, r.battle_games_played)
        for r in db.query(
            DBUserProfile.user_id,
            DBUserProfile.battle_rating,
            DBUserProfile.battle_games_played,
        ).filter(DBUserProfile.user_id.in_(ids)).all()
    }

    def _rank_key_of(uid):
        rating, games = rank_rows.get(uid, (None, 0))
        return _bt_public_rank_key(rating, games)

    def _player(uid):
        if uid is None:
            return None
        s = settings.get(uid) or {}
        return {
            "user_id": uid,
            "name": (s.get("first_name") or s.get("username") or "Игрок").strip() or "Игрок",
            "photo_url": s.get("photo_url"),
            "rank_key": _rank_key_of(uid),
        }

    # Бот занимает место гостя (guest_id NULL): отдаём его как «игрока-бота».
    # Медали у бота нет (rank_key None) — фронт её просто не рисует.
    def _guest_player():
        if battle.is_bot:
            return {"user_id": None, "name": "Бот", "photo_url": None,
                    "is_bot": True, "rank_key": None}
        return _player(battle.guest_id)

    # Стадия расстановки: общий таймер + кто уже отправил. Раскладка — ТОЛЬКО
    # своя (приватность до финала).
    assign = None
    if battle.status == "assigning":
        deadline = _bt_aware(battle.deadline_at)
        remaining = max(0, int((deadline - now).total_seconds() * 1000)) if deadline else 0
        my_pos = None
        if viewer_role == "host":
            my_pos = battle.host_positions
        elif viewer_role == "guest":
            my_pos = battle.guest_positions
        # Карта опасных позиций СВОИХ пиков — предупреждения на слотах
        # расстановки (счёт v2: жёсткий штраф не должен приходить сюрпризом).
        # Сгоревшие герои (ap2) — void, в раскладку не входят.
        _burned_a = {a.hero_id for a in actions if a.kind == "burn"}
        my_picks = [a.hero_id for a in actions
                    if a.kind == "pick" and a.actor == viewer_role
                    and a.hero_id not in _burned_a]
        assign = {
            "remaining_ms": remaining,
            "you_submitted": bool(my_pos),
            "opponent_submitted": bool(
                battle.guest_positions if viewer_role == "host" else battle.host_positions
            ),
            "your_positions": my_pos,
            "pos_risk": _bt_pos_risk(my_picks),
        }

    # ── Этапный драфт (ap2): блок stage + маскировка текущего этапа ─────────
    stage_block = None
    hidden_idx: set = set()
    if battle.mode == _BT_AP2_MODE and battle.status == "drafting":
        burned = {a.hero_id for a in actions if a.kind == "burn"}
        stage_i = battle.turn_index
        prev_q = sum(_BT_AP_STAGES[:stage_i])
        need = _bt_ap_cumq(stage_i)
        eff_rows = {"host": [], "guest": []}
        for a in actions:
            if a.kind == "pick" and a.hero_id not in burned:
                eff_rows[a.actor].append(a)
        # Скрываем эффективные пики ТЕКУЩЕГО этапа всех, кроме зрителя
        # (не-участнику скрыты обе стороны).
        for side in ("host", "guest"):
            if side == viewer_role:
                continue
            hidden_idx.update(a.idx for a in eff_rows[side][prev_q:])
        started = _bt_aware(battle.turn_started_at)
        starts_in = max(0, int((started - now).total_seconds() * 1000)) if started else 0
        elapsed_ms = max(0, int((now - started).total_seconds() * 1000)) if started else 0
        base_ms = _bt_ap_stage_base_ms(stage_i)
        opp_side = "guest" if viewer_role == "host" else "host"
        you_rows = eff_rows.get(viewer_role, []) if viewer_role in ("host", "guest") else []
        you_done = len(you_rows) >= need
        # Живое догорание резерва зрителя: сверх базы, дельтой от последнего
        # своего действия этапа (та же арифметика, что списание при коммите).
        my_reserve = _bt_reserve_ms(battle, viewer_role) if viewer_role in ("host", "guest") else 0
        reserve_disp = my_reserve
        if viewer_role in ("host", "guest") and not you_done and started is not None:
            prev_ms = 0
            for a in actions:
                ts = _bt_aware(a.created_at)
                if a.actor == viewer_role and ts is not None and ts > started:
                    prev_ms = max(prev_ms, int((ts - started).total_seconds() * 1000))
            live_burn = max(0, elapsed_ms - base_ms) - max(0, prev_ms - base_ms)
            reserve_disp = max(0, my_reserve - max(0, live_burn))
        stage_block = {
            "index": stage_i,
            "stages": list(_BT_AP_STAGES),
            "quota": _BT_AP_STAGES[stage_i],
            "starts_in_ms": starts_in,
            "base_ms": base_ms,
            "main_remaining_ms": max(0, base_ms - elapsed_ms),
            "reserve_remaining_ms": reserve_disp,
            "you_picked": len(you_rows[prev_q:]),
            "opp_picked": len(eff_rows[opp_side][prev_q:]),
            "you_done": you_done,
            "opp_done": len(eff_rows[opp_side]) >= need,
            "burned": sorted(burned),
        }

    current = None
    if (battle.status == "drafting" and battle.mode != _BT_AP2_MODE
            and battle.turn_index < len(seq)):
        actor = _bt_actor_of(battle, battle.turn_index)
        kind = seq[battle.turn_index][1]
        base_ms = _bt_base_ms(kind)
        started = _bt_aware(battle.turn_started_at)
        deadline = _bt_aware(battle.deadline_at)
        # Стартовый отсчёт: turn_started_at может быть в будущем (первый ход
        # после матча). До старта elapsed=0 (время не горит), а в total
        # отсчёт не включаем — фронт получает «останется на момент старта».
        starts_in = max(0, int((started - now).total_seconds() * 1000)) if started else 0
        elapsed_ms = max(0, int((now - started).total_seconds() * 1000)) if started else 0
        total_remaining = max(0, int((deadline - now).total_seconds() * 1000) - starts_in) if deadline else 0
        main_remaining = max(0, base_ms - elapsed_ms)
        # Остаток резерва актора С УЧЁТОМ уже горящего на этом ходе.
        reserve_now = min(_bt_reserve_ms(battle, actor),
                          max(0, total_remaining - main_remaining))
        current = {
            "actor": actor,
            "kind": kind,
            "starts_in_ms": starts_in,
            "main_remaining_ms": main_remaining,
            "reserve_remaining_ms": reserve_now,
            "total_remaining_ms": total_remaining,
        }

    # Изменение рейтинга «тебя» за этот бой — для «+N» на экране результата.
    # Только завершённый живой бой со снимком (бот рейтинг не двигает).
    you_rating = None
    if (
        viewer_role in ("host", "guest")
        and battle.status == "finished"
        and not battle.is_bot
    ):
        before = getattr(battle, viewer_role + "_rating_before")
        after = getattr(battle, viewer_role + "_rating_after")
        if after is not None and before is not None:
            rk_key, rk_name = _bt_rank_for(after)
            you_rating = {
                "before": before,
                "after": after,
                "delta": after - before,
                "rank_key": rk_key,
                "rank_name": rk_name,
            }

    return {
        "version": battle.state_version,
        "code": battle.code,
        "mode": battle.mode,
        "status": battle.status,
        "you": viewer_role,
        "vs_bot": bool(battle.is_bot),
        "friendly": bool(battle.is_friendly),
        "first_pick": battle.first_pick,
        "host": _player(battle.host_id),
        "guest": _guest_player(),
        "reserves": {
            "host_ms": battle.host_reserve_ms,
            "guest_ms": battle.guest_reserve_ms,
        },
        "turn_index": battle.turn_index,
        "sequence": ([] if battle.mode == _BT_AP2_MODE
                     else [{"actor_rel": a, "kind": k} for a, k in seq]),
        "current": current,
        "stage": stage_block,
        "assign": assign,
        "actions": [
            {"idx": a.idx, "actor": a.actor, "kind": a.kind,
             "hero_id": (None if a.idx in hidden_idx else a.hero_id),
             "hidden": a.idx in hidden_idx,
             "is_auto": bool(a.is_auto)}
            for a in actions
        ],
        "winner": battle.winner,
        "result": battle.result,
        "rating": you_rating,
    }


def _bt_get_battle(db: Session, code: str, for_update: bool = False) -> DBDraftBattle:
    q = db.query(DBDraftBattle).filter(DBDraftBattle.code == code.strip().upper())
    if for_update:
        q = q.with_for_update()
    battle = q.first()
    if battle is None:
        raise HTTPException(status_code=404, detail="battle not found")
    return battle


def _bt_active_battle(db: Session, user_id: int):
    return (
        db.query(DBDraftBattle)
        .filter(
            (DBDraftBattle.host_id == user_id) | (DBDraftBattle.guest_id == user_id)
        )
        .filter(DBDraftBattle.status.in_(_BT_ACTIVE_STATUSES))
        .order_by(DBDraftBattle.id.desc())
        .first()
    )


def _bt_draft_locked(db: Session, user_id: int) -> bool:
    """Анти-чит: занят ли юзер живой битвой (drafting/assigning).

    Используется блоком в /api/draft/evaluate. Прокручивает _bt_tick, чтобы
    мёртвая битва (просроченный дедлайн) финализировалась и замок снялся сам —
    никаких «вечных» блокировок. searching НЕ блокирует (в очереди можно
    теорикрафтить)."""
    battle = _bt_active_battle(db, user_id)
    if battle is None or battle.status not in ("drafting", "assigning"):
        return False
    now = _bt_now()
    if _bt_tick(db, battle, now):
        db.commit()
        _bt_notify(battle.id)
    return battle.status in ("drafting", "assigning")


def _bt_start_battle(battle: DBDraftBattle, guest_id: int, now: datetime) -> None:
    """Гость закреплён — жеребьёвка и первый ход (со стартовым отсчётом).

    Таймер первого хода стартует через _BT_START_COUNTDOWN_MS, а не сразу:
    матч исполняет ОДИН из игроков, второй узнаёт о нём своим поллом + оба
    смотрят интерстишл «Соперник найден» — без отсчёта эти секунды сгорали у
    первого пикера ещё до того, как он видел драфт."""
    battle.guest_id = guest_id
    battle.status = "drafting"
    battle.first_pick = random.choice(("host", "guest"))
    battle.turn_index = 0
    battle.started_at = now
    battle.last_action_at = now
    battle.state_version += 1
    _bt_start_turn(battle, now + _tm_timedelta(milliseconds=_BT_START_COUNTDOWN_MS))
    _bt_log("battle_start", battle.host_id, guest_id)


# ── Pydantic ────────────────────────────────────────────────────────────────

class BattleStartReq(BaseModel):
    token: str
    mode: str = "cm"          # 'cm' (с банами) / 'ap' (без банов)


class BattleCodeReq(BaseModel):
    token: str
    code: str
    # 'cancel_search' — отмена с экрана поиска: при гонке с матчером НЕ форфейт
    # (см. api_battle_leave). Отсутствует = явная сдача/обычный leave.
    intent: str | None = None


class BattleActionReq(BaseModel):
    token: str
    code: str
    hero_id: int


# ── Эндпоинты ───────────────────────────────────────────────────────────────

_bt_online_cache = {"n": 0, "at": 0.0}
_BT_ONLINE_TTL = 8.0   # счётчику онлайна секундная свежесть не нужна


@app.get("/api/battle/online")
def api_battle_online(token: str, db: Session = Depends(get_db)):
    """Сколько человек сейчас «в Битве драфтов»: участники активных битв —
    ищущие соперника (searching/waiting) + играющие (drafting/assigning).

    Кеш в памяти процесса на _BT_ONLINE_TTL: счётчик дёргается поллингом с
    экранов меню/поиска, точность до пары секунд не нужна. Расхождение между
    4 воркерами безвредно (число приблизительное). Считается честно — без
    накрутки: один человек = одна активная битва (инвариант), UNION дедупит."""
    _tm_require_user(token=token)
    now = time.time()
    if now - _bt_online_cache["at"] < _BT_ONLINE_TTL:
        return {"online": _bt_online_cache["n"]}
    row = db.execute(text(
        """
        SELECT COUNT(*) FROM (
            SELECT host_id AS uid FROM draft_battles
                WHERE status IN ('searching', 'waiting', 'drafting', 'assigning')
            UNION
            SELECT guest_id AS uid FROM draft_battles
                WHERE status IN ('drafting', 'assigning') AND guest_id IS NOT NULL
        ) t
        """
    )).fetchone()
    n = int(row[0]) if row else 0
    _bt_online_cache["n"] = n
    _bt_online_cache["at"] = now
    return {"online": n}


@app.get("/api/battle/active")
def api_battle_active(token: str, db: Session = Depends(get_db)):
    """Активная битва юзера (для resume при входе в раздел) или null."""
    uid = _tm_require_user(token=token)
    battle = _bt_active_battle(db, uid)
    if battle is None:
        return {"code": None}
    now = _bt_now()
    if _bt_tick(db, battle, now):
        db.commit()
        _bt_notify(battle.id)
        if battle.status not in _BT_ACTIVE_STATUSES:
            return {"code": None}
    return {"code": battle.code, "status": battle.status, "mode": battle.mode}


@app.post("/api/battle/queue")
def api_battle_queue(data: BattleStartReq, db: Session = Depends(get_db)):
    """Быстрый матч: атомарно забираем чужую searching-комнату того же режима
    или встаём в очередь своей. Гонка двух воркеров решается row-lock'ом
    (FOR UPDATE SKIP LOCKED на PG; dev-SQLite однопроцессный)."""
    uid = _tm_require_user(token=data.token)
    if data.mode not in _BT_MODES:
        raise HTTPException(status_code=422, detail="invalid mode")
    # Клиент знает только 'cm'/'ap'; при включённом рубильнике 'ap' создаёт
    # ЭТАПНЫЕ битвы (ap2). Легаси-'ap' комнаты в очереди новым не матчатся
    # (mode-фильтр ниже) и протухнут по TTL.
    if data.mode == "ap" and _BT_AP_STAGED:
        data.mode = _BT_AP2_MODE

    existing = _bt_active_battle(db, uid)
    if existing is not None:
        return {
            "code": existing.code,
            "status": existing.status,
            "matched": existing.status == "drafting",
        }

    # Намерение играть (existing уже отсеян выше — это не resume).
    _bt_log("battle_queue", uid)

    now = _bt_now()
    ttl_cutoff = now - _tm_timedelta(minutes=_BT_WAITING_TTL_MIN)
    # Подбор по рейтингу: осматриваем самых давно ждущих первыми (у них окно
    # шире — расширяется по их времени ожидания), берём первого в допуске.
    my_rating = _bt_player_rating(db, uid)
    scan = (
        db.query(DBDraftBattle)
        .filter(DBDraftBattle.status == "searching")
        .filter(DBDraftBattle.mode == data.mode)
        .filter(DBDraftBattle.host_id != uid)
        .filter(DBDraftBattle.created_at >= ttl_cutoff)
        .order_by(DBDraftBattle.created_at)   # дольше всех ждущие — первыми
        .with_for_update(skip_locked=True)
        .limit(_BT_MATCH_SCAN_LIMIT)
        .all()
    )
    host_ratings: dict[int, int] = {}
    if scan:
        for hid, hr in (
            db.query(DBUserProfile.user_id, DBUserProfile.battle_rating)
            .filter(DBUserProfile.user_id.in_([c.host_id for c in scan]))
            .all()
        ):
            host_ratings[hid] = hr if hr is not None else _BT_RATING_BASE

    candidate = None
    for c in scan:
        cand_rating = host_ratings.get(c.host_id, _BT_RATING_BASE)
        created = _bt_aware(c.created_at)
        wait = (now - created).total_seconds() if created else 0.0
        window = _bt_match_window(wait)
        if window is None or abs(my_rating - cand_rating) <= window:
            candidate = c
            break

    if candidate is not None:
        _bt_start_battle(candidate, uid, now)
        host_id, guest_id, code = candidate.host_id, uid, candidate.code
        db.commit()
        _bt_notify(candidate.id)
        _bt_send_match_push(host_id, guest_id, code)
        return {"code": code, "status": "drafting", "matched": True}

    battle = DBDraftBattle(
        code=_bt_new_code(db), mode=data.mode, status="searching",
        host_id=uid, host_reserve_ms=_BT_RESERVE_MS, guest_reserve_ms=_BT_RESERVE_MS,
        created_at=now,
    )
    db.add(battle)
    db.commit()
    return {"code": battle.code, "status": "searching", "matched": False}


_bt_bot_username_cache: str | None = None


def _bt_bot_username() -> str | None:
    """Username бота через getMe (кэш на процесс) — для ссылки-вызова.
    API-процесс не знает своё имя из конфига, но владеет BOT_TOKEN."""
    global _bt_bot_username_cache
    if _bt_bot_username_cache:
        return _bt_bot_username_cache
    if not BOT_TOKEN:
        return None
    try:
        r = httpx.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getMe", timeout=3)
        username = ((r.json() or {}).get("result") or {}).get("username")
        if username:
            _bt_bot_username_cache = username
        return username
    except Exception as e:
        logger.warning("[battle] getMe failed: %s", e)
        return None


def _bt_prepare_invite_message(uid: int, code: str, invite_url: str):
    """PreparedInlineMessage для shareMessage: карточка вызова с инлайн-кнопкой
    «Принять вызов» прямо в сообщении (вместо голой ссылки текстом).
    None при любой ошибке — фронт откатится на t.me/share/url."""
    if not BOT_TOKEN:
        return None
    result = {
        "type": "article",
        "id": f"ch_{code}",
        "title": "Вызов на битву драфтов",
        "description": "Товарищеский матч 1×1 в D2Helper",
        "input_message_content": {
            "message_text": (
                "⚔️ <b>Вызов на битву драфтов!</b>\n"
                "Товарищеский матч в D2Helper — рейтинг не на кону, только гордость."
            ),
            "parse_mode": "HTML",
        },
        "reply_markup": {"inline_keyboard": [[
            {"text": "⚔️ Принять вызов", "url": invite_url}
        ]]},
    }
    try:
        r = httpx.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/savePreparedInlineMessage",
            json={"user_id": uid, "result": result,
                  "allow_user_chats": True, "allow_group_chats": True},
            timeout=3,
        )
        d = r.json()
        if d.get("ok"):
            return ((d.get("result") or {}).get("id"))
        logger.warning("[battle] savePreparedInlineMessage rejected: %s", d)
    except Exception as e:
        logger.warning("[battle] savePreparedInlineMessage failed: %s", e)
    return None


@app.post("/api/battle/challenge")
def api_battle_challenge(data: BattleStartReq, db: Session = Depends(get_db)):
    """«Сыграть с другом»: приватная товарищеская комната + ссылка-вызов.

    Ссылка ведёт в БОТА (t.me/<bot>?start=db_КОД), не напрямую в мини-апп:
    /start бота держит гейт обязательных подписок — вызов от друга не должен
    его обходить (прямой startapp-линк открыл бы апп без подписок). Рейтинг
    товарищеские бои не двигают (win-trading через твинков)."""
    uid = _tm_require_user(token=data.token)
    if data.mode not in _BT_MODES:
        raise HTTPException(status_code=422, detail="invalid mode")
    mode = _BT_AP2_MODE if (data.mode == "ap" and _BT_AP_STAGED) else data.mode

    existing = _bt_active_battle(db, uid)
    if existing is not None:
        raise HTTPException(status_code=409, detail="Сначала закончи текущую битву.")
    # Прошлый неиспользованный вызов — гасим, чтобы не копить комнаты
    # (waiting не входит в active-статусы и не блокирует, но зомби не нужны).
    db.query(DBDraftBattle).filter(
        DBDraftBattle.host_id == uid,
        DBDraftBattle.status == "waiting",
    ).update({"status": "abandoned"}, synchronize_session=False)

    now = _bt_now()
    battle = DBDraftBattle(
        code=_bt_new_code(db), mode=mode, status="waiting",
        host_id=uid, is_friendly=True,
        host_reserve_ms=_BT_RESERVE_MS, guest_reserve_ms=_BT_RESERVE_MS,
        created_at=now,
    )
    db.add(battle)
    db.commit()

    username = _bt_bot_username()
    invite_url = f"https://t.me/{username}?start=db_{battle.code}" if username else None
    # Красивое сообщение-вызов с КНОПКОЙ (Bot API 8.0, prepared inline message):
    # фронт отправит его через Telegram.WebApp.shareMessage. Best-effort —
    # без него фронт падает на обычный t.me/share/url со ссылкой текстом.
    prepared_id = _bt_prepare_invite_message(uid, battle.code, invite_url) if invite_url else None
    return {"code": battle.code, "invite_url": invite_url,
            "prepared_msg_id": prepared_id, "ttl_min": _BT_WAITING_TTL_MIN}


@app.post("/api/battle/join")
def api_battle_join(data: BattleCodeReq, db: Session = Depends(get_db)):
    """Вход по коду: RESUME своей битвы ИЛИ приём товарищеского вызова.

    Вызов друга («Сыграть с другом», 2026-07-17): комната status='waiting'
    + is_friendly, друг приходит по deep-link `?battle=КОД` из шаринга.
    Клейм под FOR UPDATE (двое из группового чата тапнули одновременно —
    второй получает «вызов уже принят»). Прочие чужие коды → 409, как раньше."""
    uid = _tm_require_user(token=data.token)
    code = (data.code or "").strip().upper()
    battle = _bt_get_battle(db, code)

    role = _bt_role(battle, uid)
    if role is not None:
        return {"code": battle.code, "status": battle.status, "you": role}

    if not (battle.status == "waiting" and battle.is_friendly):
        raise HTTPException(
            status_code=409,
            detail="Войти можно только через быстрый поиск соперника.",
        )

    # Приём вызова: гость не должен сидеть в другой активной битве.
    mine = _bt_active_battle(db, uid)
    if mine is not None:
        raise HTTPException(
            status_code=409,
            detail="Сначала закончи свою текущую битву.",
        )
    now = _bt_now()
    locked = _bt_get_battle(db, code, for_update=True)
    if locked.status != "waiting" or locked.guest_id is not None:
        raise HTTPException(status_code=409, detail="Вызов уже принят или отменён.")
    created = _bt_aware(locked.created_at)
    if created and now - created > _tm_timedelta(minutes=_BT_WAITING_TTL_MIN):
        raise HTTPException(status_code=409, detail="Приглашение устарело.")
    # Хост мог бросить комнату и уйти в другую битву — вызов мёртв.
    host_busy = (
        db.query(DBDraftBattle.id)
        .filter((DBDraftBattle.host_id == locked.host_id)
                | (DBDraftBattle.guest_id == locked.host_id))
        .filter(DBDraftBattle.status.in_(("drafting", "assigning")))
        .first()
    )
    if host_busy is not None:
        raise HTTPException(status_code=409, detail="Приглашение устарело.")
    _bt_start_battle(locked, uid, now)
    db.commit()
    _bt_notify(locked.id)
    return {"code": locked.code, "status": locked.status, "you": "guest"}


@app.get("/api/battle/history")
def api_battle_history(token: str, limit: int = 20, db: Session = Depends(get_db)):
    """Последние завершённые битвы игрока — лента истории на экране меню.

    Отдаёт компактную строку на битву (исход, счёт, соперник, дата + снимок
    рейтинга — пока NULL, задел под этап рейтинга). Полный разбор открывается
    тапом по строке: фронт переоткрывает результат через /battle/state по code.
    Бот-битвы включены (на холодном старте это большинство партий) с пометкой."""
    uid = _tm_require_user(token=token)
    limit = max(1, min(int(limit), 50))

    rows = (
        db.query(DBDraftBattle)
        .filter(DBDraftBattle.status == "finished")
        .filter((DBDraftBattle.host_id == uid) | (DBDraftBattle.guest_id == uid))
        .order_by(DBDraftBattle.finished_at.desc())
        .limit(limit)
        .all()
    )

    # Резолвим имена/аватары/ранги живых соперников батчем.
    opp_ids = []
    for b in rows:
        opp_id = b.guest_id if b.host_id == uid else b.host_id
        if opp_id:
            opp_ids.append(opp_id)
    settings = _tm_load_user_settings(db, opp_ids) if opp_ids else {}
    opp_ranks: dict[int, str] = {}
    if opp_ids:
        for r_uid, r_rating, r_games in (
            db.query(
                DBUserProfile.user_id,
                DBUserProfile.battle_rating,
                DBUserProfile.battle_games_played,
            ).filter(DBUserProfile.user_id.in_(opp_ids)).all()
        ):
            opp_ranks[r_uid] = _bt_public_rank_key(r_rating, r_games)

    out = []
    for b in rows:
        my_role = "host" if b.host_id == uid else "guest"
        opp_role = "guest" if my_role == "host" else "host"
        vs_bot = bool(b.is_bot and opp_role == "guest")

        if vs_bot:
            opponent = {"name": "Бот", "photo_url": None, "is_bot": True,
                        "rank_key": None}
        else:
            opp_id = b.guest_id if my_role == "host" else b.host_id
            s = settings.get(opp_id) or {}
            opponent = {
                "name": (s.get("first_name") or s.get("username") or "Игрок").strip() or "Игрок",
                "photo_url": s.get("photo_url"),
                "is_bot": False,
                "rank_key": opp_ranks.get(opp_id),
            }

        res = b.result or {}
        final = res.get("final") or {}
        forfeit_role = res.get("forfeit")  # роль сдавшегося, если форфейт

        if b.winner == "draw":
            outcome = "draw"
        elif b.winner == my_role:
            outcome = "win"
        elif b.winner in ("host", "guest"):
            outcome = "loss"
        else:
            outcome = "draw"

        out.append({
            "code": b.code,
            "mode": b.mode,
            "finished_at": b.finished_at.isoformat() if b.finished_at else None,
            "opponent": opponent,
            "vs_bot": vs_bot,
            "friendly": bool(b.is_friendly),
            "outcome": outcome,
            "forfeit": forfeit_role is not None,
            "forfeit_reason": res.get("reason"),
            "your_score": final.get(my_role),
            "opp_score": final.get(opp_role),
            "rating_before": getattr(b, f"{my_role}_rating_before", None),
            "rating_after": getattr(b, f"{my_role}_rating_after", None),
        })

    return {"battles": out}


@app.get("/api/battle/profile")
def api_battle_profile(token: str, db: Session = Depends(get_db)):
    """Рейтинговый профиль игрока для меню битвы: текущий рейтинг, ранг и
    состояние калибровки. На калибровке ранг отдаём как «Калибровка» (отдельный
    бейдж, не Пешка) — фронт решает, показывать ли число."""
    uid = _tm_require_user(token=token)
    p = (
        db.query(DBUserProfile.battle_rating, DBUserProfile.battle_games_played)
        .filter(DBUserProfile.user_id == uid)
        .first()
    )
    rating = (p.battle_rating if p and p.battle_rating is not None else _BT_RATING_BASE)
    games = (p.battle_games_played if p and p.battle_games_played is not None else 0)
    calibrating = _bt_is_calibrating(games)
    key, name = _bt_rank_for(rating)

    next_rank_at = None
    for threshold, _k, _n in _BT_RANKS:
        if threshold > rating:
            next_rank_at = threshold
            break

    return {
        "rating": rating,
        "rank_key": "calibration" if calibrating else key,
        "rank_name": "Калибровка" if calibrating else name,
        "calibrating": calibrating,
        "games_played": games,
        "calibration_total": _BT_CALIBRATION_GAMES,
        "next_rank_at": next_rank_at,
    }


@app.get("/api/battle/leaderboard")
def api_battle_leaderboard(token: str, db: Session = Depends(get_db)):
    """Лестница рангов: топ-N на КАЖДУЮ секцию ранга с ГЛОБАЛЬНЫМИ местами.

    Раньше отдавался глобальный топ-25 — с ростом пула все 25 лучших стали
    Предвестником+ и секция «Пешка» на витрине опустела (пешки в глобальный
    топ не влезают по определению). Секционная витрина требует представителей
    каждого ранга. Забаненные исключены; you — место среди established."""
    uid = _tm_require_user(token=token)
    banned = set(get_banned_user_ids())
    PER_TIER = 10

    rows = (
        db.query(
            DBUserProfile.user_id,
            DBUserProfile.battle_rating,
            DBUserProfile.battle_games_played,
            DBUserProfile.settings,
        )
        .filter(DBUserProfile.battle_games_played >= _BT_CALIBRATION_GAMES)
        .order_by(DBUserProfile.battle_rating.desc(), DBUserProfile.user_id)
        .limit(2000)
        .all()
    )
    rows = [r for r in rows if r.user_id not in banned]

    # Глобальное место (после исключения banned) + отсев по PER_TIER на ранг.
    top = []
    tier_counts: dict[str, int] = {}
    for place, r in enumerate(rows, start=1):
        rating = r.battle_rating if r.battle_rating is not None else _BT_RATING_BASE
        key = _bt_public_rank_key(rating, r.battle_games_played)
        if tier_counts.get(key, 0) >= PER_TIER:
            continue
        tier_counts[key] = tier_counts.get(key, 0) + 1
        s = r.settings or {}
        top.append({
            "place": place,
            "name": (s.get("first_name") or s.get("username") or "Игрок").strip() or "Игрок",
            "photo_url": s.get("photo_url"),
            "rank_key": key,
            "rating": rating,
            "you": r.user_id == uid,
        })

    me = (
        db.query(DBUserProfile.battle_rating, DBUserProfile.battle_games_played)
        .filter(DBUserProfile.user_id == uid)
        .first()
    )
    my_rating = (me.battle_rating if me and me.battle_rating is not None else _BT_RATING_BASE)
    my_games = (me.battle_games_played if me and me.battle_games_played is not None else 0)
    you = {
        "rating": my_rating,
        "rank_key": _bt_public_rank_key(my_rating, my_games),
        "calibrating": _bt_is_calibrating(my_games),
        "games_played": my_games,
        "calibration_total": _BT_CALIBRATION_GAMES,
        "rank": None,
    }
    if not you["calibrating"] and uid not in banned:
        # Место = сколько established строго выше + 1 (среди незабаненных).
        higher = (
            db.query(DBUserProfile.user_id, DBUserProfile.battle_rating)
            .filter(DBUserProfile.battle_games_played >= _BT_CALIBRATION_GAMES)
            .filter(DBUserProfile.battle_rating > my_rating)
            .all()
        )
        you["rank"] = sum(1 for h in higher if h.user_id not in banned) + 1

    return {"top": top, "you": you, "total": len(rows)}


@app.post("/api/battle/action")
def api_battle_action(data: BattleActionReq, db: Session = Depends(get_db)):
    """Ход (пик или бан — тип диктует последовательность)."""
    uid = _tm_require_user(token=data.token)
    battle = _bt_get_battle(db, data.code, for_update=True)
    role = _bt_role(battle, uid)
    if role is None:
        raise HTTPException(status_code=403, detail="not a participant")

    now = _bt_now()
    if _bt_tick(db, battle, now):
        db.commit()
        _bt_notify(battle.id)
        # Состояние ушло — клиент перечитает; его клик уже неактуален.
        raise HTTPException(status_code=409, detail="Ход истёк по таймеру.")

    if battle.status != "drafting":
        raise HTTPException(status_code=409, detail="Битва не в фазе драфта.")
    if data.hero_id not in _bt_known_heroes():
        raise HTTPException(status_code=422, detail="unknown hero_id")

    # Этапный драфт: своя валидация (квоты, скрытые пики, сгорание).
    if battle.mode == _BT_AP2_MODE:
        _bt_ap_action(db, battle, role, data.hero_id, now)
        db.commit()
        _bt_notify(battle.id)
        return _bt_serialize(db, battle, role, now)

    if _bt_actor_of(battle, battle.turn_index) != role:
        raise HTTPException(status_code=409, detail="Сейчас ход соперника.")
    if data.hero_id in _bt_taken_ids(db, battle.id):
        raise HTTPException(status_code=409, detail="Этот герой уже занят.")

    kind = _BT_SEQUENCES[battle.mode][battle.turn_index][1]
    # Списание резерва: всё, что сверх базового времени хода.
    started = _bt_aware(battle.turn_started_at)
    if started is not None:
        overflow_ms = int((now - started).total_seconds() * 1000) - _bt_base_ms(kind)
        if overflow_ms > 0:
            _bt_set_reserve(battle, role, _bt_reserve_ms(battle, role) - overflow_ms)

    _bt_insert_action(db, battle, role, kind, data.hero_id, False, now)
    db.commit()
    _bt_notify(battle.id)
    return _bt_serialize(db, battle, role, now)


class BattlePositionsReq(BaseModel):
    token: str
    code: str
    positions: dict[str, int]   # {hero_id(str): pos(1..5)}


@app.post("/api/battle/positions")
def api_battle_positions(data: BattlePositionsReq, db: Session = Depends(get_db)):
    """Стадия расстановки: игрок отправляет раскладку СВОИХ пиков по позициям.

    Перезапись разрешена, пока стадия не закрыта. Обе раскладки на месте →
    немедленная финализация (не ждём таймер). Раскладка валидируется жёстко:
    ровно свои 5 героев, позиции 1-5 без повторов."""
    uid = _tm_require_user(token=data.token)
    battle = _bt_get_battle(db, data.code, for_update=True)
    role = _bt_role(battle, uid)
    if role is None:
        raise HTTPException(status_code=403, detail="not a participant")

    now = _bt_now()
    if _bt_tick(db, battle, now):
        db.commit()
        _bt_notify(battle.id)
        raise HTTPException(status_code=409, detail="Время расстановки вышло.")
    if battle.status != "assigning":
        raise HTTPException(status_code=409, detail="Сейчас не стадия расстановки.")

    my_picks = _bt_picks_of(db, battle, role)
    try:
        pos_map = {str(int(k)): int(v) for k, v in (data.positions or {}).items()}
    except (TypeError, ValueError):
        raise HTTPException(status_code=422, detail="bad positions payload")
    if set(pos_map.keys()) != {str(h) for h in my_picks}:
        raise HTTPException(status_code=422, detail="positions must cover exactly your picks")
    if sorted(pos_map.values()) != list(range(1, len(my_picks) + 1)):
        raise HTTPException(status_code=422, detail="each position 1..5 must be used exactly once")

    if role == "host":
        battle.host_positions = pos_map
    else:
        battle.guest_positions = pos_map
    battle.state_version += 1
    battle.last_action_at = now

    if battle.host_positions and battle.guest_positions:
        _bt_finalize(db, battle, now)

    db.commit()
    _bt_notify(battle.id)
    return _bt_serialize(db, battle, role, now)


@app.post("/api/battle/leave")
def api_battle_leave(data: BattleCodeReq, db: Session = Depends(get_db)):
    """waiting/searching → отмена; drafting → форфейт (победа соперника).

    intent='cancel_search' (кнопка «Отменить» экрана поиска): если к моменту
    захвата лока комнату УЖЕ сматчили (другой воркер успел первым — /queue или
    ленивый матчер), отмена НЕ превращается в форфейт со штрафом рейтинга —
    возвращаем «матч начался», фронт входит в бой. Форфейт — только явная
    сдача из драфта (кнопка-флаг с confirm, intent отсутствует)."""
    uid = _tm_require_user(token=data.token)
    battle = _bt_get_battle(db, data.code, for_update=True)
    role = _bt_role(battle, uid)
    if role is None:
        raise HTTPException(status_code=403, detail="not a participant")

    if battle.status in ("waiting", "searching"):
        battle.status = "abandoned"
        battle.state_version += 1
        db.commit()
        _bt_notify(battle.id)
        return {"ok": True, "status": "abandoned"}

    if data.intent == "cancel_search" and battle.status in ("drafting", "assigning"):
        db.commit()   # отпустить лок; битву не трогаем
        return {"ok": False, "status": battle.status, "matched": True}

    if battle.status in ("drafting", "assigning"):
        battle.status = "finished"
        battle.winner = "guest" if role == "host" else "host"
        battle.result = {"forfeit": role}
        battle.finished_at = _bt_now()
        battle.deadline_at = None
        # Форфейт штрафует рейтингом так же, как обычное поражение (без счёта →
        # нейтральный множитель за разгром). Иначе рейтинг можно «сберечь» сдачей.
        _bt_apply_ratings(db, battle)
        battle.state_version += 1
        db.commit()
        _bt_notify(battle.id)
        _bt_log("battle_forfeit", uid)   # отвал из воронки (сдался посреди боя)
        return {"ok": True, "status": "finished", "winner": battle.winner}

    return {"ok": True, "status": battle.status}


@app.get("/api/battle/state")
def api_battle_state(token: str, code: str, db: Session = Depends(get_db)):
    """Разовое чтение состояния (вход на экран / резюм после сна WebView)."""
    uid = _tm_require_user(token=token)
    battle = _bt_get_battle(db, code)
    now = _bt_now()
    if _bt_tick(db, battle, now):
        db.commit()
        _bt_notify(battle.id)
    return _bt_serialize(db, battle, _bt_role(battle, uid), now)


def _bt_try_live_match(db: Session, code: str, now: datetime) -> bool:
    """Ленивый матчер из long-poll'а searching-комнаты.

    Без него два игрока, вставшие в очередь в РАЗНОЕ время, могли не сматчиться
    никогда: подбор происходил только в момент POST /queue, и если кандидат не
    прошёл по окну рейтинга — второй создавал свою комнату, обе просто поллились
    (окно «расширялось» без исполнителя), и через 40с оба получали ботов.

    Окно — по МАКСИМАЛЬНОМУ ожиданию из двух комнат: раз обе ждут, самая
    терпеливая расширяет допуск за обоих. Боевой становится ПОЛЛЯЩАЯСЯ комната
    (её хост увидит драфт этим же поллом); комната кандидата помечается
    abandoned с result={'moved_to': code} — его фронт сам перепрыгнет.

    Гонки: своя комната FOR UPDATE, кандидаты FOR UPDATE SKIP LOCKED (встречный
    воркер просто пропустит уже залоченную строку — дедлока нет; /queue и /leave
    лочат те же строки). Возвращает True, если матч состоялся."""
    mine = _bt_get_battle(db, code, for_update=True)
    if mine.status != "searching" or mine.is_bot:
        db.commit()   # отпустить лок
        return False
    my_created = _bt_aware(mine.created_at)
    my_wait = (now - my_created).total_seconds() if my_created else 0.0
    my_rating = _bt_player_rating(db, mine.host_id)
    ttl_cutoff = now - _tm_timedelta(minutes=_BT_WAITING_TTL_MIN)

    cands = (
        db.query(DBDraftBattle)
        .filter(DBDraftBattle.status == "searching")
        .filter(DBDraftBattle.mode == mine.mode)
        .filter(DBDraftBattle.id != mine.id)
        .filter(DBDraftBattle.host_id != mine.host_id)
        .filter(DBDraftBattle.created_at >= ttl_cutoff)
        .order_by(DBDraftBattle.created_at)
        .with_for_update(skip_locked=True)
        .limit(_BT_MATCH_SCAN_LIMIT)
        .all()
    )
    if not cands:
        db.commit()
        return False
    ratings: dict[int, int] = {}
    for hid, hr in (
        db.query(DBUserProfile.user_id, DBUserProfile.battle_rating)
        .filter(DBUserProfile.user_id.in_([c.host_id for c in cands]))
        .all()
    ):
        ratings[hid] = hr if hr is not None else _BT_RATING_BASE

    for c in cands:
        c_created = _bt_aware(c.created_at)
        c_wait = (now - c_created).total_seconds() if c_created else 0.0
        window = _bt_match_window(max(my_wait, c_wait))
        cand_rating = ratings.get(c.host_id, _BT_RATING_BASE)
        if window is not None and abs(my_rating - cand_rating) > window:
            continue
        _bt_start_battle(mine, c.host_id, now)
        c.status = "abandoned"
        c.result = {"moved_to": mine.code}
        c.state_version += 1
        host_id, guest_id, bcode = mine.host_id, c.host_id, mine.code
        mine_id, cand_id = mine.id, c.id
        db.commit()
        _bt_notify(mine_id)
        _bt_notify(cand_id)
        _bt_send_match_push(host_id, guest_id, bcode)
        return True

    db.commit()   # никого в допуске — отпустить локи
    return False


def _bt_poll_read(code: str, user_id: int, since: int):
    """Один шаг long-poll'а (выполняется в threadpool): применить ленивые
    таймауты, отдать состояние если version > since, иначе (battle_id, сколько
    секунд можно спать до ближайшего дедлайна)."""
    with SessionLocal() as db:
        battle = _bt_get_battle(db, code)
        now = _bt_now()
        # Ленивый live-матч: пока комната ждёт в searching, каждый полл пробует
        # спарить её с другой ждущей (окно по max-ожиданию). Живой соперник
        # всегда в приоритете над бот-фоллбэком ниже.
        if battle.status == "searching" and not battle.is_bot:
            if _bt_try_live_match(db, code, now):
                battle = _bt_get_battle(db, code)
        # Бот-фолбэк: searching висит дольше таймаута и юзер всё ещё ждёт (раз
        # поллит) → подсаживаем бота. Перечитываем с FOR UPDATE и перепроверяем
        # статус — живой соперник мог занять комнату параллельно (тогда no-op).
        if (
            battle.status == "searching"
            and not battle.is_bot
            and battle.created_at is not None
            and (now - _bt_aware(battle.created_at)).total_seconds() >= _BT_BOT_FALLBACK_SEC
        ):
            locked = _bt_get_battle(db, code, for_update=True)
            if locked.status == "searching" and not locked.is_bot:
                _bt_start_battle_vs_bot(locked, now)
                db.commit()
                _bt_notify(locked.id)
                battle = locked
        if _bt_tick(db, battle, now):
            db.commit()
            _bt_notify(battle.id)
        if battle.state_version > since:
            return _bt_serialize(db, battle, _bt_role(battle, user_id), now), battle.id, 0.0
        wait_s = _BT_MAX_HOLD_SECONDS
        if battle.status == "drafting" and battle.deadline_at is not None:
            wait_s = max(0.05, (_bt_aware(battle.deadline_at) - now).total_seconds())
            # Ход бота: проснуться к моменту, когда он «надумает», чтобы сходить.
            if battle.mode == _BT_AP2_MODE:
                bot_wait = _bt_ap_bot_wait(db, battle, now)
                if bot_wait is not None:
                    wait_s = min(wait_s, bot_wait)
            else:
                _due, bot_wait = _bt_bot_due(battle, now)
                if bot_wait is not None:
                    wait_s = min(wait_s, max(0.05, bot_wait))
        elif battle.status == "searching" and not battle.is_bot:
            # Спим не дольше, чем до момента подсадки бота.
            if battle.created_at is not None:
                left = _BT_BOT_FALLBACK_SEC - (now - _bt_aware(battle.created_at)).total_seconds()
                wait_s = min(wait_s, max(0.5, left))
        return None, battle.id, wait_s


@app.get("/api/battle/events")
async def api_battle_events(token: str, code: str, since: int = 0):
    """Long polling: висим до изменения состояния (version > since), дедлайна
    текущего хода или _BT_MAX_HOLD_SECONDS. async def с реальными await —
    висящие запросы НЕ занимают threadpool; БД — через to_thread."""
    uid = await asyncio.to_thread(get_user_id_by_token, token)
    if not uid:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    deadline = time.monotonic() + _BT_MAX_HOLD_SECONDS
    while True:
        payload, battle_id, wait_s = await asyncio.to_thread(_bt_poll_read, code, uid, since)
        if payload is not None:
            return payload
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return {"changed": False, "version": since}
        await _bt_wait(battle_id, min(wait_s, remaining))


# ─────────────────────────────────────────────────────────────────────────────
#  «Битва драфтов»: фоновая уборка брошенных битв.
#
#  Состояние битвы живёт в БД, просрочки исполняются ЛЕНИВО — любым чтением
#  (long-poll соперника / заход на экран). Пока хотя бы один игрок поллит, всё
#  движется само. Но если ОБА ушли, никто не читает → строка застревает:
#    • searching/waiting — комната-зомби копится в БД;
#    • drafting/assigning — /battle/active вернёт её юзеру и НЕ пустит в новую.
#
#  Раньше sweep жил в teammates_notifier — и на окружениях без этого процесса
#  (staging) зомби не подметались вовсе. Уборка — часть домена битвы, поэтому
#  переехала сюда: работает в каждом окружении, где крутится API. При
#  нескольких uvicorn-воркерах задача запускается в каждом — это безопасно:
#  идемпотентный bulk-UPDATE по индексированному status, «лишние» воркеры
#  получают rowcount=0; джиттер разводит их по времени.
# ─────────────────────────────────────────────────────────────────────────────


def _bt_sweep_stale_battles() -> int:
    """Метит брошенные битвы как 'abandoned'. Возвращает число затронутых строк.

    Bulk-UPDATE без уведомлений: участников уже нет (на то они и брошенные).
    Редкий завис-поллер сам отвалится по hold-таймауту и перечитает abandoned."""
    now = _bt_now()
    waiting_cutoff = now - _tm_timedelta(minutes=_BT_WAITING_TTL_MIN)
    dead_cutoff = now - _tm_timedelta(seconds=_BT_DEAD_GRACE_SEC)
    with SessionLocal() as session:
        # 1) Комнаты, в которые никто не зашёл.
        r1 = session.execute(
            text(
                """
                UPDATE draft_battles
                SET status = 'abandoned', state_version = state_version + 1
                WHERE status IN ('searching', 'waiting')
                  AND created_at < :cutoff
                """
            ),
            {"cutoff": waiting_cutoff},
        )
        # 2) Битвы, брошенные посреди драфта/расстановки (никто не поллит).
        r2 = session.execute(
            text(
                """
                UPDATE draft_battles
                SET status = 'abandoned', state_version = state_version + 1
                WHERE status IN ('drafting', 'assigning')
                  AND deadline_at IS NOT NULL
                  AND deadline_at < :cutoff
                """
            ),
            {"cutoff": dead_cutoff},
        )
        session.commit()
        total = (r1.rowcount or 0) + (r2.rowcount or 0)
    if total:
        logger.info("[bt_sweep] swept %d stale battle(s) → abandoned", total)
    return total


# Ретеншен: раз в сутки чистим старьё. abandoned-строки истории не нужны;
# у finished журнал ходов не нужен (разбор из истории читает result JSON,
# а не draft_battle_actions — сами finished-строки храним, это история).
_BT_RETENTION_DAYS = 30
_BT_RETENTION_INTERVAL_SEC = 24 * 3600.0


def _bt_retention_pass() -> None:
    cutoff = _bt_now() - _tm_timedelta(days=_BT_RETENTION_DAYS)
    with SessionLocal() as session:
        r1 = session.execute(
            text(
                """
                DELETE FROM draft_battle_actions
                WHERE battle_id IN (
                    SELECT id FROM draft_battles
                    WHERE status IN ('finished', 'abandoned')
                      AND created_at < :cutoff
                )
                """
            ),
            {"cutoff": cutoff},
        )
        r2 = session.execute(
            text(
                "DELETE FROM draft_battles "
                "WHERE status = 'abandoned' AND created_at < :cutoff"
            ),
            {"cutoff": cutoff},
        )
        session.commit()
        n1, n2 = (r1.rowcount or 0), (r2.rowcount or 0)
    if n1 or n2:
        logger.info("[bt_sweep] retention: %d actions, %d abandoned battles purged", n1, n2)


async def _bt_sweep_loop() -> None:
    """Вечный цикл уборки. Ошибка одного прохода не валит цикл."""
    # Джиттер старта: несколько воркеров не бьют в БД синхронно.
    await asyncio.sleep(random.uniform(0.0, _BT_SWEEP_INTERVAL_SEC))
    last_retention = 0.0
    while True:
        try:
            await asyncio.to_thread(_bt_sweep_stale_battles)
        except Exception as e:
            logger.warning("[bt_sweep] pass failed: %s", e)
        if time.monotonic() - last_retention >= _BT_RETENTION_INTERVAL_SEC:
            last_retention = time.monotonic()
            try:
                await asyncio.to_thread(_bt_retention_pass)
            except Exception as e:
                logger.warning("[bt_sweep] retention failed: %s", e)
        await asyncio.sleep(_BT_SWEEP_INTERVAL_SEC)


@app.on_event("startup")
async def _bt_start_sweep_task() -> None:
    asyncio.create_task(_bt_sweep_loop())
    # Прогрев getMe-кэша (username бота для ссылок-вызовов): иначе ПЕРВЫЙ
    # «Сыграть с другом» после рестарта платит лишний Telegram-round-trip
    # прямо в обработчике (прод-жалоба: кнопка «молчала» секунды).
    asyncio.create_task(asyncio.to_thread(_bt_bot_username))
