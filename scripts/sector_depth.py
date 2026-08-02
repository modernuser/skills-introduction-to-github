#!/usr/bin/env python3
"""Sector depth: the 10 highest-volatility names in each GICS sector.

Realized volatility is a measurement of how violently a price has ALREADY
moved — in both directions. It is a risk measure, not an opportunity
measure, and nothing here ranks, scores, or selects by expected return.

Runs once daily after the close: rankings move slowly, so paying ~503
history requests every twenty minutes would be waste. Intraday price
movement comes free from data/sp500_closes.json, which the all-session
pipeline already refreshes for every constituent.
"""

import json
import os
import statistics
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from atomic import write_json
from update_movers import load_constituents
from update_quotes import fetch_closes

OUT_PATH = "data/sector_depth.json"
# The bulk quote endpoint update_movers relies on began 404ing in Aug 2026.
# This job already fetches every constituent's history through the endpoint
# that still works, so it also emits the closes state those features need.
CLOSES_PATH = "data/sp500_closes.json"
WINDOW = 30          # daily returns in the volatility window
PER_SECTOR = 10      # names kept per sector
MIN_SESSIONS = 20    # too little history to characterise risk honestly
TRADING_DAYS = 252   # annualisation factor
MIN_COVERAGE = 100   # below this the run is broken, not just degraded
PACE_SECONDS = 0.25


def realized_volatility(closes: list[float], window: int = WINDOW):
    """Annualised stdev of daily returns, in percent. None if too short."""
    prices = [c for c in closes if c and c > 0]
    if len(prices) < MIN_SESSIONS + 1:
        return None, 0
    returns = [
        (prices[i] - prices[i - 1]) / prices[i - 1]
        for i in range(1, len(prices))
    ][-window:]
    if len(returns) < MIN_SESSIONS:
        return None, len(returns)
    return round(statistics.stdev(returns) * (TRADING_DAYS ** 0.5) * 100, 2), len(returns)


def build(constituents: dict, closes_for) -> tuple[dict, list, int, dict]:
    """Group every constituent by sector with its volatility.

    Also returns the latest close per symbol, so the same fetch feeds
    data/sp500_closes.json without extra requests.
    """
    by_sector, errors, measured, closes = {}, [], 0, {}
    for symbol, meta in constituents.items():
        try:
            history = closes_for(symbol)
        except Exception as exc:
            errors.append(f"{symbol}: {exc}")
            continue
        if not history:
            errors.append(f"{symbol}: no data")
            continue
        closes[symbol] = {"date": history[-1][0], "close": history[-1][1]}
        vol, sessions = realized_volatility([c for _, c in history])
        if vol is None:
            continue
        measured += 1
        by_sector.setdefault(meta["sector"], []).append({
            "symbol": symbol,
            "name": meta["name"],
            "vol_30d": vol,
            "sessions": sessions,
            "last_close": history[-1][1],
            "as_of": history[-1][0],
        })
    return by_sector, errors, measured, closes


def top_per_sector(by_sector: dict, per_sector: int = PER_SECTOR) -> dict:
    return {
        sector: sorted(rows, key=lambda r: r["vol_30d"], reverse=True)[:per_sector]
        for sector, rows in sorted(by_sector.items())
    }


def main() -> int:
    constituents = load_constituents()

    def paced(symbol):
        time.sleep(PACE_SECONDS)
        return fetch_closes(symbol)

    by_sector, errors, measured, closes = build(constituents, paced)
    if measured < MIN_COVERAGE:
        print(f"only {measured} symbols measurable; leaving previous file",
              file=sys.stderr)
        for err in errors[:5]:
            print("  warn:", err, file=sys.stderr)
        return 1

    # Merge rather than replace: symbols this run could not fetch keep
    # their previous close instead of vanishing from downstream features.
    existing = {}
    if os.path.exists(CLOSES_PATH):
        with open(CLOSES_PATH) as f:
            existing = json.load(f)
    for symbol, cur in closes.items():
        if symbol not in existing or existing[symbol]["date"] <= cur["date"]:
            existing[symbol] = cur
    write_json(CLOSES_PATH, existing, separators=(",", ":"), sort_keys=True)
    print(f"Wrote {CLOSES_PATH}: {len(existing)} symbols")

    sectors = top_per_sector(by_sector)
    write_json(OUT_PATH, {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "method": "annualised stdev of the last 30 daily returns",
        "note": ("Volatility measures how violently these prices have already "
                 "moved, in both directions. Risk measure, not a forecast and "
                 "not a recommendation."),
        "window_sessions": WINDOW,
        "per_sector": PER_SECTOR,
        "coverage": measured,
        "sectors": sectors,
        "errors": errors,
    }, indent=1)
    print(f"Wrote {OUT_PATH}: {len(sectors)} sectors, "
          f"{sum(len(v) for v in sectors.values())} names, "
          f"{measured} measured, {len(errors)} errors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
