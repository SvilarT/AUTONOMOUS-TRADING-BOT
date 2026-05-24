"""Top-level entry point for the Autonomous Trading Bot repository.

The runnable services live in the backend and frontend directories. This file is
kept intentionally lightweight so `python main.py` gives a useful project entry
message instead of a scaffold placeholder.
"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent


PROJECT_ROOT = Path(__file__).resolve().parent


def main() -> None:
    """Print the canonical local-development entrypoints."""

    print(
        dedent(
            f"""
            Autonomous Trading Bot
            ======================

            Repository root: {PROJECT_ROOT}

            This is a full-stack cryptocurrency trading research platform with:
              - FastAPI backend services in ./backend
              - React operator dashboard in ./frontend
              - MongoDB-backed paper trading, risk, ledger, and readiness flows
              - gated live-readonly/manual-live controls for controlled research

            Recommended local startup:
              1. cp .env.example .env
              2. docker compose up --build

            Manual service startup:
              - Backend API:   cd backend && uvicorn server:app --reload --host 0.0.0.0 --port 8000
              - Worker:        cd backend && python worker.py
              - Frontend UI:   cd frontend && npm install --legacy-peer-deps && npm start

            Useful endpoints after startup:
              - Backend health:    http://localhost:8000/healthz
              - Backend readiness: http://localhost:8000/readyz
              - Frontend UI:       http://localhost:3000

            See README.md for the full architecture, safety model, and readiness gates.
            """
        ).strip()
    )


if __name__ == "__main__":
    main()
