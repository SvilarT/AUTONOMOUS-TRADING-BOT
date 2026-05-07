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

## Live-trading path

The intended route policy is:

| Route class | Required scope |
|---|---|
| live-readonly routes | `trading:live-preview` |
| live-trading dry-run preview | `trading:live-preview` |
| live-trading non-dry-run execution | `trading:live-execute` |
| emergency halt | `ops:halt` |
| index management | `ops:indexes` |

## Current implementation note

This PR establishes the reusable role/scope model and FastAPI dependencies. The follow-up PR should wire the dependencies onto live and ops routes in small targeted route patches.

## Why this matters

Signed live approval challenges are not sufficient by themselves. Live execution must require both:

1. a valid approval challenge; and
2. an authenticated principal with `trading:live-execute`.

That gives the live pilot a proper authorization boundary before moving toward real order execution.
