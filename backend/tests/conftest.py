from datetime import UTC, datetime

import numpy as np
import pandas as pd
import pytest
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base, make_engine
from app.indicators import daily_indicators


@pytest.fixture
def db():
    engine = make_engine("sqlite://")
    # One connection is shared with TestClient's worker thread.
    engine.dispose()
    from sqlalchemy import create_engine, event

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def fk(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session
    engine.dispose()


@pytest.fixture
def as_of():
    return datetime(2026, 10, 16, 21, 0, tzinfo=UTC)


@pytest.fixture
def bars():
    n = 180
    close = np.arange(n, dtype=float) + 50
    return pd.DataFrame(
        {
            "open": close - 0.5,
            "high": close + 2,
            "low": close - 2,
            "close": close,
            "volume": np.arange(n, dtype=float) * 1000 + 100_000,
        },
        index=pd.bdate_range("2025-01-02", periods=n).date,
    )


@pytest.fixture
def setup_frame():
    n = 180
    close = np.geomspace(10, 100, n)
    close[-21:-1] = np.linspace(100, 102, 20)
    spread = np.ones(n) * 0.02
    spread[-21:-1] = np.linspace(0.025, 0.004, 20)
    volume = np.full(n, 2_000_000.0)
    volume[-21:-1] *= np.linspace(0.9, 0.35, 20)
    pivot = np.max(close[-21:-1] * (1 + spread[-21:-1]))
    close[-1] = pivot * 1.015
    volume[-1] = 6_000_000
    raw = pd.DataFrame(
        {
            "open": close,
            "close": close,
            "high": close * (1 + spread),
            "low": close * (1 - spread),
            "volume": volume,
        }
    )
    return daily_indicators(raw)
