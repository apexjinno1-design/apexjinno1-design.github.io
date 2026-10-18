from datetime import UTC, date, datetime, timedelta

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.calendar import completed_sessions, last_completed_session
from app.db import get_db
from app.demo import seed_demo
from app.main import app
from app.models import DailyPrice, Stock, TechnicalIndicator, TradeSetup, TradeSignal
from app.providers.base import PriceBar, StockReference
from app.providers.massive import MassiveProvider, ProviderError
from app.risk import RiskParameters
from app.screener import BreakoutParameters
from app.services.ingestion import ingest_daily
from app.services.research import price_frame, scan


def test_exchange_holidays_half_days_and_dst():
    assert completed_sessions(date(2025, 7, 4), date(2025, 7, 4), datetime(2025, 7, 5, tzinfo=UTC)) == set()
    half_day = date(2025, 11, 28)
    assert not completed_sessions(half_day, half_day, datetime(2025, 11, 28, 17, 59, tzinfo=UTC))
    assert completed_sessions(half_day, half_day, datetime(2025, 11, 28, 18, 0, tzinfo=UTC)) == {half_day}
    assert last_completed_session(datetime(2025, 3, 7, 20, 30, tzinfo=UTC)) == date(2025, 3, 6)
    assert last_completed_session(datetime(2025, 3, 10, 20, 30, tzinfo=UTC)) == date(2025, 3, 10)


def test_calendar_supports_multi_year_historical_ingestion():
    sessions = completed_sessions(date(2016, 10, 18), date(2026, 10, 16), datetime(2026, 10, 17, tzinfo=UTC))
    assert date(2016, 10, 18) in sessions and date(2026, 10, 16) in sessions
    assert len(sessions) > 2500


class FixtureProvider:
    name = "fixture"

    def __init__(self):
        self.close = 100

    def reference(self, symbol):
        return StockReference(symbol, symbol)

    def daily_bars(self, symbol, start, end, adjusted=True):
        return [
            PriceBar(date(2026, 10, 15), 100, 110, 90, self.close, 1000),
            PriceBar(date(2026, 10, 16), 101, 111, 91, 102, 1000),
        ]


def test_ingestion_revisions_idempotence_and_incomplete_session(db):
    provider = FixtureProvider()
    t = datetime(2026, 10, 16, 18, tzinfo=UTC)
    result = ingest_daily(db, provider, ["ABC"], date(2026, 10, 15), date(2026, 10, 16), observed_at=t)
    assert result["inserted"] == 1 and result["excluded_incomplete_or_non_session"] == 1
    assert (
        ingest_daily(db, provider, ["ABC"], date(2026, 10, 15), date(2026, 10, 16), observed_at=t)[
            "unchanged"
        ]
        == 1
    )
    stock = db.scalar(select(Stock))
    assert price_frame(db, stock, t - timedelta(seconds=1)).empty
    provider.close = 105
    ingest_daily(
        db, provider, ["ABC"], date(2026, 10, 15), date(2026, 10, 16), observed_at=t + timedelta(minutes=1)
    )
    assert db.scalar(select(func.count()).select_from(DailyPrice)) == 2
    assert price_frame(db, stock, t).close.iloc[-1] == 100
    assert price_frame(db, stock, t + timedelta(minutes=2)).close.iloc[-1] == 105
    assert price_frame(db, stock, t, adjusted=False).empty


def test_synthetic_and_real_provider_data_cannot_mix(db, as_of):
    seed_demo(db, as_of)
    p = FixtureProvider()
    with pytest.raises(ValueError, match="separate database"):
        ingest_daily(db, p, ["DEMOA"], date(2026, 10, 15), date(2026, 10, 16), observed_at=as_of)
    with pytest.raises(ValueError, match="separate database"):
        ingest_daily(db, p, ["NEWREAL"], date(2026, 10, 15), date(2026, 10, 16), observed_at=as_of)


def test_offset_timestamps_replay_the_same_observations(db, as_of):
    from datetime import timezone

    shifted = as_of.astimezone(timezone(timedelta(hours=10)))
    seed_demo(db, shifted)
    canonical = scan(db, as_of, BreakoutParameters(), RiskParameters())
    offset = scan(db, shifted, BreakoutParameters(), RiskParameters())
    assert canonical == offset
    assert db.scalar(select(func.count()).select_from(TechnicalIndicator)) == 6


def test_scan_snapshots_signals_and_repeatability(db, as_of):
    seed_demo(db, as_of)
    p, risk = BreakoutParameters(), RiskParameters()
    result = scan(db, as_of, p, risk)
    assert result["universe_size"] == 6
    assert result["regime"]["regime"] == "GREEN"
    assert all(c["symbol"].startswith("DEMO") for c in result["candidates"])
    triggered = [c for c in result["candidates"] if c["status"] == "TRIGGERED"]
    assert triggered, [(c["symbol"], c["checks"]) for c in result["candidates"]]
    assert db.scalar(select(func.count()).select_from(TradeSignal)) == len(triggered)
    assert scan(db, as_of, p, risk)["candidates"] == result["candidates"]
    assert db.scalar(select(func.count()).select_from(TechnicalIndicator)) == 6
    assert db.scalar(select(func.count()).select_from(TradeSetup)) == 6
    assert db.scalar(select(TechnicalIndicator)).provenance["price_ids"]
    before = scan(db, as_of - timedelta(seconds=1), p, risk)
    assert not before["candidates"]


