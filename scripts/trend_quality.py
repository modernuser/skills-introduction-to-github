#!/usr/bin/env python3
"""Trend quality: how straight a line has each stock climbed?

For every constituent, regress LOG price on session number over a 90-day
window and keep two numbers:

  slope_annual_pct  the fitted exponential growth rate, annualized
  r2                how much of the price path that straight line explains

R-squared here is a goodness-of-fit statistic describing the PAST. A name
at r2 = 0.95 has risen in an unusually straight line; one at r2 = 0.20 got
to the same place by lurching. Selecting on it means selecting for orderly
trends rather than for big moves, which is why it is paired with the slope:
r2 alone would rank a stock that crept up 2% in a perfect line above one
that tripled with two pullbacks.

WHAT THIS IS NOT: it is not the R-squared of a return forecast. Those are
different quantities that share a name. A predictive R-squared near 0.88
on daily returns does not occur outside of overfitting — scripts/factor_lab
measures that one and reports it honestly, and it sits near zero. Nothing
here says a straight past line continues. That question is what the
dartboard experiment exists to answer, against a random control.

Log prices, not raw: a straight line in log space is a constant percentage
growth rate, which is what "trending" should mean. Fitting raw prices makes
every high-priced stock look like it curves.
"""

import json
import math
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from atomic import write_json

OUT_PATH = "data/trend_quality.json"
WINDOW = 90            # sessions in the regression, ~4.5 months
MIN_SESSIONS = 60      # shorter than this does not characterise a trend
TRADING_DAYS = 252
MIN_R2 = 0.88          # the straightness floor
SELECT_COUNT = 10


def fit(closes: list[float]) -> dict | None:
    """OLS of log(price) on session index. Returns slope, intercept, r2.

    Closed form rather than a solver: with one regressor the normal
    equations are two lines, and it runs over ~500 symbols.
    """
    if len(closes) < MIN_SESSIONS or any(c <= 0 for c in closes):
        return None
    y = [math.log(c) for c in closes]
    n = len(y)
    xs = list(range(n))
    mx = (n - 1) / 2
    my = sum(y) / n
    sxx = sum((x - mx) ** 2 for x in xs)
    sxy = sum((x - mx) * (v - my) for x, v in zip(xs, y))
    if sxx == 0:
        return None
    slope = sxy / sxx
    intercept = my - slope * mx

    ss_tot = sum((v - my) ** 2 for v in y)
    # Tolerance, not `== 0`: summing identical logs leaves float dust, which
    # would otherwise divide into a meaningless r2 for a flat price. Real
    # log-price variance over 90 sessions is many orders of magnitude above
    # this, so nothing genuine is discarded.
    if ss_tot < 1e-12:
        return None                     # a flat line: no trend to describe
    ss_res = sum((v - (intercept + slope * x)) ** 2 for x, v in zip(xs, y))
    r2 = 1 - ss_res / ss_tot

    # exp(slope) is the per-session growth factor; compound it over a year.
    # Clamped before exp so a degenerate fit cannot overflow the float.
    annual = (math.exp(min(slope * TRADING_DAYS, 700)) - 1) * 100
    return {
        "slope_annual_pct": round(annual, 2),
        "r2": round(r2, 4),
        "sessions": n,
    }


def score(row: dict) -> float:
    """Rank key: annualized slope discounted by how ragged the path was.

    Multiplying by r2 is what keeps this from being a pure momentum sort —
    a violent 300% move with r2 = 0.30 scores below a steady 120% at 0.95.
    """
    return row["slope_annual_pct"] * row["r2"]


def build(histories: dict[str, list[tuple[str, float]]], names: dict) -> dict:
    rows = []
    for symbol, history in histories.items():
        stats = fit([c for _, c in history[-WINDOW:]])
        if stats is None:
            continue
        rows.append({
            "symbol": symbol,
            "name": names.get(symbol, symbol),
            "last_close": history[-1][1],
            "as_of": history[-1][0],
            **stats,
        })
    rows.sort(key=score, reverse=True)
    return rows


def select(rows: list[dict], min_r2: float = MIN_R2,
           count: int = SELECT_COUNT) -> list[dict]:
    """The straightest strong uptrends: r2 >= floor AND rising."""
    qualified = [r for r in rows
                 if r["r2"] >= min_r2 and r["slope_annual_pct"] > 0]
    return qualified[:count]


def main(histories=None) -> int:
    import csv
    with open("data/sp500_constituents.csv") as f:
        names = {r["Symbol"].strip(): r["Security"].strip()
                 for r in csv.DictReader(f)}

    if histories is None:               # pragma: no cover - network path
        print("trend_quality needs histories; run it from sector_depth.py",
              file=sys.stderr)
        return 1

    rows = build(histories, names)
    picks = select(rows)
    write_json(OUT_PATH, {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "method": (f"OLS of log(close) on session index over {WINDOW} "
                   f"sessions; ranked by annualized slope x r2"),
        "note": ("r2 measures how straight the PAST price path was, not the "
                 "probability of anything. It is a goodness-of-fit statistic, "
                 "not a forecast and not advice. Whether straight past "
                 "trends continue is what the dartboard experiment tests, "
                 "against a random control."),
        "window_sessions": WINDOW,
        "min_r2": MIN_R2,
        "select_count": SELECT_COUNT,
        "measured": len(rows),
        "qualified": sum(1 for r in rows
                         if r["r2"] >= MIN_R2 and r["slope_annual_pct"] > 0),
        "selected": picks,
        "ranked": rows[:50],
    }, indent=1)
    print(f"Wrote {OUT_PATH}: {len(rows)} measured, "
          f"{len(picks)} selected at r2 >= {MIN_R2}")
    return 0


if __name__ == "__main__":              # pragma: no cover
    raise SystemExit(main())
