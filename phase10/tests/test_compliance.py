"""Tests for compliance modules: KYC and AML services."""

from __future__ import annotations

import pytest
import asyncio

from phase10.compliance.kyc import KYCService
from phase10.compliance.aml import AMLService


@pytest.mark.asyncio
async def test_kyc_verification() -> None:
    kyc = KYCService()
    result = await kyc.verify_user("user123", {"id": "mock"})
    assert result["verified"] is True
    assert result["risk_level"] == "low"


@pytest.mark.asyncio
async def test_aml_monitoring() -> None:
    aml = AMLService()
    # A transaction below the threshold should not be flagged
    res = await aml.assess_transaction("u1", {"amount": 5000.0, "asset": "BTC", "destination": "dest"})
    assert res["flagged"] is False
    # A large transaction should trigger a flag
    res2 = await aml.assess_transaction("u1", {"amount": 20000.0, "asset": "BTC", "destination": "dest"})
    assert res2["flagged"] is True
    assert "threshold" in res2["reason"]
