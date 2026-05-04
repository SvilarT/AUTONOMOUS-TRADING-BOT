SHELL := /usr/bin/env bash

.PHONY: help setup-backend test-backend lint-backend audit-backend run-backend run-worker indexes setup-frontend build-frontend dev-up dev-down logs copy-env

help:
	@echo "Autonomous Trading Bot commands"
	@echo "  make copy-env        Copy .env.example to .env when .env is absent"
	@echo "  make setup-backend   Install backend dependencies"
	@echo "  make test-backend    Run backend test suite"
	@echo "  make lint-backend    Run backend lint/security scan"
	@echo "  make audit-backend   Run backend dependency audit"
	@echo "  make run-backend     Run FastAPI API role locally"
	@echo "  make run-worker      Run dedicated bot worker role locally"
	@echo "  make indexes         Create/verify Mongo indexes"
	@echo "  make setup-frontend  Install frontend dependencies"
	@echo "  make build-frontend  Build frontend"
	@echo "  make dev-up          Start local Docker compose stack"
	@echo "  make dev-down        Stop local Docker compose stack"
	@echo "  make logs            Tail local Docker compose logs"

copy-env:
	@test -f .env || cp .env.example .env

setup-backend:
	cd backend && python -m pip install --upgrade pip setuptools wheel && python -m pip install -r requirements.txt -r requirements-dev.txt

test-backend:
	cd backend && DEBUG=True JWT_SECRET=test-secret-with-more-than-32-characters CORS_ORIGINS=http://localhost:3000 python -m pytest tests

lint-backend:
	cd backend && python -m ruff check . && python -m bandit -q -r . -x tests

audit-backend:
	cd backend && python -m pip_audit -r requirements.txt

run-backend:
	cd backend && RUNTIME_ROLE=api API_EMBED_BOT_MANAGER=false RUN_MONGO_INDEX_BOOTSTRAP=false uvicorn server:app --host 0.0.0.0 --port 8000 --reload

run-worker:
	cd backend && RUNTIME_ROLE=worker RUN_MONGO_INDEX_BOOTSTRAP=false python worker.py

indexes:
	cd backend && RUNTIME_ROLE=indexes python manage_indexes.py

setup-frontend:
	cd frontend && npm install --legacy-peer-deps

build-frontend:
	cd frontend && REACT_APP_BACKEND_URL=http://localhost:8000 CI=false npm run build

dev-up: copy-env
	docker compose up --build

dev-down:
	docker compose down

logs:
	docker compose logs -f
