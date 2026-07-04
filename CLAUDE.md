# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Personal finance API (FastAPI + SQLModel) with a vanilla-JS frontend. Auth via JWT. SQLite in dev, PostgreSQL in prod (switched by `DATABASE_URL`). Deployed to Railway via `Procfile`.

## Commands

Windows dev environment; the venv lives at `.venv/`.

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt   # install deps
.venv\Scripts\uvicorn main:app --reload                       # run server on :8000
.venv\Scripts\python.exe smoke_test.py                        # end-to-end smoke test
```

- Swagger UI: http://localhost:8000/docs — Frontend: http://localhost:8000/app/
- There is no pytest suite yet (pytest is in requirements). `smoke_test.py` runs the full API flow in-process via TestClient — **it writes to the same `finance.db` as the dev server**, so expect test data in the live DB if you run it.
- No Alembic. Tables are created by `create_db_and_tables()` at app startup (lifespan). After any model change, delete `finance.db` and restart — there are no migrations.
- **Do not unpin `bcrypt==4.0.1`**: passlib 1.7.4 crashes with bcrypt 5.x on every hash.

## Architecture

### Ownership model (the key invariant)

Users own `Account` and `Category` rows directly (`user_id` FK). `Transaction`, `Investment`, and `InvestmentOperation` have **no** `user_id` — they belong to an account, and ownership is always verified through the account chain, returning **404 (never 403)** on foreign resources:

- `routers/accounts.get_owned_account()` is the shared helper, reused by `transactions.py` and `investments.py`.
- List endpoints filter with a JOIN on `Account.user_id` (see `_user_transactions_query` in `routers/stats.py`).

Accounts have **no balance column** — balances/net worth are derived: liquid cash = Σ(income − expense) transactions; investment value = Σ(shares × avg_buy_price) of open positions.

### Auth flow

`routers/auth.py` login (JSON body, not OAuth2 form) → `core/security.py` issues JWT with `sub` = user id → `core/deps.py` `get_current_user` decodes it via `OAuth2PasswordBearer`. Endpoints use the `CurrentUser` / `SessionDep` annotated dependencies from `core/deps.py`.

### Investments domain (three tables in `models/investment.py`)

- `Asset` — global catalog, **shared across all users** (ticker unique; optional `isin`, `last_price` for current-value/return calcs).
- `Investment` — one open position per (account, asset). `shares`/`avg_buy_price` are **always rebuilt by replaying the operation log** (`_recompute_position` in `routers/investments.py`) — never mutate them incrementally, or splits/out-of-order ops corrupt them. Selling down to 0 shares sets `closed_at` (positions are never deleted).
- `InvestmentOperation` — immutable buy/sell/**split** log. For splits, `shares` holds the ratio (25 = 25:1). Ops carry `amount` (exact cash, preferred over shares×price for invested totals) and `note`.
- `POST /investments/import/xlsx` imports the personal Excel format (headers: ISIN, Import, Price, Date, Reason, Cantidad (acciones), Comisión (€)); idempotent — duplicate (investment, date, shares, price) rows are skipped. Splits are NOT auto-detected: register them via `POST /investments/{id}/split` after importing.
- `GET /investments/{id}/progress` derives the invested-vs-value time series (value at each op = cumulative shares × that day's price), consumed by the frontend INVESTMENTS view.

### Registration requirements

- New model files must be imported in `models/__init__.py` or `create_all` won't see the table.
- Collection routes end in a trailing slash (`/accounts/`, `/transactions/`, …) because routers define `@router.get("/")` under a prefix — the frontend calls them with the slash.

### Frontend (`frontend/`)

No-build vanilla JS SPA, served two ways: mounted at `/app` by `main.py` (StaticFiles) and deployable to GitHub Pages as-is.

- Plain `<script>` tags with globals, load order matters (index.html bottom): `utils → api → charts → auth → views → app.js`.
- Hash routing: each page is an object with a `load()` method registered in the `Views` map in `js/app.js`; adding a page = new section in index.html + new js file + `Views` entry + nav link.
- `js/api.js`: JWT in localStorage key `fin_token`; API base defaults to `http://localhost:8000`, overridable via localStorage `fin_api_base`. A 401 clears the token and forces re-login.
- Charts are hand-rolled SVG/CSS in `js/charts.js` — no dependencies anywhere.
- After frontend changes, hard-refresh the browser (`Ctrl+F5`); stale cached JS is a recurring trap.

## Repo notes

- `finance.db` is live dev data (gitignored); delete it to reset.
- `finance-frontend/` contains only agent-tooling scaffolding (`.agents/skills`), not app code — the real frontend is `frontend/`.
