This `phase10` directory contains the most feature‑complete version of the
autonomous trading bot to date.  Building on earlier phases, it introduces
comprehensive monitoring, alerting and user notification capabilities in
addition to the extensive testing, documentation and continuous
integration (CI) pipeline added in Phase 9.  The architecture remains
modular, allowing new features to be integrated without disrupting
existing components.

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
* **FastAPI Routes** – REST endpoints are organized by function
  (`/users`, `/marketplace`, `/security`, `/compliance`, `/monitoring`,
  `/notifications`) and return Pydantic‑validated responses.
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
   pytest -q phase9/tests
   ```

3. Launch the FastAPI application for interactive exploration:

   ```bash
   uvicorn phase9.api.main:app --reload
   ```

4. Explore the documentation in `phase10/docs/` for more details on
   system architecture, monitoring and notification features.
