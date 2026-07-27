#!/usr/bin/env python3
"""US equity market session clock — pre-market, regular, after-hours, closed.

Everything the rest of the pipeline needs to know about *when* it is, in
market terms. Pure stdlib and fully deterministic, so it is heavily
unit-tested rather than trusted.

Sessions (America/New_York, so DST is handled by the tz database):
  pre      04:00 - 09:30
  regular  09:30 - 16:00   (13:00 on half-days)
  after    16:00 - 20:00   (17:00 on half-days)
  closed   everything else, plus weekends and market holidays
"""

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

ET = ZoneInfo("America/New_York")

PRE_OPEN = time(4, 0)
REGULAR_OPEN = time(9, 30)
REGULAR_CLOSE = time(16, 0)
AFTER_CLOSE = time(20, 0)
HALF_DAY_CLOSE = time(13, 0)
HALF_DAY_AFTER_CLOSE = time(17, 0)

# NYSE/Nasdaq full closures. Keep current; a missing future year degrades
# gracefully (the day is treated as a normal session).
HOLIDAYS = {
    # 2026
    date(2026, 1, 1), date(2026, 1, 19), date(2026, 2, 16), date(2026, 4, 3),
    date(2026, 5, 25), date(2026, 6, 19), date(2026, 7, 3), date(2026, 9, 7),
    date(2026, 11, 26), date(2026, 12, 25),
    # 2027
    date(2027, 1, 1), date(2027, 1, 18), date(2027, 2, 15), date(2027, 3, 26),
    date(2027, 5, 31), date(2027, 6, 18), date(2027, 7, 5), date(2027, 9, 6),
    date(2027, 11, 25), date(2027, 12, 24),
}

# 1:00 PM ET closes (day after Thanksgiving, Christmas Eve, July 3 eves).
HALF_DAYS = {
    date(2026, 11, 27), date(2026, 12, 24),
    date(2027, 11, 26),
}

# How old the newest quote may reasonably be, per session, before the
# pipeline is genuinely suspect (hours). Weekends/holidays are handled by
# measuring against the last session close instead of a flat number.
MAX_AGE_HOURS = {"pre": 20, "regular": 6, "after": 8, "closed": 100}


def _et(when: datetime) -> datetime:
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    return when.astimezone(ET)


def is_trading_day(day: date) -> bool:
    return day.weekday() < 5 and day not in HOLIDAYS


def close_time_for(day: date) -> time:
    return HALF_DAY_CLOSE if day in HALF_DAYS else REGULAR_CLOSE


def after_close_for(day: date) -> time:
    return HALF_DAY_AFTER_CLOSE if day in HALF_DAYS else AFTER_CLOSE


def session_at(when: datetime) -> str:
    """'pre' | 'regular' | 'after' | 'closed' for an aware/naive-UTC time."""
    local = _et(when)
    day = local.date()
    if not is_trading_day(day):
        return "closed"
    t = local.time()
    if PRE_OPEN <= t < REGULAR_OPEN:
        return "pre"
    if REGULAR_OPEN <= t < close_time_for(day):
        return "regular"
    if close_time_for(day) <= t < after_close_for(day):
        return "after"
    return "closed"


def next_transition(when: datetime):
    """(label, aware ET datetime) of the next session boundary."""
    local = _et(when)
    current = session_at(when)
    day = local.date()

    if current == "pre":
        return "regular open", datetime.combine(day, REGULAR_OPEN, ET)
    if current == "regular":
        return "close", datetime.combine(day, close_time_for(day), ET)
    if current == "after":
        return "after-hours end", datetime.combine(day, after_close_for(day), ET)

    # Closed: next pre-market open, today if we're before 04:00, else the
    # next trading day.
    if is_trading_day(day) and local.time() < PRE_OPEN:
        return "pre-market open", datetime.combine(day, PRE_OPEN, ET)
    probe = day + timedelta(days=1)
    for _ in range(10):
        if is_trading_day(probe):
            return "pre-market open", datetime.combine(probe, PRE_OPEN, ET)
        probe += timedelta(days=1)
    return "pre-market open", datetime.combine(probe, PRE_OPEN, ET)


def last_session_close(when: datetime) -> datetime:
    """Aware ET datetime of the most recent regular-session close."""
    local = _et(when)
    day = local.date()
    if is_trading_day(day) and local.time() >= close_time_for(day):
        return datetime.combine(day, close_time_for(day), ET)
    probe = day - timedelta(days=1)
    for _ in range(10):
        if is_trading_day(probe):
            return datetime.combine(probe, close_time_for(probe), ET)
        probe -= timedelta(days=1)
    return datetime.combine(probe, REGULAR_CLOSE, ET)


def describe(when: datetime = None) -> dict:
    """Everything the page and the validator need, in one call."""
    when = when or datetime.now(timezone.utc)
    current = session_at(when)
    label, at = next_transition(when)
    minutes = max(0, int((at - _et(when)).total_seconds() // 60))
    return {
        "session": current,
        "label": {"pre": "Pre-market", "regular": "Open",
                  "after": "After hours", "closed": "Closed"}[current],
        "now_et": _et(when).strftime("%Y-%m-%d %H:%M %Z"),
        "next": label,
        "next_at_et": at.strftime("%Y-%m-%d %H:%M %Z"),
        "minutes_to_next": minutes,
        "last_close_et": last_session_close(when).strftime("%Y-%m-%d %H:%M %Z"),
        "max_expected_age_hours": MAX_AGE_HOURS[current],
    }


if __name__ == "__main__":
    import json
    print(json.dumps(describe(), indent=1))
