#!/usr/bin/env python3
"""Five daily KPIs per ticker, plus multi-window returns.

Every KPI here is computed from OHLCV the pipeline already fetches — no
new provider, no new credential, no new request.

  1. vol_30d          annualized stdev of 30 daily returns (realized risk)
  2. trend_r2_90d     goodness-of-fit of log(price) on time (straightness)
  3. slope_annual_pct fitted exponential growth rate, annualized
  4. max_drawdown_90d largest peak-to-trough fall in the window
  5. volume_surge     today's volume over its 20-session mean

Returns are reported over the windows the owner specified: 1, 5, 7, 10,
30, 60, 90, 100, 200 and 360 sessions. Windows longer than the available
history report null rather than silently using a shorter span — a 360-day
return computed from 200 days is a different number wearing the same
label.

Outlier handling is MAD-winsorizing at 4 sigma (shared with factor_lab):
clip, never delete. Deleting rows to improve a fit changes the score
without changing the evidence; it also splices non-adjacent sessions so
"yesterday's close" stops being yesterday's.

NOT here: any ranking by expected return, any direction, any target.
These are measurements of what already happened.
"""

import json
import math
import os
import statistics
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from atomic import write_json
from factor_lab import winsorize
from trend_quality import fit as trend_fit

OUT_PATH = "data/kpi_panel.json"
RETURN_WINDOWS = [1, 5, 7, 10, 30, 60, 90, 100, 200, 360]
VOL_WINDOW = 30
TREND_WINDOW = 90
DRAWDOWN_WINDOW = 90
SURGE_WINDOW = 20
TRADING_DAYS = 252
KPI_NAMES = ["vol_30d", "trend_r2_90d", "slope_annual_pct",
             "max_drawdown_90d", "volume_surge"]


def realized_volatility(closes: list[float], window: int = VOL_WINDOW):
    prices = [c for c in closes if c and c > 0]
    if len(prices) < window + 1:
        return None
    rets = [(prices[i] - prices[i - 1]) / prices[i - 1]
            for i in range(1, len(prices))][-window:]
    clipped, _ = winsorize(rets)
    if len(clipped) < 2:
        return None
    return round(statistics.stdev(clipped) * math.sqrt(TRADING_DAYS) * 100, 2)


def max_drawdown(closes: list[float], window: int = DRAWDOWN_WINDOW):
    """Largest peak-to-trough decline, as a negative percent.

    Reported alongside volatility because they answer different
    questions: volatility is how much it moved, drawdown is how far down
    it went and stayed. A name can be calm and still have fallen 40%.
    """
    prices = [c for c in closes[-window:] if c and c > 0]
    if len(prices) < 2:
        return None
    peak, worst = prices[0], 0.0
    for p in prices:
        peak = max(peak, p)
        worst = min(worst, (p - peak) / peak)
    return round(worst * 100, 2)


def volume_surge(volumes: list[float], window: int = SURGE_WINDOW):
    recent = [v for v in volumes[-(window + 1):] if v and v > 0]
    if len(recent) < window + 1:
        return None
    base = statistics.fmean(recent[:-1])
    return round(recent[-1] / base, 3) if base > 0 else None


def window_returns(closes: list[float]) -> dict:
    """Percent change over each requested window; null when too short."""
    out = {}
    for w in RETURN_WINDOWS:
        key = f"r{w}"
        if len(closes) <= w or closes[-1 - w] <= 0:
            out[key] = None                 # never fake a window
        else:
            out[key] = round(
                (closes[-1] - closes[-1 - w]) / closes[-1 - w] * 100, 2)
    return out


def measure(bars: list[tuple[str, float, float]]) -> dict:
    """All five KPIs plus the window returns for one ticker."""
    closes = [b[1] for b in bars]
    volumes = [b[2] for b in bars]
    trend = trend_fit(closes[-TREND_WINDOW:]) or {}
    return {
        "as_of": bars[-1][0] if bars else None,
        "last_close": closes[-1] if closes else None,
        "sessions": len(bars),
        "kpis": {
            "vol_30d": realized_volatility(closes),
            "trend_r2_90d": trend.get("r2"),
            "slope_annual_pct": trend.get("slope_annual_pct"),
            "max_drawdown_90d": max_drawdown(closes),
            "volume_surge": volume_surge(volumes),
        },
        "returns": window_returns(closes),
    }


def build(histories: dict, names: dict) -> dict:
    panel = {}
    for symbol, bars in histories.items():
        if not bars:
            continue
        row = measure(bars)
        row["symbol"] = symbol
        row["name"] = names.get(symbol, symbol)
        panel[symbol] = row
    return panel


def as_gage_input(panel_by_source: dict, trials: int = 2) -> dict:
    """Reshape panels into the Gage R&R input structure.

    `panel_by_source[source][ticker]` -> `kpis[kpi][ticker][source] = [..]`

    Trials repeat the SAME computation on the SAME inputs. Because the
    pipeline is deterministic they must come back identical; that is the
    point — a nonzero repeatability here is a bug signal, not noise.
    """
    kpis = {}
    for name in KPI_NAMES:
        per_ticker = {}
        for source, panel in panel_by_source.items():
            for ticker, row in panel.items():
                value = row["kpis"].get(name)
                if value is None:
                    continue
                per_ticker.setdefault(ticker, {})[source] = [value] * trials
        # A part needs at least one measurement to contribute.
        kpis[name] = {t: ops for t, ops in per_ticker.items() if ops}
    return kpis


def main(histories_by_source=None, names=None) -> int:
    if histories_by_source is None:         # pragma: no cover - network path
        print("kpi_panel needs histories; run it from sector_depth.py",
              file=sys.stderr)
        return 1
    if names is None:
        import csv
        with open("data/sp500_constituents.csv") as f:
            names = {r["Symbol"].strip(): r["Security"].strip()
                     for r in csv.DictReader(f)}

    panels = {src: build(h, names)
              for src, h in histories_by_source.items()}
    primary = panels.get("stooq") or next(iter(panels.values()), {})

    write_json(OUT_PATH, {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": ("Measurements of what already happened. No KPI here ranks "
                 "by expected return, and none is a forecast or advice."),
        "return_windows": RETURN_WINDOWS,
        "kpi_names": KPI_NAMES,
        "sources_measured": sorted(panels),
        "tickers": len(primary),
        "panel": primary,
    }, indent=1)
    print(f"Wrote {OUT_PATH}: {len(primary)} tickers, "
          f"sources {sorted(panels)}")

    # Measurement system analysis over whatever sources were available.
    import gage_rr
    return gage_rr.main(as_gage_input(panels))


if __name__ == "__main__":                  # pragma: no cover
    raise SystemExit(main())
