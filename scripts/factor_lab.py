#!/usr/bin/env python3
"""Factor lab: does a candidate feature predict tomorrow's return at all?

This measures predictive power out-of-sample and reports the answer
honestly, including when the answer is "no". It ranks nothing, scores no
opportunity, and emits no direction — the output is a diagnostic about
FEATURES, not a statement about what any price will do next.

Two features are carried over from the batch this replaces:

  vol_surge      today's volume over its trailing 20-session mean
  vwap_momentum  close vs the 10-session volume-weighted average price

Both are real, standard constructions. Three things about the original
method were not, and are corrected here:

1. Two of its four "features" were np.random.normal(0, 1) placeholders.
   Random regressors cannot predict anything, but they DO absorb variance
   in-sample, so they inflate the very score used to accept the model.
   They are gone. In their place is one deliberate noise column, never
   fitted alongside the real ones — it is run as a separate control so
   every report carries a visible "this is what no skill looks like"
   reading on the same data.

2. R-squared was computed on the same rows the model was fitted to.
   In-sample fit on daily returns is not evidence; with enough columns it
   reaches any threshold you like on pure noise. Everything here is
   walk-forward: fit on the past, predict one unseen session, step, repeat.
   Out-of-sample R-squared near zero (or negative) is the normal, correct
   result for next-day returns, not a bug.

3. Confidence was `min(abs(pred) * 1000 + 50, 99.9)`. That number looks
   like a probability and is not one. It is replaced by the information
   coefficient — the rank correlation between prediction and outcome —
   reported with the t-statistic of its null, so a reading can actually be
   compared against chance.

Stdlib only: this runs in the same pipeline as everything else, which
installs no scientific stack.
"""

import json
import os
import statistics
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from atomic import write_json

OUT_PATH = "data/factor_lab.json"
VOL_WINDOW = 20        # trailing sessions for the volume baseline
VWAP_WINDOW = 10       # trailing sessions for the volume-weighted price
MIN_TRAIN = 120        # sessions before the first out-of-sample prediction
MIN_OOS = 30           # fewer unseen points than this is not a measurement
WINSOR_K = 4.0         # robust clip, in MAD-sigmas, applied to returns
RIDGE = 1e-6           # tiny penalty; keeps a singular design solvable
PACE_SECONDS = 0.25
MAD_TO_SIGMA = 1.4826  # scales median-absolute-deviation to a normal sigma


# --------------------------------------------------------------------------
# Robust statistics
# --------------------------------------------------------------------------

def winsorize(values: list[float], k: float = WINSOR_K) -> tuple[list, int]:
    """Clip extreme values to k robust sigmas. Returns (clipped, n_clipped).

    Three corrections to the original 3-sigma scrub, which filtered price
    LEVELS and deleted the offending rows:

    * Levels are not stationary. Over a year of an uptrend the mean sits
      below recent price, so a level filter preferentially deletes the
      most recent sessions — the ones every downstream feature needs.
      Returns are the stationary quantity, so the filter belongs there.
    * Mean and standard deviation are themselves dragged by the outliers
      they are meant to catch. Median and MAD are not.
    * Deleting rows from a time series silently splices non-adjacent
      sessions together, after which "yesterday's close" is not
      yesterday's. Clipping keeps every timestamp and caps the magnitude.

    Note this is a modelling convenience, not a claim that tails are
    noise. Fat tails in returns are real and are where the risk lives;
    they are capped here only so a single print cannot dominate a fit.
    """
    if len(values) < 3:
        return list(values), 0
    med = statistics.median(values)
    deviations = [abs(v - med) for v in values]
    scale = statistics.median(deviations)
    if scale == 0:
        # More than half the values sit exactly on the median, so the MAD
        # collapses to zero and every outlier is "infinitely many sigmas".
        # Fall back to the mean absolute deviation, which stays finite and
        # still ignores the sign of the excursion.
        scale = statistics.fmean(deviations)
    if scale == 0:
        return list(values), 0            # genuinely constant: nothing to clip
    lo, hi = med - k * MAD_TO_SIGMA * scale, med + k * MAD_TO_SIGMA * scale
    out, clipped = [], 0
    for v in values:
        if v < lo:
            out.append(lo)
            clipped += 1
        elif v > hi:
            out.append(hi)
            clipped += 1
        else:
            out.append(v)
    return out, clipped


