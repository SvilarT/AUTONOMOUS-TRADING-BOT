# Phase 9 Regression, CI, Route Import Validation, and Frontend Build Verification

> This is for educational/backtesting/paper-trading use only. Live trading involves substantial risk of loss. Not financial advice.

Phase 9 strengthens verification after the Phase 5 through Phase 8 manual live pilot layers. It does not submit live orders and does not enable autonomous live trading.

## Objective

Catch regressions before the project moves into exchange credential hardening and full dry-run rehearsal.

## Added in this phase

### Backend route import validation

Added `backend/tests/test_phase9_route_import_validation.py`.

It verifies:

- `api_routes_v3` imports cleanly;
- all pilot readiness/workflow/review routes are registered;
- Phase 5 through Phase 8 service modules import cleanly.

### Mongo index validation

Added `backend/tests/test_phase9_mongo_index_validation.py`.

It verifies indexes for:

- manual live pilot reports;
- manual live pilot signoffs;
- post-submit reconciliation requirements.

### Frontend static pilot UI validation

Added `frontend/src/__tests__/phase9-pilot-review-ui.test.js`.

It verifies:

- authenticated `/pilot-review` route is present;
- `PilotReviewPanel` imports required API helpers;
- frontend API client contains all pilot review endpoint paths.

### CI updates

Updated `.github/workflows/ci.yml` with explicit Phase 9 validation steps:

- targeted backend validation for Phase 5 through Phase 9 live-pilot tests;
- targeted frontend validation for the pilot review UI test;
- existing full backend tests, backend quality, frontend lint/test/build, Docker build, and Compose smoke checks remain active.

## Local validation commands

Run backend targeted validation:

    cd backend
    python -m pytest \
      tests/test_phase9_route_import_validation.py \
      tests/test_phase9_mongo_index_validation.py \
      tests/test_phase5_manual_live_pilot_readiness.py \
      tests/test_phase6_manual_live_pilot_workflow.py \
      tests/test_phase7_pilot_review_control.py \
      -q

Run frontend targeted validation:

    cd frontend
    npm test -- --watchAll=false --runTestsByPath src/__tests__/phase9-pilot-review-ui.test.js

Run full frontend build:

    cd frontend
    npm run build

Run full backend tests:

    cd backend
    python -m pytest tests -q

## Phase 9 acceptance checklist

| Requirement | Status |
|---|---:|
| API route import validation exists | Complete |
| Pilot route registration is tested | Complete |
| Phase 5 through Phase 8 service imports are tested | Complete |
| Pilot Mongo indexes are tested | Complete |
| Frontend pilot review route is tested | Complete |
| Frontend pilot API helper references are tested | Complete |
| CI runs targeted backend Phase 9 validation | Complete |
| CI runs targeted frontend Phase 9 validation | Complete |
| Existing full backend and frontend CI remains active | Complete |
| No automatic live order is submitted | Complete |
| No autonomous live trading is introduced | Complete |

## Next phase

Phase 10 should focus on exchange account and secrets hardening:

- separate readonly and execution API keys;
- no withdrawal permissions;
- no margin/futures/derivatives permissions;
- secret rotation runbook;
- environment validation;
- log redaction checks;
- production-safe credential handling.
