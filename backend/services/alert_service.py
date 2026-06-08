from datetime import datetime, timezone
from typing import Any, Dict

import aiohttp

from services.settings_v2 import SETTINGS


class AlertService:
    def __init__(self, db):
        self.db = db

    @staticmethod
    def utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    async def _deliver_webhook(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        webhook_url = SETTINGS.ops_alert_webhook_url
        if not webhook_url:
            return {"configured": False, "status": "not_configured"}
        try:
            timeout = aiohttp.ClientTimeout(total=3)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(webhook_url, json={"event": "autonomous_trading_bot_alert", "alert": alert}) as response:
                    return {"configured": True, "status": "delivered" if 200 <= response.status < 300 else "failed", "http_status": response.status}
        except Exception as exc:
            return {"configured": True, "status": "failed", "error": exc.__class__.__name__}

    async def emit(
        self,
        user_id: str,
        alert_type: str,
        severity: str,
        message: str,
        context: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        alert = {
            "user_id": user_id,
            "type": alert_type,
            "severity": severity,
            "message": message,
            "context": context or {},
            "created_at": self.utc_now(),
            "acknowledged": False,
            "delivery": {"configured": bool(SETTINGS.ops_alert_webhook_url), "status": "pending"},
        }
        result = await self.db.alerts.insert_one(alert)
        delivery = await self._deliver_webhook({key: value for key, value in alert.items() if key != "_id"})
        await self.db.alerts.update_one({"_id": result.inserted_id}, {"$set": {"delivery": delivery}})
        alert["delivery"] = delivery
        alert.pop("_id", None)
        return alert

    async def list_alerts(self, user_id: str, limit: int = 100):
        return await self.db.alerts.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)
