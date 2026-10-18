# Indicator formulas and strategy rules

All daily windows count **completed regular US exchange sessions**, not calendar days. Let `C,H,L,O,V` be adjusted daily close/high/low/open/volume in ascending session order. Missing warm-up values are null, never zero. Non-finite OHLCV, duplicate/unsorted sessions, invalid envelopes and negative volume are rejected. Indicator functions are pure trailing operations; the service excludes incomplete sessions and gaps. Returns are decimal fractions unless a field explicitly ends in `_pct`.

| Field | Formula and warm-up |
| --- | --- |
| return_1 / 20 / 63 / 126 | `C[t]/C[t-n] - 1`, requires n+1 observations. No forward fill. |
| rs_qqq63 | `(C[t]/C[t-63]-1) - (QQQ[t]/QQQ[t-63]-1)`; benchmark is reindexed to the stock's exact sessions, and missing endpoints yield null. Excess return in percentage points when multiplied by 100; not a price-ratio line. |
| rs_percentile | `100 * average_tie_rank(return_63) / N` for fresh loaded active common stocks with valid returns. Uses t-1 for setup qualification. Lowest distinct rank is 100/N; singleton =100. N is reported; not a whole-market rank unless the whole market is loaded. |
| sector_rs63 | Equal-weight mean of valid t-1 63d returns for observed known-sector members minus QQQ t-1 63d return. Unknown sectors excluded. No sector index, ETF proxy or historical classification is fabricated. |
| sma10 / 20 / 50 | Arithmetic mean of the latest n closes; n observations required. |
| ema10 / 20 | `alpha=2/(n+1)`, seed at first close, recurrence `E[t]=alpha*C[t]+(1-alpha)*E[t-1]`; output hidden until n observations. Seeded over retained history, so a different history start can change EMA. Input price IDs preserve the chosen history. |
| adr20_pct | Arithmetic mean of the latest 20 values of `100*(H/L-1)`; 20 observations required. |
| atr14 | True range `max(H-L, abs(H-Cprev), abs(L-Cprev))`. First bar TR=H-L. Seed ATR at the arithmetic mean of first 14 TRs, then Wilder recurrence `(13*ATRprev+TR)/14`. Requires 14 observations. |
| avg_volume20 | Mean of latest 20 V values, including t. |
| avg_dollar_volume20 | Mean of latest 20 `C*V` values; a close-based turnover approximation, not sum of intraday traded notional. |
| rvol | `V[t] / mean(V[t-20:t-1])`; excludes the signal bar from baseline. Requires 21 bars. Zero baseline => null. |
| consolidation_high / low | Max H / min L of preceding 20 bars by default, excluding t. Configurable function window. |
| breakout_pivot | The generic indicator's preceding-window consolidation high. The strategy's selected `pivot` can use a different 10–40 session base and is returned separately. |
| volatility_contraction | Mean of latest 5 `(H-L)/C` divided by mean of preceding non-overlapping 15 `(H-L)/C` values. Requires 20 bars; zero denominator => null. |
| volume_contraction | Mean of latest 5 V / mean of preceding non-overlapping 15 V. Requires 20 bars; zero denominator => null. |

## Breakout selection

For each configured base length `b` in [10,40], evaluate the `b` sessions **before** the signal session. Rank alternatives by number of quality checks passed; ties choose the shorter base. Full qualification requires all checks. Daily state is a fresh observation, not an assumed order lifecycle.

1. Prior-session 63d return >=30% **or** 126d return >=50%.
2. Prior-session cross-sectional 63d return percentile >=70.
3. Base first close / close at the start of the preceding 21-session window -1 >=20%. This is an endpoint advance heuristic, not a discretionary chart annotation.
4. Base depth `(max(H)-min(L))/max(H)` <=25%.
5. Mean `(H-L)/C` of last floor(b/2) base bars / first floor(b/2) <=0.85. For odd b, the middle bar is excluded from this comparison.
6. Mean volume of those late/early halves <=0.85.
7. Minimum low of late half >= minimum low of early half *0.98 (2% tolerance for constructive higher lows).
8. SMA10 and SMA20 on t-1 are both strictly higher than on t-2.
9. Prior-session average dollar volume >=$10m.
10. Prior-session price >=$5.

