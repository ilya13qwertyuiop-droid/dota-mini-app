import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from bot import get_user_id_by_token

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHECK_CHAT_ID = os.environ.get("CHECK_CHAT_ID")  # chat_id канала для проверки

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")
if not CHECK_CHAT_ID:
    raise RuntimeError("CHECK_CHAT_ID is not set")

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


# простейшая заглушка профиля на будущее
class Profile(BaseModel):
    user_id: int
    favorite_heroes: list[str] = []
    settings: dict = {}


fake_profiles: dict[int, Profile] = {}


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
async def get_profile(user_id: int):
    return fake_profiles.get(user_id, Profile(user_id=user_id))


@app.post("/api/profile", response_model=Profile)
async def save_profile(profile: Profile):
    fake_profiles[profile.user_id] = profile
    return profile
