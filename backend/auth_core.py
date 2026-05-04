from datetime import datetime, timedelta, timezone
from typing import Any, Dict
import uuid

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from jwt import ExpiredSignatureError, InvalidTokenError
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app_state import db, logger, pwd_context, security
from runtime_config import JWT_SECRET


class User(BaseModel):
    model_config = ConfigDict(extra="ignore")
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    password_hash: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    to_encode.update({"exp": datetime.now(timezone.utc) + timedelta(days=7)})
    return jwt.encode(to_encode, JWT_SECRET, algorithm="HS256")


def verify_token(token: str):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except ExpiredSignatureError:
        logger.info("Rejected expired JWT")
        return None
    except InvalidTokenError as exc:
        logger.warning("Rejected invalid JWT: %s", exc.__class__.__name__)
        return None


async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    payload = verify_token(credentials.credentials)
    if not payload or "user_id" not in payload:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = await db.users.find_one({"id": payload["user_id"]}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


async def signup(user_data: UserCreate):
    email = str(user_data.email).lower().strip()
    existing = await db.users.find_one({"email": email})
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(email=email, password_hash=pwd_context.hash(user_data.password))
    user_dict = user.model_dump()
    user_dict["email"] = str(user_dict["email"]).lower().strip()
    user_dict["created_at"] = user_dict["created_at"].isoformat()
    await db.users.insert_one(user_dict)

    config = {
        "user_id": user.id,
        "is_active": False,
        "capital_floor": 0.97,
        "max_daily_loss": 0.015,
        "risk_target_vol": 0.10,
        "symbols": ["BTC-USD", "ETH-USD"],
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    await db.bot_configs.insert_one(config)

    token = create_access_token({"user_id": user.id, "email": user.email})
    return TokenResponse(access_token=token, user={"id": user.id, "email": user.email})


async def login(credentials: UserLogin):
    email = str(credentials.email).lower().strip()
    user = await db.users.find_one({"email": email}, {"_id": 0})
    if not user or not pwd_context.verify(credentials.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"user_id": user["id"], "email": user["email"]})
    return TokenResponse(access_token=token, user={"id": user["id"], "email": user["email"]})
