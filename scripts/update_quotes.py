#!/usr/bin/env python3
"""Fetch daily price history for the watchlist and write tracker data files.

Data sources:
- stooq.com free daily CSV
- Yahoo Finance chart API fallback

Writes:
- data/quotes.json
- data/suggested_tickers.json (data-driven watchlist suggestions)
"""

import csv
import io
import json
import os
import sys
import urllib.request
from datetime import UTC, datetime

# Ticker -> display name. SPY is the benchmark for context.
TICKERS = {
    "NVDA": "NVIDIA",
    "MU": "Micron Technology",
    "SNDK": "SanDisk",
    "SOXX": "iShares Semiconductor ETF",
    "SOXL": "Direxion Semi Bull 3X",
    "SPY": "S&P 500 ETF (benchmark)",
}

# A one-day move at or beyond this magnitude is flagged as significant.
SIGNIFICANT_PCT = 3.0
SUGGESTIONS_STALE_DAYS = 5

HISTORY_URL = "https://stooq.com/q/d/l/?s={symbol}.us&i=d"
YAHOO_URL = (
    "https://query1.finance.yahoo.com/v8/finance/chart/"
    "{symbol}?range=3mo&interval=1d"
)


def _now_iso() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read()


def fetch_history_stooq(symbol: str) -> list[dict]:
    text = _get(HISTORY_URL.format(symbol=symbol.lower())).decode(
        "utf-8", errors="replace"
    )
    rows = []
    for row in csv.DictReader(io.StringIO(text)):
        raw_close = (row.get("Close") or "").strip()
        raw_date = (row.get("Date") or "").strip()
        raw_volume = (row.get("Volume") or "").strip()
        if not raw_date or not raw_close or raw_close.upper() == "N/A":
            continue
        try:
            close = float(raw_close)
        except ValueError:
            continue
        volume = None
        if raw_volume and raw_volume.upper() != "N/A":
            try:
                parsed = int(float(raw_volume))
                if parsed > 0:
                    volume = parsed
            except ValueError:
                volume = None
        rows.append({"date": raw_date, "close": close, "volume": volume})
    return rows


def fetch_history_yahoo(symbol: str) -> list[dict]:
    payload = json.loads(_get(YAHOO_URL.format(symbol=symbol)))
    result = payload["chart"]["result"][0]
    stamps = result.get("timestamp") or []
    quote = result.get("indicators", {}).get("quote", [{}])[0]
    close_series = quote.get("close") or []
    volume_series = quote.get("volume") or []

    rows = []
    for i, ts in enumerate(stamps):
        if i >= len(close_series) or close_series[i] is None:
            continue
        date = datetime.fromtimestamp(ts, tz=UTC).strftime("%Y-%m-%d")
        volume = None
        if i < len(volume_series) and volume_series[i] is not None:
            parsed = int(volume_series[i])
            if parsed > 0:
                volume = parsed
        rows.append(
            {
                "date": date,
                "close": round(float(close_series[i]), 4),
                "volume": volume,
            }
        )
    return rows


def fetch_history(symbol: str) -> tuple[list[dict], str, str]:
    stooq_url = HISTORY_URL.format(symbol=symbol.lower())
    try:
        rows = fetch_history_stooq(symbol)
        if rows:
            return rows, "stooq", stooq_url
    except Exception:
        pass

    yahoo_url = YAHOO_URL.format(symbol=symbol)
    rows = fetch_history_yahoo(symbol)
    return rows, "yahoo", yahoo_url


def pct_change(rows: list[dict], sessions_back: int):
    if len(rows) <= sessions_back:
        return None
    latest = rows[-1]["close"]
    prior = rows[-1 - sessions_back]["close"]
    if prior == 0:
        return None
    return round((latest - prior) / prior * 100, 2)


def volume_ratio(rows: list[dict], lookback: int = 20):
    if len(rows) < 2:
        return None
    latest_volume = rows[-1].get("volume")
    if not latest_volume:
        return None

    window = [r.get("volume") for r in rows[-(lookback + 1) : -1] if r.get("volume")]
    if not window:
        return None

    avg_volume = sum(window) / len(window)
    if avg_volume <= 0:
        return None
    return round(latest_volume / avg_volume, 2)


def is_stale(latest_date: str, now: datetime) -> bool:
    try:
        dt = datetime.strptime(latest_date, "%Y-%m-%d").replace(tzinfo=UTC)
    except ValueError:
        return True
    return (now - dt).days > SUGGESTIONS_STALE_DAYS


