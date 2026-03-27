# Consolidation Plan

This branch prepares the `phase-upgrades` work for safe merge into `main`.

## Goal
Flatten temporary `phase*` completion folders into a canonical runtime layout.

## Canonical target layout

```text
backend/
  api/
  core/
  plugins/
  monitoring/
  notifications/
  security/
  compliance/
  marketplace/
  environment.py
  feature_flags.py
  live_market.py
  main.py
tests/
docs/
```

## Working rules
- Keep the latest complete version of each subsystem.
- Rewrite imports so no final runtime file imports from `phase*` paths.
- Treat `phase*` folders as temporary upgrade scaffolding, not final structure.

## Known issue already identified
- `phase12/main.py` imports `phase5` modules and must be rewritten before merge.

## Expected consolidation sources
- Core runtime: mostly `phase12`
- Monitoring / notifications / security / compliance: `phase10+`
- Environment / feature flags: `phase11+`
- Live market / dashboard: `phase12`

## Merge rule
Do not merge this branch into `main` until canonical runtime paths and imports are normalized.
