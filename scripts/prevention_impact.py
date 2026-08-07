#!/usr/bin/env python3
"""Elder-fraud prevention impact: estimate, bound, and chart.

WHAT THIS ANSWERS
    How much money did this program keep out of criminals' hands in a given
    month, and how far can that month drift before something has actually
    changed rather than merely wobbled?

WHAT IT CANNOT ANSWER, AND WHY THE DESIGN SAYS SO OUT LOUD
    Prevented dollars are counterfactual. Nobody observes the loss that did
    not happen. Every number here is a MODEL OUTPUT conditioned on stated
    priors, not a measurement, and the code is built so that distinction
    survives contact with a slide deck:

      * Two bands, never merged. The Monte Carlo interval says how uncertain
        one period's estimate is given the priors. The control limits say how
        much the metric moves period to period when nothing has changed.
        These are different questions. Plotting one and calling it the other
        is the standard way this genre of number becomes indefensible.

      * A national-consistency filter. Parameter draws implying a US-wide
        elder-fraud loss outside the FTC's published range are rejected
        outright. A local estimate that only makes sense in a country losing
        $400B a year is not allowed to price one month of one business.

      * A provenance gate. Any parameter carrying `verified: false` blocks
        the headline figure from being marked publishable. Per this repo's
        rule 13 -- a control nobody checks is a claim -- the gate is code
        that runs, not a paragraph asking nicely.

TWO PROCESSES, TWO CHARTS -- THE CENTRAL DESIGN DECISION
    An early version charted total prevented dollars on one individuals
    chart. It produced sigma = 1.66 log-units and an upper control limit of
    $230,000,000, which is not a control limit but a confession. The cause
    was not the arithmetic: the series is a MIXTURE of two processes with
    nothing in common.

      Awareness  a continuous accrual over a protected population that
                 changes slowly and smoothly. Observed spread on real-shaped
                 inputs: about 2,700-3,200 per 1,000 person-months.
      Interdiction  rare, heavy-tailed events. Six in twelve months, one of
                 them forty times another.

    Alternating between them gives a bimodal series, and an individuals
    chart fitted to a bimodal series estimates the GAP BETWEEN THE MODES as
    if it were noise. Limits then grow wide enough to contain anything, so
    the chart can never signal -- the most dangerous failure mode available,
    because it still looks like a chart. So:

      Chart 1 (primary)  awareness rate, USD per 1,000 protected
                         person-months. This is the repeatable process and
                         the one worth controlling. It answers: is the
                         program still doing what it did last month?
      Chart 2  interdiction COUNT per period, exact Poisson limits rather
               than cbar +/- k*sqrt(cbar) -- the normal approximation is
               poor at the handful-per-month counts this program produces.
      Chart 3  interdiction SEVERITY, log dollars per event, individuals
               chart across events (not periods -- a month with no event is
               not a zero, it is an absence of data).

    Total prevented dollars are still reported per period with Monte Carlo
    bands, explicitly NOT as a control chart. A sum of two processes with
    different physics has no single stable voice to speak in.

WHY THE PRIMARY METRIC IS A RATE, NOT DOLLARS
    Raw monthly dollars rise when the business grows and fall when it
    shrinks, so a control chart on them detects headcount, not
    effectiveness. Dividing by the protected population -- a stock that
    accrues from each month's reach and decays with an explicit half-life --
    isolates how well the program works from how big it got. Growth then
    shows up where it belongs, in the denominator and in the total, instead
    of masquerading as a process shift.

    Note what this buys: a program drifting from 45-minute sessions toward
    expo-table handouts holds its headline dollars steady while the rate
    falls. The rate chart sees that. A dollars chart never would.

TWO CHOICES THAT ARE EASY TO GET WRONG
    Log scale. Fraud losses are lognormal with sigma near 2.8 -- mean around
    fifty times median. A symmetric +/-2 sigma band on raw dollars puts the
    lower limit below zero (impossible) and the upper limit where nothing
    ever lands, so it can only ever fire high. Charting log dollars restores
    the near-symmetry Shewhart's constants assume, and limits are
    exponentiated back into dollars, arriving correctly asymmetric.

    Sigma from the moving range, not the standard deviation. For individuals
    data sigma-hat = MRbar/1.128, or the more outlier-resistant
    median(MR)/0.954 used by default here. The sample standard deviation
    absorbs the very special causes the chart exists to find: one $118,000
    interdiction inflates it enough to swallow itself, and the chart goes
    quiet exactly when it should shout.

ON "TWO SIGMA" SPECIFICALLY, SINCE IT WAS ASKED FOR
    At +/-2 sigma, 4.55% of in-control points fall outside by chance -- about
    one false alarm every 22 months on monthly data. That is a WARNING limit,
    not an action limit, and a lone excursion means investigate, not
    "something changed". The genuine signal at this width is the Western
    Electric rule: 2 of 3 consecutive points beyond the same-side 2 sigma
    line, whose chance rate is about 0.16% per point. Both are computed, and
    labelled distinctly so the difference cannot be lost downstream.

Pure standard library: no numpy, matching the rest of scripts/.
"""

