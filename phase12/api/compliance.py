"""Compliance API routes for KYC and AML.

This module defines endpoints that allow the platform to perform
identity verification (Know Your Customer, KYC) and transaction
monitoring (Anti‑Money Laundering, AML).  The underlying services are
stubs; integrate real providers in production.
"""

from __future__ import annotations

from typing import Dict, Any, List

from fastapi import APIRouter
from pydantic import BaseModel, Field

from ..compliance.kyc import KYCService
from ..compliance.aml import AMLService


router = APIRouter(prefix="/compliance", tags=["compliance"])

kyc_service = KYCService()
aml_service = AMLService()


class KYCRequest(BaseModel):
    user_id: str
    documents: Dict[str, Any] = Field(..., description="Mapping of document type to content or metadata")


@router.post("/kyc")
async def perform_kyc(req: KYCRequest) -> Dict[str, Any]:
    """Perform KYC verification for a user."""
    result = await kyc_service.verify_user(req.user_id, req.documents)
    return result


class Transaction(BaseModel):
    amount: float
    asset: str
    destination: str


class AMLRequest(BaseModel):
    user_id: str
    transactions: List[Transaction]


@router.post("/aml")
async def perform_aml(req: AMLRequest) -> List[Dict[str, Any]]:
    """Monitor transactions for AML concerns."""
    # Convert Transaction models to dicts for the service
    tx_dicts = [tx.dict() for tx in req.transactions]
    results = await aml_service.monitor_transactions(req.user_id, tx_dicts)
    return results
