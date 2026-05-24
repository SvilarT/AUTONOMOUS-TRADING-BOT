# Autonomous Trading Bot Frontend

React operator dashboard for the Autonomous Trading Bot platform.

This frontend is not a generic Create React App demo. It is the browser-facing control surface for authentication, portfolio visibility, risk telemetry, bot controls, live-readonly/manual-live readiness views, and pilot-review workflows exposed by the FastAPI backend.

---

## Runtime Role

The frontend provides the operator UI for:

- user signup and login;
- authenticated dashboard access;
- portfolio, trade, position, risk, and market-analysis views;
- bot start/stop controls for paper/simulation workflows;
- system status and readiness visibility;
- pilot-review workflows at `/pilot-review`.

The app expects the backend API to be available through `REACT_APP_BACKEND_URL`.

---

## Key Routes

| Route | Purpose |
|---|---|
| `/` | Login/signup screen when unauthenticated; redirects authenticated users to `/dashboard`. |
| `/dashboard` | Main authenticated operator dashboard. |
| `/pilot-review` | Authenticated manual-live pilot review and signoff surface. |

Authentication tokens and user metadata are stored in browser `localStorage` by the current app implementation.

---

## Local Development

From the repository root, the recommended full-stack path is:

```bash
cp .env.example .env
docker compose up --build
```

For frontend-only development:

```bash
cd frontend
npm install --legacy-peer-deps
REACT_APP_BACKEND_URL=http://localhost:8000 npm start
```

The development server runs at:

```text
http://localhost:3000
```

---

## Environment Variables

| Variable | Required | Example | Description |
|---|---:|---|---|
| `REACT_APP_BACKEND_URL` | Yes | `http://localhost:8000` | Base URL for the FastAPI backend. |
| `CI` | No | `false` | Used by CI/build scripts to control Create React App test behavior. |

For Docker Compose, the frontend image receives `REACT_APP_BACKEND_URL` as a build argument.

---

## Scripts

```bash
npm start
```

Runs the local development server.

```bash
npm test -- --watchAll=false
```

Runs the frontend test suite once.

```bash
npm run lint
```

Runs ESLint over `src` with the configured warning threshold.

```bash
npm run build
```

Builds the production static bundle into `build/`.

---

## Backend Contract

The frontend talks to the backend through the shared API client in:

```text
src/lib/apiClient.js
```

The API client handles:

- backend base URL resolution;
- bearer-token injection;
- request ID propagation;
- normalized backend error envelopes;
- dashboard/readiness/worker helper calls.

Backend health and readiness endpoints:

```text
http://localhost:8000/healthz
http://localhost:8000/readyz
```

---

## Safety Posture

The frontend is an operator dashboard. It does not independently approve live trading.

Live execution remains controlled by backend-side gates, including trading mode, kill switches, symbol allowlists, notional caps, manual approval requirements, audit records, reconciliation requirements, and release gates.

Do not treat a visible frontend control as sufficient authorization for live trading. The backend is the source of truth for execution permission.

---

## Validation

Frontend validation is part of the repository CI pipeline:

- dependency installation;
- ESLint;
- React tests;
- targeted pilot-review UI tests;
- production build;
- Docker image build;
- Docker Compose smoke test.

Run locally before opening frontend changes:

```bash
cd frontend
npm install --legacy-peer-deps
npm run lint
npm test -- --watchAll=false
npm run build
```

---

## Related Project Docs

See the repository root for the full system-level documentation:

- `README.md` — project overview, safety model, setup, and roadmap status;
- `ARCHITECTURE.md` — backend/frontend/runtime topology;
- `PRODUCTION_ROADMAP.md` — staged readiness plan;
- `docs/` — phase-specific readiness and operations notes.
