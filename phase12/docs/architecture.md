---
title: System Architecture
---

# Architecture Overview

The autonomous trading platform is composed of multiple modular
services that interact through well‑defined interfaces.  Each
component can be independently tested and replaced without affecting
the rest of the system.

## Core Components

* **Data Provider & Pipeline** – Responsible for ingesting historical
  and real‑time market data and normalizing it into a standard
  schema.  Implemented in `phase12/core/data_provider.py` and
  `phase12/core/data_pipeline.py`.
* **Strategy Engine** – Loads strategy plugins from the configuration
  and executes them on incoming data.  See
  `phase12/core/strategy_engine.py`.
* **Execution Router & Connectors** – Abstracts away exchange‑specific
  APIs.  The router selects the best connector based on fee and
  availability.  Connectors live under `phase12/plugins/`.
* **Risk Manager** – Computes exposure, volatility, Value‑at‑Risk,
  expected shortfall and other metrics.  It enforces limits on
  position size and triggers kill switches when thresholds are
  breached (see `phase12/core/risk_manager.py`).
* **Portfolio Service** – Tracks cash balances, positions and
  P&L for each user or account.  In Phase 12 this uses an in‑memory
  repository for demonstration.
* **Marketplace Service** – Allows users to register, rate and
  subscribe to strategies.  It maintains performance statistics and
  reputation scores (`phase12/marketplace/service.py`).
* **Security & Compliance** – Modules from Phase 8 manage secrets
  (`phase12/security/secrets_manager.py`), simulate a custody service
  (`phase12/security/custody.py`) and stub out KYC and AML checks
  (`phase12/compliance/*`).
* **Monitoring & Notifications** – Phase 10 added Prometheus metrics and
  a lightweight notification system.  Metrics are defined in
  `phase12/monitoring/metrics.py` and exposed via the API in
  `phase12/api/monitoring.py`.  The notification service lives in
  `phase12/notifications/service.py` and routes for sending
  notifications are defined in `phase12/api/notifications.py`.

* **Environment & Feature Flags** – Phase 11 introduced an
  ``Environment`` class (`phase12/environment.py`) that encodes whether the
  bot is running in paper mode or live mode, and a
  ``FeatureFlagService`` (`phase12/feature_flags.py`) that stores
  boolean flags used to toggle experimental features.  These services
  are initialised from `config.yml` and can be queried via the API.

* **Live Market Dashboard** – Phase 12 adds a `trade_notifier` and
  accompanying API endpoints.  The notifier (`phase12/live_market.py`)
  maintains WebSocket connections and broadcasts trade events.  The
  dashboard (`phase12/api/live_market.py`) serves an HTML page that
  connects to the WebSocket and uses Chart.js to visualise trade
  activity in real time.

## API Layer

FastAPI is used to expose REST endpoints.  The API is organized into
separate routers:

* **Main API** – Handles portfolio queries, risk metrics and trade
  execution (`phase12/api/main.py`).
* **Marketplace API** – Provides endpoints for registering
  strategies, subscribing and rating (`phase12/api/marketplace.py`).
* **Security API** – Demonstrates secret management and custody
  operations (`phase12/api/security.py`).
* **Compliance API** – Exposes KYC and AML verification
  (`phase12/api/compliance.py`).
* **Monitoring API** – Exposes health checks and Prometheus metrics
  (`phase12/api/monitoring.py`).
* **Notifications API** – Provides endpoints for sending trade
  confirmations, risk alerts and system status messages
  (`phase12/api/notifications.py`).
* **Environment & Features API** – Returns the current operating
  environment and configured feature flags (`phase12/api/main.py` via
  `/environment` and `/features`).

* **Live Market API** – Serves the live dashboard HTML and WebSocket
  endpoints (`phase12/api/live_market.py` via `/live` and
  `/ws/trades`).

Each router can be extended or replaced without disrupting others.
