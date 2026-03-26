This `phase12` directory contains the most feature‑complete version of the
autonomous trading bot to date.  Building on earlier phases, it introduces
support for paper‑trading vs. live environments and a feature flag system
to enable staged rollouts of new functionality.  These additions sit
alongside the comprehensive monitoring, alerting and notification
capabilities introduced in Phase 10, and the extensive testing,
documentation and continuous integration (CI) pipeline added in Phase 9.
Phase 12 further adds a **live market dashboard** that streams trade
events in real time via WebSockets and renders them using Chart.js on a
responsive line chart.  This visualisation enables operators to
monitor trade activity with minimal latency.  The architecture remains
modular, allowing new features to be integrated
without disrupting existing components.

## What’s Included

* **Modular Services** – The core directory contains services for data
  ingestion, strategy execution, order routing, risk management and
  portfolio tracking.  Each service is decoupled with clear
  interfaces.
* **Strategy Marketplace** – Users can publish, rate and subscribe to
  strategies via a dedicated marketplace service and API.
* **Security & Compliance** – Secrets management, custody integration and
  stub KYC/AML modules illustrate how to meet regulatory requirements.
* **Monitoring & Metrics** – A Prometheus instrumentation layer
  records trade counts, latency distributions, risk events and service
  health.  Endpoints under `/monitoring` expose metrics and health
  information in a format compatible with Prometheus or other
  monitoring systems.
* **Notifications** – A lightweight notification service provides
  endpoints for sending trade confirmations, risk alerts and system
  status messages.  In this demonstration implementation the messages
  are printed to standard output; in production they would be
  delivered via email, SMS or push notification.
* **Environment & Feature Flags** – The bot can operate in paper or live
  mode as specified in `config.yml`.  A simple feature flag service
  allows experimental modules to be toggled on or off, enabling
  incremental deployment and testing.
* **Live Market Dashboard** – A dedicated `/live` endpoint serves a web
  page that displays your trades as they occur.  Trades submitted via
  the API are broadcast over a WebSocket to connected clients and
  plotted on a Chart.js line chart, colour‑coded by action (green for
  buys, red for sells).
* **FastAPI Routes** – REST endpoints are organized by function
  (`/users`, `/marketplace`, `/security`, `/compliance`, `/monitoring`,
  `/notifications`, `/environment`, `/features`) and return
  Pydantic‑validated responses.
* **Testing Suite** – The `tests/` directory contains unit and
  integration tests for every major component, including new tests for
  monitoring and notifications.  Tests can be run with `pytest` and
  cover both synchronous and asynchronous code paths.
* **Documentation** – Markdown documents in the `docs/` directory
  describe the architecture and provide an overview of the project.
* **CI Workflow** – A GitHub Actions workflow under `.github/workflows/ci.yml`
  automatically installs dependencies and runs the test suite on push and
  pull requests across multiple Python versions.

## Getting Started

1. Install dependencies using the provided `requirements.txt`:

   ```bash
   python -m pip install -r requirements.txt
   ```

2. Run the unit tests:

   ```bash
   pytest -q phase12/tests
   ```

3. Launch the FastAPI application for interactive exploration:

   ```bash
   uvicorn phase12.api.main:app --reload
   ```

4. Explore the documentation in `phase12/docs/` for more details on
   system architecture, environment configuration, the live market
   dashboard and other staged rollout features.
