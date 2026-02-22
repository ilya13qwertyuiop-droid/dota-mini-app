import os
import httpx
from datetime import datetime, timezone
from typing import Generator


from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.orm.attributes import flag_modified


from backend.db import get_user_id_by_token, init_tokens_table


BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHECK_CHAT_ID = os.environ.get("CHECK_CHAT_ID")  # chat_id канала для проверки


if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")
if not CHECK_CHAT_ID:
    raise RuntimeError("CHECK_CHAT_ID is not set")


# --- DB setup start ---
# Путь к БД SQLite
DATABASE_URL = "sqlite:///./backend/dota_bot.db"


# Создаём engine и session
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Декларативная база для моделей
Base = declarative_base()



# Модель UserProfile
class DBUserProfile(Base):
    __tablename__ = "user_profiles"


    user_id = Column(Integer, primary_key=True, index=True)
    favorite_heroes = Column(JSON, default=list)  # список героев
    settings = Column(JSON, default=dict)  # произвольные настройки



# Модель QuizResult
class DBQuizResult(Base):
    __tablename__ = "quiz_results"


    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("user_profiles.user_id"), index=True)
    result = Column(JSON, nullable=False)  # результат квиза
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))



# Функция для получения сессии БД (dependency injection для FastAPI)
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()



# Создаём таблицы при старте приложения
Base.metadata.create_all(bind=engine)
init_tokens_table()
# --- DB setup end ---


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
    print(f"[API DEBUG] save_telegram_data: token={data.token[:10]}...")
    
    user_id = get_user_id_by_token(data.token)
    if not user_id:
        print("[API DEBUG] Token validation FAILED")
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    print(f"[API DEBUG] Token valid, user_id={user_id}")
    
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
    flag_modified(db_profile, "settings")  # ✅ Помечаем JSON-поле как измененное

    db.commit()

    print(f"[API DEBUG] Telegram data saved for user {user_id}")
    print(f"[API DEBUG] photo_url: {data.photo_url}")  # ✅ Логируем аватар для отладки
    return {"success": True}


