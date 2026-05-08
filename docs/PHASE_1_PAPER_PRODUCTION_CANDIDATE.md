# Phase 1 Paper Production Candidate

> This is for educational/backtesting/paper-trading use only. Live trading involves substantial risk of loss. Not financial advice.

Phase 1 hardens the paper/simulation system so it can behave like a production-style service without live-order risk.

## Objective

Make paper-mode operation stable, observable, restart-safe, and dashboard-visible before advancing deeper into live-readonly and manual live pilot work.

## Completed in this phase

### Worker heartbeat and ownership

- Added `WorkerHeartbeatServiceV2`.
- Workers now record heartbeat status, active bot ownership, hostname, role, and stale thresholds.
- Bot ownership prevents a second worker from starting the same user's bot while ownership is current.
- Expired ownership can be recovered by another worker.
- Bot ownership is released when a bot stops.

### Worker visibility

- Added `/api/ops/workers` for worker status visibility.
- Dashboard groundwork can show worker count, stale workers, and active bot ownership.

### Mongo indexes

- Added indexes for worker heartbeats and bot ownership.

### Frontend API normalization

- Added a reusable frontend API client.
- Requests now include `X-Request-ID`.
- API errors are normalized from backend error envelopes.
- Dashboard errors can include request IDs for operator debugging.

### Dashboard mode/readiness visibility

- Added `SystemStatusPanel`.
- Dashboard now surfaces trading mode, readiness status, worker count, and stale-worker warnings.

### Tests

- Added worker heartbeat tests.
- Added bot ownership tests.
- Added stale heartbeat detection tests.
- Added ownership release tests.

## Phase 1 safety boundary

- Autonomous execution remains paper/simulation only.
- Live execution remains manual and gated.
- Phase 1 does not introduce autonomous live trading.
- Worker ownership is used to reduce duplicate paper bot execution risk.

## Acceptance checklist

| Requirement | Status |
|---|---:|
| Paper bot remains the only autonomous order-producing path | Complete |
| Worker heartbeat exists | Complete |
| Worker status is visible through API | Complete |
| Bot ownership blocks duplicate worker execution | Complete |
| Stale ownership can be recovered | Complete |
| Dashboard has mode/readiness/worker visibility groundwork | Complete |
| Frontend API errors are normalized | Complete |
| Request IDs propagate from frontend requests | Complete |
| Worker heartbeat/ownership tests exist | Complete |

## Remaining paper-hardening follow-ups

Phase 1 is functionally complete for the paper-production candidate milestone. Recommended follow-up improvements before Phase 2:

- Expand paper E2E tests to cover a full bot cycle through worker scheduling.
- Raise backend coverage target toward 80% and then 90% for critical services.
- Add more paper sell, fee, and reconciliation invariant tests.
- Add dashboard tests for the system status panel.
- Add worker graceful shutdown signal tests.

## Next phase

Phase 2: Worker Reliability and Runtime Operations.

The next phase should deepen worker production behavior with stronger graceful shutdown, bot-cycle scheduling guarantees, richer worker status, alerting on stale workers, and restart/duplicate-execution simulation tests.
