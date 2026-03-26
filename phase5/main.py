"""Phase 5 entry point with enhanced risk controls.

This script demonstrates the trading loop using the Phase‑5 risk manager.
It loads strategy and connector plugins, instantiates services and runs
a single simulated cycle.  The risk manager parameters (including the
risk profile) are read from the configuration file.  Portfolio metrics
include volatility, value‑at‑risk, expected shortfall and correlation.
"""

import asyncio
import yaml
import random
from typing import Dict, Any, List

from phase5.core.strategy_engine import StrategyEngine
from phase5.core.execution_router import ExecutionRouter
from phase5.core.risk_manager import RiskManager
from phase5.core.portfolio_service import PortfolioService, AbstractPortfolioRepo
from phase5.plugin_loader import load_strategies, load_connectors


class InMemoryRepo(AbstractPortfolioRepo):
    def __init__(self) -> None:
        self.state: Dict[str, Dict[str, Any]] = {}
        self.positions: Dict[str, List[Dict[str, Any]]] = {}

    async def get_state(self, user_id: str) -> Dict[str, Any] | None:
        return self.state.get(user_id)

    async def upsert_state(self, user_id: str, updates: Dict[str, Any]) -> None:
        current = self.state.get(user_id, {})
        merged = current.copy()
        for k, v in updates.items():
            if k in ("cash_balance", "realized_pnl"):
                merged[k] = merged.get(k, 0.0) + v
            else:
                merged[k] = v
        self.state[user_id] = merged

    async def get_positions(self, user_id: str) -> List[Dict[str, Any]]:
        return self.positions.get(user_id, [])

    async def upsert_position(self, user_id: str, symbol: str, updates: Dict[str, Any]) -> None:
        pos_list = self.positions.setdefault(user_id, [])
        existing = next((p for p in pos_list if p["symbol"] == symbol), None)
        if existing:
            existing.update(updates)
        else:
            pos_list.append(updates)

    async def delete_position(self, user_id: str, symbol: str) -> None:
        pos_list = self.positions.get(user_id)
        if not pos_list:
            return
        self.positions[user_id] = [p for p in pos_list if p["symbol"] != symbol]


def generate_random_walk(base_price: float, length: int = 100, volatility: float = 0.003) -> List[float]:
    price = base_price
    series = []
    for _ in range(length):
        delta = random.uniform(-volatility, volatility)
        price *= 1 + delta
        series.append(round(price, 2))
    return series


async def run_once(config_path: str) -> None:
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    strategies = load_strategies(config)
    connectors = load_connectors(config)
    strategy_engine = StrategyEngine(strategies)
    execution_router = ExecutionRouter(connectors)
    # Determine risk profile from config (default moderate)
    risk_cfg = config.get("risk", {})
    risk_profile = risk_cfg.get("profile", "moderate")
    risk_manager = RiskManager(risk_profile=risk_profile)
    repo = InMemoryRepo()
    portfolio_service = PortfolioService(repo)
    # Choose a symbol to trade; use first symbol from connector base prices
    if not connectors:
        print("No connectors configured.")
        return
    # For simplicity, assume connectors[0] has attribute base_prices as in mock connectors
    first_conn = connectors[0]
    base_prices: Dict[str, float] = getattr(first_conn, "base_prices", {"BTC-USD": 45000.0})
    symbol = next(iter(base_prices.keys()))
    # Generate synthetic price history
    prices = generate_random_walk(base_prices[symbol])
    # Determine existing positions
    user_id = "user1"
    positions = await repo.get_positions(user_id)
    has_position = any(p["symbol"] == symbol for p in positions)
    # Generate signals
    signals = strategy_engine.generate_all(prices, has_position)
    if not signals:
        print("No signals generated.")
        return
    # Pick best signal by confidence and score
    top = max(signals, key=lambda s: (abs(s.get("score", 0.0)), s.get("confidence", 0.0)))
    action = top.get("action")
    notional = 100.0 * (top.get("confidence", 50.0) / 100.0)
    # Compute metrics
    state = await repo.get_state(user_id) or {"cash_balance": 10000.0, "equity_high": 10000.0, "daily_start_equity": 10000.0}
    price_map = {symbol: prices[-1]}
    history = {symbol: prices}
    metrics = risk_manager.portfolio_metrics(state, positions, price_map, history)
    kill = risk_manager.should_kill_switch(metrics)
    if kill.get("triggered"):
        print("Kill switch triggered:", kill["reason"])
        return
    allowed = risk_manager.can_open_position(metrics, positions, notional)
    if action == "BUY" and allowed.get("allowed"):
        connector = await execution_router.select_connector(symbol)
        result = await execution_router.buy(symbol, notional)
        await portfolio_service.record_buy_fill(user_id, symbol, result.get("filled_price", price_map[symbol]), result.get("base_units", 0.0), result.get("notional_usd", notional))
        print(f"Executed BUY for {symbol} via {connector.name}:", result)
    elif action == "SELL" and has_position:
        pos = next((p for p in positions if p["symbol"] == symbol), None)
        if pos:
            connector = await execution_router.select_connector(symbol)
            result = await execution_router.sell(symbol, pos.get("base_units", 0.0))
            await portfolio_service.record_sell_fill(user_id, symbol, result.get("filled_price", price_map[symbol]), pos.get("base_units", 0.0))
            print(f"Executed SELL for {symbol} via {connector.name}:", result)
    else:
        print("No trade executed.")
    # Display metrics and state
    updated_state = await repo.get_state(user_id)
    print("State:", updated_state)
    print("Metrics:", metrics)


if __name__ == "__main__":
    import os
    cfg = os.path.join(os.path.dirname(__file__), "config.yml")
    asyncio.run(run_once(cfg))