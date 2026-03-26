---
title: Project Overview
---

# Autonomous Trading Bot – Phase 11 Documentation

Welcome to the documentation for Phase 11 of the autonomous trading bot
project.  Building upon the extensive testing suite and CI pipeline
introduced in Phase 9, and the monitoring and notification layer
introduced in Phase 10, this phase adds support for paper versus live
environments and introduces feature flags to enable staged rollouts of
new functionality.  A simple configuration setting lets you run the bot
in a simulated environment without contacting real exchanges.  Feature
flags allow you to gradually enable experimental modules for specific
users or cohorts.

## Highlights

* **Environment Awareness** – The bot can operate in "paper" mode
  (simulation) or "live" mode as configured in `config.yml`.  Paper
  mode ensures that trades are simulated and that only mock connectors
  are used; this is ideal for pre‑release testing and paper trading
  scenarios.
* **Feature Flags** – A feature flag service allows new modules or
  behaviours to be toggled on or off at runtime.  Feature flags enable
  staged rollout and A/B testing without redeploying code.
* **Monitoring & Metrics** – Prometheus counters, histograms and
  gauges measure trade activity, latency and risk events.  A
  `/monitoring/metrics` endpoint exposes these metrics in a standard
  format.  A `/monitoring/health` endpoint indicates the service’s
  health status, useful for Kubernetes liveness/readiness probes.
* **Notifications** – Dedicated endpoints under `/notifications` allow
  the system or users to send trade confirmations, risk alerts and
  system status messages.  The underlying service can be swapped for
  real notification providers (email, SMS, push) as needed.
* **Unit and Integration Tests** – The `tests/` directory contains
  extensive tests covering core services (risk manager, marketplace,
  security, compliance) as well as new tests for monitoring,
  notifications, environment and feature flags.  Integration tests
  use FastAPI’s `TestClient` and `pytest-asyncio` for asynchronous
  endpoints.
* **Requirements** – A `requirements.txt` file lists all Python
  dependencies needed to run the services and tests.
* **Continuous Integration** – A GitHub Actions workflow runs the test
  suite against multiple Python versions on every push and pull
  request, preventing regressions.
* **Security & Compliance** – Phase 8 additions (secrets management,
  custody integration, KYC/AML modules) continue to be part of this
  phase, ensuring the bot adheres to best practices.

For further details on architecture and module design, consult the
other documents in this directory and the docstrings within the code.
