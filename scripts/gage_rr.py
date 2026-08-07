#!/usr/bin/env python3
"""Gage R&R — measurement system analysis for the KPI pipeline.

Before trusting any KPI to rank tickers, establish that the measurement
system itself is sound. Classic MSA vocabulary maps onto this project
directly:

    part         a ticker
    operator     a data source (stooq / yahoo-fallback)
    trial        one computation of the KPI from that source
    measurement  the KPI value (vol_30d, trend r2, slope, ...)

Two variance components matter:

  REPEATABILITY (EV) — same source, same ticker, repeated runs.
      This pipeline is deterministic, so EV must be EXACTLY ZERO. Any
      nonzero repeatability is not measurement noise, it is a bug:
      hidden state, ordering dependence, or an unseeded RNG.

  REPRODUCIBILITY (AV) — different sources, same ticker.
      This is the real question, and it is the one the Aug 2026 audit
      raised: stooq and Yahoo may not share a price-adjustment
      convention. `fetch_closes` falls back per symbol, so a single
      ranking can mix conventions across tickers. AV measures exactly
      that disagreement.

%R&R is R&R variation as a share of total variation. The conventional
acceptance bands (AIAG) are:

    <= 10%   acceptable
    10-30%   marginal — usable, with justification
    >  30%   unacceptable — the measurement system cannot distinguish
             parts, so any ranking built on it is mostly noise

Deliberately NOT here: any attempt to reach a target by discarding data.
A measurement system either resolves the parts or it does not, and
deleting inconvenient observations changes the number without changing
the truth.
"""

import json
import math
import os
import statistics
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from atomic import write_json

OUT_PATH = "data/gage_rr.json"
ACCEPTABLE_PCT = 10.0
MARGINAL_PCT = 30.0


def _variance(values: list[float]) -> float:
    return statistics.pvariance(values) if len(values) > 1 else 0.0


def analyze(measurements: dict[str, dict[str, list[float]]]) -> dict:
    """Variance-components Gage R&R.

    `measurements[part][operator] = [trial, trial, ...]`

    Uses the variance-components form rather than the range method: it
    handles unbalanced designs (sources that cover different subsets of
    tickers, which is exactly what a per-symbol fallback produces).
    """
    parts = sorted(measurements)
    if len(parts) < 2:
        return {"evaluated": False,
                "reason": f"need >= 2 parts (tickers), got {len(parts)}"}

    operators = sorted({op for p in parts for op in measurements[p]})
    if not operators:
        return {"evaluated": False, "reason": "no operators (sources) present"}

    # Repeatability: variance within (part, operator), pooled.
    within = []
    for p in parts:
        for op, trials in measurements[p].items():
            if len(trials) > 1:
                within.append(_variance(trials))
    ev_var = statistics.fmean(within) if within else 0.0

    # Per-(part, operator) means feed the remaining components.
    cell_mean = {p: {op: statistics.fmean(t)
                     for op, t in measurements[p].items() if t}
                 for p in parts}

    # Reproducibility: variance among operator means, after removing the
    # part effect — i.e. the average disagreement between sources on the
    # same ticker. Zero when every source reports the same value.
    per_part_spread = []
    for p in parts:
        vals = list(cell_mean[p].values())
        if len(vals) > 1:
            per_part_spread.append(_variance(vals))
    av_var = statistics.fmean(per_part_spread) if per_part_spread else 0.0
    # The operator effect double-counts repeatability; subtract it, floor
    # at zero (a negative variance component means "indistinguishable
    # from zero", not a negative quantity).
    av_var = max(0.0, av_var - ev_var / max(
        1, statistics.fmean([len(t) for p in parts
                             for t in measurements[p].values()])))

    # Part variation: spread of the part means. This is the SIGNAL a
    # ranking depends on — if tickers do not differ, nothing can rank them.
    part_means = [statistics.fmean(list(cell_mean[p].values()))
                  for p in parts if cell_mean[p]]
    pv_var = _variance(part_means)

    rr_var = ev_var + av_var
    total_var = rr_var + pv_var

    def pct(v):
        return round(math.sqrt(v / total_var) * 100, 3) if total_var > 0 else None

    pct_rr = pct(rr_var)
    if pct_rr is None:
        verdict = "indeterminate"
    elif pct_rr <= ACCEPTABLE_PCT:
        verdict = "acceptable"
    elif pct_rr <= MARGINAL_PCT:
        verdict = "marginal"
    else:
        verdict = "unacceptable"

    return {
        "evaluated": True,
        "parts": len(parts),
        "operators": operators,
        "repeatability_sd": round(math.sqrt(ev_var), 8),
        "reproducibility_sd": round(math.sqrt(av_var), 8),
        "part_variation_sd": round(math.sqrt(pv_var), 8),
        "total_variation_sd": round(math.sqrt(total_var), 8),
        "pct_rr": pct_rr,
        "pct_repeatability": pct(ev_var),
        "pct_reproducibility": pct(av_var),
        "pct_part_variation": pct(pv_var),
        "verdict": verdict,
        "deterministic": ev_var == 0.0,
    }


