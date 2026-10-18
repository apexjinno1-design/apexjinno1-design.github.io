from unittest.mock import patch

import httpx
import pytest

from app.config import Settings
from app.providers.massive import MassiveProvider


@pytest.mark.parametrize("scheme", ["postgres", "postgresql", "postgresql+psycopg"])
def test_managed_postgres_urls_use_installed_driver(scheme):
    settings = Settings(_env_file=None, database_url=f"{scheme}://fixture:fixture@db/stock")
    assert settings.database_url == "postgresql+psycopg://fixture:fixture@db/stock"


def test_request_pacing_applies_before_next_provider_call():
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={})))
    with (
        client,
        patch("app.providers.massive.time.monotonic", side_effect=[100, 100, 101, 112]),
        patch("app.providers.massive.time.sleep") as pause,
    ):
        provider = MassiveProvider("fixture-only", client, requests_per_minute=5)
        provider._get("https://api.massive.com/test")
        provider._get("https://api.massive.com/test")
        pause.assert_called_once_with(11)


def test_overlapping_refreshes_do_not_make_provider_requests():
    from app.main import refresh_lock, scheduled_refresh

    with refresh_lock, patch("app.main.MassiveProvider") as provider:
        scheduled_refresh()
        provider.assert_not_called()


def test_background_refresh_populates_research_without_duplicate_prices(db, monkeypatch):
    from datetime import UTC, datetime

    from sqlalchemy import func, select

    from app import main
    from app.demo import DemoProvider
    from app.models import DailyPrice, TechnicalIndicator

    provider = DemoProvider(datetime.now(UTC))
    provider.close = lambda: None
    settings = Settings(
        _env_file=None,
        massive_api_key="fixture-only",
        ingest_symbols=",".join(provider.symbols),
        demo_mode=False,
    )
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    monkeypatch.setattr(main, "MassiveProvider", lambda *args, **kwargs: provider)
    monkeypatch.setattr(main, "SessionLocal", lambda: db)
    main.scheduled_refresh()
    first_count = db.scalar(select(func.count()).select_from(DailyPrice))
    assert first_count == 2340
    assert db.scalar(select(func.count()).select_from(TechnicalIndicator)) == 6
    db.rollback()
    main.scheduled_refresh()
    assert db.scalar(select(func.count()).select_from(DailyPrice)) == first_count
    assert db.scalar(select(func.count()).select_from(TechnicalIndicator)) == 12