@app.get("/api/profile_full", response_model=UserStats)
async def get_profile_full(token: str, db: Session = Depends(get_db)):
    """Получает полный профиль пользователя с историей квизов"""
    print(f"[API DEBUG] get_profile_full: token={token[:10]}...")
    
    # 1. Проверяем токен
    user_id = get_user_id_by_token(token)
    if not user_id:
        print("[API DEBUG] Token validation FAILED")
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    print(f"[API DEBUG] Token valid, user_id={user_id}")
    
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
                    print(f"[API DEBUG] Legacy format detected in quiz_history for user {user_id}")

            if combined_result:
                quiz_history.append({
                    "date": base_date,
                    "result": combined_result
                })

    
    # 5. Извлекаем данные Telegram из settings
    settings = db_profile.settings or {}
    
    print(f"[API DEBUG] Profile loaded: {len(quiz_results)} quizzes found")
    
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
    print(f"[API DEBUG] save_result: token={data.token[:10]}...")

    user_id = get_user_id_by_token(data.token)
    if not user_id:
        print("[API DEBUG] Token validation FAILED")
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    print(f"[API DEBUG] Token valid, user_id={user_id}")

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
        # Сохраняем position_quiz
        combined_result["position_quiz"] = data.result

        # Чистим legacy верхнеуровневые ключи
        for legacy_key in ["type", "position", "posShort", "positionIndex", "date", "isPure", "extraPos"]:
            combined_result.pop(legacy_key, None)

        print(f"[API DEBUG] Saved position_quiz in new format")

    elif result_type == "hero_quiz":
        # Сохраняем hero_quiz по позициям (0-4)
        hero_position_index = data.result.get("heroPositionIndex")
        if hero_position_index is not None:
            # Инициализируем словарь если его нет
            if "hero_quiz_by_position" not in combined_result:
                combined_result["hero_quiz_by_position"] = {}

            # Сохраняем результат для конкретной позиции
            combined_result["hero_quiz_by_position"][str(hero_position_index)] = data.result
            print(f"[API DEBUG] Saved hero_quiz for position {hero_position_index} in new format")

            # Чистим legacy hero_quiz (если был)
            combined_result.pop("hero_quiz", None)
        else:
            # Нет heroPositionIndex - неожиданная ситуация
            print(f"[API DEBUG] WARNING: hero_quiz without heroPositionIndex, skipping save")
    else:
        # Неизвестный тип - не трогаем данные
        print(f"[API DEBUG] Unknown or missing result.type: {result_type}, skip update")
        return SaveResultResponse(success=True)
    
    print(f"[API DEBUG] BEFORE COMMIT combined_result for user {user_id}: {combined_result}")

    if db_quiz_result:
        db_quiz_result.result = combined_result
        db_quiz_result.updated_at = datetime.now(timezone.utc)
        flag_modified(db_quiz_result, "result")  # ✅ КРИТИЧНО: помечаем JSON-поле как измененное
        print(f"[API DEBUG] AFTER ASSIGN db_quiz_result.result for user {user_id}: {db_quiz_result.result}")
    else:
        db_quiz_result = DBQuizResult(
            user_id=user_id,
            result=combined_result,
            updated_at=datetime.now(timezone.utc)
        )
        db.add(db_quiz_result)
        print(f"[API DEBUG] AFTER CREATE db_quiz_result.result for user {user_id}: {db_quiz_result.result}")

    # Обновляем favorite_heroes для профиля, если это геройский квиз
    try:
        if result_type == "hero_quiz":
            # Берём topHeroes из нового формата
            top_heroes = data.result.get("topHeroes") or []
            hero_names = [
                h.get("name") if isinstance(h, dict) else h
                for h in top_heroes
                if h
            ]
            if hero_names:
                db_user_profile.favorite_heroes = hero_names
                flag_modified(db_user_profile, "favorite_heroes")  # ✅ Помечаем JSON-поле как измененное
                print(f"[API DEBUG] favorite_heroes updated for user {user_id}: {hero_names}")
    except Exception as e:
        print(f"[API DEBUG] Failed to update favorite_heroes for user {user_id}: {e}")

    db.commit()
    db.refresh(db_quiz_result)

    print(f"[API DEBUG] Quiz result saved for user {user_id}")
    print(f"[API DEBUG] AFTER COMMIT & REFRESH db_quiz_result.result for user {user_id}: {db_quiz_result.result}")

    # Дополнительная проверка: читаем данные напрямую из БД
    verification_query = db.query(DBQuizResult).filter(DBQuizResult.user_id == user_id).first()
    if verification_query:
        print(f"[API DEBUG] VERIFICATION READ from DB for user {user_id}: {verification_query.result}")

    return SaveResultResponse(success=True)


@app.get("/api/get_result", response_model=GetResultResponse)
async def get_result(token: str, db: Session = Depends(get_db)):
    """Получает результат квиза по токену"""
    print(f"[API DEBUG] get_result: token={token[:10]}...")
    
    # 1. по токену достаём user_id
    user_id = get_user_id_by_token(token)
    if not user_id:
        print("[API DEBUG] Token validation FAILED")
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    print(f"[API DEBUG] Token valid, user_id={user_id}")


    # 2. Ищем результат квиза в БД по user_id
    db_quiz_result = db.query(DBQuizResult).filter(DBQuizResult.user_id == user_id).first()


    # 3. Возвращаем результат (или None, если записи нет)
    if db_quiz_result:
        print(f"[API DEBUG] Quiz result found for user {user_id}")
        return GetResultResponse(result=db_quiz_result.result)
    else:
        print(f"[API DEBUG] No quiz result found for user {user_id}")
        return GetResultResponse(result=None)

# ========== Hero Matchups ==========
# TODO: OpenDota API integration — реализовать /api/hero_matchups через opendota_client

