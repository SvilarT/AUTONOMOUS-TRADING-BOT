# Production Consolidation Criteria

This branch is being consolidated for live trading and production-grade deployment.

## Priority order
1. Core trading control plane (`backend/core`)
2. Connector and plugin boundaries (`backend/plugins`)
3. API surface required for controlled execution (`backend/api`)
4. Monitoring, notifications and runtime controls
5. Security, secrets and compliance support
6. Entry points, tests and docs

## Hard rules
- No surviving runtime file may import from any `phase*` path.
- Prefer the latest implementation only when it does not introduce stale phase coupling.
- Keep abstractions that support persistence, testability and operational control.
- Treat in-memory repositories and synthetic market data as placeholders to be isolated, not expanded.
- Favor deterministic runtime structure over milestone-history preservation.

## Production focus
- Risk controls over feature breadth
- Execution correctness over demo convenience
- Observability over UI flourish
- Runtime clarity over historical phase traceability