def acceptance(result: dict) -> dict:
    """PASS/FAIL with the reason attached, per the standing protocol.

    IF PASS  -> the change may be applied and documented.
    IF FAIL  -> root cause, corrective action and evidence are required,
                and the loop repeats. A FAIL is a finding, not an error;
                what is forbidden is recording PASS without the evidence.
    """
    if not result.get("evaluated"):
        return {"status": "FAIL",
                "reason": result.get("reason", "not evaluated"),
                "root_cause_required": True}

    problems = []
    if not result["deterministic"]:
        problems.append(
            f"repeatability is {result['repeatability_sd']}, expected exactly "
            "0 — this pipeline is deterministic, so nonzero within-source "
            "variance indicates hidden state or ordering dependence, not "
            "measurement noise")
    if result["verdict"] == "unacceptable":
        problems.append(
            f"%R&R {result['pct_rr']}% exceeds {MARGINAL_PCT}% — the "
            "measurement system cannot reliably distinguish tickers, so any "
            "ranking built on this KPI is mostly measurement variation")
    if result["verdict"] == "indeterminate":
        problems.append("total variation is zero — the KPI does not vary "
                        "across tickers and cannot rank anything")

    if problems:
        return {"status": "FAIL", "reason": "; ".join(problems),
                "root_cause_required": True}
    return {"status": "PASS",
            "reason": f"%R&R {result['pct_rr']}% ({result['verdict']}), "
                      "repeatability exactly 0",
            "root_cause_required": False}


def run(kpis: dict[str, dict[str, dict[str, list[float]]]]) -> dict:
    """`kpis[kpi_name][ticker][source] = [trials]` -> full report."""
    results, gates = {}, {}
    for name, measurements in sorted(kpis.items()):
        results[name] = analyze(measurements)
        gates[name] = acceptance(results[name])
    overall = ("PASS" if gates and all(g["status"] == "PASS"
                                       for g in gates.values()) else "FAIL")
    return {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "method": ("variance-components Gage R&R; parts=tickers, "
                   "operators=data sources, trials=repeated computations"),
        "note": ("Measurement system analysis, not a market claim. It asks "
                 "whether a KPI can be measured consistently — never whether "
                 "the KPI predicts anything. Acceptance bands are AIAG "
                 "(<=10% acceptable, <=30% marginal)."),
        "acceptance_bands": {"acceptable_pct": ACCEPTABLE_PCT,
                             "marginal_pct": MARGINAL_PCT},
        "kpis": results,
        "gates": gates,
        "overall": overall,
    }


def main(kpis=None) -> int:
    if kpis is None:                        # pragma: no cover - network path
        print("gage_rr needs measurements; run it from kpi_panel.py",
              file=sys.stderr)
        return 1
    report = run(kpis)
    write_json(OUT_PATH, report, indent=1)
    print(f"Wrote {OUT_PATH}: overall {report['overall']}")
    for name, gate in sorted(report["gates"].items()):
        print(f"  {gate['status']:4} {name}: {gate['reason']}")
    return 0 if report["overall"] == "PASS" else 1


if __name__ == "__main__":                  # pragma: no cover
    raise SystemExit(main())