def test_stale_benchmark_blocks_regime_and_positions(db, as_of):
    seed_demo(db, as_of)
    qqq = db.scalar(select(Stock).where(Stock.symbol == "QQQ"))
    db.delete(
        db.scalar(select(DailyPrice).where(DailyPrice.stock_id == qqq.id).order_by(DailyPrice.session.desc()))
    )
    db.flush()
    result = scan(db, as_of, BreakoutParameters(), RiskParameters())
    assert result["regime"]["regime"] is None
    assert "QQQ" in result["excluded_stale_symbols"]
    assert all(not c["plan"]["eligible"] and not c["qualified"] for c in result["candidates"])


def test_gapped_history_does_not_silently_change_return_horizon(db, as_of):
    seed_demo(db, as_of)
    stock = db.scalar(select(Stock).where(Stock.symbol == "DEMOA"))
    bar = db.scalars(
        select(DailyPrice).where(DailyPrice.stock_id == stock.id).order_by(DailyPrice.session)
    ).all()[30]
    db.delete(bar)
    db.flush()
    result = scan(db, as_of, BreakoutParameters(), RiskParameters())
    assert "DEMOA" in result["excluded_gapped_symbols"]
    assert "DEMOA" not in [c["symbol"] for c in result["candidates"]]


def test_db_foreign_key_integrity(db, as_of):
    db.add(
        DailyPrice(
            stock_id=999,
            session=date(2026, 10, 15),
            open=100,
            high=101,
            low=99,
            close=100,
            volume=1,
            provider="x",
            adjusted=True,
            available_at=as_of,
        )
    )
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_provider_auth_pagination_and_daily_timestamp():
    calls = []

    def handler(request):
        calls.append(request)
        assert request.headers["Authorization"] == "Bearer test-only"
        assert "apiKey" not in request.url.query.decode()
        if "aggs" in request.url.path:
            return httpx.Response(
                200,
                json={"results": [{"t": 1792108800000, "o": 100, "h": 110, "l": 90, "c": 105, "v": 1000}]},
            )
        if len(calls) == 1:
            return httpx.Response(
                200,
                json={
                    "results": [{"ticker": "ABC", "name": "ABC", "type": "CS"}],
                    "next_url": "https://api.massive.com/v3/reference/tickers?cursor=2",
                },
            )
        return httpx.Response(200, json={"results": [{"ticker": "DEF", "type": "CS"}]})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        provider = MassiveProvider("test-only", client)
        assert [s.symbol for s in provider.active_stocks()] == ["ABC", "DEF"]
        assert provider.daily_bars("ABC", date(2026, 10, 15), date(2026, 10, 16))[0].close == 105
    assert len(calls) == 3


@pytest.mark.parametrize(
    "url",
    [
        "http://api.massive.com/x",
        "https://evil.example/x",
        "https://api.massive.com.evil.example/x",
        "https://api.massive.com:444/x",
    ],
)
def test_provider_never_leaks_key_to_pagination_destination(url):
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: pytest.fail("Must not make a request"))
    ) as client:
        with pytest.raises(ProviderError, match="destination"):
            MassiveProvider("test-only", client)._get(url)


def test_provider_entitlement_error_is_sanitized():
    def handler(request):
        return httpx.Response(403, json={"error": "test-only must never appear"})

    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ProviderError) as error:
            MassiveProvider("test-only", client).active_stocks()
    assert "403" in str(error.value) and "test-only" not in str(error.value)


def test_api_end_to_end_and_validation(db, as_of):
    seed_demo(db, as_of)
    db.commit()
    app.dependency_overrides[get_db] = lambda: db
    try:
        with TestClient(app) as client:
            assert client.get("/api/health").status_code == 200
            assert client.get("/api/dashboard").json()["data_mode"] == "empty"
            response = client.post("/api/screen/breakouts", json={"as_of": as_of.isoformat()})
            assert response.status_code == 200, response.text
            assert len(response.json()["candidates"]) == 6
            dashboard = client.get("/api/dashboard").json()
            assert dashboard["data_mode"] == "synthetic" and len(dashboard["candidates"]) == 6
            detail = client.get("/api/stocks/DEMOA").json()
            assert len(detail["bars"]) == 260
            assert detail["snapshot"]["provenance"]["price_ids"]
            assert client.get("/api/stocks/UNKNOWN").status_code == 404
            assert not client.get("/api/backtests").json()["available"]
            assert (
                client.post("/api/screen/breakouts", json={"as_of": "2026-10-16T21:00:00"}).status_code == 422
            )
            assert (
                client.post("/api/screen/breakouts", json={"risk": {"account_equity": -1}}).status_code == 422
            )
            assert (
                client.post(
                    "/api/ingest/daily",
                    json={"symbols": ["../bad"], "start": "2026-10-01", "end": "2026-10-16"},
                ).status_code
                == 422
            )
    finally:
        app.dependency_overrides.clear()
