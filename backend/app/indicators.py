"""Pure trailing calculations. See docs/indicators.md for units and warm-up rules."""

import numpy as np
import pandas as pd

OHLCV = ["open", "high", "low", "close", "volume"]
VERSION = "daily-v1"


def validate_bars(bars: pd.DataFrame) -> None:
    if not set(OHLCV) <= set(bars.columns):
        raise ValueError("Missing OHLCV columns")
    if not bars.index.is_unique or not bars.index.is_monotonic_increasing:
        raise ValueError("Bars must have unique, increasing session indices")
    v = bars[OHLCV].astype(float)
    if not np.isfinite(v.to_numpy()).all():
        raise ValueError("OHLCV must be finite")
    if (v[["open", "high", "low", "close"]] <= 0).any().any() or (v.volume < 0).any():
        raise ValueError("Prices must be positive and volume nonnegative")
    if (
        (v.high < v[["open", "close", "low"]].max(axis=1))
        | (v.low > v[["open", "close", "high"]].min(axis=1))
    ).any():
        raise ValueError("Invalid OHLC envelope")


def wilder_average(series: pd.Series, period: int) -> pd.Series:
    result = pd.Series(np.nan, index=series.index, dtype=float)
    if len(series) >= period:
        result.iloc[period - 1] = series.iloc[:period].mean()
        for i in range(period, len(series)):
            result.iloc[i] = (result.iloc[i - 1] * (period - 1) + series.iloc[i]) / period
    return result


def daily_indicators(
    bars: pd.DataFrame, benchmark: pd.Series | None = None, base_sessions: int = 20
) -> pd.DataFrame:
    validate_bars(bars)
    if base_sessions < 2:
        raise ValueError("base_sessions must be at least 2")
    out = bars.copy().astype(float)
    close, high, low, volume = (out[x] for x in ("close", "high", "low", "volume"))
    for n in (1, 20, 63, 126):
        out[f"return_{n}"] = close.pct_change(n, fill_method=None)
    for n in (10, 20, 50):
        out[f"sma{n}"] = close.rolling(n, min_periods=n).mean()
    for n in (10, 20):
        out[f"ema{n}"] = close.ewm(span=n, adjust=False, min_periods=n).mean()
    out["adr20_pct"] = ((high / low - 1) * 100).rolling(20, min_periods=20).mean()
    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(
        axis=1
    )
    out["atr14"] = wilder_average(tr, 14)
    out["avg_volume20"] = volume.rolling(20, min_periods=20).mean()
    out["avg_dollar_volume20"] = (close * volume).rolling(20, min_periods=20).mean()
    baseline = volume.shift(1).rolling(20, min_periods=20).mean()
    out["rvol"] = volume / baseline.replace(0, np.nan)
    out["consolidation_high"] = high.shift().rolling(base_sessions, min_periods=base_sessions).max()
    out["consolidation_low"] = low.shift().rolling(base_sessions, min_periods=base_sessions).min()
    out["breakout_pivot"] = out.consolidation_high
    ranges = (high - low) / close
    out["volatility_contraction"] = ranges.rolling(5).mean() / ranges.shift(5).rolling(15).mean().replace(
        0, np.nan
    )
    out["volume_contraction"] = volume.rolling(5).mean() / volume.shift(5).rolling(15).mean().replace(
        0, np.nan
    )
    if benchmark is not None:
        # Reindex before shifting: comparisons share the stock's exact endpoint sessions.
        b = benchmark.reindex(close.index)
        out["rs_qqq63"] = out.return_63 - b.pct_change(63, fill_method=None)
    else:
        out["rs_qqq63"] = np.nan
    return out.replace([np.inf, -np.inf], np.nan)


def relative_strength_ranks(values: dict[str, float]) -> dict[str, float]:
    s = pd.Series(values, dtype=float).dropna()
    return (s.rank(method="average", pct=True) * 100).to_dict()


def sector_relative_strength(
    returns: dict[str, float], sectors: dict[str, str | None], benchmark_return: float
) -> dict[str, float]:
    """Equal-weight observed sector membership; not an ETF or historical sector index."""
    frame = pd.DataFrame({"return": pd.Series(returns), "sector": pd.Series(sectors)}).dropna()
    return (frame.groupby("sector")["return"].mean() - benchmark_return).to_dict()


def json_values(row: pd.Series) -> dict:
    return {k: float(v) if pd.notna(v) and np.isfinite(v) else None for k, v in row.items()}