import argparse
import json
import math
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from atomic import write_json

INPUT_PATH = "impact/prevention_inputs.json"
OUT_PATH = "data/prevention_impact.json"

DEFAULT_DRAWS = 20000
DEFAULT_SEED = 20260807

# Shewhart constants for a moving range of n=2.
D2_MEAN_MR = 1.128      # sigma = MRbar / d2
D4_MEDIAN_MR = 0.954    # sigma = median(MR) / d4, resistant to a lone spike

Z_95 = 1.6448536269514722   # one-sided 95th percentile of the standard normal
PERT_LAMBDA = 4.0           # standard PERT weight on the mode

# Two-sided tail matching +/-2 sigma under normality, used for the exact
# Poisson limits on the count chart.
TWO_SIGMA_TAIL = 0.02275

# Scale for the charted rate. Person-months, because a person protected for
# three months is three times the exposure-reduction opportunity of a person
# protected for one, and the denominator has to say so.
PPM_SCALE = 1000.0

# Parameters tracked draw-by-draw for the variance-contribution report.
TRACKED_PARAMS = ["incidence", "loss_median", "sigma_log", "expected_loss",
                  "half_life", "recovery"]


# --------------------------------------------------------------------------
# Distributions
# --------------------------------------------------------------------------

def draw(spec: dict, rng: random.Random) -> float:
    """Sample one value from a parameter spec.

    Supported: point, pert (a bounded, mode-weighted Beta -- the right shape
    for elicited quantities because it cannot wander past stated bounds), and
    lognormal_median_p95 for anything heavy-tailed.
    """
    kind = spec.get("dist", "point")

    if kind == "point":
        return float(spec["value"])

    if kind == "pert":
        low, mode, high = float(spec["low"]), float(spec["mode"]), float(spec["high"])
        if not low <= mode <= high:
            raise ValueError(f"pert requires low <= mode <= high, got {spec}")
        if high == low:
            return low
        lam = float(spec.get("lambda", PERT_LAMBDA))
        alpha = 1.0 + lam * (mode - low) / (high - low)
        beta = 1.0 + lam * (high - mode) / (high - low)
        return low + rng.betavariate(alpha, beta) * (high - low)

    if kind == "lognormal_median_p95":
        median, p95 = float(spec["median"]), float(spec["p95"])
        mu = math.log(median)
        sigma = (math.log(p95) - mu) / Z_95
        return rng.lognormvariate(mu, sigma)

    raise ValueError(f"unknown distribution kind: {kind!r}")


def lognormal_mean(median: float, sigma_log: float) -> float:
    """E[L] for a lognormal given its median and log-scale sigma.

    exp(mu + sigma^2/2) with mu = ln(median). The sigma^2/2 term is the whole
    story of fraud loss data: at sigma = 2.8 the mean sits ~50x above the
    median, so "average loss" and "typical loss" differ by a factor of fifty
    and reporting either one alone misleads.
    """
    return median * math.exp(0.5 * sigma_log ** 2)


# --------------------------------------------------------------------------
# Provenance gate
# --------------------------------------------------------------------------

def unverified_parameters(params: dict) -> list[str]:
    """Names of parameters not yet confirmed against a primary source.

    Walks one level into grouped specs (stage_loss_probability, ...) where
    the flag lives on a `_verified` key beside the members.
    """
    unverified = []
    for name, spec in params.items():
        if not isinstance(spec, dict):
            continue
        if "dist" in spec:
            if not spec.get("verified", False):
                unverified.append(name)
        elif "_verified" in spec:
            if not spec.get("_verified", False):
                unverified.append(name)
    return sorted(unverified)


# --------------------------------------------------------------------------
# Protected population: a stock, not a running total
# --------------------------------------------------------------------------

def protected_person_months(periods: list[dict], cohort: str, index: int,
                            half_life_months: float) -> float:
    """Person-months of active protection in `periods[index]` for one cohort.

    Everyone reached in an earlier period still counts, discounted by
    2^(-age/half_life). The decay is the load-bearing part: without it a
    seminar given in 2019 keeps earning credit in 2026, which is precisely
    how impact estimates turn into fiction. With it, a program that stops
    delivering watches its own number fall.
    """
    total = 0.0
    for j in range(index + 1):
        reached = float(periods[j].get("reach", {}).get(cohort, 0) or 0)
        if reached <= 0:
            continue
        age = index - j
        total += reached * (0.5 ** (age / half_life_months))
    return total


