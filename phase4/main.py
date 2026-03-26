"""Entry point demonstrating the adaptive learning engine and enhanced risk manager.

This script wires together the plugin loader, strategy engine,
execution router, portfolio service and the new machine‑learning
strategy.  It simulates a single trading cycle using synthetic price
data and prints the resulting portfolio state.  To run this example,
execute ``python phase4/main.py`` from the repository root.

In a production system, replace the simulated price series with a
``MarketDataPipeline`` subscriber and schedule periodic invocations of
the trading loop.
"""

import asyncio
import yaml
from typing import Dict, Any, List

from phase4.core.strategy_engine import StrategyEngine
from phase4.core.execution_router import ExecutionRouter
from phase4.core.risk_manager import RiskManager
from phase4.core.portfolio_service import PortfolioService, AbstractPortfolioRepo
from phase4.plugin_loader import load_strategies, load_connectors


class InMemoryRepo(AbstractPortfolioRepo):
    """In‑memory portfolio repository for demonstration purposes."""

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


async def run_bot(config_path: str) -> None:
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    strategies = load_strategies(config)
    connectors = load_connectors(config)
    strategy_engine = StrategyEngine(strategies)
    execution_router = ExecutionRouter(connectors)
    risk_manager = RiskManager()
    portfolio_repo = InMemoryRepo()
    portfolio_service = PortfolioService(portfolio_repo)
    # Simulate a single trading cycle for user1 on BTC‑USD
    user_id = "user1"
    symbol = "BTC-USD"
    # Generate a synthetic price series: random walk around base price
    base_price = 45000.0
    import random
    prices: List[float] = []
    price = base_price
    for _ in range(100):
        delta = random.uniform(-0.003, 0.003)
        price *= 1 + delta
        prices.append(round(price, 2))
    # Determine whether a position exists
    positions = await portfolio_repo.get_positions(user_id)
    has_position = any(p["symbol"] == symbol for p in positions)
    # Generate signals using all registered strategies
    signals = strategy_engine.generate_all(prices, has_position)
    # Choose the top signal by confidence and absolute score
    if not signals:
        print("No signals generated.")
        return
    signals_sorted = sorted(
        signals,
        key=lambda s: (abs(s.get("score", 0.0)), s.get("confidence", 0.0)),
        reverse=True,
    )
    top = signals_sorted[0]
    action = top.get("action")
    notional = 100.0 * (top.get("confidence", 50.0) / 100.0)
    # Compute portfolio metrics with price history for volatility/VAR
    state = await portfolio_repo.get_state(user_id) or {}
    price_map = {symbol: prices[-1]}
    price_history_map = {symbol: prices}
    metrics = risk_manager.portfolio_metrics(state, positions, price_map, price_history_map)
    allowed = risk_manager.can_open_position(metrics, positions, notional)
    if action == "BUY" and allowed.get("allowed"):
        connector = await execution_router.select_connector(symbol)
        if connector is None:
            print("No suitable connector available.")
            return
        result = await execution_router.buy(symbol, notional)
        await portfolio_service.record_buy_fill(
            user_id, symbol, result.get("filled_price", price_map[symbol]), result.get("base_units", 0.0), result.get("notional_usd", notional)
        )
        print(f"Bought {symbol} via {connector.name}:", result)
    elif action == "SELL" and has_position:
        # Sell all units in position
        pos = next((p for p in positions if p["symbol"] == symbol), None)
        if pos:
            connector = await execution_router.select_connector(symbol)
            result = await execution_router.sell(symbol, pos.get("base_units", 0.0))
            await portfolio_service.record_sell_fill(
                user_id, symbol, result.get("filled_price", price_map[symbol]), pos.get("base_units", 0.0)
            )
            print(f"Sold {symbol} via {connector.name}:", result)
    else:
        print("No trade executed.")
    # Display updated portfolio metrics
    updated_state = await portfolio_repo.get_state(user_id)
    updated_positions = await portfolio_repo.get_positions(user_id)
    print("State:", updated_state)
    print("Positions:", updated_positions)
    print("Metrics:", metrics)


if __name__ == "__main__":
    import os
    cfg_path = os.path.join(os.path.dirname(__file__), "config.yml")
    asyncio.run(run_bot(cfg_path))