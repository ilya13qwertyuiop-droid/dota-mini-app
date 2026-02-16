import os
import httpx
from datetime import datetime, timezone
from typing import Generator

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from sqlalchemy import create_engine, Column, Integer, String, JSON, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from db import get_user_id_by_token, init_tokens_table

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


# простейшая заглушка профиля на будущее
class Profile(BaseModel):
    user_id: int
    favorite_heroes: list[str] = []
    settings: dict = {}


# УСТАРЕЛО: эндпоинты /api/profile/* теперь работают с БД (DBUserProfile)
# Оставлено на случай, если используется где-то ещё
fake_profiles: dict[int, Profile] = {}

# УСТАРЕЛО: эндпоинты /api/save_result и /api/get_result теперь работают с БД (DBQuizResult)
# Оставлено на случай, если используется где-то ещё
quiz_results: dict[int, dict] = {}


@app.post("/api/check-subscription", response_model=CheckResponse)
async def check_subscription(data: CheckRequest):
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


@app.get("/api/profile/{user_id}", response_model=Profile)
async def get_profile(user_id: int, db: Session = Depends(get_db)):
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
    # 1. по токену достаём user_id
    user_id = get_user_id_by_token(data.token)
    if not user_id:
        print("[API DEBUG] Token validation FAILED")
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    print(f"[API DEBUG] Token valid, user_id={user_id}")

    # 2. Убедимся, что профиль пользователя существует (для foreign key)
    db_user_profile = db.query(DBUserProfile).filter(DBUserProfile.user_id == user_id).first()
    if not db_user_profile:
        # Создаём профиль автоматически, если его ещё нет
        db_user_profile = DBUserProfile(
            user_id=user_id,
            favorite_heroes=[],
            settings={}
        )
        db.add(db_user_profile)
        db.commit()

    # 3. Ищем существующий результат квиза в БД
    db_quiz_result = db.query(DBQuizResult).filter(DBQuizResult.user_id == user_id).first()

    if db_quiz_result:
        # 4. Если найден — обновляем result и updated_at
        db_quiz_result.result = data.result
        db_quiz_result.updated_at = datetime.now(timezone.utc)
    else:
        # 5. Если не найден — создаём новый
        db_quiz_result = DBQuizResult(
            user_id=user_id,
            result=data.result,
            updated_at=datetime.now(timezone.utc)
        )
        db.add(db_quiz_result)

    # 6. Сохраняем изменения в БД
    db.commit()
    db.refresh(db_quiz_result)

    return SaveResultResponse(success=True)


@app.get("/api/get_result", response_model=GetResultResponse)
async def get_result(token: str, db: Session = Depends(get_db)):
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
        return GetResultResponse(result=db_quiz_result.result)
    else:
        return GetResultResponse(result=None)
