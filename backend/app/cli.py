import argparse
import json
from datetime import UTC, datetime

from sqlalchemy import select

from app.config import get_settings
from app.db import SessionLocal
from app.demo import seed_demo
from app.models import Stock
from app.providers.massive import MassiveProvider, ProviderError
from app.schemas import ScanRequest
from app.services.ingestion import ingest_daily, save_reference
from app.services.research import scan


def main():
    parser = argparse.ArgumentParser(description="Local research administration")
    parser.add_argument("command", choices=["demo", "scan", "ingest"])
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument("--symbols", help="Comma-separated symbols, including benchmark ETFs")
    selection.add_argument(
        "--universe", action="store_true", help="Refresh active US common stocks and ingest all"
    )
    parser.add_argument("--start", type=lambda x: datetime.fromisoformat(x).date())
    parser.add_argument("--end", type=lambda x: datetime.fromisoformat(x).date())
    args = parser.parse_args()
    now = datetime.now(UTC)
    if args.command == "ingest":
        from app.schemas import IngestRequest
        from app.services.research import BENCHMARKS, SECTOR_ETFS

        if get_settings().demo_mode:
            parser.error("Use DEMO_MODE=false and a separate provider database")
        if not args.start or not args.end or not (args.symbols or args.universe):
            parser.error("ingest requires --start, --end and --symbols or --universe")
        provider = None
        failed = []
        try:
            provider = MassiveProvider(
                get_settings().massive_api_key.get_secret_value(),
                requests_per_minute=get_settings().massive_requests_per_minute,
            )
            if args.universe:
                with SessionLocal() as db, db.begin():
                    refs = provider.active_stocks()
                    for ref in refs:
                        save_reference(db, ref, provider.name, now)
                    symbols = list(
                        db.scalars(select(Stock.symbol).where(Stock.active, Stock.security_type == "CS"))
                    )
                symbols = list(dict.fromkeys([*BENCHMARKS, *SECTOR_ETFS, *symbols]))
            else:
                symbols = args.symbols.split(",")
            # Validate before downloading; API bounds remain 100, CLI works one symbol at a time.
            for symbol in symbols:
                request = IngestRequest(symbols=[symbol], start=args.start, end=args.end)
                try:
                    with SessionLocal() as db, db.begin():
                        result = ingest_daily(db, provider, request.symbols, request.start, request.end)
                    print(json.dumps({"symbol": symbol, **result}), flush=True)
                except (ProviderError, ValueError) as exc:
                    failed.append(symbol)
                    print(json.dumps({"symbol": symbol, "error": str(exc)}), flush=True)
        except (ProviderError, ValueError) as exc:
            parser.exit(1, f"Ingestion failed: {exc}\n")
        finally:
            if provider:
                provider.close()
        if failed:
            parser.exit(1, f"Failed symbols: {','.join(failed)}\n")
        return
    with SessionLocal() as db, db.begin():
        if args.command == "demo":
            if not get_settings().demo_mode:
                parser.error("DEMO_MODE=true is required. Use a dedicated synthetic database.")
            print(json.dumps(seed_demo(db, now)))
        request = ScanRequest()
        result = scan(db, now, request.breakout, request.risk)
        print(
            json.dumps(
                {
                    "session": result["session"],
                    "universe_size": result["universe_size"],
                    "regime": result["regime"]["regime"],
                    "statuses": {c["symbol"]: c["status"] for c in result["candidates"]},
                }
            )
        )


if __name__ == "__main__":
    main()
