import hashlib
import json
from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.calendar import aware, completed_sessions, last_completed_session
from app.indicators import (
    VERSION,
    daily_indicators,
    json_values,
    relative_strength_ranks,
    sector_relative_strength,
)
from app.models import DailyPrice, Stock, TechnicalIndicator, TradeSetup, TradeSignal
from app.risk import RiskParameters
from app.screener import BreakoutParameters, RegimeParameters, detect_breakout, market_regime

BENCHMARKS = ("SPY", "QQQ", "IWM")
SECTOR_ETFS = ("XLB", "XLC", "XLE", "XLF", "XLI", "XLK", "XLP", "XLRE", "XLU", "XLV", "XLY")


def price_frame(db: Session, stock: Stock, as_of: datetime, adjusted: bool = True) -> pd.DataFrame:
    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone aware")
    as_of = as_of.astimezone(UTC)
    rows = db.scalars(
        select(DailyPrice)
        .where(
            DailyPrice.stock_id == stock.id,
            DailyPrice.available_at <= as_of,
            DailyPrice.provider == stock.provider,
            DailyPrice.adjusted == adjusted,
            DailyPrice.session >= as_of.date() - timedelta(days=760),
            DailyPrice.session <= as_of.date(),
        )
        .order_by(DailyPrice.session, DailyPrice.available_at, DailyPrice.id)
    ).all()
    if not rows:
        return pd.DataFrame()
    complete = completed_sessions(rows[0].session, rows[-1].session, as_of)
    latest = {r.session: r for r in rows if r.session in complete}
    if not latest:
        return pd.DataFrame()
    return (
        pd.DataFrame(
            [
                {
                    "session": d,
                    **{k: getattr(r, k) for k in ("open", "high", "low", "close", "volume")},
                    "price_id": r.id,
                    "available_at": aware(r.available_at).isoformat(),
                }
                for d, r in latest.items()
            ]
        )
        .set_index("session")
        .sort_index()
    )


def scan(
    db: Session,
    as_of: datetime,
    breakout: BreakoutParameters,
    risk: RiskParameters,
    regime_parameters: RegimeParameters | None = None,
) -> dict:
    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone aware")
    as_of = as_of.astimezone(UTC)
    stocks = db.scalars(select(Stock).order_by(Stock.symbol)).all()
    raw = {s.symbol: price_frame(db, s, as_of) for s in stocks}
    raw = {k: v for k, v in raw.items() if not v.empty}
    expected = last_completed_session(as_of)
    current = {k: v for k, v in raw.items() if v.index[-1] == expected}
    # A row count must represent exchange sessions, not silently skip missing bars.
    gaps = {k for k, v in current.items() if set(v.index) != completed_sessions(v.index[0], expected, as_of)}
    current = {k: v for k, v in current.items() if k not in gaps}
    benchmark = current.get("QQQ")
    frames = {
        k: daily_indicators(
            v[["open", "high", "low", "close", "volume"]], benchmark.close if benchmark is not None else None
        )
        for k, v in current.items()
    }
    regime = market_regime(
        {s: frames[s] for s in (*BENCHMARKS, *SECTOR_ETFS) if s in frames}, regime_parameters
    )
    candidates = [s for s in stocks if s.active and s.security_type == "CS" and s.symbol in frames]
    # Ranks used for quality precede the signal session to avoid moving the goalposts on a breakout day.
    momentum = {
        s.symbol: float(frames[s.symbol].iloc[-2].return_63)
        for s in candidates
        if len(frames[s.symbol]) >= 65 and pd.notna(frames[s.symbol].iloc[-2].return_63)
    }
    ranks = relative_strength_ranks(momentum)
    sector_rs = {}
    if benchmark is not None and len(benchmark) >= 65:
        q = benchmark.close.iloc[-2] / benchmark.close.iloc[-65] - 1
        sector_rs = sector_relative_strength(momentum, {s.symbol: s.sector for s in candidates}, q)
    config = {
        "breakout": breakout.model_dump(),
        "risk": risk.model_dump(),
        "regime": (regime_parameters or RegimeParameters()).model_dump(),
    }
    fingerprint = hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()
    output = []
    for stock in candidates:
        symbol, frame = stock.symbol, frames[stock.symbol]
        snapshot = json_values(frame.iloc[-1])
        snapshot["rs_percentile"] = ranks.get(symbol)
        snapshot["sector_rs63"] = sector_rs.get(stock.sector)
        result = detect_breakout(frame, ranks.get(symbol), regime["regime"], breakout, risk)
        # Missing benchmark history blocks qualifications, not just position size.
        if benchmark is None or snapshot["rs_qqq63"] is None:
            result["qualified"] = False
            result["status"] = "BUILDING"
            result["checks"]["benchmark_history"] = False
            result["plan"]["eligible"] = False
            result["plan"]["shares"] = 0
        provenance = {
            "provider": stock.provider,
            "adjusted": True,
            "availability": "synthetic" if stock.provider == "demo" else "observed_at_ingestion",
            "price_ids": [int(v) for v in raw[symbol].price_id],
            "benchmark": "QQQ",
            "benchmark_price_ids": [int(v) for v in benchmark.price_id] if benchmark is not None else [],
            "parameters": config,
            "universe_symbols": sorted(momentum),
            "sector": stock.sector,
            "regime_evidence": regime,
            "note": "Current active universe; not a survivorship-free historical backtest",
        }
        indicator = db.scalar(
            select(TechnicalIndicator).where(
                TechnicalIndicator.stock_id == stock.id,
                TechnicalIndicator.as_of == as_of,
                TechnicalIndicator.version == VERSION,
                TechnicalIndicator.parameters_hash == fingerprint,
            )
        )
        if indicator is None:
            indicator = TechnicalIndicator(
                stock_id=stock.id,
                as_of=as_of,
                session=frame.index[-1],
                version=VERSION,
                parameters_hash=fingerprint,
                values=snapshot,
                provenance=provenance,
            )
            db.add(indicator)
            db.flush()
            setup = TradeSetup(
                stock_id=stock.id,
                indicator_id=indicator.id,
                as_of=as_of,
                strategy="momentum_breakout",
                status=result["status"],
                parameters_hash=fingerprint,
                plan=result["plan"],
                explanation={k: v for k, v in result.items() if k != "plan"},
            )
            db.add(setup)
            db.flush()
            if result["status"] == "TRIGGERED":
                db.add(
                    TradeSignal(
                        setup_id=setup.id,
                        observed_at=as_of,
                        kind="daily_close_confirmation",
                        evidence={
                            "close": snapshot["close"],
                            "rvol": snapshot["rvol"],
                            "entry_trigger": result["entry_trigger"],
                            "not_a_fill": True,
                        },
                    )
                )
        output.append(
            {
                "symbol": symbol,
                "name": stock.name,
                "sector": stock.sector,
                "session": frame.index[-1].isoformat(),
                "provider": stock.provider,
                "indicators": snapshot,
                **result,
            }
        )
    db.flush()
    return {
        "as_of": as_of.isoformat(),
        "session": expected.isoformat(),
        "regime": regime,
        "parameters": config,
        "universe_size": len(candidates),
        "rs_observations": len(momentum),
        "excluded_stale_symbols": sorted(set(raw) - set(current) - gaps),
        "excluded_gapped_symbols": sorted(gaps),
        "missing_sector_etfs": [s for s in SECTOR_ETFS if s not in frames],
        "candidates": sorted(output, key=lambda x: (-x["score"], x["symbol"])),
        "data_mode": "synthetic" if any(s.provider == "demo" for s in candidates) else "provider",
        "ep": {"available": False, "reason": "Phase 2: intraday volume and verified catalysts required"},
    }


