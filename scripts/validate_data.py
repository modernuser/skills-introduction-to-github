#!/usr/bin/env python3
"""Validate the data files the pipeline is about to commit.

Runs in the workflow after the fetch steps and before the commit, so a
run that produced malformed or stale output fails loudly (which opens an
alert issue) instead of publishing garbage. This is the in-repo verifier:
it works whether or not any interactive session is around to check.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from atomic import write_json
from market_session import describe, last_session_close

MAX_QUOTE_AGE_DAYS = 6  # stooq date can lag a long weekend, never a week
STALE_AGE_DAYS = 4      # fallback; session-aware check below is primary


def fail(msg: str):
    print(f"VALIDATION FAILED: {msg}", file=sys.stderr)
    sys.exit(1)


def file_age_days(iso_ts: str) -> float:
    ts = datetime.strptime(iso_ts, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    return round((datetime.now(timezone.utc) - ts).total_seconds() / 86400, 2)


def write_health(q, newest, started) -> None:
    """Machine-readable health report next to the data it describes."""
    files = {}
    quote_age = (datetime.now(timezone.utc)
                 - datetime.strptime(newest, "%Y-%m-%d").replace(tzinfo=timezone.utc)).days
    # Session-aware: measure against the last real session close, so a
    # weekend or holiday never looks like a broken pipeline.
    behind_close = (last_session_close(datetime.now(timezone.utc)).date()
                    - datetime.strptime(newest, "%Y-%m-%d").date()).days
    files["quotes"] = {
        "present": True, "updated": q["updated"],
        "records": len(q["quotes"]) + len(q.get("core", [])) + len(q["sectors"]),
        "newest_record_age_days": quote_age,
        "sessions_behind_last_close": behind_close,
        "status": "stale" if behind_close > 1 else "ok",
    }
    for name in ("news", "movers", "rotation", "portfolios", "extended",
                 "sector_depth", "factor_lab"):
        path = f"data/{name}.json"
        if not os.path.exists(path):
            files[name] = {"present": False, "status": "missing"}
            continue
        with open(path) as f:
            d = json.load(f)
        entry = {"present": True, "status": "ok"}
        updated = d.get("updated") or d.get("asof") or d.get("generated")
        if updated:
            entry["updated"] = updated
            if "T" in updated and file_age_days(updated) > STALE_AGE_DAYS + 1:
                entry["status"] = "stale"
        entry["records"] = (len(d.get("news", {})) or len(d.get("entries", []))
                            or len(d.get("gainers", [])) * 2
                            or len(d.get("portfolios", {}))
                            or sum(len(v) for v in d.get("sectors", {}).values()))
        files[name] = entry
    session = describe()
    write_json("data/health.json", {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "market": session,
        "duration_ms": int((time.monotonic() - started) * 1000),
        "source_errors": q.get("errors", []),
        "primary_source_failures_count": q.get("fallback_count", 0),
        "files": files,
        "overall": ("degraded"
                    if any(v["status"] == "stale" for v in files.values())
                    or q.get("errors") else "ok"),
    }, indent=1)


def main() -> int:
    started = time.monotonic()
    with open("data/quotes.json") as f:
        q = json.load(f)
    if len(q.get("quotes", [])) < 5:
        fail(f"only {len(q.get('quotes', []))} quotes")
    if len(q.get("sectors", [])) != 11:
        fail(f"{len(q.get('sectors', []))} sectors, expected 11")
    for item in q["quotes"] + q["sectors"] + q.get("core", []):
        if not (item.get("close", 0) > 0):
            fail(f"non-positive close for {item.get('symbol')}")
        if not all(isinstance(item.get(k), (int, float)) for k in ("d1", "w1", "m1")):
            fail(f"missing move fields for {item.get('symbol')}")
        if "hi52" in item:
            if not (item["lo52"] - 0.01 <= item["close"] <= item["hi52"] + 0.01):
                fail(f"close outside 52-week range for {item.get('symbol')}")
    newest = max(item["date"] for item in q["quotes"])
    age = (datetime.now(timezone.utc)
           - datetime.strptime(newest, "%Y-%m-%d").replace(tzinfo=timezone.utc)).days
    if age > MAX_QUOTE_AGE_DAYS:
        fail(f"newest quote date {newest} is {age} days old")

    if os.path.exists("data/news.json"):
        with open("data/news.json") as f:
            n = json.load(f)
        if not isinstance(n.get("news"), dict) or not n["news"]:
            fail("news.json has no headlines")

    if os.path.exists("data/movers.json"):
        with open("data/movers.json") as f:
            m = json.load(f)
        for key in ("gainers", "losers"):
            lst = m.get(key, [])
            if len(lst) != 10:
                fail(f"movers {key} has {len(lst)} entries")
            if any(not (x.get("close", 0) > 0) for x in lst):
                fail(f"movers {key} has non-positive close")

    if os.path.exists("data/extended.json"):
        with open("data/extended.json") as f:
            ext = json.load(f)
        if ext.get("session") not in ("pre", "after"):
            fail(f"extended.json has invalid session {ext.get('session')!r}")
        for sym, e in ext.get("quotes", {}).items():
            if not (e.get("price", 0) > 0 and e.get("prev_close", 0) > 0):
                fail(f"extended quote {sym} has non-positive price")

    if os.path.exists("data/sector_depth.json"):
        with open("data/sector_depth.json") as f:
            sd = json.load(f)
        per = sd.get("per_sector", 10)
        for sector, rows in sd.get("sectors", {}).items():
            if len(rows) > per:
                fail(f"sector {sector} has {len(rows)} rows, max {per}")
            for r in rows:
                if not (r.get("vol_30d", 0) > 0):
                    fail(f"non-positive volatility for {r.get('symbol')}")
                if not (r.get("last_close", 0) > 0):
                    fail(f"non-positive close for {r.get('symbol')}")
            ordered = [r["vol_30d"] for r in rows]
            if ordered != sorted(ordered, reverse=True):
                fail(f"sector {sector} is not ordered by volatility")

    if os.path.exists("data/factor_lab.json"):
        with open("data/factor_lab.json") as f:
            fl = json.load(f)
        # Structural enforcement of the project's standing boundary: this
        # file reports how well features track outcomes, and must never
        # acquire a direction, a confidence score, or a target flag.
        banned = {"direction", "likelihood", "likelihood_pct", "signal",
                  "target_acquired", "recommendation", "buy", "sell"}
        for result in fl.get("results", []):
            for section in ("features", "noise_control"):
                leaked = banned & {k.lower() for k in result.get(section, {})}
                if leaked:
                    fail(f"factor_lab {result.get('symbol')} emits {leaked}")
            stats = result.get("features", {})
            if stats.get("evaluated") and stats.get("oos_sessions", 0) < 2:
                fail(f"factor_lab {result.get('symbol')} claims an "
                     "evaluation with no out-of-sample points")

    if os.path.exists("data/portfolios.json"):
        with open("data/portfolios.json") as f:
            pf = json.load(f)
        for key, p in pf["portfolios"].items():
            if not (p.get("value", 0) > 0):
                fail(f"portfolio {key} has non-positive value")
            if any(h["shares"] <= 0 or h["last_close"] <= 0 for h in p["holdings"]):
                fail(f"portfolio {key} has a broken holding")

    write_health(q, newest, started)
    print(f"validation OK: {len(q['quotes'])} quotes (newest {newest}), "
          "sectors/news/movers/portfolios well-formed; health report written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
