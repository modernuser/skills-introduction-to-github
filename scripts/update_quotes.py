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

# Ticker lists live in watchlist.json so they can be edited without
# touching code. "watchlist" gets full tiles; "sectors" gets the compact
# sector-pulse table.
with open("watchlist.json") as _f:
    _config = json.load(_f)
TICKERS = _config["watchlist"]
SECTORS = _config.get("sectors", {})

# A one-day move at or beyond this magnitude is flagged as significant.
SIGNIFICANT_PCT = 3.0

HISTORY_URL = "https://stooq.com/q/d/l/?s={symbol}.us&i=d"
YAHOO_URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/"
    "{symbol}?range=3mo&interval=1d"
)


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def fetch_closes_stooq(symbol: str) -> list[tuple[str, float]]:
    text = _get(HISTORY_URL.format(symbol=symbol.lower())).decode(
        "utf-8", errors="replace"
    )
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


def fetch_closes(symbol: str) -> list[tuple[str, float]]:
    try:
        closes = fetch_closes_stooq(symbol)
        if closes:
            return closes
    except Exception:
        pass
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
    }
    if with_recent:
        # last ~30 sessions for the sparkline
        quote["recent"] = [c for _, c in closes[-30:]]
    return quote


def main() -> int:
    errors = []
    quotes = [
        q for symbol, name in TICKERS.items()
        if (q := build_quote(symbol, name, errors, with_recent=True))
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
        "sectors": sectors,
        "errors": errors,
    }
    os.makedirs("data", exist_ok=True)
    with open("data/quotes.json", "w") as f:
        json.dump(out, f, indent=1)
    print(f"Wrote data/quotes.json with {len(quotes)} symbols; {len(errors)} errors")
    for e in errors:
        print("  warn:", e, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