# --------------------------------------------------------------------------
# One coherent draw of every parameter
# --------------------------------------------------------------------------

def draw_scenario(params: dict, cohorts: dict, rng: random.Random) -> dict:
    """Sample a mutually consistent parameter set.

    Drawn jointly, once per iteration, so that a scenario with a high loss
    median also carries its own incidence and its own effect size. Sampling
    each parameter independently inside the period loop would let a single
    reported month mix an optimistic effect size with a pessimistic one.
    """
    loss_median = draw(params["loss_median_usd"], rng)
    sigma_log = draw(params["loss_sigma_log"], rng)
    stage_specs = params["stage_loss_probability"]
    evidence_specs = params["evidence_weight"]

    return {
        "loss_median": loss_median,
        "sigma_log": sigma_log,
        "expected_loss": lognormal_mean(loss_median, sigma_log),
        "incidence": draw(params["annual_incidence_60plus"], rng),
        "half_life": draw(params["persistence_half_life_months"], rng),
        "recovery": draw(params["recovery_absent_intervention"], rng),
        "rrr": {name: draw(params[cfg["rrr_parameter"]], rng)
                for name, cfg in cohorts.items()},
        "stage": {k: draw(v, rng) for k, v in stage_specs.items()
                  if not k.startswith("_")},
        "evidence": {k: draw(v, rng) for k, v in evidence_specs.items()
                     if not k.startswith("_")},
    }


def national_total(scenario: dict, population: float) -> float:
    """US-wide annual elder-fraud loss implied by this scenario."""
    return scenario["incidence"] * scenario["expected_loss"] * population


def scenario_is_consistent(scenario: dict, params: dict) -> bool:
    """Does this scenario imply a national total the FTC would recognise?

    The tether. Priors on incidence and loss severity are individually wide
    because the evidence is genuinely weak, but their PRODUCT is pinned by a
    published aggregate. Rejecting the inconsistent corner of the joint prior
    tightens the estimate using data rather than using preference -- and it
    tightens exactly the product (incidence x E[loss]) that drives the
    awareness channel, which is why the final band is narrower than the
    marginal priors suggest.
    """
    total = national_total(scenario, float(params["population_60plus"]["value"]))
    low = float(params["national_annual_loss_low"]["value"])
    high = float(params["national_annual_loss_high"]["value"])
    return low <= total <= high


# --------------------------------------------------------------------------
# Per-period estimate under one scenario
# --------------------------------------------------------------------------

def awareness_channel(periods: list[dict], index: int, cohorts: dict,
                      scenario: dict) -> tuple[float, float]:
    """(prevented USD, protected person-months) from the awareness channel.

    Accrual accounting, not attribution-at-delivery. A month is credited with
    the expected losses averted across everyone currently protected, whenever
    they were reached. Crediting all future benefit to the month of delivery
    would double-count repeat attendees and make the series unchartably lumpy.

        averted events = person-months * (incidence / 12) * RRR
        prevented USD  = averted events * E[loss]
    """
    prevented = 0.0
    person_months = 0.0
    for cohort in cohorts:
        ppm = protected_person_months(periods, cohort, index, scenario["half_life"])
        if ppm <= 0:
            continue
        person_months += ppm
        events = ppm * (scenario["incidence"] / 12.0) * scenario["rrr"][cohort]
        prevented += events * scenario["expected_loss"]
    return prevented, person_months


def interdiction_case_value(case: dict, scenario: dict) -> float:
    """Prevented USD from one documented intervention in an in-progress scam.

        exposure * P(loss | stage) * (1 - recovery) * evidence * attribution

    Four discounts, each removing a way the raw exposure figure lies:

      P(loss | stage)  not every interrupted scam would have completed;
      (1 - recovery)   money the bank would have clawed back anyway was not
                       prevented by this program -- omitting this term is the
                       most common way interdiction tallies get inflated;
      evidence         an uncorroborated account is worth less than a bank
                       confirmation, and says so numerically;
      attribution      a save shared with a teller who also flagged it is not
                       wholly this program's.
    """
    exposure = float(case.get("exposure_usd", 0) or 0)
    if exposure <= 0:
        return 0.0
    stage = case.get("stage", "contacted")
    if stage not in scenario["stage"]:
        raise ValueError(f"unknown interdiction stage: {stage!r}")
    evidence = case.get("evidence", "inferred")
    if evidence not in scenario["evidence"]:
        raise ValueError(f"unknown evidence tier: {evidence!r}")
    return (exposure
            * scenario["stage"][stage]
            * (1.0 - scenario["recovery"])
            * scenario["evidence"][evidence]
            * float(case.get("attribution", 1.0)))


