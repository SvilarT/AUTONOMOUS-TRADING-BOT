"""FastAPI application exposing the trading bot functionality.

This module defines REST endpoints for interacting with the autonomous
trading bot.  Endpoints include retrieving a user’s portfolio state,
computing risk metrics and submitting trade instructions.  The API is
deliberately minimal; it should be extended with authentication,
pagination, error handling and additional endpoints for production use.
"""

from __future__ import annotations

import asyncio
import os
import random
from typing import Dict, Any

import yaml
from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse

from .schemas import PortfolioResponse, MetricsResponse, TradeRequest, TradeResponse
from ..core.strategy_engine import StrategyEngine
from ..core.execution_router import ExecutionRouter
from ..core.risk_manager import RiskManager
from ..core.portfolio_service import PortfolioService, AbstractPortfolioRepo
from ..plugin_loader import load_strategies, load_connectors
from ..monitoring.metrics import trade_requests_total, trade_latency_seconds, risk_events_total
import time


class InMemoryRepo(AbstractPortfolioRepo):
    """In‑memory repository for API use.  Persists state across requests."""

    def __init__(self) -> None:
        self.state: Dict[str, Dict[str, Any]] = {}
        self.positions: Dict[str, list[Dict[str, Any]]] = {}

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

    async def get_positions(self, user_id: str) -> list[Dict[str, Any]]:
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


def load_configuration() -> Dict[str, Any]:
    """Load YAML configuration from the phase10 directory."""
    cfg_path = os.path.join(os.path.dirname(__file__), "..", "config.yml")
    with open(cfg_path, "r") as f:
        return yaml.safe_load(f)


