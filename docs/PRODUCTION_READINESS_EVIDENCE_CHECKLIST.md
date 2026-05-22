# Production Readiness Evidence Checklist

> This is for educational/backtesting/paper-trading use only. Live trading involves substantial risk of loss. Not financial advice.

This repository now contains the staged readiness architecture from Phase 0 through Phase 19. That does not automatically make a deployment production-live ready.

Production readiness requires evidence that the gates have been executed and satisfied in the actual environment.

## Current meaning of the codebase

The repository is production-readiness-framework complete.

It includes gates for:

- paper trading foundation;
- live-readonly observation;
- manual pilot readiness;
- dry-run rehearsal;
- tiny manual pilot control;
- pilot review;
- operations hardening;
- controlled manual live release;
- autonomous gate design;
- autonomous shadow mode;
- autonomous canary controls;
- final production release review.

## Required evidence before production-live approval

### 1. CI and local validation

Required evidence:

- main branch CI passes;
- backend tests pass;
- frontend tests pass;
- frontend build passes;
- Docker build passes;
- Docker Compose smoke test passes;
- dependency audit passes;
- security scan passes;
- Phase 12 through Phase 19 tests pass in CI.

Local command:

    cd backend
    python -m pytest \
      tests/test_phase12_tiny_manual_live_pilot_control.py \
      tests/test_phase13_pilot_release_criteria.py \
      tests/test_phase14_operations_hardening.py \
      tests/test_phase15_manual_release_gate.py \
      tests/test_phase16_gate_design.py \
      tests/test_phase17_shadow_mode.py \
      tests/test_phase18_canary_controls.py \
      tests/test_phase19_production_release_gate.py \
      -q

### 2. Credential and secret hardening

Required evidence:

- readonly exchange credentials are separated from execution credentials;
- no withdrawal permission exists;
- no transfer permission exists if configurable;
- no margin/futures/derivatives permission exists;
- secrets are not in frontend variables;
- secrets are not in logs;
- secrets are not in GitHub;
- kill switch default is closed;
- live notional caps remain tiny.

### 3. Dry-run dress rehearsal

Required evidence:

- backend starts cleanly;
- frontend builds cleanly;
- live-readonly snapshot works;
- live-readonly reconciliation works;
- pilot readiness is clear;
- exact dry-run order succeeds;
- dry-run response includes gate, risk, audit, and reconciliation metadata;
- dry-run does not indicate live execution;
- pilot report generation works;
- operator signoff works;
- expansion status clears.

### 4. Tiny manual live pilot

Required evidence:

- one tiny manually approved order only;
- preferred notional 1 to 5 USD;
- BTC-USD or ETH-USD only;
- immediate kill-switch restoration;
- live-readonly orders/fills fetched;
- reconciliation completed;
- post-submit requirement resolved;
- pilot report generated;
- operator signoff recorded;
- no repeat order before review.

### 5. Limited manual live release

Required evidence:

- Phase 13 limited manual release criteria pass;
- Phase 14 operations hardening criteria pass;
- Phase 15 controlled manual release gate passes;
- max order notional remains limited;
- daily notional cap remains limited;
- every order requires manual and signed approval;
- every order requires exact dry run first;
- every order requires reconciliation, report, and signoff afterward.

### 6. Autonomous evidence

Required evidence before any autonomous production consideration:

- Phase 16 design gate passes;
- Phase 17 shadow mode runs for required duration;
- shadow review passes;
- Phase 18 canary candidate gate passes;
- canary review passes;
- no scale-up occurs before review.

### 7. Final production release approval

Required evidence:

- Phase 19 production release gate passes;
- release approver identity is recorded;
- incident commander is assigned;
- monitoring is active;
- alerting is active;
- rollback is validated;
- backup/restore is validated;
- no unresolved live state exists.

## Readiness labels

| Label | Meaning |
|---|---|
| Framework complete | Gates and services exist in code. |
| Validation complete | CI and local test evidence pass. |
| Manual pilot ready | Dry-run rehearsal and credential hardening pass. |
| Controlled manual live ready | Tiny pilot, review, operations, and controlled manual gate pass. |
| Autonomous canary ready | Shadow review and canary gate pass. |
| Production-live ready | Phase 19 gate passes with real operational evidence. |

## Final rule

Do not call the project production-live ready until Phase 19 passes with real environment evidence.