def interdiction_channel(period: dict, scenario: dict) -> float:
    """Total prevented USD from all interventions in one period."""
    return sum(interdiction_case_value(c, scenario)
               for c in (period.get("interdictions") or []))


# --------------------------------------------------------------------------
# Monte Carlo
# --------------------------------------------------------------------------

def percentile(sorted_values: list[float], q: float) -> float:
    """Linear-interpolated percentile of an already-sorted list."""
    if not sorted_values:
        return 0.0
    if len(sorted_values) == 1:
        return sorted_values[0]
    pos = q * (len(sorted_values) - 1)
    lo, hi = math.floor(pos), math.ceil(pos)
    if lo == hi:
        return sorted_values[int(pos)]
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (pos - lo)


def _summarise(values: list[float]) -> dict:
    s = sorted(values)
    return {
        "p05": round(percentile(s, 0.05), 2),
        "p50": round(percentile(s, 0.50), 2),
        "p95": round(percentile(s, 0.95), 2),
        "mean": round(sum(s) / len(s), 2) if s else 0.0,
    }


def simulate(config: dict, draws: int = DEFAULT_DRAWS,
             seed: int = DEFAULT_SEED) -> dict:
    """Run the Monte Carlo and summarise each period.

    Cumulative totals are accumulated PER DRAW and percentiled at the end,
    never by summing per-period percentiles. Those agree only if the periods
    are perfectly rank-correlated; they are strongly but not perfectly
    correlated here, so summing percentiles would quietly overstate the
    width of the cumulative band.

    A low consistency-acceptance rate is diagnostic, not cosmetic: it means
    the stated priors mostly contradict published national totals, and the
    caller is told so rather than handed a confident number built from the
    surviving sliver.
    """
    params = config["parameters"]
    cohorts = config["cohorts"]
    periods = config["periods"]
    consistency_on = config.get("national_consistency", {}).get("enabled", True)

    rng = random.Random(seed)
    n = len(periods)
    totals = [[] for _ in range(n)]
    awareness = [[] for _ in range(n)]
    interdiction = [[] for _ in range(n)]
    aware_rates = [[] for _ in range(n)]
    ppms = [[] for _ in range(n)]
    cumulative = []
    tracked = {k: [] for k in TRACKED_PARAMS}

    attempted = 0
    accepted = 0
    max_attempts = draws * 200

    while accepted < draws and attempted < max_attempts:
        attempted += 1
        scenario = draw_scenario(params, cohorts, rng)
        if consistency_on and not scenario_is_consistent(scenario, params):
            continue
        accepted += 1
        for key in TRACKED_PARAMS:
            tracked[key].append(scenario[key])

        running = 0.0
        for i, period in enumerate(periods):
            aware_usd, ppm = awareness_channel(periods, i, cohorts, scenario)
            inter_usd = interdiction_channel(period, scenario)
            total = aware_usd + inter_usd
            running += total
            awareness[i].append(aware_usd)
            interdiction[i].append(inter_usd)
            totals[i].append(total)
            ppms[i].append(ppm)
            aware_rates[i].append(aware_usd / ppm * PPM_SCALE if ppm > 0 else 0.0)
        cumulative.append(running)

    if accepted == 0:
        raise RuntimeError(
            "national-consistency filter rejected every draw: the priors on "
            "incidence and loss severity are mutually inconsistent with the "
            "published national range. Widen the priors or check the inputs.")

    summary = []
    for i, period in enumerate(periods):
        summary.append({
            "period": period["period"],
            "reach": period.get("reach", {}),
            "interdiction_count": len(period.get("interdictions") or []),
            "protected_person_months": round(percentile(sorted(ppms[i]), 0.50), 1),
            "prevented_usd": _summarise(totals[i]),
            "channel_p50": {
                "awareness": round(percentile(sorted(awareness[i]), 0.50), 2),
                "interdiction": round(percentile(sorted(interdiction[i]), 0.50), 2),
            },
            "awareness_rate_per_1000_ppm": _summarise(aware_rates[i]),
        })

    return {
        "periods": summary,
        "cumulative_prevented_usd": _summarise(cumulative),
        "draws_requested": draws,
        "draws_accepted": accepted,
        "draws_attempted": attempted,
        "consistency_acceptance_rate": round(accepted / attempted, 4),
        "_tracked": tracked,
        "_final_period_totals": totals[-1] if totals else [],
    }


# --------------------------------------------------------------------------
# Control charts
# --------------------------------------------------------------------------

def _median(values: list[float]) -> float:
    s = sorted(values)
    n = len(s)
    if n == 0:
        return 0.0
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2.0


