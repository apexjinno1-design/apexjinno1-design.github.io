# Live hosting with Render

GitHub stores and validates the code; Render runs the live frontend, private Python API and managed PostgreSQL database. GitHub Pages cannot run this application stack.

## Launch

1. Open [Deploy to Render](https://render.com/deploy?repo=https://github.com/apexjinno1-design/apexjinno1-design.github.io), sign in, and authorize access to this GitHub repository. Alternatively, select **New Blueprint**, repository `apexjinno1-design/apexjinno1-design.github.io`, branch `main`, blueprint `render.yaml`.
2. Review the blueprint: `stock-web` (public website), `stock-api` (private API), and `stock-db` (managed PostgreSQL) in the same region. These use **paid service plans**. Review Render's current prices and deployment summary before creating them. No Render resources have been created by the agent.
3. Enter your real Massive key in Render's secure `MASSIVE_API_KEY` prompt. The cloud environment's injected key is not automatically transferred. Never put it in GitHub, a frontend variable or chat.
4. Deploy, then open the **public URL shown by Render for `stock-web`**. Use its actual URL; the hostname may receive a suffix.
5. At the browser sign-in prompt, username is `research`. Obtain the generated `SCREENER_PASSWORD` from `stock-web` → **Environment**. You can replace it there with your own strong password; redeploy after changes. Keep `REQUIRE_AUTH=true`.
6. Allow several minutes for initial ingestion, then reload or click **Run daily scan**. Default symbols: SPY, QQQ, IWM, NVDA, AMD, AAPL, MSFT, META, with approximately 550 calendar days of history. Five common stocks are a starter research universe, not the whole US market; ranking sample size is displayed.

The launch link opens Render's review flow; it does not establish that a website has deployed. Account sign-in, billing approval where required, repository connection and secure key entry remain user actions.

Use **New → Blueprint** to create the complete stack from `render.yaml`. Creating a single **Web Service** from the repository does not automatically use the blueprint and defaults to looking for `Dockerfile` at the repository root. This repository has separate frontend and backend Dockerfiles.

## Fix “open Dockerfile: no such file or directory”

The blueprint uses explicit paths relative to the repository root. For services managed by the blueprint, sync the latest `main` commit and redeploy. For manually created services, open **Settings → Build & Deploy** and use:

| Setting | Website (`stock-web`) | Private API (`stock-api`) |
| --- | --- | --- |
| Root Directory | Leave blank | Leave blank |
| Dockerfile Path | `./frontend/Dockerfile` | `./backend/Dockerfile` |
| Docker Build Context Directory | `./frontend` | `./backend` |

Save and select **Manual Deploy → Deploy latest commit**. A manually created website still needs the private API, PostgreSQL and environment settings described above; correcting its Dockerfile alone does not create those dependencies. Use the blueprint to provision/link the whole stack. Review existing services before creating another stack so you do not unintentionally duplicate paid resources. Do not delete existing databases.

## Service behavior

- The API normalizes Render's PostgreSQL connection URL to psycopg 3. Alembic runs before Uvicorn. It honors `PORT` and uses one process to avoid duplicate schedulers.
- The API is a **private service**. Only the Next.js server connects through `API_HOST`, port 8000. Do not make the API public without adding API authentication.
- The web service checks HTTP Basic credentials before serving pages or scan requests over Render's HTTPS endpoint. This is a single-user access gate, not a multi-user account system. Credentials are compared via fixed-length hashes and timing-safe comparison. Private responses use `Cache-Control: private, no-store`.
- Public `/api/web-health` reports only `{status: "ok"}` for readiness probes. It checks the web process, not ingestion success. Check the signed-in dashboard and backend logs for data readiness.
- `INITIAL_REFRESH_ENABLED=true` schedules background ingestion on startup. Identical data is not duplicated; corrections create revisions. No synthetic data is seeded. The scan runs after ingestion completes.
- `SCHEDULER_ENABLED=true` refreshes weekdays at 22:30 UTC. The exchange calendar excludes holidays and incomplete sessions. A lock prevents overlapping initial/scheduled refreshes within the single API process.
- `MASSIVE_REQUESTS_PER_MINUTE=5` paces provider requests. Adjust to your subscription's limit. The initial eight-symbol reference/history refresh takes several minutes. Entitlement errors remain errors; no demo fallback occurs.

## Expand the live universe

Update backend `INGEST_SYMBOLS` with your US common stocks plus SPY/QQQ/IWM. Redeploying schedules another initial refresh. For a large universe use the backend's Render shell and the CLI; a full download can take hours at a small rate limit. A web scan alone does not fetch or discover new stocks.

```bash
# Private API service's Render shell; choose dates appropriate to the current session:
python -m app.cli ingest --universe --start 2024-10-01 --end 2026-10-16
python -m app.cli scan
```

Retain at least 128 completed sessions. History depth and endpoint access depend on provider entitlements. Add the README's sector ETFs for sector context. Current reference metadata is not a point-in-time historical universe for backtesting.

## Troubleshooting

- **Sign-in prompt:** expected. Read/reset `SCREENER_PASSWORD` in the web service's Environment settings. A 503 about access configuration means credentials are missing; configure them rather than disabling the gate.
- **API unavailable:** confirm private API/database health, same region, linked frontend `API_HOST` and successful migrations. Never copy database connection values into logs or chat.
- **No candidates:** wait for `Provider refresh and daily scan completed` in API logs. Check key/entitlement errors (401/403), rate limits (429), history depth and freshness. Fix the prerequisite and redeploy/retry; do not relax qualification rules to hide failures.
- **BUILDING or ineligible:** valid research outcomes. Read the qualification/risk evidence; no scan must produce a trade and no returns are guaranteed.
- **Blueprint/account differences:** Render validates the blueprint at launch. If your account offers different names, regions or plans, adjust them while retaining the private API, managed PostgreSQL, required web authentication and same-region service links.

Manage database backup/retention through Render. Do not delete research data or switch to synthetic mode to resolve ingestion problems. Stop or delete billable services through Render when no longer needed.
