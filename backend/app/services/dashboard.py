from datetime import UTC, datetime

from sqlalchemy import select

from app.calendar import aware, last_completed_session
from app.models import Stock, TechnicalIndicator, TradeSetup


def saved_dashboard(db, last):
    expected = last_completed_session(datetime.now(UTC)).isoformat()
    if last is None:
        return {
            "as_of": None,
            "session": None,
            "expected_session": expected,
            "stale": True,
            "regime": {"regime": None, "reason": "Ingest data and run a scan"},
            "candidates": [],
            "data_mode": "empty",
            "universe_size": 0,
            "ep": {"available": False, "reason": "Phase 2"},
        }
    rows = db.execute(
        select(TradeSetup, Stock, TechnicalIndicator)
        .join(Stock, Stock.id == TradeSetup.stock_id)
        .join(TechnicalIndicator, TechnicalIndicator.id == TradeSetup.indicator_id)
        .where(TradeSetup.as_of == last)
        .order_by(TradeSetup.id.desc())
    ).all()
    seen, candidates = set(), []
    for setup, stock, indicator in rows:
        if stock.symbol in seen:
            continue
        seen.add(stock.symbol)
        candidates.append(
            {
                "symbol": stock.symbol,
                "name": stock.name,
                "sector": stock.sector,
                "session": indicator.session.isoformat(),
                "provider": stock.provider,
                "indicators": indicator.values,
                **setup.explanation,
                "plan": setup.plan,
            }
        )
    provenance = rows[0][2].provenance
    session = rows[0][2].session.isoformat()
    return {
        "as_of": aware(last).isoformat(),
        "session": session,
        "expected_session": expected,
        "stale": session != expected,
        "regime": provenance["regime_evidence"],
        "parameters": provenance["parameters"],
        "universe_size": len(seen),
        "rs_observations": len(provenance["universe_symbols"]),
        "candidates": sorted(candidates, key=lambda x: (-x["score"], x["symbol"])),
        "data_mode": "synthetic" if any(c["provider"] == "demo" for c in candidates) else "provider",
        "ep": {
            "available": False,
            "reason": "Phase 2: intraday confirmation and verified catalysts required",
        },
    }
