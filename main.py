import os
import time
import secrets
import string
from pathlib import Path

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from livekit import api

# =========================================================
# MT VOICE SERVER
# =========================================================

app = FastAPI(
    title="MT Voice",
    version="3.0.1"
)

# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# PATHS
# =========================================================

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
INDEX_FILE = STATIC_DIR / "index.html"

# =========================================================
# LIVEKIT
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

CODE_EXPIRE_SECONDS = 600

MAX_CODE_ATTEMPTS = 5

# =========================================================
# PROXIMITY SETTINGS
# =========================================================

VOICE_MAX_DISTANCE = 80.0
VOICE_FULL_VOLUME_DISTANCE = 5.0

# =========================================================
# MEMORY
# =========================================================

players = {}
verification_codes = {}
verified_sessions = {}

# =========================================================
# MODELS
# =========================================================

class Player(BaseModel):
    user_id: int
    x: float
    y: float
    z: float


class UsernameRequest(BaseModel):
    username: str


class VerifyCodeRequest(BaseModel):
    user_id: int
    code: str


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
# HEALTH
# =========================================================

@app.get("/health")
async def health():

    return {
        "status": "online",
        "service": "MT Voice",
        "version": "3.0.1"
    }


# =========================================================
# ROBLOX PLAYER POSITION
# =========================================================

@app.post("/roblox/player")
async def update_player(player: Player):

    players[str(player.user_id)] = {
        "x": float(player.x),
        "y": float(player.y),
        "z": float(player.z),
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

    active_players = {}

    expired_players = []

    for user_id, data in list(players.items()):

        if current_time - data["updated"] <= PLAYER_TIMEOUT:

            active_players[user_id] = {
                "x": data["x"],
                "y": data["y"],
                "z": data["z"]
            }

        else:

            expired_players.append(user_id)

    for user_id in expired_players:

        players.pop(user_id, None)

        verified_sessions.pop(
            user_id,
            None
        )

    return active_players


# =========================================================
# ROBLOX USERNAME -> USER ID
# =========================================================

async def get_roblox_user(username: str):

    username = username.strip()

    if not username:
        return None

    url = "https://users.roblox.com/v1/usernames/users"

    payload = {
        "usernames": [username],
        "excludeBannedUsers": False
    }

    try:

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=10,
                read=15,
                write=15,
                pool=10
            ),
            follow_redirects=True
        ) as client:

            response = await client.post(
                url,
                json=payload,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                    "User-Agent": "MT-Voice/3.0"
                }
            )

            if response.status_code != 200:
                print(
                    "Roblox API Error:",
                    response.status_code,
                    response.text[:500]
                )
                return None

            data = response.json()

            users = data.get("data", [])

            if not users:
                return None

            user = users[0]

            return {
                "id": int(user["id"]),
                "name": user["name"],
                "display_name": user.get(
                    "displayName",
                    user["name"]
                )
            }

    except httpx.TimeoutException as error:

        print(
            "Roblox API Timeout:",
            repr(error)
        )

        return None

    except httpx.HTTPError as error:

        print(
            "Roblox HTTP Error:",
            repr(error)
        )

        return None

    except Exception as error:

        print(
            "Roblox API Exception:",
            repr(error)
        )

        return None


# =========================================================
# GENERATE 8 CHARACTER CODE
# =========================================================

def generate_code():

    characters = string.ascii_lowercase + string.digits

    while True:

        code = "".join(
            secrets.choice(characters)
            for _ in range(8)
        )

        current_time = time.time()

        used = any(
            item["code"] == code
            and current_time - item["created"]
            <= CODE_EXPIRE_SECONDS
            for item in verification_codes.values()
        )

        if not used:

            return code


# =========================================================
# CLEANUP VERIFICATIONS
# =========================================================

def cleanup_verifications():

    current_time = time.time()

    expired_users = []

    for user_id, data in list(
        verification_codes.items()
    ):

        if (
            current_time - data["created"]
            > CODE_EXPIRE_SECONDS
        ):

            expired_users.append(user_id)

    for user_id in expired_users:

        verification_codes.pop(
            user_id,
            None
        )


# =========================================================
# REQUEST VERIFICATION
# =========================================================

@app.post("/auth/request")
async def request_verification(
    request: UsernameRequest
):

    cleanup_verifications()

    username = request.username.strip()

    if not username:

        raise HTTPException(
            status_code=400,
            detail="اكتب اسم Roblox أولاً"
        )

    print(
        f"Verification request received: {username}"
    )

    user = await get_roblox_user(
        username
    )

    if not user:

        raise HTTPException(
            status_code=404,
            detail="حساب Roblox غير موجود أو تعذر الوصول إلى Roblox حالياً"
        )

    user_id = str(user["id"])

    print(
        f"Roblox user found: {user['name']} ({user_id})"
    )

    player = players.get(user_id)

    if not player:

        raise HTTPException(
            status_code=403,
            detail=(
                "تم العثور على الحساب، لكن لم يصل السيرفر "
                "تحديث لهذا اللاعب من الماب. تأكد أنك داخل الماب."
            )
        )

    if (
        time.time() - player["updated"]
        > PLAYER_TIMEOUT
    ):

        players.pop(
            user_id,
            None
        )

        verified_sessions.pop(
            user_id,
            None
        )

        raise HTTPException(
            status_code=403,
            detail=(
                "تم العثور على الحساب، لكن اللاعب لم يعد "
                "نشطاً داخل الماب."
            )
        )

    code = generate_code()

    verification_codes[user_id] = {
        "code": code,
        "created": time.time(),
        "attempts": 0,
        "username": user["name"]
    }

    print(
        f"Verification code created for {user['name']}"
    )

    return {

        "ok": True,

        "user_id": int(user["id"]),

        "username": user["name"],

        "display_name": user["display_name"],

        "message":
            "تم إنشاء رمز التحقق، اكتب الرمز الظاهر لك داخل الماب"
    }