def lag1_autocorrelation(series: list[float]) -> float:
    """Lag-1 autocorrelation. A precondition check, not a statistic to report.

    The individuals chart assumes successive points are independent. This
    series is not: the protected population is a STOCK that carries most of
    its value from one month into the next, so consecutive rates are joined
    at the hip by construction. When that correlation is high, adjacent
    points sit close together, moving ranges shrink, and sigma = MR/d is
    understated -- the chart then fires on ordinary drift.

    Reported rather than corrected. The fix for autocorrelated data is a
    different instrument (chart the residuals of a fitted model, or widen the
    sampling interval), and silently rescaling sigma here would hide a
    modelling decision inside a helper function.
    """
    n = len(series)
    if n < 3:
        return 0.0
    mean = sum(series) / n
    denom = sum((v - mean) ** 2 for v in series)
    if denom == 0:
        return 0.0
    num = sum((series[i] - mean) * (series[i - 1] - mean) for i in range(1, n))
    return num / denom


def individuals_chart(points: list[dict], sigma_multiple: float = 2.0,
                      estimator: str = "median_moving_range",
                      log_scale: bool = True,
                      min_points: int = 8,
                      provisional_below: int = 20,
                      label: str = "") -> dict:
    """Shewhart individuals (XmR) chart with fixed limits.

    points: [{"label": str, "value": float > 0}]

    Deliberately NOT weight-scaled. An earlier version widened limits by
    sqrt(weight_bar / weight_i) on the theory that the rate is an average
    over the protected population. It is not: under a fixed scenario the
    awareness rate is a weighted mean of cohort effect sizes, with no 1/n
    sampling term at all. Its period-to-period movement is real variation in
    programme composition -- exactly what should be controlled. Applying the
    scaling during a ramp-up, when the denominator grows twentyfold, pushed
    the first limit to $230,000,000 and made the chart incapable of firing.

    Refuses to emit limits below `min_points` and marks them provisional
    below `provisional_below`. Two-sigma limits computed from five points are
    an estimate of noise made out of noise; saying so is cheaper than being
    asked later why the band moved.
    """
    usable = [p for p in points if p.get("value", 0) > 0]

    if len(usable) < min_points:
        return {
            "chart": label,
            "status": "insufficient_data",
            "n_points": len(usable),
            "min_points": min_points,
            "reason": (f"{len(usable)} usable points; limits require at least "
                       f"{min_points} and are only stable near 20-25."),
            "points": [],
            "signals": [],
        }

    values = [p["value"] for p in usable]
    transformed = [math.log(v) for v in values] if log_scale else list(values)
    moving_ranges = [abs(transformed[i] - transformed[i - 1])
                     for i in range(1, len(transformed))]

    mean_sigma = (sum(moving_ranges) / len(moving_ranges)) / D2_MEAN_MR
    median_sigma = _median(moving_ranges) / D4_MEDIAN_MR

    if estimator == "mean_moving_range":
        sigma, constant = mean_sigma, D2_MEAN_MR
    else:
        estimator, sigma, constant = "median_moving_range", median_sigma, D4_MEDIAN_MR

    # A zero sigma estimate makes the chart permanently blind: every point
    # scores 0 sigma and nothing can ever breach a zero-width band. The
    # median moving range hits zero whenever more than half the consecutive
    # pairs are identical -- a flat stretch with one step change is exactly
    # that, and it is precisely the pattern most worth catching. Fall back to
    # the mean moving range, which only vanishes if the series never moves at
    # all; if it does vanish, say so instead of emitting limits that cannot fire.
    sigma_fallback = None
    if sigma == 0 and mean_sigma > 0:
        sigma, constant = mean_sigma, D2_MEAN_MR
        sigma_fallback = (
            "median moving range was zero (a flat stretch), which would have "
            "produced a zero-width band that can never signal; fell back to the "
            "mean moving range.")

    if sigma == 0:
        return {
            "chart": label,
            "status": "degenerate_no_variation",
            "n_points": len(usable),
            "reason": ("every observation is identical, so there is no observed "
                       "variation from which to estimate limits. Any future point "
                       "that differs at all is novel by definition."),
            "observed_value": round(values[0], 2),
            "points": [],
            "signals": [],
        }

    centre = sum(transformed) / len(transformed)
    spread = sigma_multiple * sigma
    ucl_t, lcl_t = centre + spread, centre - spread

    if log_scale:
        cl, ucl, lcl = math.exp(centre), math.exp(ucl_t), math.exp(lcl_t)
    else:
        cl, ucl, lcl = centre, ucl_t, lcl_t

    charted = []
    for p, t in zip(usable, transformed):
        z = (t - centre) / sigma if sigma > 0 else 0.0
        charted.append({
            "label": p["label"],
            "value": round(p["value"], 2),
            "sigma_units": round(z, 3),
            "beyond_limits": abs(z) >= sigma_multiple,
        })

    r1 = lag1_autocorrelation(transformed)

    return {
        "chart": label,
        "status": "ok",
        "n_points": len(usable),
        "lag1_autocorrelation": round(r1, 3),
        "autocorrelation_warning": (
            f"lag-1 autocorrelation {r1:+.2f}: successive points are not "
            "independent, so moving-range sigma is understated and this chart "
            "will over-signal on ordinary drift. Read excursions as prompts to "
            "look, never as proof of a change."
        ) if abs(r1) > 0.5 else None,
        "limits_provisional": len(usable) < provisional_below,
        "provisional_note": (
            f"{len(usable)} points; limits stabilise near {provisional_below}-25. "
            "Treat the band as indicative until then."
        ) if len(usable) < provisional_below else None,
        "sigma_multiple": sigma_multiple,
        "sigma_estimator": estimator,
        "sigma_constant": constant,
        "sigma_fallback_note": sigma_fallback,
        "sigma": round(sigma, 5),
        "sigma_scale": "log_usd" if log_scale else "usd",
        "log_scale": log_scale,
        "centre_line": round(cl, 2),
        "ucl": round(ucl, 2),
        "lcl": round(lcl, 2),
        "false_alarm_rate_single_point": 0.0455,
        "points": charted,
        "signals": detect_signals(charted, sigma_multiple),
    }