All thresholds and windows above are fields of `BreakoutParameters`. History must have at least 128 sessions (enough for prior-session 126d momentum), valid benchmark alignment and fresh uninterrupted observations.

Pivot = maximum base H. Conditional entry trigger = pivot *1.001 by default. Technical stop = minimum L of the last five base bars. The technical stop is not moved to achieve a desired R multiple. The signal bar cannot redefine its own base or pivot.

- `BUILDING`: quality incomplete, far below trigger, or a price cross lacks the required volume. No eligibility.
- `READY`: fully qualified, price within 5% below trigger and still below it; entry remains conditional.
- `TRIGGERED`: fully qualified, completed daily close >=trigger and RVOL >=1.5, and not extended. A daily signal row records observation time and evidence, explicitly not an execution.
- `EXTENDED`: fully qualified but close >trigger*1.05; new entry ineligible.
- `FAILED`: fully qualified base structure but current close below the fixed technical stop; entry ineligible.

Missing benchmark data forces BUILDING. Market RED/unavailable and risk rejection can make a READY/TRIGGERED candidate ineligible without rewriting its technical status.

## Risk and regime

Planning entry is the conditional trigger for an untriggered setup. After a price cross, use max(trigger, observed close) for budget calculation, avoiding a fictitious fill at the lower pivot. No plan establishes a guaranteed future entry price.

`risk_per_share = entry-stop`; `stop_pct = 100*risk_per_share/entry`. Require positive entry/stop and stop<entry. Default hypothetical target = entry+3*risk_per_share; `upside_pct=100*(target/entry-1)`, `reward_risk=(target-entry)/risk_per_share`. The pure risk function also accepts an explicit objective; objectives <=entry or below minimum RR are rejected.

Default risk budget=0.005*account equity; allocation budget=0.15*equity. GREEN uses multiplier1, YELLOW0.5, RED/unavailable0 for **both** budgets. Max risk shares=floor(risk budget/risk per share); max allocation shares=floor(allocation budget/entry). Final shares=min(both), or zero when ineligible, RR<2, stop_pct>8%, or less than one share fits. Decimal arithmetic governs budget floors. Horizon is configurable from 1–5 sessions, default5. No time-exit execution is simulated in Phase 1. Fees/slippage are not included in sizing.

Regime counts benchmark votes: close>SMA20 **and** close>SMA50 for each of SPY/QQQ/IWM. Default GREEN=3 votes, YELLOW=1–2, RED=0. Vote thresholds are configurable. All three benchmarks must have enough fresh history; otherwise regime is unavailable and new sizing is blocked. Sector ETF evidence does not alter these three benchmark votes.

## Intraday formulas reserved for Phase 2 (not calculated in Phase 1)

- Time-adjusted RVOL: cumulative regular-session volume through completed minute offset m / mean cumulative volume through the same offset across preceding comparable completed sessions. Never scale a full-day average linearly; early-close sessions require a matched schedule. At least 20 eligible historical sessions, no future minutes.
- Five-minute opening range: max high/min low from completed 09:30–09:35 America/New_York bars on a real exchange session. No OR confirmation before those bars are observed. Bar-boundary convention and session completeness must be explicit.
- EP: initial gap `(regular-session open/previous adjusted close-1)>=10%`, unusual same-time volume, verifiable catalyst known by the signal timestamp, prior consolidation and observed OR-high confirmation. A gap alone cannot confirm EP. Earnings surprise/growth are optional evidence with publication cutoffs; missing values stay missing.

These formulas define future acceptance criteria and are not silently approximated with daily bars.
