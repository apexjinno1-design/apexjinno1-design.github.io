from datetime import UTC, date, datetime
from functools import lru_cache

import exchange_calendars as xcals
import pandas as pd


def aware(value: datetime) -> datetime:
    # SQLite drops timezone metadata; all persisted timestamps are UTC.
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


@lru_cache(maxsize=8)
def exchange_calendar(year: int, start_year: int | None = None):
    return xcals.get_calendar("XNYS", start=f"{(start_year or year) - 1}-01-01", end=f"{year + 1}-12-31")


def completed_sessions(start: date, end: date, as_of: datetime) -> set[date]:
    if as_of.tzinfo is None:
        raise ValueError("as_of must be timezone aware")
    cal = exchange_calendar(end.year, start.year)
    sessions = cal.sessions_in_range(pd.Timestamp(start), pd.Timestamp(end))
    return {s.date() for s in sessions if cal.session_close(s).to_pydatetime() <= as_of}


def last_completed_session(as_of: datetime) -> date:
    cal = exchange_calendar(as_of.year)
    day = pd.Timestamp(as_of.astimezone(UTC).date())
    session = cal.date_to_session(day, direction="previous")
    if cal.session_close(session).to_pydatetime() > as_of:
        session = cal.previous_session(session)
    return session.date()
