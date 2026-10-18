"""Optional real PostgreSQL migration/research test; never use a non-test database."""

import os
import subprocess
import sys
from datetime import UTC, datetime

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.db import make_engine
from app.demo import seed_demo
from app.risk import RiskParameters
from app.screener import BreakoutParameters
from app.services.research import scan


@pytest.mark.skipif(
    not os.environ.get("TEST_DATABASE_URL"), reason="Dedicated PostgreSQL test URL not configured"
)
def test_postgres_migration_and_research_workflow():
    url = os.environ["TEST_DATABASE_URL"]
    assert make_url(url).database.endswith("_test"), "Use a dedicated database whose name ends in _test"
    engine = make_engine(url)
    tables = set(inspect(engine).get_table_names())
    assert not tables - {"alembic_version"}, "PostgreSQL integration test requires an empty database"
    if "alembic_version" in tables:
        with engine.connect() as connection:
            assert connection.scalar(text("SELECT count(*) FROM alembic_version")) == 0
    child_env = {**os.environ, "DATABASE_URL": url, "DEMO_MODE": "true"}
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], env=child_env, check=True)
    subprocess.run([sys.executable, "-m", "alembic", "check"], env=child_env, check=True)
    try:
        with Session(engine) as db:
            at = datetime(2026, 10, 16, 21, tzinfo=UTC)
            seed_demo(db, at)
            result = scan(db, at, BreakoutParameters(), RiskParameters())
            assert result["universe_size"] == 6
            assert any(c["status"] == "TRIGGERED" for c in result["candidates"])
            assert seed_demo(db, at)["inserted"] == 0
            db.rollback()
    finally:
        subprocess.run([sys.executable, "-m", "alembic", "downgrade", "base"], env=child_env, check=True)
        engine.dispose()
