"""Deterministic synthetic fixtures. No real tickers, market observations, or performance claims."""

from datetime import UTC, date, datetime, timedelta

import numpy as np

from app.calendar import completed_sessions, last_completed_session
from app.providers.base import PriceBar, StockReference
from app.services.ingestion import ingest_daily


class DemoProvider:
    name = "demo"
    symbols = ("SPY", "QQQ", "IWM", "DEMOA", "DEMOB", "DEMOC", "DEMOD", "DEMOE", "DEMOF")

    def __init__(self, as_of: datetime):
        end = last_completed_session(as_of)
        self.sessions = sorted(completed_sessions(end - timedelta(days=450), end, as_of))[-260:]

    def reference(self, symbol: str) -> StockReference:
        if symbol not in self.symbols:
            raise ValueError("Unknown synthetic symbol")
        return StockReference(
            symbol,
            f"Synthetic {symbol}",
            "ETF" if symbol in ("SPY", "QQQ", "IWM") else "CS",
            sector=None if symbol in ("SPY", "QQQ", "IWM") else "Synthetic technology",
        )

    def active_stocks(self) -> list[StockReference]:
        return [self.reference(s) for s in self.symbols if s.startswith("DEMO")]

    def daily_bars(self, symbol: str, start: date, end: date, adjusted: bool = True) -> list[PriceBar]:
        idx = self.symbols.index(symbol)
        n = len(self.sessions)
        x = np.arange(n)
        close = (30 + idx * 9) * np.exp((0.001 if idx < 3 else 0.009 + (8 - idx) * 0.0007) * x)
        close *= 1 + 0.003 * np.sin(x / 4)
        spread = np.full(n, 0.02)
        volume = np.full(n, 2_000_000 + idx * 100_000, dtype=float)
        if idx >= 3:
            anchor = close[-22]
            # Short tight bases with rising averages, contracting ranges and turnover.
            close[-21:-1] = anchor * np.linspace(0.99, 1.025, 20)
            spread[-21:-1] = np.linspace(0.028, 0.005, 20)
            volume[-21:-1] *= np.linspace(0.9, 0.35, 20)
            pivot = max(close[-21:-1] * (1 + spread[-21:-1]))
            close[-1] = pivot * {3: 1.012, 4: 0.99, 5: 1.09, 6: 0.94, 7: 0.98, 8: 0.995}[idx]
            volume[-1] *= 3 if idx in (3, 5) else 0.8
        return [
            PriceBar(d, float(c * 0.999), float(c * (1 + w)), float(c * (1 - w)), float(c), float(v))
            for d, c, w, v in zip(self.sessions, close, spread, volume, strict=True)
            if start <= d <= end
        ]


def seed_demo(db, as_of: datetime | None = None) -> dict:
    at = as_of or datetime.now(UTC)
    provider = DemoProvider(at)
    return ingest_daily(
        db, provider, list(provider.symbols), provider.sessions[0], provider.sessions[-1], observed_at=at
    )
