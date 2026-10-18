# Basecamp — Momentum Research

A US stock research screener inspired by Qullamägi's momentum breakout process. Phase 1 includes historical daily ingestion, deterministic indicators, an explainable breakout scan, conditional position sizing, and a dashboard with stock charts. This is research software: it does not place orders, predict future prices, or promise returns.

## What is implemented

- Python 3.12, FastAPI, SQLAlchemy, PostgreSQL and Alembic; SQLite is supported for lightweight local development and tests.
- Massive REST provider adapter: paginated active US common-stock reference universe, ticker reference and adjusted daily OHLCV. Authentication remains on the backend.
- Exchange-calendar-aware ingestion, append-only price corrections, availability cutoffs and immutable indicator/setup observations with input row identifiers.
- Daily indicators, cross-sectional momentum ranking, known-sector relative strength, 10–40 session breakout bases and explicit quality checks.
- GREEN/YELLOW/RED regime using SPY, QQQ and IWM; optional sector ETF observations. Incomplete or missing benchmark data blocks position sizing.
- Technical stops, risk and allocation limits, adjustable account settings and hypothetical risk-multiple objectives.
- Next.js/React/TypeScript/Tailwind dashboard, sorting/filtering, scan controls and Lightweight Charts stock details.
- Optional single-process APScheduler refresh, deterministic synthetic data, calculation and API tests.

EP/intraday screening, alerts, executable backtesting, journal workflows, SEC ingestion, news intelligence and broker integration are **not implemented**. The future-facing tables exist; the backtesting page shows the intended validation requirements without fabricated metrics. See [roadmap](docs/roadmap.md).

## Quick start with Docker Compose

Requires Docker with Compose v2. Run commands from the repository root. Use the existing checkout; a separate Git worktree is unnecessary.

```bash
cp .env.example .env  # only if .env does not already exist
# For a synthetic demo, edit .env and set DEMO_MODE=true. No API key is needed.
docker compose up --build -d
docker compose exec api python -m app.cli demo  # only with DEMO_MODE=true
```

The API applies migrations before startup. Open the frontend on port 3000 and the API's `/docs` on port 8000 on your local machine. The onboarding environment validates these with internal requests and does not provide a localhost preview link.

Use `docker compose logs api web` to diagnose startup. `docker compose stop` preserves the database. **Do not delete the database volume to switch modes.** Use a separate Compose project (`docker compose -p stock-live ...`) and `.env` with `DEMO_MODE=false` for real data; this creates a separate named volume. Demo data and provider data must not share a research database.

The Compose PostgreSQL password is a local development default. The API and web bind to loopback; the database has no host port. This application has no user authentication or authorization layer. Add authentication, request limits, HTTPS, restricted ingress and managed database credentials before any shared/public deployment. Use one API worker if the in-process scheduler is enabled.

## Local development

