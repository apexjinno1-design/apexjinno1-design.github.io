import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import AwareDatetime
from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal, get_db
from app.models import Stock, TradeSetup
from app.providers.massive import MassiveProvider, ProviderError
from app.schemas import IngestRequest, ScanRequest
from app.services.ingestion import ingest_daily, save_reference
from app.services.research import scan, stock_detail

log = logging.getLogger(__name__)


def scheduled_refresh():
    settings = get_settings()
    provider = None
    try:
        request = IngestRequest(
            symbols=settings.ingest_symbols.split(","),
            start=datetime.now(UTC).date() - timedelta(days=550),
            end=datetime.now(UTC).date(),
        )
        provider = MassiveProvider(settings.massive_api_key.get_secret_value())
        with SessionLocal() as db, db.begin():
            ingest_daily(db, provider, request.symbols, request.start, request.end)
            scan(db, datetime.now(UTC), ScanRequest().breakout, ScanRequest().risk)
    except (ProviderError, ValueError, SQLAlchemyError):
        log.error("Scheduled refresh failed; check provider access, schema and configured symbols")
    finally:
        if provider:
            provider.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = BackgroundScheduler(timezone="UTC")
    if get_settings().scheduler_enabled and not get_settings().demo_mode:
        # 22:30 UTC is after both EST/EDT closes. The calendar still rejects non-sessions.
        scheduler.add_job(
            scheduled_refresh,
            "cron",
            day_of_week="mon-fri",
            hour=22,
            minute=30,
            max_instances=1,
            coalesce=True,
        )
        scheduler.start()
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Momentum Research API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        db.scalar(select(func.count()).select_from(Stock))
    except SQLAlchemyError:
        raise HTTPException(503, "Database unavailable or migrations not applied") from None
    return {
        "status": "ok",
        "demo_mode": get_settings().demo_mode,
        "provider_key_configured": bool(get_settings().massive_api_key.get_secret_value()),
    }


def get_provider() -> MassiveProvider:
    if get_settings().demo_mode:
        raise HTTPException(409, "Use a separate database with DEMO_MODE=false for provider ingestion")
    try:
        return MassiveProvider(get_settings().massive_api_key.get_secret_value())
    except ProviderError as exc:
        raise HTTPException(503, str(exc)) from None


@app.post("/api/ingest/universe")
def ingest_universe(db: Session = Depends(get_db)):
    provider = get_provider()
    try:
        references = provider.active_stocks()
        now = datetime.now(UTC)
        for ref in references:
            save_reference(db, ref, provider.name, now)
        db.commit()
        return {
            "upserted": len(references),
            "provider": provider.name,
            "note": "Active common-stock reference universe; ingest history separately in batches of up to 100",
        }
    except (ProviderError, ValueError) as exc:
        db.rollback()
        raise HTTPException(502, str(exc)) from None
    finally:
        provider.close()


@app.post("/api/ingest/daily")
def ingest(request: IngestRequest, db: Session = Depends(get_db)):
    provider = get_provider()
    try:
        result = ingest_daily(db, provider, request.symbols, request.start, request.end, request.adjusted)
        db.commit()
        return result
    except (ProviderError, ValueError) as exc:
        db.rollback()
        raise HTTPException(502, str(exc)) from None
    finally:
        provider.close()


@app.get("/api/stocks")
def stocks(
    limit: int = Query(100, ge=1, le=1000), offset: int = Query(0, ge=0), db: Session = Depends(get_db)
):
    rows = db.scalars(select(Stock).order_by(Stock.symbol).offset(offset).limit(limit)).all()
    return [
        {
            "symbol": s.symbol,
            "name": s.name,
            "type": s.security_type,
            "active": s.active,
            "sector": s.sector,
            "industry": s.industry,
            "provider": s.provider,
        }
        for s in rows
    ]


@app.post("/api/screen/breakouts")
def screen(request: ScanRequest, db: Session = Depends(get_db)):
    result = scan(db, request.as_of or datetime.now(UTC), request.breakout, request.risk, request.regime)
    db.commit()
    return result


@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):
    # Read-only: no scan side effects on GET. Snapshots created by POST screen or CLI.
    last = db.scalar(select(TradeSetup.as_of).order_by(TradeSetup.as_of.desc()).limit(1))
    from app.services.dashboard import saved_dashboard

    return saved_dashboard(db, last)


@app.get("/api/stocks/{symbol}")
def detail(symbol: str, as_of: AwareDatetime | None = None, db: Session = Depends(get_db)):
    if as_of and as_of > datetime.now(UTC):
        raise HTTPException(422, "as_of cannot be in the future")
    result = stock_detail(db, symbol.upper(), as_of or datetime.now(UTC))
    if result is None:
        raise HTTPException(404, "Unknown symbol")
    return result


@app.get("/api/backtests")
def backtests():
    return {
        "available": False,
        "phase": 3,
        "results": [],
        "reason": "No validated point-in-time backtest engine yet. No performance metrics are fabricated.",
    }
