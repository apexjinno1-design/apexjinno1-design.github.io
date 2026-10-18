# Development roadmap

## Phase 1 — daily research (implemented)

- Core schema and initial Alembic migration, current US stock reference ingestion, adjusted historical daily OHLCV with revision/availability metadata.
- Deterministic daily indicators and tests, explainable configurable breakout rules, regime context, technical risk sizing and immutable research observations.
- Sortable/filterable dashboard, scan settings, stock chart, evidence and conditional plan. Synthetic mode is visibly separate.
- Compose, local setup, locked dependencies, API/design/formula documentation and smoke validation.

Production-data acceptance remains gated on a Massive subscription/key and the relevant endpoint entitlements. Sector membership remains null where no authoritative classification was supplied. Full-universe throughput and deployment authentication need work before shared operation.

## Phase 2 — intraday and episodic pivots

1. Add provider capabilities for snapshots, minute bars and news; persist adjustment/source/availability metadata and regular-session completeness. Move long ingest/scan work to a dedicated job worker with progress, cancellation and resumability; add caching only where measured.
2. Opening range and same-time cumulative RVOL use exchange schedules, DST and early-close-aware historical baselines. Unit tests must verify partial range, missing minutes, timestamp boundaries and no future minutes.
3. EP state machine: >=10% gap default, unusual volume, prior base, timestamped verified material catalyst, earnings growth/surprise if available and observed OR-high break. Add authenticated manual verification with an append-only audit history. Missing/unverified catalyst must prevent confirmation.
4. Deduplicated alerts for confirmed signals with evidence and data freshness. No orders.

Acceptance: representative minute ingestion and replay, mocked provider failures, verified/unverified catalyst tests, and an end-to-end EP observation that cannot trigger early.

## Phase 3 — unbiased historical testing and journal

1. Obtain historical membership including delisted names where permitted, point-in-time reference classifications, corporate actions and original data vintages/availability timestamps. Report source gaps and survivorship limitations; do not fill them from today's universe.
2. Chronological signal and execution engine: next executable event after signal, actual calendar sessions, 1–5 session horizon, gap fills, fees/spreads/slippage/participation limits, delisting and splits. Daily bars touching stop and target are ambiguous: resolve with contemporaneous intraday evidence; otherwise use conservative stop-first and report ambiguous count separately. Never assume profit from unknown ordering.
3. Chronological out-of-sample splits, embargo/purge overlapping holding windows, rolling train/validation/test walk-forward runs. Preserve immutable run settings/data manifests. In-sample selection must not leak into later evaluation.
4. Report trade count, win rate, mean net R expectancy, profit factor, equity-path maximum drawdown, full net-return distribution and 5-session target-before-stop hit rate. Include denominator definitions, ambiguous/censored/missing cases, confidence intervals where justified and sensitivity to execution costs. Avoid annualized forecasts from small samples.
5. Journal UI/API with actual fills, notes, linked research evidence and differences from planned fills. Broker execution remains out of scope.

Acceptance: known hand-computed trade fixtures, simultaneous stop/target/gap tests, delisting fixtures, deterministic data-version replay, no-overlap walk-forward validation and a reproducible out-of-sample report with observed sample sizes.

## Phase 4 — research intelligence and optional paper execution

- SEC EDGAR adapter and accession/publication/amendment-aware fundamentals; optional contact `SEC_USER_AGENT`, rate limiting and SEC network destinations configured only when used.
- News/catalyst classification with source citations, timestamps, confidence and human override audit trail.
- Calibrated statistical probabilities only after sufficient representative observations; probability calibration, drift, uncertainty and chronological evaluation are required.
- Optional IBKR **paper** adapter with explicit operator opt-in, position reconciliation, order limits and kill switch. No live automated trading in the initial version.