def spearman(a: list[float], b: list[float]):
    """Rank correlation. Robust to the outliers Pearson would chase."""
    n = len(a)
    if n < 3:
        return None

    def ranks(xs):
        order = sorted(range(n), key=lambda i: xs[i])
        r = [0.0] * n
        i = 0
        while i < n:                      # average ranks within ties
            j = i
            while j + 1 < n and xs[order[j + 1]] == xs[order[i]]:
                j += 1
            avg = (i + j) / 2 + 1
            for k in range(i, j + 1):
                r[order[k]] = avg
            i = j + 1
        return r

    ra, rb = ranks(a), ranks(b)
    ma, mb = statistics.fmean(ra), statistics.fmean(rb)
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    den = (sum((x - ma) ** 2 for x in ra) * sum((y - mb) ** 2 for y in rb)) ** 0.5
    return round(num / den, 4) if den else None


def r_squared(actual: list[float], pred: list[float]):
    """Out-of-sample R-squared against the in-sample mean baseline.

    Negative is a real and common outcome: it means the model did worse
    than predicting a constant. In-sample R-squared cannot go negative,
    which is exactly why it flatters a useless model.
    """
    if len(actual) < 2:
        return None
    mu = statistics.fmean(actual)
    ss_tot = sum((a - mu) ** 2 for a in actual)
    if ss_tot == 0:
        return None
    ss_res = sum((a - p) ** 2 for a, p in zip(actual, pred))
    return round(1 - ss_res / ss_tot, 4)


# --------------------------------------------------------------------------
# Least squares (normal equations + ridge, Gauss-Jordan)
# --------------------------------------------------------------------------

def ols(X: list[list[float]], y: list[float]) -> list[float]:
    """Solve (X'X + ridge*I) b = X'y. X must already carry an intercept."""
    k = len(X[0])
    aug = []
    for i in range(k):
        row = [sum(X[r][i] * X[r][j] for r in range(len(X))) for j in range(k)]
        row[i] += RIDGE
        row.append(sum(X[r][i] * y[r] for r in range(len(X))))
        aug.append(row)
    for c in range(k):
        piv = max(range(c, k), key=lambda r: abs(aug[r][c]))
        aug[c], aug[piv] = aug[piv], aug[c]
        if abs(aug[c][c]) < 1e-12:
            continue                      # collinear column: leave at zero
        for r in range(k):
            if r != c and aug[r][c]:
                f = aug[r][c] / aug[c][c]
                for j in range(c, k + 1):
                    aug[r][j] -= f * aug[c][j]
    return [aug[i][k] / aug[i][i] if abs(aug[i][i]) > 1e-12 else 0.0
            for i in range(k)]


def standardize(cols: list[list[float]]) -> list[list[float]]:
    """Z-score each column so the ridge penalty is scale-fair.

    vol_surge lives near 1.0 and vwap_momentum near 0.005; without this a
    single penalty term would fall almost entirely on the smaller one.
    """
    out = []
    for col in cols:
        mu = statistics.fmean(col)
        sd = statistics.pstdev(col)
        out.append([0.0] * len(col) if sd == 0 else [(v - mu) / sd for v in col])
    return out


# --------------------------------------------------------------------------
# Features
# --------------------------------------------------------------------------

def build_rows(bars: list[tuple[str, float, float]]) -> list[dict]:
    """One row per session that has full history behind it AND a next-day
    outcome ahead of it.

    Every feature at index i is computed from sessions strictly before i,
    and the target is the return from i to i+1. Nothing in a row's inputs
    is dated at or after the outcome it is paired with, which is what
    keeps the walk-forward below honest.
    """
    dates = [b[0] for b in bars]
    closes = [b[1] for b in bars]
    volumes = [b[2] for b in bars]

    raw_returns = [0.0] + [
        (closes[i] - closes[i - 1]) / closes[i - 1] if closes[i - 1] else 0.0
        for i in range(1, len(closes))
    ]
    returns, clipped = winsorize(raw_returns)

    start = max(VOL_WINDOW, VWAP_WINDOW)
    rows = []
    for i in range(start, len(closes) - 1):
        base = statistics.fmean(volumes[i - VOL_WINDOW:i])
        if base <= 0:
            continue
        pv = sum(closes[j] * volumes[j] for j in range(i - VWAP_WINDOW, i))
        vv = sum(volumes[j] for j in range(i - VWAP_WINDOW, i))
        if vv <= 0:
            continue
        vwap = pv / vv
        if vwap <= 0 or closes[i] <= 0:
            continue
        rows.append({
            "date": dates[i],
            "vol_surge": volumes[i] / base,
            "vwap_momentum": closes[i] / vwap - 1,
            "target": returns[i + 1],
        })
    return rows, clipped


# --------------------------------------------------------------------------
# Walk-forward evaluation
# --------------------------------------------------------------------------

