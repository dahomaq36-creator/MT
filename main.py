import os
import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from livekit import api


# =========================================================
# MT VOICE SERVER
# =========================================================

app = FastAPI(
    title="MT Voice",
    version="1.0.0"
)


# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
INDEX_FILE = STATIC_DIR / "index.html"


# =========================================================
# LIVEKIT ENVIRONMENT VARIABLES
# =========================================================

LIVEKIT_URL = os.getenv("LIVEKIT_URL")
LIVEKIT_API_KEY = os.getenv("LIVEKIT_API_KEY")
LIVEKIT_API_SECRET = os.getenv("LIVEKIT_API_SECRET")

if not LIVEKIT_URL:
    raise RuntimeError("LIVEKIT_URL is missing")

if not LIVEKIT_API_KEY:
    raise RuntimeError("LIVEKIT_API_KEY is missing")

if not LIVEKIT_API_SECRET:
    raise RuntimeError("LIVEKIT_API_SECRET is missing")


# =========================================================
# SETTINGS
# =========================================================

ROOM_NAME = "mt-rp"

PLAYER_TIMEOUT = 10

players = {}


# =========================================================
# PLAYER MODEL
# =========================================================

class Player(BaseModel):
    user_id: int
    x: float
    y: float
    z: float


# =========================================================
# WEBSITE
# =========================================================

@app.get("/")
async def home():

    if not INDEX_FILE.exists():
        raise HTTPException(
            status_code=500,
            detail="static/index.html not found"
        )

    return FileResponse(
        INDEX_FILE,
        media_type="text/html"
    )


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
async def health():

    return {
        "status": "online",
        "service": "MT Voice"
    }


# =========================================================
# ROBLOX PLAYER POSITION
# =========================================================

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


# =========================================================
# GET ACTIVE PLAYERS
# =========================================================

@app.get("/roblox/players")
async def get_players():

    current_time = time.time()

    active_players = {
        user_id: data
        for user_id, data in players.items()
        if current_time - data["updated"] <= PLAYER_TIMEOUT
    }

    return active_players


# =========================================================
# LIVEKIT TOKEN
# =========================================================

@app.get("/voice/token")
async def voice_token(user_id: str):

    user_id = user_id.strip()

    if not user_id:
        raise HTTPException(
            status_code=400,
            detail="user_id is required"
        )

    if not user_id.isdigit():
        raise HTTPException(
            status_code=400,
            detail="Invalid Roblox User ID"
        )

    identity = f"roblox_{user_id}"

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
                room=ROOM_NAME,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True
            )
        )
    )

    return {
        "url": LIVEKIT_URL,
        "token": token.to_jwt(),
        "room": ROOM_NAME,
        "identity": identity
    }


# =========================================================
# CLEAN OLD PLAYERS
# =========================================================

@app.on_event("startup")
async def startup():

    print("====================================")
    print("MT Voice Server Started")
    print("LiveKit: Connected Configuration")
    print("Room:", ROOM_NAME)
    print("====================================")
