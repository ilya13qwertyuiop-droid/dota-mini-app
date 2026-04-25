import asyncio
import hashlib
import hmac
import json
import logging
import os
import random
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

# draft_matches.json — read once per process lifetime
_draft_matches_file_cache: list | None = None

# /api/hero/{hero_id}/build — full response per hero, TTL 30 min
BUILD_CACHE_TTL = 1800
_build_cache: dict[int, tuple[float, dict]] = {}  # {hero_id: (timestamp, data)}

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


from fastapi import FastAPI, HTTPException, Depends, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


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
create_all_tables()       # creates all tables if they don't exist (SQLite convenience)
init_stats_tables()       # migration: adds rank_bucket column if missing
_init_rl_table()          # rate limiting table for /api/draft/evaluate
# --- DB init end ---


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
async def save_telegram_data(data: TelegramUserData, db: Session = Depends(get_db)):
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

    db_profile.settings["username"] = data.username
    db_profile.settings["first_name"] = data.first_name
    db_profile.settings["last_name"] = data.last_name
    db_profile.settings["photo_url"] = data.photo_url
    flag_modified(db_profile, "settings")

    db.commit()
    return {"success": True}


@app.get("/api/profile_full", response_model=UserStats)
async def get_profile_full(token: str, db: Session = Depends(get_db)):
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
async def save_result(data: SaveResultRequest, db: Session = Depends(get_db)):
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
async def get_result(token: str, db: Session = Depends(get_db)):
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
async def api_hero_counters(
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

    strict = get_stats_mode() == "strict"

    base_wr = get_hero_base_winrate_from_db(hero_id, strict=strict)
    if base_wr is None:
        base_wr = 0.5
        logger.warning("[counters] No hero_stats entry for hero_id=%s, using base_wr=0.5", hero_id)

    matchups_file = _load_hero_matchups_file() or {}
    hero_entry = matchups_file.get(str(hero_id)) or {}
    vs_map = hero_entry.get("vs") or {}

    enriched = []
    for opp_id_str, pair in vs_map.items():
        match_count = int(pair.get("matchCount", 0))
        if match_count < min_games:
            continue
        try:
            opp_id = int(opp_id_str)
        except (TypeError, ValueError):
            continue
        delta = float(pair.get("synergy", 0.0)) / 100.0
        wr_vs = base_wr + delta
        enriched.append({
            "hero_id":       opp_id,
            "games":         match_count,
            "wr_vs":         round(wr_vs, 4),
            "advantage":     round(delta, 4),
            "raw_advantage": round(delta, 4),
        })

    # counters: delta <= -0.002 (they beat us), sorted worst-first
    counters = sorted(
        [e for e in enriched if e["advantage"] <= -0.002],
        key=lambda x: x["advantage"],
    )[:limit]

    # victims: delta >= 0.002 (we beat them), sorted best-first
    victims = sorted(
        [e for e in enriched if e["advantage"] >= 0.002],
        key=lambda x: x["advantage"],
        reverse=True,
    )[:limit]

    data_games = sum(e["games"] for e in enriched)

    logger.info(
        "[counters] hero_id=%s base_wr=%.4f data_games=%d counters=%d victims=%d (strict=%s, source=file)",
        hero_id, base_wr, data_games, len(counters), len(victims), strict,
    )

    return {
        "hero_id": hero_id,
        "base_winrate": base_wr,
        "data_games": data_games,
        "counters": counters,
        "victims": victims,
        "strict_mode": strict,
    }


# ========== Custom Stats: ally synergy from our own match data ==========

@app.get("/api/hero/{hero_id}/synergy")
async def api_hero_synergy(
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

    strict = get_stats_mode() == "strict"

    base_wr = get_hero_base_winrate_from_db(hero_id, strict=strict)
    if base_wr is None:
        base_wr = 0.5
        logger.warning("[synergy] No hero_stats entry for hero_id=%s, using base_wr=0.5", hero_id)

    matchups_file = _load_hero_matchups_file() or {}
    hero_entry = matchups_file.get(str(hero_id)) or {}
    with_map = hero_entry.get("with") or {}

    enriched = []
    for ally_id_str, pair in with_map.items():
        match_count = int(pair.get("matchCount", 0))
        if match_count < min_games:
            continue
        try:
            ally_id = int(ally_id_str)
        except (TypeError, ValueError):
            continue
        delta = float(pair.get("synergy", 0.0)) / 100.0
        wr_vs = base_wr + delta
        enriched.append({
            "hero_id":   ally_id,
            "games":     match_count,
            "wins":      int(round(wr_vs * match_count)),
            "wr_vs":     round(wr_vs, 4),
            "delta":     round(delta, 4),
            "advantage": round(delta, 4),
            "raw_delta": round(delta, 4),
        })

    best_allies = sorted(
        [e for e in enriched if e["delta"] >= 0],
        key=lambda x: x["delta"],
        reverse=True,
    )[:limit]

    worst_allies = sorted(
        [e for e in enriched if e["delta"] <= 0],
        key=lambda x: x["delta"],
    )[:limit]

    data_games = sum(e["games"] for e in enriched)

    logger.info(
        "[synergy] hero_id=%s base_wr=%.4f data_games=%d best=%d worst=%d (strict=%s, source=file)",
        hero_id, base_wr, data_games, len(best_allies), len(worst_allies), strict,
    )

    return {
        "hero_id": hero_id,
        "base_winrate": base_wr,
        "data_games": data_games,
        "best_allies": best_allies,
        "worst_allies": worst_allies,
        "strict_mode": strict,
    }


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
async def api_hero_build(hero_id: int):
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
        return _cached_entry[1]

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
        _build_cache[hero_id] = (time.time(), _response)
        return _response

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
    _build_cache[hero_id] = (time.time(), _response)
    return _response


# ========== Hero Positions ==========

@app.get("/api/hero/{hero_id}/positions")
async def api_hero_positions(hero_id: int):
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
async def api_items_db():
    """Returns items_by_id dict (shared across all heroes).

    Cached in-memory server-side; clients should treat it as immutable
    for the session (Cache-Control: public, max-age=3600).
    """
    data = get_app_cache_value("items_by_id") or {}
    return JSONResponse(content=data, headers={"Cache-Control": "public, max-age=3600"})


# ========== Feedback ==========

@app.get("/api/meta")
async def api_meta():
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
async def submit_feedback(data: FeedbackRequest, db: Session = Depends(get_db)):
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
async def api_draft_random():
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
_draft_popularity_cache: dict[str, int] | None = None


@app.get("/api/draft/matchups_all")
async def api_draft_matchups_all():
    """Returns full hero_matchups.json blob.

    Used by the frontend "Анализ" mode of the Drafter to compute live recommendations
    on the client without round-trips. ~1.2 MB; cached server-side and gzip-compressed
    over the wire (uvicorn handles content-encoding when the client sends Accept-Encoding).
    """
    matchups = _load_hero_matchups_file()
    if matchups is None:
        raise HTTPException(status_code=503, detail="Matchups data not available")
    return matchups


@app.get("/api/draft/popularity")
async def api_draft_popularity():
    """Returns {hero_id: total_matches} derived from dota_builds.json.

    Used as the default ordering for the Анализ picker when no heroes are placed yet
    (and as a tiebreaker when scores tie). Tiny payload (~125 entries).
    """
    global _draft_popularity_cache
    if _draft_popularity_cache is not None:
        return _draft_popularity_cache

    builds = _load_dota_builds_file()
    if builds is None:
        raise HTTPException(status_code=503, detail="Builds data not available")

    out: dict[str, int] = {}
    for hero_key, positions in builds.items():
        if not isinstance(positions, dict):
            continue
        total = 0
        for pos_data in positions.values():
            if not isinstance(pos_data, dict):
                continue
            n = pos_data.get("num_matches")
            if isinstance(n, (int, float)):
                total += int(n)
        out[str(hero_key)] = total

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


@app.post("/api/draft/evaluate")
async def api_draft_evaluate(data: DraftEvaluateRequest, db: Session = Depends(get_db)):
    """Evaluates a draft based on synergy, matchups, and position fit."""
    # ── Rate limiting: 30 req / 10 min per authenticated user ───────────────
    # Uses SQLite so all uvicorn workers share the same counters.
    rl_user_id = get_user_id_by_token(data.token) if data.token else None
    if rl_user_id:
        allowed, count = _rl_check_and_record(rl_user_id)
        logger.info("[rate_limit] user_id=%s window_count=%d allowed=%s", rl_user_id, count, allowed)
        if not allowed:
            raise HTTPException(status_code=429, detail="Слишком много запросов. Подождите немного.")

    matchups = _load_hero_matchups_file() or {}

    ally_ids = [h.hero_id for h in data.ally]
    enemy_ids = [h.hero_id for h in data.enemy]

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
    synergy_component = max(0.0, min(50.0, (avg_synergy + 1.5) / 3.0 * 50.0))

    # ── Компонент 2: Матчап против врагов (0-50) — 25 пар наш vs вражеский ──
    matchup_pairs: list[tuple[int, int, float]] = []
    for a in ally_ids:
        for e in enemy_ids:
            val = (matchups.get(str(a)) or {}).get("vs", {}).get(str(e), {}).get("synergy", 0.0)
            matchup_pairs.append((a, e, float(val)))

    matchup_score = sum(v for _, _, v in matchup_pairs) / (len(matchup_pairs) or 1)
    matchup_component = max(0.0, min(50.0, (matchup_score + 1.5) / 3.0 * 50.0))

    # ── Позиции — не влияют на total_score, только comments ─────────────────
    pos_scores: list[tuple[int, bool]] = []
    for h in data.ally:
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

    # ── Сохраняем результат если передан токен ───────────────────────────────
    uid = get_user_id_by_token(data.token) if data.token else None
    if uid:
        db.add(DBDraftResult(
            user_id=uid,
            total_score=round(total_score, 1),
            ally_heroes=ally_ids,
            enemy_heroes=enemy_ids,
        ))
        db.commit()

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


@app.get("/api/draft/leaderboard")
async def api_draft_leaderboard(db: Session = Depends(get_db)):
    """Топ-25 пользователей по сумме топ-5 результатов."""
    global _leaderboard_cache, _leaderboard_cache_ts

    if _leaderboard_cache is not None and time.time() - _leaderboard_cache_ts < 300:
        return _leaderboard_cache

    from sqlalchemy import text

    rows = db.execute(text("""
        SELECT
            d1.user_id,
            (
                SELECT COALESCE(SUM(total_score), 0)
                FROM (
                    SELECT total_score
                    FROM draft_results d2
                    WHERE d2.user_id = d1.user_id
                    ORDER BY total_score DESC
                    LIMIT 5
                )
            ) AS top5_sum,
            COUNT(*) AS draft_count
        FROM draft_results d1
        WHERE d1.user_id NOT IN (SELECT user_id FROM banned_users)
        GROUP BY d1.user_id
        ORDER BY top5_sum DESC
        LIMIT 25
    """)).fetchall()

    user_ids = [r.user_id for r in rows]
    profiles = {
        p.user_id: p
        for p in db.query(DBUserProfile).filter(DBUserProfile.user_id.in_(user_ids)).all()
    }

    result = []
    for rank, row in enumerate(rows, 1):
        profile = profiles.get(row.user_id)
        settings = (profile.settings if profile else None) or {}
        username = settings.get("first_name") or settings.get("username") or f"Игрок {row.user_id}"
        photo_url = settings.get("photo_url") or None
        result.append({
            "rank": rank,
            "user_id": row.user_id,
            "username": username,
            "photo_url": photo_url,
            "top5_sum": round(row.top5_sum, 1),
            "draft_count": row.draft_count,
        })

    _leaderboard_cache = result
    _leaderboard_cache_ts = time.time()
    return result


@app.get("/api/draft/leaderboard/me")
async def api_draft_leaderboard_me(token: str = "", db: Session = Depends(get_db)):
    """Место и счёт текущего пользователя среди всех участников.

    Два быстрых запроса вместо одного RANK() OVER на весь стол:
    1. Сумма топ-5 результатов пользователя — фильтр по user_id + LIMIT 5.
    2. Количество пользователей с большей суммой → ранг = count + 1.
    """
    if not token:
        return {"rank": None, "top5_sum": None}
    user_id = get_user_id_by_token(token)
    if not user_id:
        return {"rank": None, "top5_sum": None}

    if is_user_banned(user_id):
        return {"banned": True, "rank": None, "top5_sum": None}

    from sqlalchemy import text

    # ── Шаг 1: top5_sum пользователя (быстро: WHERE user_id + LIMIT 5) ──
    sum_row = db.execute(text("""
        SELECT COALESCE(SUM(total_score), 0) AS top5_sum
        FROM (
            SELECT total_score FROM draft_results
            WHERE user_id = :uid
            ORDER BY total_score DESC
            LIMIT 5
        )
    """), {"uid": user_id}).fetchone()

    my_sum = float(sum_row.top5_sum) if sum_row else 0.0
    if my_sum == 0.0:
        return {"rank": None, "top5_sum": None}

    # ── Шаг 2: сколько пользователей лучше → ранг без RANK() OVER ───────
    count_row = db.execute(text("""
        SELECT COUNT(*) AS better_count
        FROM (
            SELECT user_id
            FROM (
                SELECT user_id, total_score,
                       ROW_NUMBER() OVER (PARTITION BY user_id
                                         ORDER BY total_score DESC) AS rn
                FROM draft_results
                WHERE user_id NOT IN (SELECT user_id FROM banned_users)
            ) t
            WHERE rn <= 5
            GROUP BY user_id
            HAVING SUM(total_score) > :my_sum
        )
    """), {"my_sum": my_sum}).fetchone()

    rank = int(count_row.better_count) + 1 if count_row else 1
    return {"rank": rank, "top5_sum": round(my_sum, 1)}


@app.get("/api/draft/history")
async def api_draft_history(token: str, db: Session = Depends(get_db)):
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
