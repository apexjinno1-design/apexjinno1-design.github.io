# API v0.1

FastAPI generates executable OpenAPI at `/openapi.json` and interactive documentation at `/docs`. All routes below begin with `/api`. No provider credentials are accepted in request bodies or returned to the frontend. Current endpoints are intended for a trusted local workspace; there is no public user authentication.

| Method / path | Request | Result |
| --- | --- | --- |
| GET /health | none | Database connectivity/schema check, demo flag, **boolean** provider-key presence. 503 if unavailable/unmigrated. |
| POST /ingest/universe | none | Fetch paginated active US common-stock references; return upsert count/provider. No history download and no historical/delisted universe claim. |
| POST /ingest/daily | symbols[1..100], start/end ISO dates, adjusted=true | Transactional daily ingestion. inserted/unchanged/excluded counts, provider and observation time. Ordered date range <=10 years. Incomplete/non-exchange sessions excluded. |
| GET /stocks | limit=100 [1..1000], offset=0 | Alphabetical paginated reference list, including ETFs used for market context. |
| POST /screen/breakouts | optional as_of UTC/offset timestamp, breakout{}, risk{}, regime{} | New immutable snapshots, current candidates and qualification evidence, loaded-universe count, ranking sample count, regime evidence and excluded stale/gapped symbols. Uses only observations available by as_of; future/naive timestamps rejected. |
| GET /dashboard | none | Latest saved scan candidates/settings, market regime, observation timestamp, source session, expected completed session and stale flag. Empty state if no setups have been saved. No scan side effects. |
| GET /stocks/{symbol} | optional aware as_of | Adjusted bars up to 760 calendar days, SMA10/20/50, most recent snapshot at/before as_of, conditional plan, qualification checks and provenance. 404 for unknown ticker. |
| GET /backtests | none | `available:false`, phase=3, empty results and implementation status. No simulated performance values. |

Validation errors use FastAPI's 422 `detail` array. Unknown symbols return 404. Missing provider configuration is 503; provider access/entitlement/transport/invalid-data failures are sanitized 502 responses. Demo mode rejects real-provider ingestion with 409. Database failures roll back via session closure and require log diagnosis; health provides a nonsecret readiness check.

## Scan request

```json
{
  "breakout": {
    "min_base_sessions": 10,
    "max_base_sessions": 40,
    "min_return63": 0.30,
    "min_return126": 0.50,
    "min_rs_percentile": 70,
    "min_prior_advance": 0.20,
    "prior_advance_sessions": 21,
    "max_base_depth": 0.25,
    "max_range_contraction": 0.85,
    "max_volume_contraction": 0.85,
    "higher_low_tolerance": 0.02,
    "min_avg_dollar_volume": 10000000,
    "min_price": 5,
    "min_breakout_rvol": 1.5,
    "entry_buffer_pct": 0.001,
    "ready_distance_pct": 0.05,
    "max_extension_pct": 0.05
  },
  "risk": {
    "account_equity": 100000,
    "risk_fraction": 0.005,
    "allocation_fraction": 0.15,
    "max_stop_pct": 8,
    "min_reward_risk": 2,
    "target_multiple": 3,
    "horizon_sessions": 5
  },
  "regime": { "green_min_votes": 3, "yellow_min_votes": 1 }
}
```

Unspecified fields use documented defaults. Unknown setting keys, invalid numeric ranges and impossible window ordering are rejected. Targets are hypothetical risk multiples; the API does not estimate a probability. Ranking percentiles use prior-session 63d stock returns among fresh loaded active common stocks; QQQ-relative returns are separate indicator outputs.

Each candidate contains `symbol`, `name`, `sector`, `provider`, `session`, `indicators`, `status`, `qualified`, `score`, `checks`, `base_sessions`, `pivot`, `entry_trigger`, `price_confirmed`, `volume_confirmed`, `evidence` and `plan` (warm-up candidates omit unavailable levels). `plan.eligible` is independent of the classification: a triggered setup can still be rejected for market conditions or an excessive stop.

## Planned API contracts (not available yet)

Phase 2 adds queued job status, minute/snapshot ingestion, opening-range/RVOL views, EP screening, and authenticated timestamped manual catalyst verification. Phase 3 adds validated backtest runs/results, chronologically partitioned walk-forward reports and journal CRUD. Do not implement UI controls that claim those operations work before their validation prerequisites exist.
