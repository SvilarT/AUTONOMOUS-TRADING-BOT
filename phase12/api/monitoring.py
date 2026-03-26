"""Monitoring API endpoints.

This module exposes routes for health checks and metrics export.
Metrics are provided in Prometheus exposition format.  Health checks
return simple status information for readiness/liveness probes.
"""

from __future__ import annotations

from fastapi import APIRouter, Response

from ..monitoring.metrics import export_metrics, service_health


router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/health")
def health_check() -> dict[str, int]:
    """Return the current health status. 1 indicates healthy."""
    return {"status": int(service_health._value.get())}


@router.get("/metrics")
def metrics() -> Response:
    """Return all registered Prometheus metrics in plain text format."""
    data = export_metrics()
    return Response(content=data, media_type="text/plain; version=0.0.4")
