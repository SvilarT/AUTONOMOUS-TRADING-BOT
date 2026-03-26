"""Security API routes for secrets and custody operations.

This module exposes endpoints to manage secrets (for demonstration
purposes only) and to perform deposits and withdrawals via a custody
service.  In a real system, secrets would never be retrievable via
API, and withdrawals would be gated by multi‑party approvals and
compliance checks.  Use this module as a conceptual reference.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from ..security.secrets_manager import SecretsManager
from ..security.custody import MockCustodyService


router = APIRouter(prefix="/security", tags=["security"])

secrets_manager = SecretsManager()
custody_service = MockCustodyService()


class SecretRequest(BaseModel):
    key: str
    value: str


@router.get("/secrets/{key}")
def get_secret(key: str) -> dict[str, str]:
    """Retrieve a secret by key.  Only for demonstration; avoid exposing secrets via API."""
    value = secrets_manager.get_secret(key)
    if value is None:
        raise HTTPException(status_code=404, detail="Secret not found")
    return {"key": key, "value": value}


@router.post("/secrets")
def set_secret(req: SecretRequest) -> dict[str, str]:
    """Store a secret in the in‑memory store.  For testing and demo only."""
    secrets_manager.set_secret(req.key, req.value)
    return {"key": req.key, "value": req.value}


class CustodyRequest(BaseModel):
    asset: str
    amount: float
    address: str


@router.post("/deposit")
async def deposit(req: CustodyRequest) -> dict[str, Any]:
    """Deposit funds into the custody wallet.  Returns transaction metadata."""
    result = await custody_service.deposit(req.asset, req.amount, req.address)
    return {"status": "success", "transaction": result}


@router.post("/withdraw")
async def withdraw(req: CustodyRequest) -> dict[str, Any]:
    """Withdraw funds from the custody wallet.  Returns transaction metadata or error."""
    try:
        result = await custody_service.withdraw(req.asset, req.amount, req.address)
        return {"status": "success", "transaction": result}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
