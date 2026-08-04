#!/usr/bin/env python3
"""Fetch daily price history for the watchlist and write data/quotes.json.

Data source: stooq.com free daily CSV (no API key). Runs in GitHub Actions
on a schedule; the static tracker page just reads the committed JSON.
"""

import csv
import io
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

from atomic import write_json

# Ticker lists live in watchlist.json so they can be edited without
# touching code. "watchlist" gets full tiles; "sectors" gets the compact
# sector-pulse table.
with open("watchlist.json") as _f:
    _config = json.load(_f)
TICKERS = _config["watchlist"]
CORE = _config.get("core", {})
SECTORS = _config.get("sectors", {})

# A one-day move at or beyond this magnitude is flagged as significant.
SIGNIFICANT_PCT = 3.0

HISTORY_URL = "https://stooq.com/q/d/l/?s={symbol}.us&i=d"
# 2y, not 3mo. The 52-week range needs ~200 sessions; a 3-month fallback
# supplies ~63, so every tile silently lost its hi52/lo52 the moment the
# primary source started failing (Aug 2026 — all 35 symbols, 0 ranges).
# A fallback that quietly drops a feature is worse than a loud failure:
# the page kept rendering and nothing looked wrong.
YAHOO_URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/"
    "{symbol}?range=2y&interval=1d"
)
# After this many consecutive empty stooq replies, stop asking within the
# run. When the source is down it is down for every symbol, and 35 futile
# round-trips per run against a host that may be rate-limiting us is the
# opposite of helpful.
STOOQ_GIVE_UP_AFTER = 3


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def diagnose_stooq(text: str) -> str:
    """Say what arrived instead of CSV.

    "returned no rows" was true but useless: it could not distinguish a
    rate-limit notice from an HTML error page from a delisted ticker, so
    the Aug 2026 outage sat undiagnosed. stooq answers 200 with a plain
    body in every one of those cases, which is why nothing raised.
    """
    head = " ".join(text.split())[:160]
    low = head.lower()
    if not head:
        return "empty response body"
    if "exceed" in low and "limit" in low:
        return f"rate-limited: {head!r}"
    if head.lstrip().startswith(("<", "<!")):
        return f"HTML instead of CSV: {head!r}"
    if "no data" in low or "not found" in low:
        return f"no such symbol: {head!r}"
    return f"unparsable body: {head!r}"


def fetch_closes_stooq(symbol: str) -> list[tuple[str, float]]:
    text = _get(HISTORY_URL.format(symbol=symbol.lower())).decode(
        "utf-8", errors="replace"
    )
    global LAST_STOOQ_DIAGNOSIS
    LAST_STOOQ_DIAGNOSIS = diagnose_stooq(text)
    closes = []
    for row in csv.DictReader(io.StringIO(text)):
        raw = (row.get("Close") or "").strip()
        date = (row.get("Date") or "").strip()
        if raw and raw.upper() != "N/A" and date:
            try:
                closes.append((date, float(raw)))
            except ValueError:
                continue
    return closes


def fetch_closes_yahoo(symbol: str) -> list[tuple[str, float]]:
    payload = json.loads(_get(YAHOO_URL.format(symbol=symbol)))
    result = payload["chart"]["result"][0]
    stamps = result["timestamp"]
    close_series = result["indicators"]["quote"][0]["close"]
    closes = []
    for ts, close in zip(stamps, close_series):
        if close is not None:
            date = datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")
            closes.append((date, round(float(close), 4)))
    return closes


LAST_SOURCE = "stooq"
# Why the primary source was skipped, most recent first. Aug 2026: every
# symbol silently fell through to the 3-month Yahoo fallback — which also
# silently dropped 52-week ranges — because this except-branch discarded
# the reason. A fallback nobody can see is a fallback nobody fixes.
PRIMARY_FAILURES: list[str] = []
LAST_STOOQ_DIAGNOSIS = "not attempted"
STOOQ_EMPTY_STREAK = 0
# Counted separately from the message list: once the circuit breaker trips
# we stop recording a reason per symbol, but those symbols are still being
# served by the fallback and the health metric must say so.
FALLBACK_COUNT = 0


