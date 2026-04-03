import json
import logging
import os
import random
import time
import httpx
from datetime import datetime, timezone
from pathlib import Path

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
from backend.database import get_db, create_all_tables
from backend.models import UserProfile as DBUserProfile, QuizResult as DBQuizResult
from backend.db import get_user_id_by_token, init_tokens_table, init_hero_matchups_cache_table, save_feedback
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



# ========== API Endpoints ==========

@app.post("/api/check-subscription", response_model=CheckResponse)
async def check_subscription(data: CheckRequest):
    """Проверяет подписку пользователя на канал"""
    # 1. по токену достаём user_id
    user_id = get_user_id_by_token(data.token)
    if not user_id:
        # нет такого токена или он просрочен
        return CheckResponse(allowed=False)


    # 2. проверяем подписку через getChatMember
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

    If the stats DB is empty (updater hasn't run yet), returns 503.
    """
    if hero_id <= 0:
        raise HTTPException(status_code=400, detail="hero_id must be a positive integer")

    strict = get_stats_mode() == "strict"
    rows = get_hero_matchup_rows(hero_id, min_games=min_games, strict=strict)

    if not rows:
        raise HTTPException(
            status_code=503,
            detail=(
                "No matchup data for this hero (min_games threshold not met or "
                "stats DB is empty — run stats_updater.py to populate it)."
            ),
        )

    base_wr = get_hero_base_winrate_from_db(hero_id, strict=strict)
    if base_wr is None:
        # Fallback: use neutral 0.5 so advantage is still meaningful
        base_wr = 0.5
        logger.warning("[counters] No hero_stats entry for hero_id=%s, using base_wr=0.5", hero_id)

    enriched = []
    for row in rows:
        raw_adv = round(row["wr_vs"] - base_wr, 4)
        adj_adv = round(raw_adv * row["games"] / (row["games"] + BAYESIAN_SMOOTHING_C), 4)
        enriched.append({
            "hero_id":       row["hero_id"],
            "games":         row["games"],
            "wr_vs":         row["wr_vs"],
            "advantage":     adj_adv,
            "raw_advantage": raw_adv,
        })

    # counters: adjusted_advantage <= -0.02 (they beat us), sorted worst-first
    counters = sorted(
        [e for e in enriched if e["advantage"] <= -0.02],
        key=lambda x: x["advantage"],
    )[:limit]

    # victims: adjusted_advantage >= 0.02 (we beat them), sorted best-first
    victims = sorted(
        [e for e in enriched if e["advantage"] >= 0.02],
        key=lambda x: x["advantage"],
        reverse=True,
    )[:limit]

    data_games = get_hero_total_games(hero_id, strict=strict)

    logger.info(
        "[counters] hero_id=%s base_wr=%.4f data_games=%d counters=%d victims=%d (strict=%s)",
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
    If the stats DB is empty, returns 503.
    """
    if hero_id <= 0:
        raise HTTPException(status_code=400, detail="hero_id must be a positive integer")

    strict = get_stats_mode() == "strict"
    rows = get_hero_synergy_rows(hero_id, min_games=min_games, strict=strict)

    if not rows:
        raise HTTPException(
            status_code=503,
            detail=(
                "No synergy data for this hero (min_games threshold not met or "
                "stats DB is empty — run stats_updater.py to populate it)."
            ),
        )

    base_wr = get_hero_base_winrate_from_db(hero_id, strict=strict)
    if base_wr is None:
        base_wr = 0.5
        logger.warning("[synergy] No hero_stats entry for hero_id=%s, using base_wr=0.5", hero_id)

    enriched = []
    for row in rows:
        raw_delta = round(row["wr_vs"] - base_wr, 4)
        adj_delta = round(raw_delta * row["games"] / (row["games"] + BAYESIAN_SMOOTHING_C), 4)
        enriched.append({
            "hero_id":   row["hero_id"],
            "games":     row["games"],
            "wins":      row["wins"],
            "wr_vs":     row["wr_vs"],
            "delta":     adj_delta,
            "raw_delta": raw_delta,
        })

    # best_allies: adjusted_delta >= 0.02, sorted best-first (descending)
    best_allies = sorted(
        [e for e in enriched if e["delta"] >= 0.02],
        key=lambda x: x["delta"],
        reverse=True,
    )[:limit]

    # worst_allies: adjusted_delta <= -0.02, sorted worst-first (ascending)
    worst_allies = sorted(
        [e for e in enriched if e["delta"] <= -0.02],
        key=lambda x: x["delta"],
    )[:limit]

    data_games = get_hero_total_games(hero_id, strict=strict)

    logger.info(
        "[synergy] hero_id=%s base_wr=%.4f data_games=%d best=%d worst=%d (strict=%s)",
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

    patch = raw.get("patch", "")

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


def _hero_primary_pos_num(hero_id: int) -> int | None:
    """Return primary position number (1-5) from dota_builds.json for a hero, or None."""
    raw = _load_dota_builds_file()
    if not raw:
        return None
    hero_data = raw.get(str(hero_id))
    if not isinstance(hero_data, dict):
        return None
    best_key: str | None = None
    best_nm = -1
    for pk in _DOTA_POS_URL_TO_NUM:
        pos_data = hero_data.get(pk)
        if not isinstance(pos_data, dict):
            continue
        nm = pos_data.get("num_matches") or 0
        if nm > best_nm:
            best_nm = nm
            best_key = pk
    return _DOTA_POS_URL_TO_NUM.get(best_key) if best_key else None



@app.get("/api/draft/random")
async def api_draft_random():
    """Returns a random enemy draft from draft_matches.json."""
    matches = _load_draft_matches_file()
    if not matches:
        raise HTTPException(status_code=503, detail="draft_matches.json not available")

    match = random.choice(matches)
    match_id = match.get("match_id", 0)

    # Randomly pick radiant or dire as the enemy
    if random.random() < 0.5:
        heroes_raw = match.get("radiant") or match.get("radiant_heroes") or []
    else:
        heroes_raw = match.get("dire") or match.get("dire_heroes") or []

    enemy = []
    for entry in heroes_raw:
        if isinstance(entry, dict):
            hero_id = entry.get("hero_id")
            position = entry.get("position", "")
        else:
            hero_id = entry
            position = ""
        if hero_id:
            enemy.append({"hero_id": int(hero_id), "position": position})

    return {"match_id": match_id, "enemy": enemy}


class DraftHeroEntry(BaseModel):
    hero_id: int
    position: str = ""


class DraftEvaluateRequest(BaseModel):
    enemy: list[DraftHeroEntry] = []
    ally: list[DraftHeroEntry] = []


def _pos_str_to_num(pos: str) -> int | None:
    """Convert 'pos 1'..'pos 5' or 'pos%201'..'pos%205' to 1..5."""
    s = pos.strip().replace("%20", " ").lower()
    for i in range(1, 6):
        if s == f"pos {i}":
            return i
    return None


@app.post("/api/draft/evaluate")
async def api_draft_evaluate(data: DraftEvaluateRequest):
    """Evaluates a draft based on synergy, matchups, and position fit."""
    matchups = _load_hero_matchups_file() or {}

    ally_ids = [h.hero_id for h in data.ally]
    enemy_ids = [h.hero_id for h in data.enemy]

    # ── synergy_score ─────────────────────────────────────────────────────
    synergy_pairs: list[tuple[int, int, float]] = []
    for i in range(len(ally_ids)):
        for j in range(i + 1, len(ally_ids)):
            a, b = ally_ids[i], ally_ids[j]
            val = (matchups.get(str(a)) or {}).get("with", {}).get(str(b), {}).get("synergy", 0.0)
            synergy_pairs.append((a, b, float(val)))

    synergy_sum = sum(v for _, _, v in synergy_pairs)
    n_syn = len(synergy_pairs) or 1
    synergy_score = synergy_sum / n_syn

    # ── matchup_score ─────────────────────────────────────────────────────
    matchup_pairs: list[tuple[int, int, float]] = []
    for a in ally_ids:
        for e in enemy_ids:
            val = (matchups.get(str(a)) or {}).get("vs", {}).get(str(e), {}).get("synergy", 0.0)
            matchup_pairs.append((a, e, float(val)))

    matchup_sum = sum(v for _, _, _, in matchup_pairs)
    n_mu = len(matchup_pairs) or 1
    matchup_score = matchup_sum / n_mu

    # ── position_score ────────────────────────────────────────────────────
    pos_scores: list[tuple[int, float]] = []
    for h in data.ally:
        chosen = _pos_str_to_num(h.position)
        primary = _hero_primary_pos_num(h.hero_id)
        if chosen is None or primary is None:
            score = 5.0  # neutral when unknown
        else:
            diff = abs(chosen - primary)
            score = 10.0 if diff == 0 else (6.0 if diff == 1 else 2.0)
        pos_scores.append((h.hero_id, score))

    position_score = sum(s for _, s in pos_scores) / (len(pos_scores) or 1)

    # ── total_score ───────────────────────────────────────────────────────
    syn_norm = ((synergy_score + 10) / 20) * 10
    mu_norm = ((matchup_score + 10) / 20) * 10
    total_score = (syn_norm + mu_norm + position_score) / 3 * 10
    total_score = max(0.0, min(100.0, total_score))

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

    # Heroes on atypical positions → "warn"
    for hero_id, score in pos_scores:
        if len(comments) >= 5:
            break
        if score < 6.0:
            hero_entry = next((h for h in data.ally if h.hero_id == hero_id), None)
            picked_pos = hero_entry.position if hero_entry else ""
            primary_num = _hero_primary_pos_num(hero_id)
            primary_pos = f"pos {primary_num}" if primary_num else ""
            comments.append({
                "type": "warn",
                "kind": "position",
                "hero_id": hero_id,
                "picked_pos": picked_pos,
                "primary_pos": primary_pos,
            })

    return {
        "total_score": round(total_score, 1),
        "synergy_score": round(synergy_score, 2),
        "matchup_score": round(matchup_score, 2),
        "position_score": round(position_score, 2),
        "comments": comments,
    }