def build_suggestions(quotes: list[dict], errors: list[str], updated_iso: str) -> dict:
    now = datetime.now(UTC)
    by_symbol = {q["symbol"]: q for q in quotes}

    required = ["SPY", "SOXX"]
    missing = [sym for sym in required if sym not in by_symbol]
    if missing:
        return {
            "updated": updated_iso,
            "status": "unavailable",
            "message": "Suggestions unavailable: required benchmark data missing.",
            "errors": errors + [f"Missing required symbols: {', '.join(missing)}"],
            "suggestions": [],
        }

    stale_symbols = [
        q["symbol"]
        for q in quotes
        if not q.get("date") or is_stale(q["date"], now)
    ]
    if stale_symbols:
        return {
            "updated": updated_iso,
            "status": "unavailable",
            "message": "Suggestions unavailable: one or more sources are stale.",
            "errors": errors + [f"Stale quote dates for: {', '.join(stale_symbols)}"],
            "suggestions": [],
        }

    spy = by_symbol["SPY"]
    soxx = by_symbol["SOXX"]
    candidates = []

    for q in quotes:
        symbol = q["symbol"]
        if symbol == "SPY":
            continue

        signals = []
        if q["w1"] is not None and spy["w1"] is not None and (q["w1"] - spy["w1"]) >= 2.0:
            signals.append(
                {
                    "name": "1W relative strength vs SPY",
                    "value": f"{q['w1']:.2f}% vs SPY {spy['w1']:.2f}%",
                    "source_url": q["source_url"],
                    "source_timestamp": q["date"],
                    "retrieved_at": q["retrieved_at"],
                }
            )

        ratio = q.get("volume_ratio")
        if ratio is not None and ratio >= 1.5 and q["d1"] is not None and abs(q["d1"]) >= SIGNIFICANT_PCT:
            signals.append(
                {
                    "name": "Significant daily move with unusual volume",
                    "value": f"1D {q['d1']:.2f}% with volume {ratio:.2f}x 20-session avg",
                    "source_url": q["source_url"],
                    "source_timestamp": q["date"],
                    "retrieved_at": q["retrieved_at"],
                }
            )

        if symbol in {"NVDA", "MU", "SNDK", "SOXL", "SOXX"} and soxx["w1"] is not None and spy["w1"] is not None and (soxx["w1"] - spy["w1"]) >= 1.5:
            signals.append(
                {
                    "name": "Semiconductor sector trend confirmation",
                    "value": f"SOXX 1W {soxx['w1']:.2f}% vs SPY {spy['w1']:.2f}%",
                    "source_url": soxx["source_url"],
                    "source_timestamp": soxx["date"],
                    "retrieved_at": soxx["retrieved_at"],
                }
            )

        if len(signals) < 2:
            continue

        score = len(signals)
        if q["w1"] is not None and spy["w1"] is not None:
            score += max(0.0, (q["w1"] - spy["w1"]) / 5.0)

        reason = (
            f"{symbol} is flagged as a watch candidate from current verified data. "
            f"It met {len(signals)} independent signal rules tied to benchmark and/or volume behavior."
        )

        candidates.append(
            {
                "symbol": symbol,
                "name": q["name"],
                "reason": reason,
                "score": round(score, 2),
                "last_verified": updated_iso,
                "signals": signals,
                "primary_sources": sorted({s["source_url"] for s in signals}),
            }
        )

    candidates.sort(key=lambda c: c["score"], reverse=True)

    return {
        "updated": updated_iso,
        "status": "ready",
        "message": (
            "Educational watchlist candidates only, based on deterministic rules and "
            "verifiable source data. Not buy/sell advice."
        ),
        "errors": errors,
        "suggestions": candidates[:3],
        "rules": [
            "1W performance must exceed SPY by at least 2.0 percentage points.",
            "Daily move of ±3% or more with at least 1.5x 20-session average volume.",
            "Semiconductor names require SOXX 1W confirmation vs SPY by at least 1.5 percentage points.",
            "At least two independent rules must pass for a ticker to be suggested.",
        ],
    }


def main() -> int:
    quotes = []
    errors = []
    updated_iso = _now_iso()

    for symbol, name in TICKERS.items():
        try:
            rows, source, source_url = fetch_history(symbol)
        except Exception as exc:  # network or parse failure for one symbol
            errors.append(f"{symbol}: {exc}")
            continue

        if not rows:
            errors.append(f"{symbol}: no data returned")
            continue

        d1 = pct_change(rows, 1)
        quote = {
            "symbol": symbol,
            "name": name,
            "date": rows[-1]["date"],
            "close": rows[-1]["close"],
            "d1": d1,
            "w1": pct_change(rows, 5),
            "m1": pct_change(rows, 21),
            "significant": d1 is not None and abs(d1) >= SIGNIFICANT_PCT,
            "recent": [r["close"] for r in rows[-30:]],
            "volume": rows[-1].get("volume"),
            "volume_ratio": volume_ratio(rows),
            "source": source,
            "source_url": source_url,
            "retrieved_at": updated_iso,
        }
        quotes.append(quote)

    if not quotes:
        print("All fetches failed:\n" + "\n".join(errors), file=sys.stderr)
        return 1

    out = {
        "updated": updated_iso,
        "significant_pct": SIGNIFICANT_PCT,
        "quotes": quotes,
        "errors": errors,
    }

    suggestions = build_suggestions(quotes, errors, updated_iso)

    os.makedirs("data", exist_ok=True)
    with open("data/quotes.json", "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    with open("data/suggested_tickers.json", "w", encoding="utf-8") as f:
        json.dump(suggestions, f, indent=1)

    print(f"Wrote data/quotes.json with {len(quotes)} symbols; {len(errors)} errors")
    print(
        f"Wrote data/suggested_tickers.json with {len(suggestions.get('suggestions', []))} suggestions"
    )
    for e in errors:
        print("  warn:", e, file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
