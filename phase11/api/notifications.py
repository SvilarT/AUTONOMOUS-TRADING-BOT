"""Notification API endpoints.

Routes for sending different types of notifications.  Each endpoint
invokes the corresponding method on the global NotificationService
instance.  In production, authentication and authorization would be
required to send notifications on behalf of users.
"""

from __future__ import annotations

from typing import Dict, Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..notifications.service import NotificationService


router = APIRouter(prefix="/notifications", tags=["notifications"])

service = NotificationService()


class TradeConfirmationRequest(BaseModel):
    user_id: str
    details: Dict[str, Any] = Field(..., description="Trade execution details")


@router.post("/trade-confirmation")
def send_trade_confirmation(req: TradeConfirmationRequest) -> dict[str, str]:
    """Send a trade confirmation notification to a user."""
    service.send_trade_confirmation(req.user_id, req.details)
    return {"status": "sent"}


class RiskAlertRequest(BaseModel):
    user_id: str
    message: str


@router.post("/risk-alert")
def send_risk_alert(req: RiskAlertRequest) -> dict[str, str]:
    """Send a risk alert notification to a user."""
    service.send_risk_alert(req.user_id, req.message)
    return {"status": "sent"}


class SystemStatusRequest(BaseModel):
    message: str


@router.post("/system-status")
def send_system_status(req: SystemStatusRequest) -> dict[str, str]:
    """Broadcast a system status message."""
    service.send_system_status(req.message)
    return {"status": "sent"}
