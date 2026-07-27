from datetime import datetime, timezone

import pytest

from conftest import load

ms = load("market_session")


def utc(y, m, d, hh, mm=0):
    return datetime(y, m, d, hh, mm, tzinfo=timezone.utc)


# Summer (EDT, UTC-4): 04:00 ET = 08:00 UTC, 09:30 ET = 13:30 UTC,
# 16:00 ET = 20:00 UTC, 20:00 ET = 00:00 UTC next day.
@pytest.mark.parametrize("when,expected", [
    (utc(2026, 7, 27, 7, 59), "closed"),    # 03:59 ET
    (utc(2026, 7, 27, 8, 0), "pre"),        # 04:00 ET exactly
    (utc(2026, 7, 27, 13, 29), "pre"),      # 09:29 ET
    (utc(2026, 7, 27, 13, 30), "regular"),  # 09:30 ET exactly
    (utc(2026, 7, 27, 19, 59), "regular"),  # 15:59 ET
    (utc(2026, 7, 27, 20, 0), "after"),     # 16:00 ET exactly
    (utc(2026, 7, 27, 23, 59), "after"),    # 19:59 ET
    (utc(2026, 7, 28, 0, 0), "closed"),     # 20:00 ET
])
def test_summer_session_boundaries(when, expected):
    assert ms.session_at(when) == expected


# Winter (EST, UTC-5): everything shifts one hour later in UTC.
@pytest.mark.parametrize("when,expected", [
    (utc(2026, 1, 14, 8, 59), "closed"),    # 03:59 ET
    (utc(2026, 1, 14, 9, 0), "pre"),        # 04:00 ET
    (utc(2026, 1, 14, 14, 30), "regular"),  # 09:30 ET
    (utc(2026, 1, 14, 21, 0), "after"),     # 16:00 ET
    (utc(2026, 1, 15, 1, 0), "closed"),     # 20:00 ET
])
def test_winter_session_boundaries(when, expected):
    assert ms.session_at(when) == expected


def test_weekend_is_closed():
    assert ms.session_at(utc(2026, 7, 25, 17, 0)) == "closed"  # Saturday
    assert ms.session_at(utc(2026, 7, 26, 17, 0)) == "closed"  # Sunday


@pytest.mark.parametrize("holiday", [
    (2026, 1, 1), (2026, 1, 19), (2026, 2, 16), (2026, 4, 3), (2026, 5, 25),
    (2026, 6, 19), (2026, 7, 3), (2026, 9, 7), (2026, 11, 26), (2026, 12, 25),
    (2027, 1, 1), (2027, 7, 5), (2027, 11, 25), (2027, 12, 24),
])
def test_market_holidays_are_closed(holiday):
    y, m, d = holiday
    assert ms.session_at(utc(y, m, d, 15, 0)) == "closed"


def test_half_day_closes_early():
    # 2026-11-27 (day after Thanksgiving): regular ends 13:00 ET = 18:00 UTC
    assert ms.session_at(utc(2026, 11, 27, 17, 59)) == "regular"
    assert ms.session_at(utc(2026, 11, 27, 18, 0)) == "after"
    assert ms.session_at(utc(2026, 11, 27, 22, 1)) == "closed"  # after 17:00 ET


def test_next_transition_labels():
    label, _ = ms.next_transition(utc(2026, 7, 27, 12, 0))  # pre-market
    assert label == "regular open"
    label, _ = ms.next_transition(utc(2026, 7, 27, 15, 0))  # regular
    assert label == "close"
    label, at = ms.next_transition(utc(2026, 7, 25, 17, 0))  # Saturday
    assert label == "pre-market open" and at.date().isoformat() == "2026-07-27"


def test_next_transition_skips_holiday_weekend():
    # Friday 2026-07-03 is a holiday; from Thursday night the next open
    # must be Monday 2026-07-06.
    _, at = ms.next_transition(utc(2026, 7, 3, 6, 0))
    assert at.date().isoformat() == "2026-07-06"


def test_last_session_close_skips_weekend():
    close = ms.last_session_close(utc(2026, 7, 27, 10, 0))  # Monday pre-market
    assert close.date().isoformat() == "2026-07-24"         # previous Friday


def test_describe_shape():
    d = ms.describe(utc(2026, 7, 27, 15, 0))
    assert d["session"] == "regular" and d["label"] == "Open"
    assert d["next"] == "close" and d["minutes_to_next"] > 0
    assert d["max_expected_age_hours"] == 6
    assert "ET" in d["now_et"] or "E" in d["now_et"]
