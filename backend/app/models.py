"""Append-only observations; historical provider corrections remain distinguishable."""

from datetime import UTC, date, datetime

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(UTC)


class Stock(Base):
    __tablename__ = "stocks"
    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(250))
    security_type: Mapped[str] = mapped_column(String(20), default="CS")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    exchange: Mapped[str | None] = mapped_column(String(30))
    sector: Mapped[str | None] = mapped_column(String(120))
    industry: Mapped[str | None] = mapped_column(String(250))
    provider: Mapped[str] = mapped_column(String(30))
    reference_as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DailyPrice(Base):
    __tablename__ = "daily_prices"
    __table_args__ = (
        UniqueConstraint("stock_id", "session", "provider", "adjusted", "available_at"),
        CheckConstraint(
            "open > 0 AND low > 0 AND close > 0 AND high >= low AND high >= open AND high >= close AND low <= open AND low <= close AND volume >= 0",
            name="daily_valid_ohlcv",
        ),
        Index("ix_daily_stock_session_available", "stock_id", "session", "available_at"),
    )
    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), index=True)
    session: Mapped[date] = mapped_column(Date)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)
    provider: Mapped[str] = mapped_column(String(30))
    adjusted: Mapped[bool] = mapped_column(Boolean)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    availability_basis: Mapped[str] = mapped_column(String(40), default="observed_at_ingestion")


class MinutePrice(Base):
    __tablename__ = "minute_prices"
    __table_args__ = (UniqueConstraint("stock_id", "timestamp", "provider", "adjusted", "available_at"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), index=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    open: Mapped[float] = mapped_column(Float)
    high: Mapped[float] = mapped_column(Float)
    low: Mapped[float] = mapped_column(Float)
    close: Mapped[float] = mapped_column(Float)
    volume: Mapped[float] = mapped_column(Float)
    provider: Mapped[str] = mapped_column(String(30))
    adjusted: Mapped[bool] = mapped_column(Boolean)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class CorporateAction(Base):
    __tablename__ = "corporate_actions"
    __table_args__ = (UniqueConstraint("stock_id", "provider", "event_key", "available_at"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), index=True)
    event_key: Mapped[str] = mapped_column(String(160))
    kind: Mapped[str] = mapped_column(String(30))
    effective_date: Mapped[date] = mapped_column(Date)
    provider: Mapped[str] = mapped_column(String(30))
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    payload: Mapped[dict] = mapped_column(JSON)


class TechnicalIndicator(Base):
    __tablename__ = "technical_indicators"
    __table_args__ = (UniqueConstraint("stock_id", "as_of", "version", "parameters_hash"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), index=True)
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    session: Mapped[date] = mapped_column(Date)
    version: Mapped[str] = mapped_column(String(30))
    parameters_hash: Mapped[str] = mapped_column(String(64))
    values: Mapped[dict] = mapped_column(JSON)
    provenance: Mapped[dict] = mapped_column(JSON)


class Fundamental(Base):
    __tablename__ = "fundamentals"
    __table_args__ = (UniqueConstraint("stock_id", "period_end", "available_at", "provider"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), index=True)
    period_end: Mapped[date] = mapped_column(Date)
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    provider: Mapped[str] = mapped_column(String(30))
    values: Mapped[dict] = mapped_column(JSON)


class EarningsEvent(Base):
    __tablename__ = "earnings_events"
    __table_args__ = (UniqueConstraint("stock_id", "event_at", "available_at", "provider"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), index=True)
    event_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    provider: Mapped[str] = mapped_column(String(30))
    values: Mapped[dict] = mapped_column(JSON)


class NewsEvent(Base):
    __tablename__ = "news_events"
    __table_args__ = (UniqueConstraint("stock_id", "url", "available_at"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), index=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(String(1000))
    provider: Mapped[str] = mapped_column(String(30))
    catalyst_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    verified_by: Mapped[str | None] = mapped_column(String(120))


class TradeSetup(Base):
    __tablename__ = "trade_setups"
    __table_args__ = (UniqueConstraint("stock_id", "as_of", "strategy", "parameters_hash"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), index=True)
    indicator_id: Mapped[int] = mapped_column(ForeignKey("technical_indicators.id"))
    as_of: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    strategy: Mapped[str] = mapped_column(String(30), default="momentum_breakout")
    status: Mapped[str] = mapped_column(String(20), index=True)
    parameters_hash: Mapped[str] = mapped_column(String(64))
    plan: Mapped[dict] = mapped_column(JSON)
    explanation: Mapped[dict] = mapped_column(JSON)


class TradeSignal(Base):
    __tablename__ = "trade_signals"
    __table_args__ = (UniqueConstraint("setup_id", "observed_at", "kind"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    setup_id: Mapped[int] = mapped_column(ForeignKey("trade_setups.id"), index=True)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    kind: Mapped[str] = mapped_column(String(30))
    evidence: Mapped[dict] = mapped_column(JSON)


class BacktestResult(Base):
    __tablename__ = "backtest_results"
    id: Mapped[int] = mapped_column(primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    strategy: Mapped[str] = mapped_column(String(30))
    parameters: Mapped[dict] = mapped_column(JSON)
    data_manifest: Mapped[dict] = mapped_column(JSON)
    metrics: Mapped[dict] = mapped_column(JSON)
    trades: Mapped[list] = mapped_column(JSON)


class TradeJournal(Base):
    __tablename__ = "trade_journal"
    __table_args__ = (CheckConstraint("shares > 0", name="journal_positive_shares"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(ForeignKey("stocks.id"), index=True)
    signal_id: Mapped[int | None] = mapped_column(ForeignKey("trade_signals.id"))
    entered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    exited_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    shares: Mapped[int] = mapped_column(Integer)
    entry_price: Mapped[float] = mapped_column(Float)
    exit_price: Mapped[float | None] = mapped_column(Float)
    notes: Mapped[str] = mapped_column(Text, default="")
