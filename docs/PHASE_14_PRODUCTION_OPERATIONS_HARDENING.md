# Phase 14 Production Operations Hardening

> This is for educational/backtesting/paper-trading use only. Live trading involves substantial risk of loss. Not financial advice.

Phase 14 adds the production-operations readiness gate before controlled repeated manual live trading. It does not place orders and does not enable autonomous live trading.

## Objective

Make sure the project is operationally safe enough to run as a controlled manual-live service, not merely a working codebase.

The gate checks whether deployment, rollback, monitoring, alerting, backup/restore, log hygiene, incident response, and unresolved live-state controls are ready.

## Added in this phase

### Production operations hardening service

Added `Phase14OperationsHardeningServiceV2`.

It evaluates:

- deployment and rollback runbooks;
- backup and restore readiness;
- incident response readiness;
- secret rotation documentation;
- manual live reconciliation documentation;
- monitoring coverage;
- alert-channel coverage;
- database backup enablement;
- restore-drill evidence;
- log redaction;
- rate limiting;
- production CORS posture;
- unresolved live state;
- stale worker state;
- incident owner assignment.

The service does not submit orders.

### Required runbooks

The following must exist before controlled manual live trading:

- `deployment_runbook`
- `rollback_runbook`
- `backup_restore_runbook`
- `incident_response_runbook`
- `secret_rotation_runbook`
- `manual_live_reconciliation_runbook`

### Required monitors

The following monitoring coverage is required:

- `backend_health`
- `frontend_health`
- `worker_heartbeat`
- `database_connectivity`
- `unresolved_reconciliation`
- `unsigned_pilot_report`
- `live_halt_active`

### Required alert channels

The following alert channels are required:

- `critical_ops`
- `manual_live_reconciliation`

### Critical blockers

Operations readiness blocks controlled manual live trading if:

- required runbooks are missing;
- required monitors are missing;
- required alert channels are missing;
- database backup is not enabled;
- no restore drill is recorded;
- log redaction is not enabled;
- API rate limiting is not enabled;
- production CORS is not explicit;
- pending reconciliation exists;
- unsigned completed pilot report exists;
- active live halt exists;
- required worker heartbeat is stale.

### Warnings

These are warnings, not blockers:

- error tracking is not configured;
- incident commander is not assigned.

They should still be fixed before serious operation.

### Tests

Added `backend/tests/test_phase14_operations_hardening.py` covering:

- policy keeps autonomous live disallowed;
- complete configuration passes;
- missing runbooks block readiness;
- missing monitors block readiness;
- missing alert channels block readiness;
- backup/restore/log controls are required;
- unresolved live state blocks readiness;
- stale workers block readiness;
- error tracking and incident owner produce warnings.

## Operator workflow

### 1. Confirm required runbooks exist

Create and maintain operational runbooks for:

- deployment;
- rollback;
- backup and restore;
- incident response;
- secret rotation;
- manual live reconciliation.

### 2. Confirm monitoring coverage

Verify monitoring exists for:

- backend health;
- frontend health;
- worker heartbeats;
- database connectivity;
- unresolved reconciliation;
- unsigned completed pilot reports;
- active live halts.

### 3. Confirm alert channels

At minimum, configure alerting for:

- critical operational failures;
- manual live reconciliation blockers.

### 4. Confirm database safety

Before controlled manual live trading:

- backup must be enabled;
- restore drill must be recorded;
- backup credentials must be separated from app credentials;
- backups must not expose secrets unnecessarily.

### 5. Confirm runtime safety

Verify:

- log redaction is enabled;
- rate limiting is enabled;
- production CORS is explicit;
- no unresolved reconciliation exists;
- no unsigned completed pilot report exists;
- no active live halt exists;
- no required worker is stale.

### 6. Evaluate operations readiness

Use the service policy and checks to evaluate whether controlled manual live trading can proceed.

Release is allowed only when:

- `ready_for_controlled_manual_live=true`;
- `status=operations_ready`;
- `blockers=[]`.

## Stop conditions

Stop immediately if:

- rollback process is unclear;
- backups are disabled;
- restore has never been tested;
- log redaction is not confirmed;
- alerts are not configured;
- monitoring is missing;
- unresolved reconciliation exists;
- unsigned pilot report exists;
- active halt exists;
- worker heartbeat is stale;
- production CORS is wildcard or unclear.

## Local validation

Run:

    cd backend
    python -m pytest tests/test_phase14_operations_hardening.py -q

## Phase 14 acceptance checklist

| Requirement | Status |
|---|---:|
| Operations hardening service exists | Complete |
| Operations policy exists | Complete |
| Autonomous live is explicitly disallowed | Complete |
| Required runbooks are defined | Complete |
| Required monitors are defined | Complete |
| Required alert channels are defined | Complete |
| Backup readiness is checked | Complete |
| Restore drill readiness is checked | Complete |
| Log redaction is checked | Complete |
| Rate limiting is checked | Complete |
| Production CORS is checked | Complete |
| Unresolved reconciliation blocks readiness | Complete |
| Unsigned completed report blocks readiness | Complete |
| Active halt blocks readiness | Complete |
| Stale worker blocks readiness | Complete |
| Phase 14 tests exist | Complete |
| Automatic live order submission added | No |
| Autonomous live trading introduced | No |

## Next phase

Phase 15 should define the controlled manual live trading release gate:

- limited repeated manual live trading only;
- small notional cap;
- strict symbol allowlist;
- manual approval required for every order;
- reconciliation after every order;
- escalation/rollback if any anomaly appears.
