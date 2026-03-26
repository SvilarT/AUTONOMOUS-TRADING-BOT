"""API package for the Phase 6 trading bot backend.

This package provides a FastAPI application exposing REST endpoints for
interacting with the trading system.  Endpoints include retrieving
portfolio state, computing risk metrics and placing trades.  The API
leverages the core services (strategy engine, execution router, risk
manager and portfolio service) defined elsewhere in the project.
"""
