SHELL := /usr/bin/env bash

.PHONY: help setup-backend test-backend lint-backend audit-backend run-backend setup-frontend build-frontend dev-up dev-down logs copy-env

help:
	@echo "Autonomous Trading Bot commands"
	@echo "  make copy-env        Copy .env.example to .env when .env is absent"
	@echo "  make setup-backend   Install backend dependencies"
	@echo "  make test-backend    Run backend test suite"
	@echo "  make lint-backend    Run backend lint/security scan"
	@echo "  make audit-backend   Run backend dependency audit"
	@echo "  make run-backend     Run FastAPI backend locally"
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
	cd backend && uvicorn server:app --host 0.0.0.0 --port 8000 --reload

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