def stock_detail(db: Session, symbol: str, as_of: datetime) -> dict | None:
    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone aware")
    as_of = as_of.astimezone(UTC)
    stock = db.scalar(select(Stock).where(Stock.symbol == symbol))
    if stock is None:
        return None
    raw = price_frame(db, stock, as_of)
    if raw.empty:
        return {"symbol": symbol, "name": stock.name, "bars": [], "snapshot": None}
    indicators = daily_indicators(raw[["open", "high", "low", "close", "volume"]])
    bars = []
    for day, row in indicators.iterrows():
        bars.append(
            {
                "time": day.isoformat(),
                **{k: float(row[k]) for k in ("open", "high", "low", "close", "volume")},
                **{k: float(row[k]) if np.isfinite(row[k]) else None for k in ("sma10", "sma20", "sma50")},
            }
        )
    observation = db.scalar(
        select(TechnicalIndicator)
        .where(TechnicalIndicator.stock_id == stock.id, TechnicalIndicator.as_of <= as_of)
        .order_by(TechnicalIndicator.as_of.desc(), TechnicalIndicator.id.desc())
    )
    setup = (
        db.scalar(select(TradeSetup).where(TradeSetup.indicator_id == observation.id))
        if observation
        else None
    )
    return {
        "symbol": symbol,
        "name": stock.name,
        "sector": stock.sector,
        "provider": stock.provider,
        "adjusted": True,
        "bars": bars,
        "as_of": as_of.isoformat(),
        "last_session": bars[-1]["time"],
        "expected_session": last_completed_session(as_of).isoformat(),
        "snapshot": {
            "as_of": aware(observation.as_of).isoformat(),
            "session": observation.session.isoformat(),
            "indicators": observation.values,
            "provenance": observation.provenance,
            "status": setup.status if setup else None,
            "plan": setup.plan if setup else None,
            "explanation": setup.explanation if setup else None,
        }
        if observation
        else None,
        "catalysts": [],
        "catalyst_note": "News ingestion and verification arrive in Phase 2; none verified here",
    }
