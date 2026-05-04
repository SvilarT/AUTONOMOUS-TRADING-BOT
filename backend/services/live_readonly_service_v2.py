from typing import Any, Dict, List, Optional

from services.alert_service import AlertService
from services.coinbase_readonly_adapter_v2 import CoinbaseReadonlyAdapterV2, CoinbaseReadonlyError
from services.ledger_service_v2 import LedgerServiceV2
from services.portfolio_service_v2 import PortfolioServiceV2


class LiveReadonlyServiceV2:
    """Live-readonly orchestration service.

    Pulls exchange state without placing orders, compares it with internal paper
    read models, and emits alerts when material drift is detected.
    """

    def __init__(self, db, adapter: Optional[CoinbaseReadonlyAdapterV2] = None):
        self.db = db
        self.adapter = adapter or CoinbaseReadonlyAdapterV2()
        self.alerts = AlertService(db)
        self.portfolio = PortfolioServiceV2(db)
        self.ledger = LedgerServiceV2(db)

    @staticmethod
    def _symbol_from_currency(currency: str) -> Optional[str]:
        if currency in {"BTC", "ETH"}:
            return f"{currency}-USD"
        return None

    @staticmethod
    def _base_currency(symbol: str) -> str:
        return symbol.split("-")[0]

    async def snapshot(self, user_id: str, symbols: Optional[List[str]] = None) -> Dict[str, Any]:
        try:
            raw = await self.adapter.snapshot(symbols=symbols)
        except CoinbaseReadonlyError as exc:
            await self.alerts.emit(user_id, "live_readonly_snapshot_failed", "error", str(exc), {})
            raise

        raw["user_id"] = user_id
        raw["internal_positions"] = await self.portfolio.get_positions(user_id)
        raw["ledger_rebuild"] = await self.ledger.rebuild_from_ledger(user_id)
        return raw

    async def compare_exchange_to_internal(self, user_id: str, symbols: Optional[List[str]] = None, tolerance_units: float = 1e-8) -> Dict[str, Any]:
        snapshot = await self.snapshot(user_id, symbols=symbols)
        exchange_accounts = snapshot.get("accounts", [])
        internal_positions = snapshot.get("internal_positions", [])

        exchange_units_by_symbol: Dict[str, float] = {}
        for account in exchange_accounts:
            symbol = self._symbol_from_currency(str(account.get("currency", "")))
            if symbol:
                exchange_units_by_symbol[symbol] = exchange_units_by_symbol.get(symbol, 0.0) + float(account.get("balance", 0.0) or 0.0)

        internal_units_by_symbol = {
            position["symbol"]: float(position.get("base_units", 0.0) or 0.0)
            for position in internal_positions
        }

        issues = []
        for symbol in sorted(set(exchange_units_by_symbol) | set(internal_units_by_symbol)):
            exchange_units = round(exchange_units_by_symbol.get(symbol, 0.0), 12)
            internal_units = round(internal_units_by_symbol.get(symbol, 0.0), 12)
            delta = round(exchange_units - internal_units, 12)
            if abs(delta) > tolerance_units:
                issues.append(
                    {
                        "type": "exchange_internal_position_drift",
                        "symbol": symbol,
                        "exchange_units": exchange_units,
                        "internal_units": internal_units,
                        "delta_units": delta,
                    }
                )

        report = {
            "user_id": user_id,
            "status": "ok" if not issues else "mismatch",
            "mode": "live-readonly",
            "orders_allowed": False,
            "live_execution_enabled": False,
            "issues": issues,
            "snapshot": snapshot,
        }
        await self.db.live_readonly_reports.insert_one(report.copy())
        if issues:
            await self.alerts.emit(
                user_id,
                "live_readonly_drift_detected",
                "warning",
                "Exchange readonly balances differ from internal positions",
                {"issues": issues},
            )
        return report

    async def recent_orders(self, user_id: str, status: str = "all", limit: int = 100) -> Dict[str, Any]:
        try:
            orders = await self.adapter.get_orders(status=status, limit=limit)
        except CoinbaseReadonlyError as exc:
            await self.alerts.emit(user_id, "live_readonly_orders_failed", "error", str(exc), {})
            raise
        return {"user_id": user_id, "mode": "live-readonly", "orders_allowed": False, "orders": orders}

    async def recent_fills(self, user_id: str, product_id: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        try:
            fills = await self.adapter.get_fills(product_id=product_id, limit=limit)
        except CoinbaseReadonlyError as exc:
            await self.alerts.emit(user_id, "live_readonly_fills_failed", "error", str(exc), {})
            raise
        return {"user_id": user_id, "mode": "live-readonly", "orders_allowed": False, "fills": fills}
