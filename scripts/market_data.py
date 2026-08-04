#!/usr/bin/env python3
"""OHLCV history, from the same two sources the quotes pipeline uses.

update_quotes.fetch_closes deliberately returns date/close pairs only —
that is all the tracker tiles need. Volume-weighted features need the
volume column too, so this fetches the same rows and keeps it, from the
same endpoints, with the same primary/fallback order. No new provider and
no new credential.

Failures are recorded rather than swallowed: as of Aug 2026 the stooq
per-symbol endpoint is failing for every symbol and the whole watchlist
is being served by the Yahoo fallback. That went unnoticed for a while
precisely because an earlier version of this pattern discarded the reason.
"""

import csv
import io
import json
import urllib.request
from datetime import datetime, timezone

STOOQ_URL = "https://stooq.com/q/d/l/?s={symbol}.us&i=d"
YAHOO_URL = ("https://query1.finance.yahoo.com/v8/finance/chart/"
             "{symbol}?range={range}&interval=1d")
DEFAULT_RANGE = "2y"        # enough history for a 120-session training warmup

LAST_SOURCE = "stooq"
PRIMARY_FAILURES: list[str] = []


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def _rows_stooq(symbol: str) -> list[tuple[str, float, float]]:
    text = _get(STOOQ_URL.format(symbol=symbol.lower())).decode(
        "utf-8", errors="replace")
    bars = []
    for row in csv.DictReader(io.StringIO(text)):
        date = (row.get("Date") or "").strip()
        close = (row.get("Close") or "").strip()
        volume = (row.get("Volume") or "").strip()
        if not date or not close or close.upper() == "N/A":
            continue
        try:
            bars.append((date, float(close), float(volume or 0)))
        except ValueError:
            continue
    return bars


def _rows_yahoo(symbol: str, rng: str) -> list[tuple[str, float, float]]:
    payload = json.loads(_get(YAHOO_URL.format(symbol=symbol, range=rng)))
    result = payload["chart"]["result"][0]
    quote = result["indicators"]["quote"][0]
    bars = []
    for ts, close, volume in zip(result["timestamp"],
                                 quote["close"], quote["volume"]):
        if close is None:
            continue
        date = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
        bars.append((date, round(float(close), 4), float(volume or 0)))
    return bars


def fetch_ohlcv(symbol: str, rng: str = DEFAULT_RANGE):
    """Daily bars as (date, close, volume), oldest first.

    Bars whose volume is zero or missing are dropped: a volume-weighted
    feature computed from a zero-volume row is not a weak signal, it is an
    arithmetic artefact of a data gap.
    """
    global LAST_SOURCE
    bars = []
    try:
        bars = _rows_stooq(symbol)
        if bars:
            LAST_SOURCE = "stooq"
        else:
            PRIMARY_FAILURES.append(f"{symbol}: stooq returned no rows")
    except Exception as exc:
        PRIMARY_FAILURES.append(f"{symbol}: stooq {type(exc).__name__}: {exc}")

    if not bars:
        LAST_SOURCE = "yahoo-fallback"
        bars = _rows_yahoo(symbol, rng)

    return [b for b in bars if b[2] > 0]
