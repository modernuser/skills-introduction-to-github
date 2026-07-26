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
from datetime import datetime, timezone

MAX_QUOTE_AGE_DAYS = 6  # stooq date can lag a long weekend, never a week


def fail(msg: str):
    print(f"VALIDATION FAILED: {msg}", file=sys.stderr)
    sys.exit(1)


def main() -> int:
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

    if os.path.exists("data/portfolios.json"):
        with open("data/portfolios.json") as f:
            pf = json.load(f)
        for key, p in pf["portfolios"].items():
            if not (p.get("value", 0) > 0):
                fail(f"portfolio {key} has non-positive value")
            if any(h["shares"] <= 0 or h["last_close"] <= 0 for h in p["holdings"]):
                fail(f"portfolio {key} has a broken holding")

    print(f"validation OK: {len(q['quotes'])} quotes (newest {newest}), "
          "sectors/news/movers/portfolios well-formed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
