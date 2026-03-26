---
title: Project Overview
---

# Autonomous Trading Bot – Phase 9 Documentation

Welcome to the documentation for Phase 9 of the autonomous trading bot
project.  This phase introduces a comprehensive testing suite,
documentation artifacts and continuous integration (CI) pipeline to
ensure the robustness and maintainability of the platform.

## Highlights

* **Unit and Integration Tests** – The `tests/` directory contains
  extensive tests covering core services (risk manager, marketplace,
  security, compliance) and integration tests using FastAPI’s
  `TestClient`.  Asynchronous components are tested with
  `pytest-asyncio`.
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