def _poisson_cdf(k: int, lam: float) -> float:
    """P(X <= k) for Poisson(lam), summed term by term."""
    if lam <= 0:
        return 1.0
    total = 0.0
    term = math.exp(-lam)
    for i in range(0, k + 1):
        if i > 0:
            term *= lam / i
        total += term
    return min(total, 1.0)


def count_chart(counts: list[dict], tail: float = TWO_SIGMA_TAIL,
                min_points: int = 8, label: str = "") -> dict:
    """c-chart on event counts, with EXACT Poisson limits.

    The textbook c-chart uses cbar +/- k*sqrt(cbar). At the counts this
    programme actually produces -- zero to two interdictions a month -- that
    normal approximation is poor and routinely puts the lower limit below
    zero, which is not a limit but an absence of one. Inverting the Poisson
    CDF at the tail area matching +/-2 sigma (2.275% each side) gives limits
    that are integers, non-negative by construction, and correct for small
    counts.

    A lower limit of 0 here is honest and worth stating plainly: with a mean
    near one event per month, no number of consecutive zero-interdiction
    months is statistically surprising on its own. The chart can detect a
    surge; it cannot detect a stoppage. That asymmetry is a property of rare
    events, not a defect to be tuned away -- and it is the reason the
    awareness chart, not this one, is the primary instrument.
    """
    if len(counts) < min_points:
        return {
            "chart": label,
            "status": "insufficient_data",
            "n_points": len(counts),
            "reason": f"{len(counts)} periods; need at least {min_points}.",
            "points": [],
            "signals": [],
        }

    values = [c["value"] for c in counts]
    cbar = sum(values) / len(values)

    lcl = 0
    while _poisson_cdf(lcl, cbar) < tail:
        lcl += 1
    lcl = max(lcl - 1, 0)

    ucl = 0
    while _poisson_cdf(ucl, cbar) < 1 - tail and ucl < 1000:
        ucl += 1

    charted = [{
        "label": c["label"],
        "value": c["value"],
        "beyond_limits": c["value"] > ucl or c["value"] < lcl,
    } for c in counts]

    signals = [{
        "period": p["label"],
        "rule": "count_beyond_poisson_2_sigma_equivalent",
        "severity": "warning",
        "detail": f"{p['value']} events vs limits [{lcl}, {ucl}], mean {cbar:.2f}.",
    } for p in charted if p["beyond_limits"]]

    return {
        "chart": label,
        "status": "ok",
        "n_points": len(counts),
        "limit_method": "exact_poisson_inverse_cdf",
        "tail_each_side": tail,
        "centre_line": round(cbar, 3),
        "ucl": ucl,
        "lcl": lcl,
        "lower_limit_note": (
            "LCL is 0: at this event rate a quiet month is never surprising by "
            "itself. This chart detects surges, not stoppages."
        ) if lcl == 0 else None,
        "points": charted,
        "signals": signals,
    }


