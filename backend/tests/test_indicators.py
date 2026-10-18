import numpy as np
import pandas as pd
import pytest

from app.indicators import daily_indicators, relative_strength_ranks, sector_relative_strength, wilder_average


@pytest.mark.parametrize("n", [1, 20, 63, 126])
def test_returns_use_exact_trailing_endpoint(bars, n):
    values = daily_indicators(bars)
    assert values[f"return_{n}"].iloc[-1] == pytest.approx(bars.close.iloc[-1] / bars.close.iloc[-1 - n] - 1)
    assert values[f"return_{n}"].iloc[:n].isna().all()


@pytest.mark.parametrize("n", [10, 20, 50])
def test_simple_averages_and_warmup(bars, n):
    result = daily_indicators(bars)[f"sma{n}"]
    assert result.iloc[-1] == pytest.approx(sum(bars.close.iloc[-n:]) / n)
    assert result.iloc[: n - 1].isna().all()


@pytest.mark.parametrize("n", [10, 20])
def test_exponential_average_seed_and_recurrence(bars, n):
    result = daily_indicators(bars)[f"ema{n}"]
    expected = float(bars.close.iloc[0])
    alpha = 2 / (n + 1)
    for close in bars.close.iloc[1:]:
        expected = alpha * close + (1 - alpha) * expected
    assert result.iloc[-1] == pytest.approx(expected)
    assert result.iloc[: n - 1].isna().all()


def test_adr_is_average_of_daily_high_low_ratios(bars):
    out = daily_indicators(bars)
    expected = sum((h / low - 1) * 100 for h, low in zip(bars.high.iloc[-20:], bars.low.iloc[-20:])) / 20
    assert out.adr20_pct.iloc[-1] == pytest.approx(expected)
    assert out.adr20_pct.iloc[:19].isna().all()


def test_atr_wilder_seed_and_gaps(bars):
    bars.loc[bars.index[15], ["open", "high", "low", "close"]] += 20
    out = daily_indicators(bars)
    tr = []
    for i in range(len(bars)):
        r = bars.iloc[i]
        prior = bars.close.iloc[i - 1] if i else r.close
        tr.append(max(r.high - r.low, abs(r.high - prior), abs(r.low - prior)))
    value = sum(tr[:14]) / 14
    assert out.atr14.iloc[13] == pytest.approx(value)
    for x in tr[14:]:
        value = (value * 13 + x) / 14
    assert out.atr14.iloc[-1] == pytest.approx(value)
    assert out.atr14.iloc[:13].isna().all()
    assert wilder_average(pd.Series([1, 2]), 14).isna().all()


def test_average_volumes_and_rvol_excludes_current_volume(bars):
    bars.loc[bars.index[-1], "volume"] = 50_000_000
    out = daily_indicators(bars)
    assert out.avg_volume20.iloc[-1] == pytest.approx(bars.volume.iloc[-20:].mean())
    assert out.avg_dollar_volume20.iloc[-1] == pytest.approx((bars.close * bars.volume).iloc[-20:].mean())
    assert out.rvol.iloc[-1] == pytest.approx(50_000_000 / bars.volume.iloc[-21:-1].mean())
    assert out.rvol.iloc[:20].isna().all()


def test_consolidation_and_pivot_exclude_signal_day(bars):
    bars.loc[bars.index[-1], ["open", "high", "low", "close"]] *= 10
    out = daily_indicators(bars)
    assert out.consolidation_high.iloc[-1] == bars.high.iloc[-21:-1].max()
    assert out.consolidation_low.iloc[-1] == bars.low.iloc[-21:-1].min()
    assert out.breakout_pivot.iloc[-1] == out.consolidation_high.iloc[-1]


def test_contractions_compare_non_overlapping_windows(bars):
    out = daily_indicators(bars)
    r = (bars.high - bars.low) / bars.close
    assert out.volatility_contraction.iloc[-1] == pytest.approx(r.iloc[-5:].mean() / r.iloc[-20:-5].mean())
    assert out.volume_contraction.iloc[-1] == pytest.approx(
        bars.volume.iloc[-5:].mean() / bars.volume.iloc[-20:-5].mean()
    )


def test_qqq_rs_aligns_sessions_without_forward_fill(bars):
    benchmark = pd.Series(np.linspace(100, 150, len(bars)), index=bars.index)
    out = daily_indicators(bars, benchmark)
    expected = bars.close.iloc[-1] / bars.close.iloc[-64] - benchmark.iloc[-1] / benchmark.iloc[-64]
    assert out.rs_qqq63.iloc[-1] == pytest.approx(expected)
    missing = benchmark.drop(bars.index[-64])
    assert pd.isna(daily_indicators(bars, missing).rs_qqq63.iloc[-1])


def test_rs_ranks_ties_missing_and_singleton():
    assert relative_strength_ranks({"A": 0.1, "B": 0.2, "C": 0.2, "D": np.nan}) == pytest.approx(
        {"A": 100 / 3, "B": 250 / 3, "C": 250 / 3}
    )
    assert relative_strength_ranks({"A": 0.2}) == {"A": 100}


def test_sector_rs_equal_weight_known_members_only():
    actual = sector_relative_strength(
        {"A": 0.2, "B": 0.4, "C": 0.9}, {"A": "Tech", "B": "Tech", "C": None}, 0.1
    )
    assert actual == {"Tech": pytest.approx(0.2)}


def test_zero_volume_never_generates_infinity(bars):
    bars["volume"] = 0
    out = daily_indicators(bars)
    assert out.rvol.isna().all()
    assert out.volume_contraction.isna().all()
    assert not np.isinf(out.to_numpy()).any()


def test_future_changes_cannot_change_previous_indicators(bars):
    first = daily_indicators(bars)
    changed = bars.copy()
    changed.loc[changed.index[-10:], ["open", "high", "low", "close"]] *= 2
    changed.loc[changed.index[-10:], "volume"] *= 10
    pd.testing.assert_frame_equal(first.iloc[:-10], daily_indicators(changed).iloc[:-10])


@pytest.mark.parametrize("bad", ["negative", "nan", "duplicate", "unordered", "envelope"])
def test_invalid_data_is_rejected(bars, bad):
    if bad == "negative":
        bars.iloc[0, 0] = -1
    if bad == "nan":
        bars.iloc[0, 0] = np.nan
    if bad == "duplicate":
        bars.index = [bars.index[0]] * len(bars)
    if bad == "unordered":
        bars = bars.iloc[::-1]
    if bad == "envelope":
        bars.iloc[0, bars.columns.get_loc("high")] = 1
    with pytest.raises(ValueError):
        daily_indicators(bars)
