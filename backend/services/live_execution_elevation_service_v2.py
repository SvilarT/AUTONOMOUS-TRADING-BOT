import base64
import hashlib
import hmac
import os
import secrets
import struct
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from services.settings_v2 import resolve_secret_env


class LiveExecutionElevationError(RuntimeError):
    pass


class LiveExecutionElevationServiceV2:
    """Password + TOTP backed short-lived elevation for real-money actions."""

    DEFAULT_TTL_SECONDS = 300
    DEFAULT_TOTP_STEP_SECONDS = 30
    DEFAULT_TOTP_DIGITS = 6

    def __init__(self, db, pwd_context):
        self.db = db
        self.pwd_context = pwd_context

    @staticmethod
    def utc_now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def iso(value: datetime) -> str:
        return value.astimezone(timezone.utc).isoformat()

    @staticmethod
    def env_bool(name: str, default: bool = False) -> bool:
        value = os.getenv(name)
        if value is None:
            return default
        return value.strip().lower() in {"1", "true", "yes", "on"}

    @classmethod
    def mfa_required(cls) -> bool:
        return cls.env_bool("LIVE_MFA_REQUIRED", True)

    @classmethod
    def ttl_seconds(cls) -> int:
        try:
            return max(60, min(int(os.getenv("LIVE_ELEVATED_SESSION_TTL_SECONDS", str(cls.DEFAULT_TTL_SECONDS))), 900))
        except ValueError:
            return cls.DEFAULT_TTL_SECONDS

    @staticmethod
    def token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @staticmethod
    def normalize_base32_secret(secret: str) -> bytes:
        normalized = "".join(str(secret or "").strip().split()).upper()
        if not normalized:
            raise LiveExecutionElevationError("LIVE_TOTP_SECRET must be configured when LIVE_MFA_REQUIRED=true")
        padding = "=" * ((8 - len(normalized) % 8) % 8)
        try:
            return base64.b32decode(normalized + padding, casefold=True)
        except Exception as exc:
            raise LiveExecutionElevationError("LIVE_TOTP_SECRET is not valid base32") from exc

    @classmethod
    def totp_code(cls, secret: str, *, timestamp: Optional[int] = None) -> str:
        key = cls.normalize_base32_secret(secret)
        counter = int(timestamp if timestamp is not None else time.time()) // cls.DEFAULT_TOTP_STEP_SECONDS
        digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
        offset = digest[-1] & 0x0F
        binary = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
        return str(binary % (10**cls.DEFAULT_TOTP_DIGITS)).zfill(cls.DEFAULT_TOTP_DIGITS)

    @classmethod
    def verify_totp(cls, secret: str, provided_code: str, *, timestamp: Optional[int] = None) -> bool:
        code = str(provided_code or "").strip()
        if len(code) != cls.DEFAULT_TOTP_DIGITS or not code.isdigit():
            return False
        current = int(timestamp if timestamp is not None else time.time())
        return any(
            hmac.compare_digest(cls.totp_code(secret, timestamp=current + drift * cls.DEFAULT_TOTP_STEP_SECONDS), code)
            for drift in (-1, 0, 1)
        )

    @staticmethod
    def parse_timestamp(value: Any) -> Optional[datetime]:
        if not value:
            return None
        if isinstance(value, datetime):
            parsed = value
        else:
            try:
                parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            except ValueError:
                return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    async def elevate(self, *, user: Dict[str, Any], password: str, totp_code: Optional[str], request_ip: str) -> Dict[str, Any]:
        if not password or not self.pwd_context.verify(password, user.get("password_hash", "")):
            raise LiveExecutionElevationError("Password re-authentication failed")

        if self.mfa_required():
            secret = resolve_secret_env("LIVE_TOTP_SECRET")
            if not self.verify_totp(secret, str(totp_code or "")):
                raise LiveExecutionElevationError("TOTP verification failed")

        now = self.utc_now()
        expires_at = now + timedelta(seconds=self.ttl_seconds())
        token = secrets.token_urlsafe(48)
        record = {
            "user_id": user["id"],
            "token_hash": self.token_hash(token),
            "request_ip": request_ip,
            "mfa_verified": self.mfa_required(),
            "created_at": now,
            "expires_at": expires_at,
            "revoked_at": None,
            "last_used_at": None,
        }
        await self.db.live_execution_sessions.insert_one(record)
        return {
            "live_session_token": token,
            "expires_at": self.iso(expires_at),
            "mfa_verified": record["mfa_verified"],
        }

    async def verify(self, *, user_id: str, token: Optional[str], request_ip: str) -> Dict[str, Any]:
        if not token:
            raise LiveExecutionElevationError("X-Live-Session-Token header required")
        record = await self.db.live_execution_sessions.find_one(
            {"user_id": user_id, "token_hash": self.token_hash(token), "revoked_at": None},
            {"_id": 0},
        )
        if not record:
            raise LiveExecutionElevationError("Live execution session not found or revoked")
        expires_at = self.parse_timestamp(record.get("expires_at"))
        if not expires_at or self.utc_now() >= expires_at:
            await self.db.live_execution_sessions.update_one(
                {"user_id": user_id, "token_hash": self.token_hash(token), "revoked_at": None},
                {"$set": {"revoked_at": self.utc_now(), "revoked_reason": "expired"}},
            )
            raise LiveExecutionElevationError("Live execution session expired")
        if record.get("request_ip") and request_ip and record.get("request_ip") != request_ip:
            raise LiveExecutionElevationError("Live execution session IP binding mismatch")
        await self.db.live_execution_sessions.update_one(
            {"user_id": user_id, "token_hash": self.token_hash(token)},
            {"$set": {"last_used_at": self.utc_now()}},
        )
        return {"user_id": user_id, "expires_at": self.iso(expires_at), "mfa_verified": bool(record.get("mfa_verified"))}

    async def revoke(self, *, user_id: str, token: Optional[str]) -> int:
        query: Dict[str, Any] = {"user_id": user_id, "revoked_at": None}
        if token:
            query["token_hash"] = self.token_hash(token)
        result = await self.db.live_execution_sessions.update_many(
            query,
            {"$set": {"revoked_at": self.utc_now(), "revoked_reason": "operator_revoked"}},
        )
        return int(getattr(result, "modified_count", 0))