def detect_signals(points: list[dict], sigma_multiple: float) -> list[dict]:
    """Shewhart run rules, graded by what each one actually means.

    At 2 sigma a single excursion is a WARNING (4.55% by chance -- roughly one
    per 22 monthly points, so a chart with none is the surprise). The signal
    worth acting on is 2-of-3 on one side, whose chance rate is about 0.16%
    per point. Shifts and trends are reported separately because they mean
    different things: a run says the level moved, a trend says it is moving.
    """
    signals = []
    z = [p["sigma_units"] for p in points]

    for p in points:
        if p["beyond_limits"]:
            signals.append({
                "period": p["label"],
                "rule": "single_point_beyond_2_sigma",
                "severity": "warning",
                "detail": (f"{p['sigma_units']:+.2f} sigma. Expected ~4.6% of the "
                           "time with nothing wrong. Investigate; do not conclude."),
            })

    for i in range(2, len(points)):
        window = z[i - 2:i + 1]
        for sign, name in ((1, "high"), (-1, "low")):
            if len([v for v in window if sign * v >= sigma_multiple]) >= 2:
                signals.append({
                    "period": points[i]["label"],
                    "rule": "two_of_three_beyond_2_sigma",
                    "severity": "signal",
                    "detail": (f"2 of 3 consecutive points beyond +/-2 sigma on the "
                               f"{name} side. ~0.16% by chance -- treat as a real "
                               "change and find the cause."),
                })

    for i in range(7, len(points)):
        window = z[i - 7:i + 1]
        if all(v > 0 for v in window):
            side = "above"
        elif all(v < 0 for v in window):
            side = "below"
        else:
            continue
        signals.append({
            "period": points[i]["label"],
            "rule": "run_of_8_same_side",
            "severity": "signal",
            "detail": f"8 consecutive points {side} the centre line: the level has shifted.",
        })

    for i in range(6, len(points)):
        window = [p["value"] for p in points[i - 6:i + 1]]
        rising = all(b > a for a, b in zip(window, window[1:]))
        falling = all(b < a for a, b in zip(window, window[1:]))
        if rising or falling:
            signals.append({
                "period": points[i]["label"],
                "rule": "trend_of_7",
                "severity": "signal",
                "detail": (f"7 consecutive {'increases' if rising else 'decreases'}: "
                           "a trend, not a level shift."),
            })

    return signals


# --------------------------------------------------------------------------
# Where is the uncertainty actually coming from?
# --------------------------------------------------------------------------

