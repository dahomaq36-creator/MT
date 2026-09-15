import os
import time

from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel
from livekit import api

app = FastAPI()

LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

if not LIVEKIT_URL or not LIVEKIT_API_KEY or not LIVEKIT_API_SECRET:
    raise RuntimeError("LIVEKIT environment variables are missing")


class Player(BaseModel):
    user_id: int
    x: float
    y: float
    z: float


players = {}


# الصفحة الرئيسية
@app.get("/")
async def home():
    return FileResponse("static/index.html")


# استقبال موقع اللاعب من Roblox
@app.post("/roblox/player")
async def update_player(player: Player):

    players[str(player.user_id)] = {
        "x": player.x,
        "y": player.y,
        "z": player.z,
        "updated": time.time()
    }

    return {
        "ok": True
    }


# إعطاء توكن LiveKit للموقع
@app.get("/voice/token")
async def voice_token(user_id: str):

    identity = f"roblox_{user_id}"
    room_name = "mt-rp"

    token = (
        api.AccessToken(
            LIVEKIT_API_KEY,
            LIVEKIT_API_SECRET
        )
        .with_identity(identity)
        .with_name(identity)
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True
            )
        )
    )

    return {
        "url": LIVEKIT_URL,
        "token": token.to_jwt(),
        "room": room_name
    }


# معرفة مواقع اللاعبين
@app.get("/roblox/players")
async def get_players():
    return players
