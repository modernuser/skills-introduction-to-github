#!/usr/bin/env python3
"""Rolling S&P 500 movers: biggest OBSERVED daily moves across the index.

Fetches last closes for all ~500 constituents (stooq bulk endpoint), compares
against the previous trading day's stored closes, and writes the top/bottom
10 by actual percent move to data/movers.json. The universe rolls itself:
whichever names moved most show up, no selection or prediction involved.

State file data/sp500_closes.json holds {symbol: {date, close}} so the next
run has a prior day to compare against. First ever run only seeds state.
"""

import csv
import io
import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone

from atomic import write_json

CONSTITUENTS_URL = (
    "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/"
    "main/data/constituents.csv"
)
CONSTITUENTS_FALLBACK = "data/sp500_constituents.csv"
# sector_depth.py rebuilds this daily from per-symbol history — the
# endpoint that still works. This job reads it as a price source.
CLOSES_PATH = "data/sp500_closes.json"
# Our own snapshot of what we last compared against. Kept separate from
# CLOSES_PATH so the daily rebuild cannot silently erase the baseline a
# day-over-day move is measured from.
PRIOR_PATH = "data/movers_prior.json"
MOVERS_PATH = "data/movers.json"
ROTATION_PATH = "data/rotation.json"
ROTATION_TRIGGER_PCT = 5.0
ROTATION_WINDOW_DAYS = 14
BULK_URL = "https://stooq.com/q/l/?s={symbols}&f=sd2t2ohlcv&h&e=csv"
CHUNK = 40
TOP_N = 10
MIN_COVERAGE = 50  # don't publish movers off a mostly-failed fetch


def load_constituents() -> dict:
    """symbol -> {name, sector}; live list first, committed snapshot fallback."""
    try:
        req = urllib.request.Request(
            CONSTITUENTS_URL, headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode()
    except Exception as exc:
        print(f"live constituents fetch failed ({exc}); using snapshot", file=sys.stderr)
        with open(CONSTITUENTS_FALLBACK) as f:
            text = f.read()
    out = {}
    for row in csv.DictReader(io.StringIO(text)):
        out[row["Symbol"].strip()] = {
            "name": row["Security"].strip(),
            "sector": row["GICS Sector"].strip(),
        }
    return out


def stooq_symbol(symbol: str) -> str:
    return symbol.replace(".", "-").lower() + ".us"


def fetch_closes(symbols: list) -> dict:
    """symbol -> {date, close} via stooq bulk CSV, chunked politely."""
    closes = {}
    back = {stooq_symbol(s): s for s in symbols}
    for i in range(0, len(symbols), CHUNK):
        chunk = symbols[i : i + CHUNK]
        url = BULK_URL.format(symbols="+".join(stooq_symbol(s) for s in chunk))
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                text = resp.read().decode()
        except Exception as exc:
            print(f"bulk chunk failed ({exc})", file=sys.stderr)
            continue
        for row in csv.DictReader(io.StringIO(text)):
            sym = back.get(row.get("Symbol", "").lower())
            if sym is None:
                continue
            try:
                closes[sym] = {
                    "date": row["Date"],
                    "close": float(row["Close"]),
                }
            except (KeyError, TypeError, ValueError):
                continue  # N/D or malformed row
        time.sleep(0.5)
    return closes


def update_rotation(moves: list, newest_date: str) -> None:
    """In Play list: a ±5% observed day admits a ticker for ~2 weeks.

    The market's own record of where real news hit — entry and exit are
    both mechanical facts, nothing selects or recommends.
    """
    rotation = []
    if os.path.exists(ROTATION_PATH):
        with open(ROTATION_PATH) as f:
            rotation = json.load(f).get("entries", [])
    by_symbol = {r["symbol"]: r for r in rotation}

    for m in moves:
        if abs(m["pct"]) >= ROTATION_TRIGGER_PCT:
            entry = by_symbol.get(m["symbol"], {})
            by_symbol[m["symbol"]] = {
                "symbol": m["symbol"], "name": m["name"], "sector": m["sector"],
                "entered": newest_date, "trigger_pct": m["pct"],
                "last_close": m["close"],
                "first_entered": entry.get("first_entered", newest_date),
            }
        elif m["symbol"] in by_symbol:
            by_symbol[m["symbol"]]["last_close"] = m["close"]

    newest = datetime.strptime(newest_date, "%Y-%m-%d")
    keep = [
        r for r in by_symbol.values()
        if (newest - datetime.strptime(r["entered"], "%Y-%m-%d")).days
        <= ROTATION_WINDOW_DAYS
    ]
    keep.sort(key=lambda r: r["entered"], reverse=True)
    write_json(ROTATION_PATH, {"updated": newest_date, "window_days": ROTATION_WINDOW_DAYS,
                                "trigger_pct": ROTATION_TRIGGER_PCT, "entries": keep}, indent=1)
    print(f"rotation: {len(keep)} in play")


def load_closes_state() -> dict:
    """Fallback price source: the daily state sector_depth.py maintains."""
    if not os.path.exists(CLOSES_PATH):
        return {}
    with open(CLOSES_PATH) as f:
        return json.load(f)


def main() -> int:
    constituents = load_constituents()
    prior = {}
    if os.path.exists(PRIOR_PATH):
        with open(PRIOR_PATH) as f:
            prior = json.load(f)

    fresh = fetch_closes(list(constituents))
    if len(fresh) < MIN_COVERAGE:
        # Aug 2026: the bulk quote endpoint began returning 404 for every
        # chunk, which silently killed movers and the In Play rotation.
        # Fall back to the state sector_depth.py rebuilds daily from the
        # per-symbol endpoint that still works.
        fallback = load_closes_state()
        if len(fallback) >= MIN_COVERAGE:
            print(f"bulk fetch returned {len(fresh)}; using {CLOSES_PATH} "
                  f"({len(fallback)} symbols)")
            fresh = {s: c for s, c in fallback.items() if s in constituents}
        else:
            print(f"only {len(fresh)} quotes and no usable closes state; "
                  "aborting without changes", file=sys.stderr)
            return 1

    moves = []
    for sym, cur in fresh.items():
        prev = prior.get(sym)
        if prev and prev["date"] < cur["date"] and prev["close"] > 0:
            pct = (cur["close"] - prev["close"]) / prev["close"] * 100
            moves.append({
                "symbol": sym,
                "name": constituents[sym]["name"],
                "sector": constituents[sym]["sector"],
                "close": cur["close"],
                "pct": round(pct, 2),
            })

    # Advance our baseline (keep the old entry until a newer date appears).
    for sym, cur in fresh.items():
        if sym not in prior or prior[sym]["date"] <= cur["date"]:
            prior[sym] = cur
    write_json(PRIOR_PATH, prior, separators=(",", ":"), sort_keys=True)

    if len(moves) >= MIN_COVERAGE:
        moves.sort(key=lambda m: m["pct"], reverse=True)
        out = {
            "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "coverage": len(moves),
            "gainers": moves[:TOP_N],
            "losers": moves[-TOP_N:][::-1],
        }
        write_json(MOVERS_PATH, out, indent=1)
        print(f"Wrote {MOVERS_PATH}: {len(moves)} comparable symbols")
        update_rotation(moves, max(c["date"] for c in fresh.values()))
    else:
        print(f"baseline seeded ({len(fresh)} closes); movers need a prior day")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
