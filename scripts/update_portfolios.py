#!/usr/bin/env python3
"""The dartboard experiment: four paper portfolios, same fake $10,000.

- owner:     the watchlist's non-benchmark tickers, equal-weighted
- dartboard: N random S&P 500 constituents, chosen ONCE by a seeded RNG
             (recorded in the file, fully reproducible), equal-weighted
- trend:     the 10 straightest strong uptrends (trend_quality.py), i.e.
             r2 >= 0.88 of log-price on time, ranked by slope x r2
- spy:       everything in SPY

The random arm is the control that makes the others mean something: a
selection rule only earns credit for beating the darts, not merely for
making money in a rising market.

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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import trend_quality
from atomic import write_json

STATE_PATH = "data/portfolios.json"
TREND_PATH = "data/trend_quality.json"
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
    if not os.path.exists("data/sp500_closes.json"):
        print("cannot seed yet (no data/sp500_closes.json — the S&P closes "
              "state has not been built)")
        return None
    with open("data/sp500_closes.json") as f:
        universe_symbols = json.load(f)
    sp_universe = sorted(
        s for s in universe_symbols
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

    state = {
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
    add_trend_portfolio(state, prices, names)
    return state


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

    # Alpha is measured against SPY OVER THE SAME WINDOW. A portfolio added
    # later than the others starts its clock later, so comparing its return
    # to SPY's since the original inception would credit or penalise it for
    # a stretch it never held anything through. `spy_return_at_start`
    # records where SPY stood the day that portfolio was funded; it is 0
    # for the three seeded at inception, which reduces to a plain
    # difference.
    spy_now = returns["spy"]
    for key, p in state["portfolios"].items():
        base = p.get("spy_return_at_start", 0.0)
        spy_window = ((1 + spy_now / 100) / (1 + base / 100) - 1) * 100
        p["alpha_pp"] = round(returns[key] - spy_window, 2)

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


def trend_symbols():
    """The straightest strong uptrends, per data/trend_quality.json.

    Returns [] when the file is absent or nothing clears the r2 floor —
    an empty arm is the correct outcome of a strict screen in a choppy
    tape, not an error to paper over with a looser threshold.
    """
    if not os.path.exists(TREND_PATH):
        return []
    with open(TREND_PATH) as f:
        return [r["symbol"] for r in json.load(f).get("selected", [])]


def add_trend_portfolio(state, prices, names):
    """Fund the trend arm the first time a qualifying selection exists.

    Seeded separately because it cannot be built until a trend file has
    been written, which happens after the first post-close run.
    """
    symbols = [s for s in trend_symbols()
               if prices.get(s, {}).get("close", 0) > 0]
    if not symbols:
        return False
    state["portfolios"]["trend"] = {
        "label": f"Trend quality (r2 >= {trend_quality.MIN_R2})",
        "start_date": max(prices[s]["date"] for s in symbols),
        "spy_return_at_start": state["portfolios"]["spy"].get("return_pct", 0.0),
        "selection": ("top 10 by annualized log-price slope x r2, "
                      f"among names with r2 >= {trend_quality.MIN_R2} "
                      f"over {trend_quality.WINDOW} sessions"),
        "holdings": equal_weight_holdings(symbols, prices, names),
    }
    return True


def main() -> int:
    prices = load_prices()
    if os.path.exists(STATE_PATH):
        with open(STATE_PATH) as f:
            state = json.load(f)
        if "trend" not in state["portfolios"]:
            names = constituent_names()
            with open("watchlist.json") as f:
                names.update(json.load(f)["watchlist"])
            if add_trend_portfolio(state, prices, names):
                print("funded the trend-quality portfolio "
                      f"({len(state['portfolios']['trend']['holdings'])} names)")
    else:
        state = seed(prices)
        if state is None:
            return 0
        print(f"seeded portfolios on {state['start_date']} "
              f"(rng_seed {state['rng_seed']})")

    revalue(state, prices)
    write_json(STATE_PATH, state, indent=1)
    p = state["portfolios"]
    print("portfolios:", ", ".join(
        f"{k} ${p[k]['value']:.0f} ({p[k]['return_pct']:+.2f}%, "
        f"alpha {p[k]['alpha_pp']:+.2f}pp)" for k in p))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
