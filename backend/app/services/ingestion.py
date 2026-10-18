from datetime import UTC, date, datetime

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.calendar import completed_sessions
from app.indicators import validate_bars
from app.models import DailyPrice, Stock
from app.providers.base import MarketDataProvider, StockReference


def save_reference(db: Session, ref: StockReference, provider: str, observed_at: datetime) -> Stock:
    incompatible = Stock.provider != "demo" if provider == "demo" else Stock.provider == "demo"
    if db.scalar(select(Stock.id).where(incompatible).limit(1)) is not None:
        raise ValueError(
            "Use a separate database for demo data; synthetic and provider observations cannot mix"
        )
    stock = db.scalar(select(Stock).where(Stock.symbol == ref.symbol))
    if stock and stock.provider != provider:
        raise ValueError(f"{ref.symbol} belongs to {stock.provider}; use a separate database for demo data")
    if stock is None:
        stock = Stock(symbol=ref.symbol)
        db.add(stock)
    for field in ("name", "security_type", "active", "exchange", "sector", "industry"):
        setattr(stock, field, getattr(ref, field))
    stock.provider = provider
    stock.reference_as_of = observed_at
    db.flush()
    return stock


def ingest_daily(
    db: Session,
    provider: MarketDataProvider,
    symbols: list[str],
    start: date,
    end: date,
    adjusted: bool = True,
    observed_at: datetime | None = None,
) -> dict:
    supplied_observation = observed_at
    observed_at = observed_at or datetime.now(UTC)
    if observed_at.tzinfo is None or start > end:
        raise ValueError("Valid date range and timezone-aware observed_at required")
    observed_at = observed_at.astimezone(UTC)
    complete = completed_sessions(start, end, observed_at)
    inserted, unchanged, excluded = 0, 0, 0
    for symbol in dict.fromkeys(symbols):
        ref = provider.reference(symbol)
        stock = save_reference(db, ref, provider.name, observed_at)
        bars = provider.daily_bars(symbol, start, end, adjusted)
        received_at = supplied_observation.astimezone(UTC) if supplied_observation else datetime.now(UTC)
        if bars:
            frame = pd.DataFrame([vars(b) for b in bars]).set_index("session")
            validate_bars(frame)
        existing = db.scalars(
            select(DailyPrice)
            .where(
                DailyPrice.stock_id == stock.id,
                DailyPrice.provider == provider.name,
                DailyPrice.adjusted == adjusted,
                DailyPrice.session >= start,
                DailyPrice.session <= end,
            )
            .order_by(DailyPrice.available_at, DailyPrice.id)
        ).all()
        latest = {b.session: b for b in existing}
        for bar in bars:
            if bar.session not in complete:
                excluded += 1
                continue
            prior = latest.get(bar.session)
            if prior and all(
                getattr(prior, f) == getattr(bar, f) for f in ("open", "high", "low", "close", "volume")
            ):
                unchanged += 1
                continue
            db.add(
                DailyPrice(
                    stock_id=stock.id,
                    **vars(bar),
                    provider=provider.name,
                    adjusted=adjusted,
                    available_at=received_at,
                    ingested_at=received_at,
                    availability_basis="synthetic" if provider.name == "demo" else "observed_at_ingestion",
                )
            )
            inserted += 1
    db.flush()
    return {
        "inserted": inserted,
        "unchanged": unchanged,
        "excluded_incomplete_or_non_session": excluded,
        "provider": provider.name,
        "observed_at": observed_at.isoformat(),
    }
