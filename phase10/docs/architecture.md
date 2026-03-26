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
  schema.  Implemented in `phase10/core/data_provider.py` and
  `phase10/core/data_pipeline.py`.
* **Strategy Engine** – Loads strategy plugins from the configuration
  and executes them on incoming data.  See
  `phase10/core/strategy_engine.py`.
* **Execution Router & Connectors** – Abstracts away exchange‑specific
  APIs.  The router selects the best connector based on fee and
  availability.  Connectors live under `phase10/plugins/`.
* **Risk Manager** – Computes exposure, volatility, Value‑at‑Risk,
  expected shortfall and other metrics.  It enforces limits on
  position size and triggers kill switches when thresholds are
  breached (see `phase10/core/risk_manager.py`).
* **Portfolio Service** – Tracks cash balances, positions and
  P&L for each user or account.  In Phase 10 this uses an in‑memory
  repository for demonstration.
* **Marketplace Service** – Allows users to register, rate and
  subscribe to strategies.  It maintains performance statistics and
  reputation scores (`phase10/marketplace/service.py`).
* **Security & Compliance** – Modules from Phase 8 manage secrets
  (`phase10/security/secrets_manager.py`), simulate a custody service
  (`phase10/security/custody.py`) and stub out KYC and AML checks
  (`phase10/compliance/*`).
* **Monitoring & Notifications** – Phase 10 adds Prometheus metrics and
  a lightweight notification system.  Metrics are defined in
  `phase10/monitoring/metrics.py` and exposed via the API in
  `phase10/api/monitoring.py`.  The notification service lives in
  `phase10/notifications/service.py` and routes for sending
  notifications are defined in `phase10/api/notifications.py`.

## API Layer

FastAPI is used to expose REST endpoints.  The API is organized into
separate routers:

* **Main API** – Handles portfolio queries, risk metrics and trade
  execution (`phase10/api/main.py`).
* **Marketplace API** – Provides endpoints for registering
  strategies, subscribing and rating (`phase10/api/marketplace.py`).
* **Security API** – Demonstrates secret management and custody
  operations (`phase10/api/security.py`).
* **Compliance API** – Exposes KYC and AML verification
  (`phase10/api/compliance.py`).
* **Monitoring API** – Exposes health checks and Prometheus metrics
  (`phase10/api/monitoring.py`).
* **Notifications API** – Provides endpoints for sending trade
  confirmations, risk alerts and system status messages
  (`phase10/api/notifications.py`).

Each router can be extended or replaced without disrupting others.
