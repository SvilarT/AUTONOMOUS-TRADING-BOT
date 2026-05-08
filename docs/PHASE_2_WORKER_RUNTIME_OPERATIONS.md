# Phase 2 Worker Reliability and Runtime Operations

> This is for educational/backtesting/paper-trading use only. Live trading involves substantial risk of loss. Not financial advice.

Phase 2 hardens the paper worker runtime so the autonomous paper system can be operated like a service instead of a fragile background loop.

## Objective

Make the paper worker observable, restart-aware, duplicate-resistant, and safer to stop before the project advances deeper into live-readonly and manual live pilot work.

## Completed in this phase

### Worker lifecycle states

Workers now publish richer lifecycle states through the heartbeat record:

- `starting`
- `running`
- `error`
- `stopping`
- `stopped`

Each heartbeat includes:

- worker id
- hostname
- role
- status
- active bot ids
- active bot count
- last heartbeat timestamp
- stale threshold
- metadata

### Ownership renewal

Bot ownership is now renewed while a worker remains responsible for a user's paper bot.

This reduces the chance that a still-running worker loses its lock simply because the ownership TTL expires.

### Ownership recovery

Expired ownership can still be recovered by another worker. Current ownership remains protected from another worker until the lock expires.

### Graceful worker shutdown

The dedicated worker entrypoint now handles stop requests through process signals.

On stop, the worker:

- marks the manager as stopping;
- stops active paper bots;
- releases bot ownership;
- records a stopped heartbeat;
- closes the Mongo client.

### Stale worker detection

Worker status listing now returns a `stale_count` and marks stale workers.

A stale worker is one whose latest heartbeat is older than its configured stale threshold and whose lifecycle status is not already stopped or stopping.

### Stale worker alerting

Added an ops endpoint to emit deduplicated stale-worker alerts:

- `POST /api/ops/workers/stale-alerts`

Alerts are written to the existing alerts collection under the system alert user id.

### Tests

Phase 2 extends worker tests for:

- heartbeat staleness;
- active bot counts;
- ownership blocking;
- expired ownership recovery;
- ownership renewal;
- current-worker-only release;
- release-all-owned-bots behavior;
- stale-worker reporting;
- stale-worker alert deduplication.

## Operational expectations

A healthy worker should:

- publish regular heartbeats;
- renew ownership for every active paper bot;
- report `running` while active;
- report `stopping` during shutdown;
- report `stopped` after shutdown;
- release all owned bot locks before exiting.

An operator should investigate when:

- `stale_count` is greater than zero;
- a worker stays in `error` state;
- a bot ownership lock repeatedly expires;
- active bot count differs from expected active bot configs;
- duplicate workers attempt to own the same user bot.

## Configuration

Relevant environment variables:

- `WORKER_ID`: optional stable worker id.
- `WORKER_HEARTBEAT_STALE_AFTER_SECONDS`: heartbeat stale threshold. Default: 30.
- `BOT_OWNERSHIP_TTL_SECONDS`: paper bot ownership TTL. Default: 45.

## Phase 2 safety boundary

- Autonomous execution remains paper/simulation only.
- This phase does not add autonomous live trading.
- Worker ownership protects paper bot scheduling, not live execution.
- Live execution remains manually gated and protected by the existing live safety controls.

## Acceptance checklist

| Requirement | Status |
|---|---:|
| Worker lifecycle states exist | Complete |
| Worker graceful shutdown path exists | Complete |
| Worker heartbeat includes active bot count | Complete |
| Active bot ownership is renewed | Complete |
| Expired ownership can be recovered | Complete |
| Worker can release all owned bots | Complete |
| Stale-worker report exists | Complete |
| Stale-worker alert endpoint exists | Complete |
| Stale-worker alerts are deduplicated | Complete |
| Runtime tests cover ownership renewal and alerting | Complete |

## Next phase

Phase 3: Live-Readonly Reliability.

The next phase should focus on making exchange observation reliable before manual live pilot work:

- Coinbase readonly adapter hardening;
- timeout and read-only retry policy;
- rate-limit handling;
- normalized readonly error taxonomy;
- persisted exchange snapshots;
- live-readonly reconciliation scheduler;
- stale live data visibility;
- dashboard connection status.