def walk_forward(rows: list[dict], feature_names: list[str],
                 min_train: int = MIN_TRAIN) -> dict:
    """Expanding-window backtest: fit on the past, predict one unseen day.

    The model never sees the row it is scored on, nor any row after it.
    """
    if len(rows) < min_train + MIN_OOS:
        return {"evaluated": False,
                "reason": f"need {min_train + MIN_OOS} rows, have {len(rows)}"}

    preds, actuals, dates = [], [], []
    for cut in range(min_train, len(rows)):
        train = rows[:cut]
        cols = standardize([[r[f] for r in train] for f in feature_names])
        X = [[1.0] + [cols[c][i] for c in range(len(feature_names))]
             for i in range(len(train))]
        y = [r["target"] for r in train]
        beta = ols(X, y)

        # Standardize the held-out row with TRAIN statistics only. Using
        # full-sample moments here would leak the future into the input.
        x_new = [1.0]
        for f in feature_names:
            series = [r[f] for r in train]
            mu, sd = statistics.fmean(series), statistics.pstdev(series)
            x_new.append(0.0 if sd == 0 else (rows[cut][f] - mu) / sd)

        preds.append(sum(b * v for b, v in zip(beta, x_new)))
        actuals.append(rows[cut]["target"])
        dates.append(rows[cut]["date"])

    ic = spearman(preds, actuals)
    n = len(preds)
    # Under the null of no skill the rank correlation has SE ~ 1/sqrt(n-1).
    t_stat = round(ic * ((n - 1) ** 0.5), 2) if ic is not None else None
    hit = sum(1 for p, a in zip(preds, actuals)
              if (p > 0 and a > 0) or (p < 0 and a < 0))
    return {
        "evaluated": True,
        "oos_sessions": n,
        "first_oos": dates[0],
        "last_oos": dates[-1],
        "oos_r2": r_squared(actuals, preds),
        "information_coefficient": ic,
        "ic_t_stat": t_stat,
        # A coin flip is 50%. Reported for context only: direction accuracy
        # says nothing about whether the moves it got right were the big ones.
        "direction_agreement_pct": round(hit / n * 100, 1),
    }


def evaluate_symbol(symbol: str, bars: list[tuple[str, float, float]]) -> dict:
    rows, clipped = build_rows(bars)
    real = walk_forward(rows, ["vol_surge", "vwap_momentum"])

    # Control: the identical protocol driven by a feature that cannot
    # predict anything. Whatever the real features score, it should be
    # read against this, not against zero and not against 0.88.
    import random
    rng = random.Random(hash(symbol) & 0xFFFF)
    noise_rows = [dict(r, noise=rng.gauss(0, 1)) for r in rows]
    control = walk_forward(noise_rows, ["noise"])

    return {
        "symbol": symbol,
        "sessions": len(bars),
        "rows_modelled": len(rows),
        "returns_winsorized": clipped,
        "features": real,
        "noise_control": control,
    }


def main(bars_for=None) -> int:
    if bars_for is None:                  # pragma: no cover - network path
        from market_data import fetch_ohlcv

        def bars_for(symbol):
            time.sleep(PACE_SECONDS)
            return fetch_ohlcv(symbol)

    with open("watchlist.json") as f:
        watchlist = json.load(f)
    symbols = list(watchlist["watchlist"])

    results, errors = [], []
    for symbol in symbols:
        try:
            bars = bars_for(symbol)
        except Exception as exc:
            errors.append(f"{symbol}: {type(exc).__name__}: {exc}")
            continue
        if not bars:
            errors.append(f"{symbol}: no bars returned")
            continue
        results.append(evaluate_symbol(symbol, bars))

    if not results:
        print("no symbols evaluated:\n" + "\n".join(errors), file=sys.stderr)
        return 1

    scored = [r for r in results if r["features"].get("evaluated")]
    median_r2 = (statistics.median([r["features"]["oos_r2"] for r in scored
                                    if r["features"]["oos_r2"] is not None])
                 if scored else None)
    write_json(OUT_PATH, {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "method": ("expanding-window walk-forward OLS; features standardized "
                   "on training data only; returns winsorized at "
                   f"{WINSOR_K} MAD-sigmas"),
        "note": ("A diagnostic of feature predictability, not a forecast and "
                 "not a recommendation. Out-of-sample R-squared near zero is "
                 "the expected result for next-day returns; compare each "
                 "reading against its noise_control, which measures a "
                 "feature known to have no predictive power."),
        "min_train_sessions": MIN_TRAIN,
        "median_oos_r2": median_r2,
        "symbols_evaluated": len(scored),
        "results": results,
        "errors": errors,
    }, indent=1)
    print(f"Wrote {OUT_PATH}: {len(scored)}/{len(results)} evaluated, "
          f"median OOS R2 {median_r2}, {len(errors)} errors")
    return 0


if __name__ == "__main__":                # pragma: no cover
    raise SystemExit(main())
