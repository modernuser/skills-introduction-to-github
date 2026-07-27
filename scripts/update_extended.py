#!/usr/bin/env python3
"""Pre-market and after-hours prices for the watchlist and market core.

stooq is end-of-day only, so extended-hours coverage comes from Yahoo's
chart endpoint (already this project's price fallback) with
includePrePost=true. Written to its own file so official closes in
quotes.json stay clean and a failed extended fetch degrades nothing.

Extended-hours prices are thin and volatile by nature — they are labeled
as pre/post everywhere they appear and never blended into a close.
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from atomic import write_json
from market_session import session_at

OUT_PATH = "data/extended.json"
CHART_URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/"
    "{symbol}?range=1d&interval=5m&includePrePost=true"
)


def _load_symbols() -> dict:
    with open("watchlist.json") as f:
        cfg = json.load(f)
    symbols = dict(cfg.get("core", {}))
    symbols.update(cfg["watchlist"])
    return symbols


def fetch_extended(symbol: str) -> dict | None:
    """Latest non-regular-session print, or None when there isn't one."""
    req = urllib.request.Request(
        CHART_URL.format(symbol=symbol), headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.load(resp)

    result = payload["chart"]["result"][0]
    meta = result.get("meta", {})
    prev_close = meta.get("chartPreviousClose") or meta.get("previousClose")
    stamps = result.get("timestamp") or []
    closes = (result.get("indicators", {}).get("quote", [{}])[0]
              .get("close") or [])

    latest = None
    for ts, price in zip(stamps, closes):
        if price is None:
            continue
        when = datetime.fromtimestamp(ts, tz=timezone.utc)
        phase = session_at(when)
        if phase in ("pre", "after"):
            latest = (when, float(price), phase)

    if latest is None or not prev_close:
        return None
    when, price, phase = latest
    return {
        "price": round(price, 4),
        "prev_close": round(float(prev_close), 4),
        "pct": round((price - float(prev_close)) / float(prev_close) * 100, 2),
        "time": when.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "session": phase,
        "source": "yahoo-chart-prepost",
    }


def main() -> int:
    now = datetime.now(timezone.utc)
    phase = session_at(now)
    if phase not in ("pre", "after"):
        print(f"session is '{phase}'; extended-hours fetch skipped")
        return 0

    quotes, errors = {}, []
    for symbol in _load_symbols():
        try:
            data = fetch_extended(symbol)
            if data:
                quotes[symbol] = data
        except Exception as exc:  # one symbol must not sink the run
            errors.append(f"{symbol}: {exc}")

    if not quotes:
        print("no extended-hours prints available; leaving previous file",
              file=sys.stderr)
        for err in errors[:5]:
            print("  warn:", err, file=sys.stderr)
        return 0

    write_json(OUT_PATH, {
        "updated": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "session": phase,
        "quotes": quotes,
        "errors": errors,
    }, indent=1)
    print(f"Wrote {OUT_PATH}: {len(quotes)} symbols in '{phase}' session; "
          f"{len(errors)} errors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
