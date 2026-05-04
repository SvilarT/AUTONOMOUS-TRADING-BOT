from datetime import datetime, timezone
from typing import Any, Dict, Optional

from services.coinbase_live_execution_adapter_v2 import CoinbaseLiveExecutionAdapterV2, CoinbaseLiveExecutionError
from services.execution_service_v2 import ExecutionServiceV2
from services.live_order_audit_service_v2 import LiveOrderAuditServiceV2
from services.live_trading_gate_v2 import LiveTradingGateV2
from services.trading_mode_v2 import TradingModeService


class LiveTradingServiceV2:
    """Gated live execution orchestration.

    This service is the only intended entrypoint for live orders. It performs a
    gate preflight, writes a hash-chained audit record, supports dry-run
    previews, and only then delegates to the live adapter.
    """

    def __init__(self, db, adapter: Optional[CoinbaseLiveExecutionAdapterV2] = None, gate: Optional[LiveTradingGateV2] = None):
        self.db = db
        self.adapter = adapter or CoinbaseLiveExecutionAdapterV2()
        self.gate = gate or LiveTradingGateV2()
        self.audits = LiveOrderAuditServiceV2(db)

    @staticmethod
    def utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

    async def _user_config(self, user_id: str) -> Dict[str, Any]:
        return await self.db.bot_configs.find_one({"user_id": user_id}, {"_id": 0}) or {}

    async def _audit(self, record: Dict[str, Any]) -> Dict[str, Any]:
        return await self.audits.append(record)

    async def preview_market_buy(self, user_id: str, symbol: str, notional_usd: float) -> Dict[str, Any]:
        return await self.place_market_buy(user_id, symbol, notional_usd, dry_run=True)

    async def place_market_buy(
        self,
        user_id: str,
        symbol: str,
        notional_usd: float,
        approval_token: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        user_config = await self._user_config(user_id)
        mode = TradingModeService().mode.value
        client_order_id = ExecutionServiceV2.build_client_order_id("live_buy", symbol, f"{user_id}:{symbol}:BUY:{self.utc_now()}")
        gate = self.gate.safe_preflight(
            trading_mode=mode,
            user_config=user_config,
            symbol=symbol,
            side="BUY",
            notional_usd=notional_usd,
            approval_token=approval_token,
            dry_run=dry_run,
        )
        audit = await self._audit(
            {
                "user_id": user_id,
                "symbol": symbol,
                "side": "BUY",
                "notional_usd": round(float(notional_usd), 8),
                "client_order_id": client_order_id,
                "dry_run": dry_run,
                "gate": gate,
                "status": "blocked" if not gate.get("allowed") else "preflight_passed",
            }
        )
        if not gate.get("allowed"):
            return {"success": False, "status": "blocked", "audit": audit, "gate": gate}

        try:
            order = await self.adapter.place_market_buy(symbol, notional_usd, client_order_id=client_order_id, dry_run=dry_run)
        except CoinbaseLiveExecutionError as exc:
            await self._audit({**audit, "status": "adapter_error", "error": str(exc)})
            raise
        await self._audit({**audit, "status": order.get("status"), "order": order})
        return {"success": bool(order.get("success")), "status": order.get("status"), "order": order, "audit": audit, "gate": gate}

    async def preview_market_sell(self, user_id: str, symbol: str, base_units: float, reference_price: float) -> Dict[str, Any]:
        return await self.place_market_sell(user_id, symbol, base_units, reference_price=reference_price, dry_run=True)

    async def place_market_sell(
        self,
        user_id: str,
        symbol: str,
        base_units: float,
        reference_price: float,
        approval_token: Optional[str] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        notional_estimate = float(base_units) * float(reference_price)
        user_config = await self._user_config(user_id)
        mode = TradingModeService().mode.value
        client_order_id = ExecutionServiceV2.build_client_order_id("live_sell", symbol, f"{user_id}:{symbol}:SELL:{self.utc_now()}")
        gate = self.gate.safe_preflight(
            trading_mode=mode,
            user_config=user_config,
            symbol=symbol,
            side="SELL",
            notional_usd=notional_estimate,
            approval_token=approval_token,
            dry_run=dry_run,
        )
        audit = await self._audit(
            {
                "user_id": user_id,
                "symbol": symbol,
                "side": "SELL",
                "base_units": round(float(base_units), 12),
                "notional_usd": round(notional_estimate, 8),
                "client_order_id": client_order_id,
                "dry_run": dry_run,
                "gate": gate,
                "status": "blocked" if not gate.get("allowed") else "preflight_passed",
            }
        )
        if not gate.get("allowed"):
            return {"success": False, "status": "blocked", "audit": audit, "gate": gate}

        try:
            order = await self.adapter.place_market_sell(symbol, base_units, client_order_id=client_order_id, dry_run=dry_run)
        except CoinbaseLiveExecutionError as exc:
            await self._audit({**audit, "status": "adapter_error", "error": str(exc)})
            raise
        await self._audit({**audit, "status": order.get("status"), "order": order})
        return {"success": bool(order.get("success")), "status": order.get("status"), "order": order, "audit": audit, "gate": gate}

    async def list_audits(self, user_id: str, limit: int = 100):
        return await self.db.live_order_audits.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1).limit(limit).to_list(limit)

    async def verify_audit_chain(self, user_id: str, limit: int = 1000):
        return await self.audits.verify_user_chain(user_id, limit=limit)
