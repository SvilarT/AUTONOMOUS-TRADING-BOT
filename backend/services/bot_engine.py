from datetime import datetime, timezone
import asyncio
import logging

from services.execution_control_v2 import ExecutionControlV2
from services.execution_service_v2 import ExecutionServiceV2
from services.portfolio_service_v2 import PortfolioServiceV2
from services.market_data_service import MarketDataService
from services.risk_guard_v2 import RiskGuardV2
from services.signal_planner_v2 import SignalPlannerV2
from services.trading_mode_v2 import TradingModeError, TradingModeService

logger = logging.getLogger(__name__)


class BotEngine:
    def __init__(self, db):
        self.db = db
        self.execution = ExecutionServiceV2()
        self.execution_control = ExecutionControlV2(db)
        self.portfolio = PortfolioServiceV2(db)
        self.market = MarketDataService()
        self.planner = SignalPlannerV2()
        self.mode = TradingModeService()
        self.running = False

    async def start(self, user_id: str):
        self.running = True
        logger.info(f"Bot started: {user_id}")

        while self.running:
            try:
                await self.cycle(user_id)
                await asyncio.sleep(8)
            except Exception as e:
                logger.error(f"Cycle error: {e}")
                await asyncio.sleep(3)

    async def stop(self):
        self.running = False

    async def cycle(self, user_id: str):
        config = await self.db.bot_configs.find_one({"user_id": user_id})
        if not config or not config.get("is_active"):
            return

        risk = RiskGuardV2.from_config(config)
        await self.portfolio.ensure_account_state(user_id)
        symbols = config.get("symbols", ["BTC-USD"])
        price_map = await self.get_price_map(symbols)
        snapshot = await self.portfolio.update_risk_snapshot(user_id, price_map)
        state = await self.db.portfolio_state.find_one({"user_id": user_id}) or {}
        positions = await self.portfolio.get_positions(user_id)
        metrics = risk.portfolio_metrics(state, positions, price_map)
        metrics["daily_loss_pct"] = max(metrics.get("daily_loss_pct", 0.0), max(0.0, -float(snapshot.get("daily_pnl", 0.0)) / (float(snapshot.get("max_equity", 1.0)) or 1.0)))
        metrics["drawdown_pct"] = max(metrics.get("drawdown_pct", 0.0), float(snapshot.get("current_drawdown", 0.0)))
        kill = risk.should_kill_switch(metrics)

        if kill.get("triggered"):
            await self.halt_bot(user_id, kill.get("reason"))
            return

        if self.mode.is_readonly:
            logger.info("Bot is in live-readonly mode; analysis allowed, execution disabled")
            return

        for symbol in symbols:
            positions = await self.portfolio.get_positions(user_id)
            state = await self.db.portfolio_state.find_one({"user_id": user_id}) or {}
            await self.process_symbol(user_id, symbol, positions, state, risk, price_map)

    async def halt_bot(self, user_id: str, reason: str):
        await self.db.bot_configs.update_one(
            {"user_id": user_id},
            {"$set": {"is_active": False, "halt_reason": reason, "updated_at": datetime.now(timezone.utc).isoformat()}},
        )
        logger.warning(f"Bot halted for {user_id}: {reason}")

    async def get_price_map(self, symbols):
        price_map = {}
        for symbol in symbols:
            try:
                current = await self.market.get_current_price(symbol)
                price_map[symbol] = float(current.get("price", 0.0))
            except Exception as exc:
                logger.warning(f"Unable to mark {symbol}: {exc}")
        return price_map

    async def process_symbol(self, user_id, symbol, positions, state, risk: RiskGuardV2, price_map):
        hist = await self.market.get_historical_data(symbol, periods=120)
        prices = [h["price"] for h in hist if h.get("price")]
        position = next((p for p in positions if p["symbol"] == symbol), None)
        plan = self.planner.build_plan(symbol, prices, has_position=bool(position))

        if plan["action"] == "BUY" and not position:
            metrics = risk.portfolio_metrics(state, positions, {**price_map, symbol: prices[-1] if prices else 0.0})
            guard = risk.can_open_position(metrics, positions, plan.get("notional", 0.0), state.get("last_trade_at"))
            if guard["allowed"]:
                await self.execute_buy(user_id, symbol, plan.get("notional", 0.0), plan)
            else:
                logger.info(f"Buy blocked for {symbol}: {guard.get('reason')}")

        elif plan["action"] == "SELL" and position:
            await self.execute_sell(user_id, symbol, position, plan)

    async def execute_buy(self, user_id, symbol, notional, context):
        try:
            self.mode.assert_can_trade()
        except TradingModeError as exc:
            logger.warning(str(exc))
            return

        idempotency_key = self.execution_control.build_idempotency_key(user_id, symbol, "BUY", context)
        if await self.execution_control.already_executed(idempotency_key):
            logger.info(f"Skipping duplicate BUY for {symbol}: {idempotency_key}")
            return

        lock = await self.execution_control.acquire_lock(user_id, symbol, "BUY")
        if not lock.get("acquired"):
            logger.info(f"Buy lock blocked for {symbol}: {lock.get('reason')}")
            return

        try:
            order = await self.execution.buy(symbol, notional, signal_snapshot=context, idempotency_key=idempotency_key)
            order["idempotency_key"] = idempotency_key
            await self.portfolio.record_trade_attempt(user_id, symbol, "BUY", order, context)
            if not order.get("success"):
                logger.error(f"Buy failed for {symbol}: {order}")
                return

            await self.portfolio.record_buy_fill(
                user_id,
                symbol,
                order["filled_price"],
                order["base_units"],
                order["notional_usd"],
                order.get("fee_usd", 0.0),
            )

            await self.db.portfolio_state.update_one(
                {"user_id": user_id},
                {"$set": {"last_trade_at": datetime.now(timezone.utc).isoformat()}},
                upsert=True,
            )
            await self.portfolio.update_risk_snapshot(user_id, {symbol: float(order["filled_price"])})
        finally:
            await self.execution_control.release_lock(lock["key"])

    async def execute_sell(self, user_id, symbol, position, context=None):
        try:
            self.mode.assert_can_trade()
        except TradingModeError as exc:
            logger.warning(str(exc))
            return

        context = context or {"position": position}
        idempotency_key = self.execution_control.build_idempotency_key(user_id, symbol, "SELL", context)
        if await self.execution_control.already_executed(idempotency_key):
            logger.info(f"Skipping duplicate SELL for {symbol}: {idempotency_key}")
            return

        lock = await self.execution_control.acquire_lock(user_id, symbol, "SELL")
        if not lock.get("acquired"):
            logger.info(f"Sell lock blocked for {symbol}: {lock.get('reason')}")
            return

        try:
            order = await self.execution.sell(symbol, position["base_units"], idempotency_key=idempotency_key)
            order["idempotency_key"] = idempotency_key
            await self.portfolio.record_trade_attempt(user_id, symbol, "SELL", order, context)
            if not order.get("success"):
                logger.error(f"Sell failed for {symbol}: {order}")
                return

            result = await self.portfolio.record_sell_fill(
                user_id,
                symbol,
                order["filled_price"],
                order["base_units"],
                order.get("fee_usd", 0.0),
            )

            await self.db.trades_v2.update_one(
                {"client_order_id": order.get("client_order_id")},
                {"$set": {"realized_pnl": result.get("realized_pnl", 0.0), "idempotency_key": idempotency_key}},
            )

            await self.db.portfolio_state.update_one(
                {"user_id": user_id},
                {"$set": {"last_trade_at": datetime.now(timezone.utc).isoformat()}},
                upsert=True,
            )
            await self.portfolio.update_risk_snapshot(user_id, {symbol: float(order["filled_price"])})
        finally:
            await self.execution_control.release_lock(lock["key"])
