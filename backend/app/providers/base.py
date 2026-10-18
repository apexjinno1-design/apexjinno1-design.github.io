from dataclasses import dataclass
from datetime import date
from typing import Protocol


@dataclass(frozen=True)
class StockReference:
    symbol: str
    name: str
    security_type: str = "CS"
    active: bool = True
    exchange: str | None = None
    sector: str | None = None
    industry: str | None = None


@dataclass(frozen=True)
class PriceBar:
    session: date
    open: float
    high: float
    low: float
    close: float
    volume: float


class MarketDataProvider(Protocol):
    name: str

    def active_stocks(self) -> list[StockReference]: ...
    def reference(self, symbol: str) -> StockReference: ...
    def daily_bars(self, symbol: str, start: date, end: date, adjusted: bool = True) -> list[PriceBar]: ...
