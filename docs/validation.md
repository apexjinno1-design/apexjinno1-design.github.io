# Validation record

Validated in the cloud workspace on 18 October 2026 (Australia/Brisbane). All market-looking fixtures below are **synthetic** and establish software behavior only.

| Check | Observed outcome |
| --- | --- |
| Backend pytest including dedicated PostgreSQL integration | 66 passed after hosting additions. One upstream Starlette/AnyIO deprecation warning; no failed or expected-failure tests. |
| Ruff on backend app/tests | Passed. |
| PostgreSQL 16 migration lifecycle | Upgrade, schema-drift check, demo ingestion, persisted research, idempotent reingestion, rollback and downgrade passed in a dedicated `_test` database. Repeated runs permit an empty Alembic version table. |
| Docker Compose | Python API and Next.js production images built; PostgreSQL and API health checks passed; web, dashboard and stock detail requests returned 200. |
| Functional research workflow | 2,340 daily bars across nine symbols; six common-stock candidates; SPY/QQQ/IWM regime GREEN; DEMOA TRIGGERED and DEMOB READY. Second identical ingestion inserted zero rows and reported 2,340 unchanged. |
| Functional HTTP checks | Dashboard returned six visibly synthetic candidates. DEMOA returned 260 chart bars, a conditional risk plan and stored provenance. Stock detail server render and Next.js same-origin scan POST passed. |
| Native installation/startup | `scripts/install.sh`, `scripts/start-demo.sh`, frontend development startup, database health, dashboard, stock detail and scan proxy passed. Local SQLite database lives outside source under `/workspace/.stock-runtime`. |
| Next.js production build / TypeScript | Passed with Next.js 16.4.2, including the access proxy and public web health route; dynamic pages fetch at runtime. |
| npm audit | Zero reported vulnerabilities after updating Next.js. Audit is a registry observation, not a guarantee of security. |

## Hosted deployment additions

The Render blueprint and its launch instructions are in [deployment.md](deployment.md). GitHub push was verified against the remote `main` ref. Real authenticated Massive NVDA reference and daily-history requests succeed in the cloud environment: 21 bars for the tested month and 378 bars over the 550-calendar-day request. The latter is sufficient for daily-indicator warm-up. Credentials are not transferred to Render automatically.

Five frontend access-control unit tests passed. A production standalone server smoke test passed: public health, 401 challenges for protected pages and scan requests, rejection of wrong credentials, authenticated dashboard/scan, private response caching and internal `API_HOST` routing. Backend tests additionally validate managed database URL handling, request pacing, overlapping-refresh exclusion and initial refresh persistence/idempotence using a synthetic provider fixture. The blueprint YAML parses and its private service, database links, secure key prompt and required generated password were checked locally.

Hosted additions include managed-PostgreSQL URL normalization, configurable provider request pacing, guarded initial background refresh, a private API service link, and mandatory website authentication in the Render blueprint. Deployment has not been executed in a Render account; no public service URL or account-level blueprint validation is claimed. Review its paid plans in Render before creating resources.

## Reproduce the PostgreSQL test

The optional test requires a dedicated empty database with a name ending in `_test`. It refuses databases with application tables. It runs migrations and rolls back fixtures, then downgrades to base; never point it at a research or production database.

```bash
docker run -d --name stock-test-postgres \
  -e POSTGRES_USER=screener -e POSTGRES_PASSWORD=screener -e POSTGRES_DB=stock_test \
  -p 127.0.0.1:5432:5432 postgres:16-alpine
# Wait for: docker exec stock-test-postgres pg_isready -U screener -d stock_test
cd backend
TEST_DATABASE_URL=postgresql+psycopg://screener:screener@127.0.0.1:5432/stock_test \
  uv run pytest -q
```

Without `TEST_DATABASE_URL`, 65 tests run and the dedicated PostgreSQL check is reported as skipped. CI provisions that database and runs all 66 tests.

## Limits of this validation

- **Full-universe live ingestion is unrun.** Authenticated NVDA reference and historical daily requests passed, but a complete US-universe download and the initial hosted refresh have not run. Provider limits and individual endpoint entitlements still apply. Adapter mocks additionally cover pagination, destination restrictions and sanitized entitlement errors.
- **Browser interaction tests are unrun.** Playwright's Chromium download was denied by network policy at `cdn.playwright.dev` (HTTP 403). No screenshot, visual inspection or automated browser sorting/chart interaction result is claimed. TypeScript/build checks and functional server requests passed. Permit the browser download domain if you want to add this optional validation.
- **Container trust was configured explicitly.** The first build encountered UnknownIssuer behind the environment proxy. The optional `compose.cloud.yaml` uses the environment's public proxy CA via a Docker build secret; TLS and artifact verification remained enabled. API system trust includes the supplied public CA; no API credential was baked into an image.
- **Historical performance is not validated.** No backtest engine, EP confirmation, broker execution, journal UI, news fetch or SEC integration is implemented. Current active-stock references and modern adjusted backfills are not a survivorship-free or point-in-time historical dataset.
- **Publication is separate.** Saved cloud setup/startup instructions and credential requirements are draft configuration. A successful build, running service or draft save does not publish an environment or prove restoration in a fresh task.
