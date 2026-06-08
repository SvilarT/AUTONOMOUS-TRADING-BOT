import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from services.alert_service import AlertService
from services.live_order_audit_service_v2 import LiveOrderAuditServiceV2


class LiveCircuitBreakerError(RuntimeError):
    pass


class LiveCircuitBreakerServiceV2:
    """Persistent live halt automation for security and broker anomalies."""

    IMMEDIATE_HALT_EVENTS = {"audit_chain_failure", "credential_boundary_failure"}
    BURST_HALT_EVENTS = {"adapter_error", "broker_rejection", "rate_limit_violation", "approval_replay", "idempotency_violation", "elevation_failure"}

    def __init__(self, db):
        self.db = db
        self.alerts = AlertService(db)
        self.audits = LiveOrderAuditServiceV2(db)

    @staticmethod
    def utc_now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def env_int(name: str, default: int, minimum: int = 1, maximum: int = 10_000) -> int:
        try:
            return max(minimum, min(int(os.getenv(name, str(default))), maximum))
        except ValueError:
            return default

    async def active_halt(self, user_id: str) -> Optional[Dict[str, Any]]:
        return await self.db.live_halts.find_one(
            {"$or": [{"scope": "global"}, {"scope": "user", "user_id": user_id}], "active": True},
            {"_id": 0},
            sort=[("created_at", -1)],
        )

    async def trip(self, *, user_id: str, reason: str, event_type: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        existing = await self.active_halt(user_id)
        if existing:
            return existing
        record = {
            "scope": "user",
            "user_id": user_id,
            "reason": reason,
            "event_type": event_type,
            "context": context or {},
            "active": True,
            "created_by": "live_circuit_breaker_v2",
            "created_at": self.utc_now(),
            "reset_at": None,
            "reset_by": None,
        }
        await self.db.live_halts.insert_one(record)
        await self.alerts.emit(user_id, "live_trading_halted", "critical", reason, {"event_type": event_type, **(context or {})})
        return record

    async def record_event(
        self,
        *,
        user_id: str,
        event_type: str,
        message: str,
        severity: str = "warning",
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        now = self.utc_now()
        event = {"user_id": user_id, "event_type": event_type, "message": message, "severity": severity, "context": context or {}, "created_at": now}
        await self.db.live_execution_events.insert_one(event)
        await self.alerts.emit(user_id, event_type, severity, message, context or {})

        halt = None
        if event_type in self.IMMEDIATE_HALT_EVENTS:
            halt = await self.trip(user_id=user_id, reason=message, event_type=event_type, context=context)
        elif event_type in self.BURST_HALT_EVENTS:
            window_seconds = self.env_int("LIVE_CIRCUIT_BREAKER_WINDOW_SECONDS", 300, minimum=30, maximum=3600)
            threshold = self.env_int("LIVE_CIRCUIT_BREAKER_FAILURE_THRESHOLD", 3, minimum=1, maximum=100)
            count = await self.db.live_execution_events.count_documents(
                {"user_id": user_id, "event_type": event_type, "created_at": {"$gte": now - timedelta(seconds=window_seconds)}}
            )
            if count >= threshold:
                halt = await self.trip(
                    user_id=user_id,
                    reason=f"Automatic live halt: {event_type} threshold reached",
                    event_type=event_type,
                    context={"count": count, "window_seconds": window_seconds, **(context or {})},
                )
        return {"event": event, "halt": halt}

    async def assert_audit_chain(self, user_id: str) -> Dict[str, Any]:
        result = await self.audits.verify_user_chain(user_id)
        if result.get("status") != "ok":
            await self.record_event(
                user_id=user_id,
                event_type="audit_chain_failure",
                message="Live audit chain verification failed; live trading halted",
                severity="critical",
                context={"verification": result},
            )
            raise LiveCircuitBreakerError("Live audit chain verification failed")
        return result

    async def reset_user_halts(self, *, user_id: str, reset_by: str, reason: str) -> int:
        result = await self.db.live_halts.update_many(
            {"scope": "user", "user_id": user_id, "active": True},
            {"$set": {"active": False, "reset_at": self.utc_now(), "reset_by": reset_by, "reset_reason": reason}},
        )
        return int(getattr(result, "modified_count", 0))
