# Phase 3 Live-Readonly Reliability

> This is for educational/backtesting/paper-trading use only. Live trading involves substantial risk of loss. Not financial advice.

Phase 3 hardens exchange observation before any manual live pilot work. The system can read live Coinbase Exchange state, persist snapshots, detect stale data, and expose readonly freshness without enabling autonomous live execution.

## Objective

Make live-readonly mode reliable, observable, and safe enough to serve as the account-state foundation for future manual live trading gates.

## Completed in this phase

### Coinbase readonly adapter hardening

`CoinbaseReadonlyAdapterV2` now includes:

- request timeout configuration;
- bounded retry attempts for retryable readonly failures;
- retry-safe behavior for readonly GET requests only;
- HTTP error taxonomy;
- rate-limit classification;
- exchange-unavailable classification;
- credential-error classification;
- malformed-response classification;
- network-error classification;
- structured `CoinbaseReadonlyError.to_dict()` metadata;
- credential aliasing that never exposes raw credentials.

### Error taxonomy

Readonly errors now carry:

- `kind`;
- `status`;
- `retryable`;
- message.

This gives operators and tests a stable way to distinguish credential failures from rate limits, exchange outages, malformed responses, timeouts, network errors, and generic HTTP errors.

### Persisted snapshots

`LiveReadonlyServiceV2` now persists readonly snapshots into `live_readonly_snapshots` with:

- user id;
- exchange;
- adapter version;
- credential alias;
- snapshot payload;
- snapshot hash;
- snapshot timestamp;
- created timestamp;
- live execution disabled metadata.

### Freshness status

Added live-readonly freshness status through:

- `GET /api/live-readonly/status`

The status reports:

- missing snapshot;
- invalid timestamp;
- fresh snapshot;
- stale snapshot;
- age seconds;
- max allowed age seconds;
- snapshot hash;
- exchange;
- adapter version;
- credential alias.

### Dashboard visibility

The dashboard system status panel now includes live-readonly freshness state.

### Indexes

Added Mongo indexes for:

- live-readonly reports checked timestamp;
- live-readonly snapshots by user and created time;
- unique snapshot hash.

### Tests

Extended live-readonly tests for:

- credential aliasing;
- structured readonly error taxonomy;
- rate-limit classification;
- exchange-unavailable classification;
- credential rejection classification;
- structured error serialization;
- persisted snapshot metadata;
- latest snapshot missing/fresh/stale states;
- reconciliation snapshot hash persistence;
- alert context carrying readonly error taxonomy.

## Operational expectations

A healthy live-readonly system should:

- use readonly exchange credentials only;
- never expose raw credentials in responses or logs;
- produce recent snapshots;
- report `fresh` status before manual live trading attempts;
- classify exchange failures correctly;
- alert when snapshot, orders, or fills reads fail;
- persist hashes for snapshot traceability;
- continue to block order placement through the readonly adapter.

## Configuration

Relevant environment variables:

- `COINBASE_EXCHANGE_API_KEY`
- `COINBASE_EXCHANGE_API_SECRET`
- `COINBASE_EXCHANGE_PASSPHRASE`
- `COINBASE_EXCHANGE_URL`
- `COINBASE_READONLY_TIMEOUT_SECONDS`, default `10`
- `COINBASE_READONLY_MAX_RETRIES`, default `2`
- `LIVE_READONLY_MAX_SNAPSHOT_AGE_SECONDS`, default `300`

## Phase 3 safety boundary

- Live-readonly mode can observe exchange/account state.
- Live-readonly mode still cannot place orders.
- Autonomous live trading remains unavailable.
- Manual live execution remains separately gated.
- Future manual live pilot work must require fresh live-readonly status before non-dry-run order submission.

## Acceptance checklist

| Requirement | Status |
|---|---:|
| Coinbase readonly timeout support exists | Complete |
| Retry policy for readonly retryable failures exists | Complete |
| Rate-limit errors are classified | Complete |
| Exchange outage errors are classified | Complete |
| Credential errors are classified | Complete |
| Malformed responses are classified | Complete |
| Snapshot metadata is persisted | Complete |
| Snapshot hash is persisted | Complete |
| Latest snapshot freshness status exists | Complete |
| Dashboard shows live-readonly status | Complete |
| Snapshot indexes exist | Complete |
| Readonly adapter still rejects order methods | Complete |
| Live autonomous trading remains unavailable | Complete |

## Next phase

Phase 4: Manual Live Trading Readiness.

The next phase should wire live order state transitions into the real adapter lifecycle, normalize broker responses, require post-order reconciliation, expand live risk decisions, and produce a manual live pilot runbook.