def fetch_closes(symbol: str) -> list[tuple[str, float]]:
    global LAST_SOURCE, STOOQ_EMPTY_STREAK, FALLBACK_COUNT
    if STOOQ_EMPTY_STREAK < STOOQ_GIVE_UP_AFTER:
        try:
            closes = fetch_closes_stooq(symbol)
            if closes:
                STOOQ_EMPTY_STREAK = 0
                LAST_SOURCE = "stooq"
                return closes
            STOOQ_EMPTY_STREAK += 1
            PRIMARY_FAILURES.append(f"{symbol}: stooq {LAST_STOOQ_DIAGNOSIS}")
            if STOOQ_EMPTY_STREAK == STOOQ_GIVE_UP_AFTER:
                PRIMARY_FAILURES.append(
                    f"stooq gave {STOOQ_GIVE_UP_AFTER} empty replies in a row; "
                    "skipping it for the rest of this run")
        except Exception as exc:
            STOOQ_EMPTY_STREAK += 1
            PRIMARY_FAILURES.append(
                f"{symbol}: stooq {type(exc).__name__}: {exc}")
    FALLBACK_COUNT += 1
    LAST_SOURCE = "yahoo-fallback"
    return fetch_closes_yahoo(symbol)


def pct_change(closes: list[tuple[str, float]], sessions_back: int):
    if len(closes) <= sessions_back:
        return None
    latest = closes[-1][1]
    prior = closes[-1 - sessions_back][1]
    if prior == 0:
        return None
    return round((latest - prior) / prior * 100, 2)


def build_quote(symbol: str, name: str, errors: list, with_recent: bool):
    try:
        closes = fetch_closes(symbol)
    except Exception as exc:  # network or parse failure for one symbol
        errors.append(f"{symbol}: {exc}")
        return None
    if not closes:
        errors.append(f"{symbol}: no data returned")
        return None
    d1 = pct_change(closes, 1)
    quote = {
        "symbol": symbol,
        "name": name,
        "date": closes[-1][0],
        "close": closes[-1][1],
        "d1": d1,
        "w1": pct_change(closes, 5),
        "m1": pct_change(closes, 21),
        "significant": d1 is not None and abs(d1) >= SIGNIFICANT_PCT,
        "source": LAST_SOURCE,
    }
    if with_recent:
        # last ~30 sessions for the sparkline
        quote["recent"] = [c for _, c in closes[-30:]]
        # 52-week closing range (~252 sessions). The gate stays even though
        # the fallback now requests 2y: a short reply from either source
        # must never masquerade as a yearly range. `ranges_present` in the
        # output is what makes a shortfall visible rather than silent.
        year = [c for _, c in closes[-252:]]
        if len(year) >= 200:
            quote["hi52"] = max(year)
            quote["lo52"] = min(year)
    return quote


def main() -> int:
    global STOOQ_EMPTY_STREAK, FALLBACK_COUNT
    STOOQ_EMPTY_STREAK = FALLBACK_COUNT = 0
    PRIMARY_FAILURES.clear()
    errors = []
    quotes = [
        q for symbol, name in TICKERS.items()
        if (q := build_quote(symbol, name, errors, with_recent=True))
    ]
    core = [
        q for symbol, name in CORE.items()
        if (q := build_quote(symbol, name, errors, with_recent=False))
    ]
    sectors = [
        q for symbol, name in SECTORS.items()
        if (q := build_quote(symbol, name, errors, with_recent=False))
    ]

    if not quotes:
        print("All fetches failed:\n" + "\n".join(errors), file=sys.stderr)
        return 1

    out = {
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "significant_pct": SIGNIFICANT_PCT,
        "quotes": quotes,
        "core": core,
        "sectors": sectors,
        "errors": errors,
        # Visible degradation: which symbols fell back and why.
        "primary_source_failures": PRIMARY_FAILURES[:20],
        "fallback_count": FALLBACK_COUNT,
        # A feature can disappear without anything failing. When the
        # fallback was 3 months long, every 52-week range vanished from
        # the tiles and no check noticed, because each individual run was
        # "successful". Counting the ranges makes their absence a number
        # something can alarm on.
        "ranges_present": sum(1 for q in quotes if "hi52" in q),
        "ranges_expected": len(quotes),
    }
    write_json("data/quotes.json", out, indent=1)
    print(f"Wrote data/quotes.json with {len(quotes)} symbols; {len(errors)} errors")
    if FALLBACK_COUNT:
        print(f"  WARNING: {FALLBACK_COUNT} symbol(s) fell back off the "
              f"primary source; first: {PRIMARY_FAILURES[0]}", file=sys.stderr)
    for e in errors:
        print("  warn:", e, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
