import os
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHECK_CHAT_ID = os.environ.get("CHECK_CHAT_ID")  # chat_id канала для проверки

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set")
if not CHECK_CHAT_ID:
    raise RuntimeError("CHECK_CHAT_ID is not set")

app = FastAPI(title="Dota Mini App Backend")


class CheckRequest(BaseModel):
    user_id: int  # Telegram user_id из mini app (позже добавим initData)


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
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember"
    params = {"chat_id": CHECK_CHAT_ID, "user_id": data.user_id}

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