def _rank(values: list[float]) -> list[float]:
    """Fractional ranks, ties averaged."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and values[order[j + 1]] == values[order[i]]:
            j += 1
        avg = (i + j) / 2.0
        for k in range(i, j + 1):
            ranks[order[k]] = avg
        i = j + 1
    return ranks


def _spearman(a: list[float], b: list[float]) -> float:
    ra, rb = _rank(a), _rank(b)
    n = len(ra)
    ma, mb = sum(ra) / n, sum(rb) / n
    num = sum((x - ma) * (y - mb) for x, y in zip(ra, rb))
    da = math.sqrt(sum((x - ma) ** 2 for x in ra))
    db = math.sqrt(sum((y - mb) ** 2 for y in rb))
    return num / (da * db) if da > 0 and db > 0 else 0.0


def variance_contributions(sim: dict) -> list[dict]:
    """Rank each parameter by how much of the output spread it explains.

    Squared Spearman correlation between each parameter's draws and the final
    period's prevented total, normalised to sum to 100%. The ranking is the
    measurement roadmap: it names which single number is worth spending money
    to pin down, instead of guessing which assumption feels shakiest.

    Computed on the ACCEPTED sample in a single pass, deliberately not by
    freeze-one-and-rerun. Freezing a parameter changes which draws survive the
    national-consistency filter, so a re-run compares two different
    populations and reports differences in the filter as if they were
    sensitivity. The first version of this function did exactly that and
    returned negative contributions -- an impossible result that was the bug
    announcing itself.
    """
    output = sim.get("_final_period_totals") or []
    tracked = sim.get("_tracked") or {}
    if len(output) < 100:
        return []

    raw = []
    for name, draws_list in tracked.items():
        if len(draws_list) != len(output):
            continue
        rho = _spearman(draws_list, output)
        raw.append({"parameter": name, "spearman": round(rho, 4), "r2": rho ** 2})

    total = sum(r["r2"] for r in raw)
    for r in raw:
        r["share_of_explained_variance_pct"] = (
            round(100 * r["r2"] / total, 1) if total > 0 else 0.0)
        r["r2"] = round(r["r2"], 4)

    raw.sort(key=lambda r: -r["r2"])
    return raw


# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------

def build_report(config: dict, draws: int = DEFAULT_DRAWS,
                 seed: int = DEFAULT_SEED) -> dict:
    sim = simulate(config, draws=draws, seed=seed)
    cc_cfg = config.get("control_chart", {})
    k = float(cc_cfg.get("sigma_multiple", 2.0))
    estimator = cc_cfg.get("sigma_estimator", "median_moving_range")
    min_points = int(cc_cfg.get("min_periods_for_limits", 8))
    provisional_below = int(cc_cfg.get("provisional_below_periods", 20))

    awareness_chart = individuals_chart(
        [{"label": p["period"], "value": p["awareness_rate_per_1000_ppm"]["p50"]}
         for p in sim["periods"]],
        sigma_multiple=k, estimator=estimator,
        log_scale=bool(cc_cfg.get("log_scale", True)),
        min_points=min_points, provisional_below=provisional_below,
        label="awareness_rate_usd_per_1000_protected_person_months")

    counts = count_chart(
        [{"label": p["period"], "value": p["interdiction_count"]}
         for p in sim["periods"]],
        min_points=min_points, label="interdictions_per_period")

    # Severity is charted per EVENT, not per period. A month with no
    # interdiction is not a $0 observation; it is an absence of one, and
    # feeding it in as a zero would drag the centre line toward a value no
    # event can ever take.
    case_points = []
    for period in config["periods"]:
        for case in (period.get("interdictions") or []):
            case_points.append({
                "label": f"{period['period']}:{case.get('id', '?')}",
                "value": float(case.get("exposure_usd", 0) or 0),
            })
    severity = individuals_chart(
        case_points, sigma_multiple=k, estimator=estimator, log_scale=True,
        min_points=min_points, provisional_below=provisional_below,
        label="interdiction_exposure_usd_per_event")

    unverified = unverified_parameters(config["parameters"])
    example_periods = [p["period"] for p in config["periods"] if p.get("_example")]

    blockers = []
    if unverified:
        blockers.append(f"{len(unverified)} parameter(s) unverified against a primary source")
    if example_periods:
        blockers.append(f"{len(example_periods)} period(s) are example data, not a real service log")
    if awareness_chart["status"] != "ok":
        blockers.append("primary control limits not established")
    elif awareness_chart.get("limits_provisional"):
        blockers.append("primary control limits provisional (fewer than 20 periods)")

    return {
        "generated_by": "scripts/prevention_impact.py",
        "operator": config.get("business", {}).get("operator"),
        "estimate": {
            "cumulative_prevented_usd": sim["cumulative_prevented_usd"],
            "note": ("Counterfactual model output, not a measurement. The p05-p95 "
                     "band is PARAMETER uncertainty. It is not the control-chart "
                     "band, which describes period-to-period process variation. "
                     "The two answer different questions and must not be merged."),
        },
        "publishable": not blockers,
        "publication_blockers": blockers,
        "unverified_parameters": unverified,
        "example_periods": example_periods,
        "monte_carlo": {
            "draws_requested": sim["draws_requested"],
            "draws_accepted": sim["draws_accepted"],
            "consistency_acceptance_rate": sim["consistency_acceptance_rate"],
            "seed": seed,
        },
        "periods": sim["periods"],
        "charts": {
            "primary_awareness_rate": awareness_chart,
            "interdiction_count": counts,
            "interdiction_severity": severity,
        },
        "variance_contributions": variance_contributions(sim),
    }


def load_config(path: str = INPUT_PATH) -> dict:
    with open(path) as f:
        return json.load(f)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--input", default=INPUT_PATH)
    ap.add_argument("--output", default=OUT_PATH)
    ap.add_argument("--draws", type=int, default=DEFAULT_DRAWS)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    args = ap.parse_args(argv)

    config = load_config(args.input)
    report = build_report(config, draws=args.draws, seed=args.seed)
    write_json(args.output, report, indent=2)

    cum = report["estimate"]["cumulative_prevented_usd"]
    print(f"wrote {args.output}")
    print(f"  cumulative prevented (p50): ${cum['p50']:,.0f}")
    print(f"  90% parameter band:         ${cum['p05']:,.0f} - ${cum['p95']:,.0f}")
    print(f"  consistency acceptance:     "
          f"{report['monte_carlo']['consistency_acceptance_rate']:.1%}")

    primary = report["charts"]["primary_awareness_rate"]
    if primary["status"] == "ok":
        print(f"  primary chart: CL {primary['centre_line']:,.0f} "
              f"[{primary['lcl']:,.0f}, {primary['ucl']:,.0f}] per 1,000 person-months")
        for s in primary["signals"]:
            print(f"    {s['severity'].upper()}: {s['period']} {s['rule']}")
    else:
        print(f"  primary chart: {primary['reason']}")

    if not report["publishable"]:
        print("  NOT PUBLISHABLE:")
        for b in report["publication_blockers"]:
            print(f"    - {b}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