# =========================================================
# ROBLOX CHECKS FOR VERIFICATION CODE
# =========================================================

@app.get(
    "/roblox/verification/{user_id}"
)
async def get_player_verification(
    user_id: int
):

    cleanup_verifications()

    user_id = str(user_id)

    data = verification_codes.get(
        user_id
    )

    if not data:

        return {
            "pending": False
        }

    if (
        time.time() - data["created"]
        > CODE_EXPIRE_SECONDS
    ):

        verification_codes.pop(
            user_id,
            None
        )

        return {
            "pending": False
        }

    return {

        "pending": True,

        "code": data["code"],

        "expires_in": max(
            0,
            int(
                CODE_EXPIRE_SECONDS
                - (
                    time.time()
                    - data["created"]
                )
            )
        )
    }


# =========================================================
# VERIFY CODE
# =========================================================

@app.post("/auth/verify")
async def verify_code(
    request: VerifyCodeRequest
):

    cleanup_verifications()

    user_id = str(request.user_id)

    data = verification_codes.get(
        user_id
    )

    if not data:

        raise HTTPException(
            status_code=400,
            detail="رمز التحقق غير موجود أو انتهت صلاحيته"
        )

    player = players.get(user_id)

    if not player:

        verification_codes.pop(
            user_id,
            None
        )

        raise HTTPException(
            status_code=403,
            detail="تعذر التحقق، الحساب لم يعد داخل الماب"
        )

    if (
        time.time() - player["updated"]
        > PLAYER_TIMEOUT
    ):

        verification_codes.pop(
            user_id,
            None
        )

        raise HTTPException(
            status_code=403,
            detail="تعذر التحقق، الحساب لم يعد داخل الماب"
        )

    if data["attempts"] >= MAX_CODE_ATTEMPTS:

        verification_codes.pop(
            user_id,
            None
        )

        raise HTTPException(
            status_code=429,
            detail="تم تجاوز عدد المحاولات، اطلب رمزاً جديداً"
        )

    entered_code = (
        request.code
        .strip()
        .lower()
    )

    if entered_code != data["code"]:

        data["attempts"] += 1

        remaining = (
            MAX_CODE_ATTEMPTS
            - data["attempts"]
        )

        raise HTTPException(
            status_code=400,
            detail=(
                "رمز التحقق غير صحيح. "
                f"المحاولات المتبقية: {remaining}"
            )
        )

    verification_codes.pop(
        user_id,
        None
    )

    verified_sessions[user_id] = {
        "verified": True,
        "created": time.time()
    }

    return {

        "ok": True,

        "user_id": request.user_id,

        "username": data["username"],

        "message":
            "تم التحقق بنجاح"
    }


# =========================================================
# LIVEKIT TOKEN
# =========================================================

@app.get("/voice/token")
async def voice_token(
    user_id: str
):

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

    session = verified_sessions.get(
        user_id
    )

    if not session:

        raise HTTPException(
            status_code=403,
            detail="يجب التحقق من الحساب أولاً"
        )

    player = players.get(
        user_id
    )

    if not player:

        verified_sessions.pop(
            user_id,
            None
        )

        raise HTTPException(
            status_code=403,
            detail="الحساب لم يعد داخل الماب"
        )

    if (
        time.time() - player["updated"]
        > PLAYER_TIMEOUT
    ):

        verified_sessions.pop(
            user_id,
            None
        )

        raise HTTPException(
            status_code=403,
            detail="الحساب لم يعد داخل الماب"
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

        "identity": identity,

        "voice_max_distance":
            VOICE_MAX_DISTANCE,

        "voice_full_volume_distance":
            VOICE_FULL_VOLUME_DISTANCE
    }


# =========================================================
# STARTUP
# =========================================================

@app.on_event("startup")
async def startup():

    print("====================================")
    print("MT Voice Server Started")
    print("Version: 3.0.1")
    print("Verification: Enabled")
    print("Code Length: 8")
    print("Code Expiry: 10 Minutes")
    print("Voice Proximity: Enabled")
    print(
        "Voice Max Distance:",
        VOICE_MAX_DISTANCE
    )
    print(
        "Voice Full Volume Distance:",
        VOICE_FULL_VOLUME_DISTANCE
    )
    print(
        "LiveKit Room:",
        ROOM_NAME
    )
    print(
        "CORS: Enabled"
    )
    print("====================================")