def create_app() -> FastAPI:
    app = FastAPI(title="Autonomous Trading Bot API", version="0.1")

    # Shared instances (lazy initialised on startup)
    class Services:
        config: Dict[str, Any] | None = None
        strategy_engine: StrategyEngine | None = None
        execution_router: ExecutionRouter | None = None
        risk_manager: RiskManager | None = None
        portfolio_service: PortfolioService | None = None

    @app.on_event("startup")
    async def startup_event() -> None:
        # Load config and instantiate services
        Services.config = load_configuration()
        strategies = load_strategies(Services.config)
        connectors = load_connectors(Services.config)
        Services.strategy_engine = StrategyEngine(strategies)
        Services.execution_router = ExecutionRouter(connectors)
        # Risk profile from config
        risk_cfg = Services.config.get("risk", {})
        profile = risk_cfg.get("profile", "moderate")
        Services.risk_manager = RiskManager(risk_profile=profile)
        repo = InMemoryRepo()
        Services.portfolio_service = PortfolioService(repo)

        # Note: MarketplaceService is initialised in the marketplace router module.  If
        # you wish to share a single instance across the app, import
        # `service` from `phase7.api.marketplace` here and assign it to Services.

    def get_services() -> Services:
        if Services.strategy_engine is None:
            raise HTTPException(status_code=503, detail="Services not initialised")
        return Services

    @app.get("/users/{user_id}/portfolio", response_model=PortfolioResponse)
    async def get_portfolio(user_id: str, services: Services = Depends(get_services)) -> PortfolioResponse:
        # Ensure account exists
        state = await services.portfolio_service.ensure_account_state(user_id)
        positions = await services.portfolio_service.repo.get_positions(user_id)
        # Convert positions to model list
        return PortfolioResponse(state=state, positions=positions)

    @app.get("/users/{user_id}/metrics", response_model=MetricsResponse)
    async def get_metrics(user_id: str, services: Services = Depends(get_services)) -> MetricsResponse:
        # Compute risk metrics using synthetic price history for demonstration
        state = await services.portfolio_service.repo.get_state(user_id) or {"cash_balance": 10000.0, "equity_high": 10000.0, "daily_start_equity": 10000.0}
        positions = await services.portfolio_service.repo.get_positions(user_id)
        # Build price_map and price_history for each symbol using base_prices from first connector
        connectors = services.execution_router.connectors
        if not connectors:
            raise HTTPException(status_code=400, detail="No connectors configured")
        base_prices: Dict[str, float] = getattr(connectors[0], "base_prices", {})
        price_map: Dict[str, float] = {}
        history: Dict[str, list[float]] = {}
        for sym in base_prices:
            price = base_prices[sym]
            price_map[sym] = price
            # generate random walk for demonstration
            series = [price]
            for _ in range(services.risk_manager.vol_lookback + 5):
                delta = random.uniform(-0.003, 0.003)
                price *= 1 + delta
                series.append(price)
            history[sym] = series
        metrics = services.risk_manager.portfolio_metrics(state, positions, price_map, history)
        return MetricsResponse(metrics=metrics)

    @app.post("/users/{user_id}/trade", response_model=TradeResponse)
    async def submit_trade(user_id: str, req: TradeRequest, services: Services = Depends(get_services)) -> TradeResponse:
        """Handle a trade request and instrument metrics for monitoring."""
        # Start timer for latency measurement
        start = time.perf_counter()
        status_label = "success"
        try:
            # Validate action
            action = req.action.upper()
            if action not in {"BUY", "SELL"}:
                raise HTTPException(status_code=400, detail="Action must be BUY or SELL")
            # Generate price map using base price from first connector
            connectors = services.execution_router.connectors
            if not connectors:
                raise HTTPException(status_code=400, detail="No connectors available")
            base_prices: Dict[str, float] = getattr(connectors[0], "base_prices", {})
            price = base_prices.get(req.symbol)
            if price is None:
                raise HTTPException(status_code=400, detail=f"Symbol {req.symbol} not supported")
            # Compute risk metrics for this trade
            state = await services.portfolio_service.repo.get_state(user_id) or {"cash_balance": 10000.0, "equity_high": 10000.0, "daily_start_equity": 10000.0}
            positions = await services.portfolio_service.repo.get_positions(user_id)
            price_map = {req.symbol: price}
            # Generate synthetic history for this symbol
            hist = [price]
            for _ in range(services.risk_manager.vol_lookback + 5):
                delta = random.uniform(-0.003, 0.003)
                price *= 1 + delta
                hist.append(price)
            history = {req.symbol: hist}
            metrics = services.risk_manager.portfolio_metrics(state, positions, price_map, history)
            # Check kill switch
            if services.risk_manager.should_kill_switch(metrics)["triggered"]:
                # Record risk event
                risk_events_total.labels(event="kill_switch").inc()
                status_label = "failure"
                return TradeResponse(success=False, details={"reason": "risk kill switch triggered"})
            allowed = services.risk_manager.can_open_position(metrics, positions, req.notional)
            if action == "BUY" and allowed.get("allowed"):
                connector = await services.execution_router.select_connector(req.symbol)
                result = await services.execution_router.buy(req.symbol, req.notional)
                await services.portfolio_service.record_buy_fill(
                    user_id,
                    req.symbol,
                    result.get("filled_price", price_map[req.symbol]),
                    result.get("base_units", 0.0),
                    result.get("notional_usd", req.notional),
                )
                return TradeResponse(success=True, details=result)
            elif action == "SELL":
                # Sell up to specified notional if position exists
                pos = next((p for p in positions if p["symbol"] == req.symbol), None)
                if not pos:
                    status_label = "failure"
                    return TradeResponse(success=False, details={"reason": "no position to sell"})
                # Determine units to sell based on notional and price
                units = req.notional / price_map[req.symbol]
                units = min(units, pos.get("base_units", 0.0))
                connector = await services.execution_router.select_connector(req.symbol)
                result = await services.execution_router.sell(req.symbol, units)
                await services.portfolio_service.record_sell_fill(
                    user_id,
                    req.symbol,
                    result.get("filled_price", price_map[req.symbol]),
                    units,
                )
                return TradeResponse(success=True, details=result)
            else:
                # Denied by risk constraints
                risk_events_total.labels(event="open_denied").inc()
                status_label = "failure"
                return TradeResponse(success=False, details={"reason": allowed.get("reason", "trade not allowed")})
        finally:
            # Update metrics after processing the trade
            duration = time.perf_counter() - start
            trade_latency_seconds.observe(duration)
            trade_requests_total.labels(status=status_label).inc()

    # Include additional routers (marketplace, security, compliance, monitoring, notifications)
    from .marketplace import router as marketplace_router
    app.include_router(marketplace_router)
    # Security endpoints for secrets and custody
    from .security import router as security_router
    app.include_router(security_router)
    # Compliance endpoints for KYC/AML
    from .compliance import router as compliance_router
    app.include_router(compliance_router)
    # Monitoring endpoints (metrics and health checks)
    from .monitoring import router as monitoring_router
    app.include_router(monitoring_router)
    # Notifications endpoints
    from .notifications import router as notifications_router
    app.include_router(notifications_router)

    return app


app = create_app()