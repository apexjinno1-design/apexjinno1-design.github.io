import time
from datetime import UTC, date, datetime
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import httpx

from app.providers.base import PriceBar, StockReference


class ProviderError(RuntimeError):
    pass


class MassiveProvider:
    name = "massive"
    base_url = "https://api.massive.com"

    def __init__(self, api_key: str, client: httpx.Client | None = None, requests_per_minute: int = 0):
        if not api_key:
            raise ProviderError("Set MASSIVE_API_KEY on the backend to ingest live provider data")
        self.client = client or httpx.Client(timeout=40, follow_redirects=False)
        self._owns_client = client is None
        self._key = api_key
        self._interval = 60 / requests_per_minute if requests_per_minute > 0 else 0
        self._next_request = 0.0

    def close(self):
        if self._owns_client:
            self.client.close()

    def _get(self, url: str, params: dict | None = None) -> dict:
        parts = urlsplit(url)
        if (
            parts.scheme != "https"
            or parts.hostname != "api.massive.com"
            or parts.port not in (None, 443)
            or parts.username
            or parts.password
            or parts.fragment
        ):
            raise ProviderError("Rejected unexpected provider pagination destination")
        for attempt in range(4):
            delay = self._next_request - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            self._next_request = time.monotonic() + self._interval
            try:
                response = self.client.get(
                    url, params=params, headers={"Authorization": f"Bearer {self._key}"}
                )
            except httpx.HTTPError:
                raise ProviderError(
                    "Provider connection failed; check network and API availability"
                ) from None
            if response.status_code in (429, 500, 502, 503, 504) and attempt < 3:
                retry = response.headers.get("Retry-After", "")
                time.sleep(min(float(retry), 60) if retry.isdigit() else 2**attempt)
                continue
            if response.status_code >= 300:
                # Never include request URLs, headers, keys, or arbitrary provider body in logs.
                raise ProviderError(
                    f"Massive returned HTTP {response.status_code}; check plan entitlements and API access"
                )
            try:
                payload = response.json()
            except ValueError:
                raise ProviderError("Massive returned invalid JSON") from None
            if not isinstance(payload, dict):
                raise ProviderError("Massive returned an invalid response shape")
            if payload.get("status") in ("ERROR", "NOT_AUTHORIZED"):
                raise ProviderError("Massive returned an error status")
            return payload
        raise ProviderError("Provider retry budget exhausted")

    def _pages(self, path: str, params: dict) -> list[dict]:
        url, seen, results = self.base_url + path, set(), []
        while url:
            if url in seen:
                raise ProviderError("Provider returned cyclic pagination")
            seen.add(url)
            payload = self._get(url, params)
            results.extend(payload.get("results", []))
            url, params = payload.get("next_url"), None
        return results

    @staticmethod
    def _reference(data: dict) -> StockReference:
        return StockReference(
            symbol=data["ticker"],
            name=data.get("name", data["ticker"]),
            security_type=data.get("type", "UNKNOWN"),
            active=data.get("active", True),
            exchange=data.get("primary_exchange"),
            industry=data.get("sic_description"),
        )

    def active_stocks(self) -> list[StockReference]:
        data = self._pages(
            "/v3/reference/tickers",
            {"market": "stocks", "locale": "us", "type": "CS", "active": "true", "limit": 1000},
        )
        return [self._reference(d) for d in data]

    def reference(self, symbol: str) -> StockReference:
        data = self._get(f"{self.base_url}/v3/reference/tickers/{symbol}").get("results")
        if not data:
            raise ProviderError(f"No reference information returned for {symbol}")
        if data.get("locale", "us") != "us" or data.get("market", "stocks") != "stocks":
            raise ProviderError(f"{symbol} is outside the US stock universe")
        return self._reference(data)

    def daily_bars(self, symbol: str, start: date, end: date, adjusted: bool = True) -> list[PriceBar]:
        data = self._pages(
            f"/v2/aggs/ticker/{symbol}/range/1/day/{start}/{end}",
            {"adjusted": str(adjusted).lower(), "sort": "asc", "limit": 50000},
        )
        result = []
        for row in data:
            day = datetime.fromtimestamp(row["t"] / 1000, UTC).astimezone(ZoneInfo("America/New_York")).date()
            if start <= day <= end:
                result.append(PriceBar(day, row["o"], row["h"], row["l"], row["c"], row["v"]))
        return result
