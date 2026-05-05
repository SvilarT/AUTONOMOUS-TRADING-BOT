# CI Gates

> This is for educational/backtesting/paper-trading use only. Live trading involves substantial risk of loss. Not financial advice.

The CI workflow is the merge gate for production readiness work. It validates backend correctness, backend static/security posture, frontend quality, Docker buildability, and local stack bootability.

## Jobs

| Job | Purpose |
|---|---|
| `backend-tests` | Runs pytest with MongoDB service and coverage threshold |
| `backend-quality` | Runs Ruff, Bandit, and pip-audit |
| `frontend-quality` | Runs frontend lint, tests, and production build |
| `docker-build` | Builds backend and frontend Docker images |
| `compose-smoke` | Boots MongoDB, index bootstrap, API, worker, and frontend through Docker Compose |
| `ci-complete` | Aggregates all required jobs into a single required status check |

## Local equivalent

```bash
make setup-backend
make setup-frontend
make ci-local
```

For the compose smoke path:

```bash
cp .env.example .env
make dev-up
curl http://localhost:8000/healthz
curl http://localhost:8000/readyz
curl http://localhost:3000
make dev-down
```

## Required GitHub branch protection

Configure repository branch protection for `main`:

1. Require pull request before merging.
2. Require status checks before merging.
3. Require the `ci-complete` status check.
4. Require branches to be up to date before merging.
5. Block force pushes.
6. Block deletions.
7. Require conversation resolution before merging.
8. Restrict who can dismiss reviews if reviews are enabled.

## Current coverage gate

The backend coverage floor is currently set to 70%. Raise this progressively:

- 70% now
- 80% after integration tests expand
- 90% before manual live pilot

## Secret scanning

This repo should enable GitHub Advanced Security secret scanning when available. A dedicated workflow-level scanner can be added later if repository policy permits the action and token permissions.

## Merge policy

No PR that affects execution, risk, live trading, ledger, auth, settings, or deployment should merge unless CI passes.
