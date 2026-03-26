"""Pydantic schemas for API requests and responses.

These models define the structure of incoming requests and outgoing
responses for the Phase‑6 REST API.  Using Pydantic ensures type
validation and generates OpenAPI documentation automatically when used
with FastAPI.
"""

from __future__ import annotations

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class Position(BaseModel):
    symbol: str
    base_units: float
    avg_price: float
    notional_usd: Optional[float] = None


class State(BaseModel):
    cash_balance: float = Field(..., description="Current cash balance in base currency")
    equity_high: float
    daily_start_equity: float
    realized_pnl: Optional[float] = 0.0


class PortfolioResponse(BaseModel):
    state: State
    positions: List[Position]


class MetricsResponse(BaseModel):
    metrics: Dict[str, Any]


class TradeRequest(BaseModel):
    symbol: str
    action: str  # "BUY" or "SELL"
    notional: float


class TradeResponse(BaseModel):
    success: bool
    details: Dict[str, Any]