Requires Python 3.12+, [uv](https://docs.astral.sh/uv/) and Node.js 22+. Dependencies are locked in `backend/uv.lock` and `frontend/package-lock.json`.

```bash
cd backend
uv sync --frozen
# SQLite fallback; PostgreSQL is recommended and used by Compose.
export DATABASE_URL=sqlite:///./demo.db
export DEMO_MODE=true
uv run alembic upgrade head
uv run python -m app.cli demo
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

In a second shell:

```bash
cd frontend
npm ci
API_BASE_URL=http://127.0.0.1:8000 npm run dev
```

In this cloud workspace, home-directory caches are read-only. Set `UV_CACHE_DIR=/workspace/.cache/uv`, pass `--cache /workspace/.cache/npm` to npm installation commands, and use `BUILDX_CONFIG=/workspace/.cache/buildx` with Docker builds. `scripts/install.sh` uses those locations automatically. The root `.env` is read by Compose; for a local backend either export variables or put a separate ignored `.env` in `backend/`. Never commit credentials or use a `NEXT_PUBLIC_` name for keys.

If Docker builds run behind a trusted TLS inspection proxy, supply its **public CA certificate** with the optional override; verification stays enabled. The API installs that CA into its system trust store, and the frontend uses it during dependency installation. Do not supply a private key or an untrusted certificate.

```bash
STOCK_PROXY_CA=/usr/local/share/ca-certificates/environment-proxy-ca.crt \
BUILDX_CONFIG=/workspace/.cache/buildx \
docker compose -f compose.yaml -f compose.cloud.yaml up --build -d
```

## Real market data

Use a **separate, non-demo database**, `DEMO_MODE=false` and a backend-only `MASSIVE_API_KEY`. In cloud environment settings, enter the key securely and allow `api.massive.com`; do not paste it in chat. Provider subscriptions determine history, delay, rate limits and endpoint entitlements. The application retries bounded 429/5xx responses, keeps TLS verification enabled and does not fall back to synthetic data on provider failure.

```bash
# With the API running against the real-data database:
curl -f -X POST http://127.0.0.1:8000/api/ingest/universe
curl -f -X POST http://127.0.0.1:8000/api/ingest/daily \
  -H 'Content-Type: application/json' \
  -d '{"symbols":["SPY","QQQ","IWM","NVDA","AMD","AAPL"],"start":"2024-10-01","end":"2026-10-16"}'
curl -f -X POST http://127.0.0.1:8000/api/screen/breakouts \
  -H 'Content-Type: application/json' -d '{}'
```

Choose dates appropriate to the latest completed US session; at least 128 complete sessions are needed for quality classification. Ingest history in batches of at most 100 symbols. For a whole reference universe use the CLI below, which commits each symbol independently and reports failed symbols. A full-universe first download can be slow or exceed a small plan's quotas; it is deliberately not run automatically during setup.

```bash
cd backend
uv run python -m app.cli ingest --universe --start 2024-10-01 --end 2026-10-16
# Or select a smaller universe:
uv run python -m app.cli ingest --symbols SPY,QQQ,IWM,NVDA,AMD,AAPL --start 2024-10-01 --end 2026-10-16
uv run python -m app.cli scan
```

Sector ETFs: `XLB,XLC,XLE,XLF,XLI,XLK,XLP,XLRE,XLU,XLV,XLY`. Include these to display their regime evidence. The GREEN/YELLOW/RED vote uses SPY/QQQ/IWM; sector ETF observations are contextual. Massive's SIC description is stored as **industry**, never silently relabelled as a sector. Sector RS is null until sector membership is available from a supported classification source. An active-reference refresh is not a historical membership database, and absent symbols are not automatically marked delisted.

`SCHEDULER_ENABLED=true` schedules refreshes at 22:30 UTC on weekdays, using validated `INGEST_SYMBOLS` (default: SPY/QQQ/IWM). Add your research symbols and optionally sector ETFs explicitly. The exchange calendar excludes holidays, early/incomplete sessions and stale benchmarks. Keep the scheduler disabled in demo mode and run one scheduler/API process. Redis is not required in Phase 1; introduce caching only after query profiling.

## Validation

```bash
cd backend
uv run pytest -q
uv run ruff check app tests
uv run alembic check
cd ../frontend
npm run typecheck
npm run build
```

Calculation tests cover every implemented daily formula, warm-ups, missing values, ties, zero denominators and causality. Additional tests exercise all setup states, risk rejection/sizing, exchange holidays/DST/early closes, revision replay, duplicate ingestion, stale/gapped history, provider pagination/authentication boundaries and the complete API workflow. An optional PostgreSQL integration test runs when `TEST_DATABASE_URL` points to a **dedicated empty test database** (see `docs/validation.md`).

## Interpretation and limits

- A daily scan observes completed sessions. `TRIGGERED` means a close cleared the buffered pivot with sufficient daily volume; it does not establish when an intraday order would have filled. A gap is not assumed filled at the lower pivot. Use the detail page's planning entry and keep the conditional entry trigger distinct.
- Scan rankings are relative to the **loaded, fresh common-stock universe**. A 100th percentile rank among six synthetic stocks is not a ranking of all US stocks. The dashboard reports the sample size.
- A snapshot stores the inputs, settings and version used. Modern backfilled adjusted prices were first observed **at ingestion**, not at their historical session close. Historical queries before observation return no such rows. Backfills, revised adjustments, latest reference metadata and today's active universe are not sufficient for unbiased backtesting.
- Stops remain at the last five sessions' technical low within the selected base. Wide stops are rejected. Targets default to 3R hypotheses, not forecasts; the 2R preference does not estimate the chance of reaching a target. Size limits exclude fees/slippage and require a separate execution model before use in trading.
- Stale or gapped price series are excluded. Missing benchmark history prevents confirmation/position eligibility. No catalyst or EP confirmation is inferred from a gap alone.

## Design documents

- [Architecture and data flow](docs/architecture.md)
- [Database schema](docs/schema.md)
- [API specifications](docs/api.md)
- [Indicator formulas and screening rules](docs/indicators.md)
- [Phased development roadmap](docs/roadmap.md)
- [Validation evidence and remaining limitations](docs/validation.md)

TradingView Lightweight Charts is used under its Apache 2.0 license. Chart attribution is retained; see [TradingView](https://www.tradingview.com/).
