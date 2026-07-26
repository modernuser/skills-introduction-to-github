#!/usr/bin/env python3
"""The dartboard experiment: three paper portfolios, same fake $10,000.

- owner:     the watchlist's non-benchmark tickers, equal-weighted
- dartboard: N random S&P 500 constituents, chosen ONCE by a seeded RNG
             (recorded in the file, fully reproducible), equal-weighted
- spy:       everything in SPY

Seeds itself on the first run where prices exist; afterwards each run
revalues holdings and records one history point per trading day. Alpha is
REALIZED return minus SPY's realized return — observed, never projected.
Prices reuse data already fetched: quotes.json (watchlist + SPY) and
sp500_closes.json (all constituents, from the Rolling 500).
"""

import csv
import json
import os
import random
import sys

STATE_PATH = "data/portfolios.json"
START_CASH = 10000.0
DART_COUNT = 11


def load_prices():
    """symbol -> {date, close} from watchlist quotes + S&P closes state."""
    prices = {}
    if os.path.exists("data/sp500_closes.json"):
        with open("data/sp500_closes.json") as f:
            prices.update(json.load(f))
    with open("data/quotes.json") as f:
        q = json.load(f)
    for item in q["quotes"]:
        prices[item["symbol"]] = {"date": item["date"], "close": item["close"]}
    return prices


def constituent_names():
    with open("data/sp500_constituents.csv") as f:
        return {r["Symbol"].strip(): r["Security"].strip()
                for r in csv.DictReader(f)}


def equal_weight_holdings(symbols, prices, names):
    per = START_CASH / len(symbols)
    return [{
        "symbol": s,
        "name": names.get(s, s),
        "shares": round(per / prices[s]["close"], 6),
        "start_close": prices[s]["close"],
        "last_close": prices[s]["close"],
    } for s in symbols]


def seed(prices):
    with open("watchlist.json") as f:
        watch = json.load(f)["watchlist"]
    owner_syms = [s for s, name in watch.items() if "benchmark" not in name.lower()]
    sp_universe = sorted(
        s for s in json.load(open("data/sp500_closes.json"))
        if s in constituent_names() and prices.get(s, {}).get("close", 0) > 0
    )
    missing = [s for s in owner_syms + ["SPY"] if prices.get(s, {}).get("close", 0) <= 0]
    if missing or len(sp_universe) < 100:
        print(f"cannot seed yet (missing prices: {missing or 'S&P universe'})")
        return None

    start_date = max(prices[s]["date"] for s in owner_syms)
    rng_seed = int(start_date.replace("-", ""))
    dart_syms = random.Random(rng_seed).sample(sp_universe, DART_COUNT)
    names = constituent_names()
    names.update({s: watch[s] for s in owner_syms})

    return {
        "start_date": start_date,
        "start_cash": START_CASH,
        "rng_seed": rng_seed,
        "note": ("Paper experiment. Owner picks = watchlist ex-benchmarks; "
                 "dartboard = seeded random draw from S&P 500 constituents; "
                 "alpha = realized return minus SPY's. Not advice."),
        "portfolios": {
            "owner": {"label": "Owner's picks",
                      "holdings": equal_weight_holdings(owner_syms, prices, names)},
            "dartboard": {"label": "Dartboard (random)",
                          "holdings": equal_weight_holdings(dart_syms, prices, names)},
            "spy": {"label": "Just buy SPY",
                    "holdings": equal_weight_holdings(["SPY"], prices, names)},
        },
        "history": [],
    }


def revalue(state, prices):
    returns = {}
    for key, p in state["portfolios"].items():
        value = 0.0
        for h in p["holdings"]:
            fresh = prices.get(h["symbol"], {}).get("close", 0)
            if fresh > 0:
                h["last_close"] = fresh
            value += h["shares"] * h["last_close"]
        p["value"] = round(value, 2)
        p["return_pct"] = round((value / state["start_cash"] - 1) * 100, 2)
        returns[key] = p["return_pct"]
    for key, p in state["portfolios"].items():
        p["alpha_pp"] = round(returns[key] - returns["spy"], 2)

    asof = max((prices[h["symbol"]]["date"]
                for p in state["portfolios"].values() for h in p["holdings"]
                if h["symbol"] in prices), default=state["start_date"])
    state["asof"] = asof
    point = {"date": asof,
             **{k: state["portfolios"][k]["return_pct"] for k in state["portfolios"]}}
    hist = state["history"]
    if hist and hist[-1]["date"] == asof:
        hist[-1] = point
    else:
        hist.append(point)


def main() -> int:
    prices = load_prices()
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            state = json.load(f)
    else:
        state = seed(prices)
        if state is None:
            return 0
        print(f"seeded portfolios on {state['start_date']} "
              f"(rng_seed {state['rng_seed']})")

    revalue(state, prices)
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=1)
    p = state["portfolios"]
    print("portfolios:", ", ".join(
        f"{k} ${p[k]['value']:.0f} ({p[k]['return_pct']:+.2f}%, "
        f"alpha {p[k]['alpha_pp']:+.2f}pp)" for k in p))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
