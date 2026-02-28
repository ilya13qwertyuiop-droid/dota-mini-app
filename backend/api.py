import logging
import os
import httpx
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


from fastapi import FastAPI, HTTPException, Depends, Query
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
)


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


@app.get("/api/profile/{user_id}", response_model=Profile)
async def get_profile(user_id: int, db: Session = Depends(get_db)):
    """Получает базовый профиль пользователя (устаревший эндпоинт)"""
    # 1. Ищем профиль в БД по user_id
    db_profile = db.query(DBUserProfile).filter(DBUserProfile.user_id == user_id).first()


    # 2. Если не найден — создаём новый с пустыми данными
    if not db_profile:
        db_profile = DBUserProfile(
            user_id=user_id,
            favorite_heroes=[],
            settings={}
        )
        db.add(db_profile)
        db.commit()
        db.refresh(db_profile)


    # 3. Возвращаем Pydantic модель Profile
    return Profile(
        user_id=db_profile.user_id,
        favorite_heroes=db_profile.favorite_heroes or [],
        settings=db_profile.settings or {}
    )


@app.post("/api/profile", response_model=Profile)
async def save_profile(profile: Profile, db: Session = Depends(get_db)):
    """Сохраняет базовый профиль пользователя (устаревший эндпоинт)"""
    # 1. Ищем существующий профиль в БД
    db_profile = db.query(DBUserProfile).filter(DBUserProfile.user_id == profile.user_id).first()


    # 2. Если не найден — создаём новый
    if not db_profile:
        db_profile = DBUserProfile(
            user_id=profile.user_id,
            favorite_heroes=profile.favorite_heroes,
            settings=profile.settings
        )
        db.add(db_profile)
    else:
        # 3. Если найден — обновляем данные
        db_profile.favorite_heroes = profile.favorite_heroes
        db_profile.settings = profile.settings
        flag_modified(db_profile, "favorite_heroes")  # ✅ Помечаем JSON-поля как измененные
        flag_modified(db_profile, "settings")


    # 4. Сохраняем изменения в БД
    db.commit()
    db.refresh(db_profile)


    # 5. Возвращаем актуальный профиль
    return Profile(
        user_id=db_profile.user_id,
        favorite_heroes=db_profile.favorite_heroes or [],
        settings=db_profile.settings or {}
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

    # Достаём существующий агрегированный результат
    db_quiz_result = db.query(DBQuizResult).filter(DBQuizResult.user_id == user_id).first()

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

    enriched = [
        {
            "hero_id": row["hero_id"],
            "games": row["games"],
            "wr_vs": row["wr_vs"],
            "advantage": round(row["wr_vs"] - base_wr, 4),
        }
        for row in rows
    ]

    # counters: advantage < 0 (they beat us), sorted worst-first (ascending)
    counters = sorted(
        [e for e in enriched if e["advantage"] < 0],
        key=lambda x: x["advantage"],
    )[:limit]

    # victims: advantage >= 0 (we beat them), sorted best-first (descending)
    victims = sorted(
        [e for e in enriched if e["advantage"] >= 0],
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

    enriched = [
        {
            "hero_id": row["hero_id"],
            "games": row["games"],
            "wins": row["wins"],
            "wr_vs": row["wr_vs"],
            "delta": round(row["wr_vs"] - base_wr, 4),
        }
        for row in rows
    ]

    # best_allies: delta >= 0, sorted best-first (descending)
    best_allies = sorted(
        [e for e in enriched if e["delta"] >= 0],
        key=lambda x: x["delta"],
        reverse=True,
    )[:limit]

    # worst_allies: delta < 0, sorted worst-first (ascending)
    worst_allies = sorted(
        [e for e in enriched if e["delta"] < 0],
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


# ========== Feedback ==========

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
