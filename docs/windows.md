# Run STOCK on your Windows computer

Hosting the app on your own computer has no Render/private-service hosting charges. Docker Desktop is free for personal use under its applicable terms. Your Massive data access still follows your own provider subscription.

## First launch

1. Install [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/). Follow its installer, including any Windows/WSL setup it requests, and restart Windows if prompted.
2. Open Docker Desktop and wait until its engine is running.
3. [Download the STOCK ZIP](https://github.com/apexjinno1-design/apexjinno1-design.github.io/archive/refs/heads/main.zip) and **extract it**. Open the extracted folder containing `Start STOCK.bat`.
4. Double-click **Start STOCK.bat**. This opens the checked-in PowerShell launcher using a process-local execution policy; it does not change Windows' global policy. If your computer is managed by an organization, follow its software policy.
5. When prompted, enter your Massive key in the launcher window. It is hidden while typing. Never paste it in chat. It is cached only in `.local\stock.env`, which is excluded from Git; keep that file private. An already-set `MASSIVE_API_KEY` process variable is reused.
6. Let Docker build and start the application. The launcher opens your browser automatically after the website is ready.

The database, API and website all run locally in Docker. You do not install Python, Node.js, PostgreSQL or a hosted private service separately. The first image downloads/build can take several minutes. Initial real-data ingestion then takes several more minutes; wait and reload the dashboard. The launcher does not seed synthetic data or assume that a provider error is a valid scan.

Default first universe: SPY/QQQ/IWM for market context and NVDA/AMD/AAPL/MSFT/META for screening. Five stocks are a starter watchlist, not a full-US ranking universe. Data history/endpoint access depends on your Massive plan. The app uses a conservative five requests per minute by default.

## Daily use

- Start Docker Desktop, then double-click **Start STOCK.bat**. Your saved key is reused and the current history/scan refreshes automatically on backend startup.
- Keep Docker Desktop and your computer running while using the app. Scheduled refreshes run at 22:30 UTC on weekdays only while the backend is running; this is 08:30 the next day in Brisbane.
- Double-click **Stop STOCK.bat** to stop the app. Your stock database remains in Docker's `stock-local_postgres_data` volume. Do not delete that volume if you want to keep the history.
- You may close the launcher window after startup. Closing it does not stop the Docker services.
- Render is not needed for this local workflow. Review/suspend any paid Render services you no longer use in your own account, preserving any database you want to keep.

## Useful fixes

- **Docker not found / not running:** install/open Docker Desktop, wait for the engine, then start again.
- **Port already in use:** stop the other local program using port 3000 or 8000. The launcher does not kill unrelated programs.
- **Cannot save files:** extract the ZIP to a normal folder you can write to, such as Documents. Do not launch directly from inside the ZIP.
- **Update the Massive key:** stop the app, delete only `.local\stock.env`, then start again to re-enter it. If Windows has an existing `MASSIVE_API_KEY` environment variable, update/remove that binding too because Docker Compose environment values take precedence over the cached file.
- **No candidates after several minutes:** open Docker Desktop, find the `stock-local` application's `api` container and inspect its logs for key/entitlement errors (401/403), rate limits (429) or data-refresh failures. Never share keys or connection strings from container settings. After a successful refresh, the dashboard contains the loaded stock candidates.
- **Demo data appears:** the supplied launcher explicitly disables demo mode and uses a separate `stock-local` project/database. Check that you opened the locally launched website and that the selected Docker project is `stock-local`. Existing demo database volumes are preserved.

## Equivalent terminal commands

After the launcher has prepared the local files, the startup command it runs is:

```powershell
docker compose --project-name stock-local --env-file .local/stock.env --file compose.yaml --file compose.local.yaml up --build --detach --wait --wait-timeout 180
```

The stop command is `docker compose --project-name stock-local --file compose.yaml stop`. Services bind only to your computer's loopback addresses; this is not a publicly hosted website.

The Docker workflow is validated in the cloud Linux environment. The Windows batch/PowerShell launchers cannot be tested end to end on that machine; they require Docker Desktop on your actual Windows computer.
