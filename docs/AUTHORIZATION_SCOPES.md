# Authorization Scopes

> This is for educational/backtesting/paper-trading use only. Live trading involves substantial risk of loss. Not financial advice.

This document defines the scoped authorization foundation for live-trading readiness.

## Roles

| Role | Meaning |
|---|---|
| `user` | Default authenticated user |
| `trader` | User allowed to perform manually approved live execution |
| `admin` | Administrative operator with all scopes |

## Scopes

| Scope | Purpose |
|---|---|
| `trading:paper` | Paper-mode bot/dashboard operations |
| `trading:live-preview` | Live-readonly and dry-run preview operations |
| `trading:live-execute` | Non-dry-run manually gated live execution |
| `ops:readiness` | Operational readiness checks |
| `ops:indexes` | Mongo index bootstrap through API |
| `ops:halt` | Emergency halt |
| `admin:roles` | Future role/scope management |
| `admin:*` | All scopes |

## Default scope posture

Default users receive safe baseline scopes:

```text
trading:paper
trading:live-preview
ops:readiness
ops:halt
```

Default users do **not** receive:

```text
trading:live-execute
ops:indexes
admin:roles
admin:*
```

## Enforced route policy

Route scope enforcement is centralized in `ScopeEnforcementMiddlewareV2`. It blocks privileged live/ops paths before handlers execute.

| Route class | Required scope |
|---|---|
| `/api/live-readonly/*` | `trading:live-preview` |
| `/api/live-trading/gate` | `trading:live-preview` |
| `/api/live-trading/audits` | `trading:live-preview` |
| `/api/live-trading/market-buy` with `dry_run=true` | `trading:live-preview` |
| `/api/live-trading/market-sell` with `dry_run=true` | `trading:live-preview` |
| `/api/live-trading/market-buy` with `dry_run=false` | `trading:live-execute` |
| `/api/live-trading/market-sell` with `dry_run=false` | `trading:live-execute` |
| `/api/ops/readiness` | `ops:readiness` |
| `/api/ops/indexes/ensure` | `ops:indexes` |
| `/api/ops/emergency-halt` | `ops:halt` |

## Why middleware enforcement

The live/ops paths require a single authorization choke point that is harder to bypass than scattered route-level checks. Middleware also allows dry-run vs. non-dry-run live requests to be differentiated before they reach execution handlers.

## Why this matters

Signed live approval challenges are not sufficient by themselves. Live execution must require both:

1. a valid approval challenge; and
2. an authenticated principal with `trading:live-execute`.

That gives the live pilot a proper authorization boundary before moving toward real order execution.
