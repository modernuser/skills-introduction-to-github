"""Tests for the elder-fraud prevention impact estimator.

Two of these are regression tests for bugs that shipped in the first draft
and were caught only by running the thing on realistic inputs:

  * `test_ramp_up_does_not_explode_limits` -- limits were scaled by
    sqrt(weight_bar / weight_i), which during a twentyfold ramp-up in the
    protected population produced an upper control limit of $230,000,000.
  * `test_variance_contributions_are_non_negative` -- sensitivity was
    computed by freeze-one-and-rerun, which changed the acceptance set of the
    national-consistency filter and returned negative contributions.

Both are cheap to assert and would have failed loudly on the original code.
"""

import json
import math
import random
from pathlib import Path

import pytest

import prevention_impact as pi

REPO = Path(__file__).resolve().parents[2]
REAL_INPUTS = REPO / "impact" / "prevention_inputs.json"


# --------------------------------------------------------------------------
# Fixtures
# --------------------------------------------------------------------------

def minimal_config(periods=None, **overrides):
    """A small but structurally complete config."""
    config = {
        "parameters": {
            "population_60plus": {"dist": "point", "value": 78_000_000,
                                  "verified": True},
            "national_annual_loss_low": {"dist": "point", "value": 10_100_000_000,
                                         "verified": True},
            "national_annual_loss_high": {"dist": "point", "value": 81_500_000_000,
                                          "verified": True},
            "loss_median_usd": {"dist": "pert", "low": 800, "mode": 1600,
                                "high": 4000, "verified": True},
            "loss_sigma_log": {"dist": "pert", "low": 2.0, "mode": 2.8,
                               "high": 3.2, "verified": True},
            "annual_incidence_60plus": {"dist": "pert", "low": 0.002, "mode": 0.012,
                                        "high": 0.06, "verified": True},
            "rrr_intensive": {"dist": "pert", "low": 0.10, "mode": 0.22,
                              "high": 0.40, "verified": True},
            "rrr_standard": {"dist": "pert", "low": 0.05, "mode": 0.12,
                             "high": 0.25, "verified": True},
            "rrr_brief": {"dist": "pert", "low": 0.0, "mode": 0.03,
                          "high": 0.10, "verified": True},
            "persistence_half_life_months": {"dist": "pert", "low": 3.0, "mode": 9.0,
                                             "high": 24.0, "verified": True},
            "recovery_absent_intervention": {"dist": "pert", "low": 0.02, "mode": 0.10,
                                             "high": 0.30, "verified": True},
            "stage_loss_probability": {
                "contacted": {"dist": "pert", "low": 0.02, "mode": 0.08, "high": 0.25},
                "persuaded": {"dist": "pert", "low": 0.25, "mode": 0.50, "high": 0.75},
                "funds_staged": {"dist": "pert", "low": 0.55, "mode": 0.80, "high": 0.95},
                "in_transit": {"dist": "pert", "low": 0.70, "mode": 0.90, "high": 0.99},
                "_verified": True,
            },
            "evidence_weight": {
                "documented": {"dist": "point", "value": 1.0},
                "client_attested": {"dist": "pert", "low": 0.5, "mode": 0.75, "high": 0.9},
                "inferred": {"dist": "pert", "low": 0.1, "mode": 0.3, "high": 0.5},
                "_verified": True,
            },
        },
        "cohorts": {
            "intensive": {"rrr_parameter": "rrr_intensive"},
            "standard": {"rrr_parameter": "rrr_standard"},
            "brief": {"rrr_parameter": "rrr_brief"},
        },
        "national_consistency": {"enabled": True},
        "control_chart": {"sigma_multiple": 2.0,
                          "sigma_estimator": "median_moving_range",
                          "log_scale": True, "min_periods_for_limits": 8,
                          "provisional_below_periods": 20},
        "periods": periods if periods is not None else [
            {"period": f"2026-{m:02d}",
             "reach": {"intensive": 5, "standard": 25, "brief": 100},
             "interdictions": []}
            for m in range(1, 13)
        ],
    }
    config.update(overrides)
    return config


def fixed_scenario(**overrides):
    scenario = {
        "loss_median": 1600.0,
        "sigma_log": 2.8,
        "expected_loss": pi.lognormal_mean(1600.0, 2.8),
        "incidence": 0.012,
        "half_life": 9.0,
        "recovery": 0.10,
        "rrr": {"intensive": 0.22, "standard": 0.12, "brief": 0.03},
        "stage": {"contacted": 0.08, "persuaded": 0.50,
                  "funds_staged": 0.80, "in_transit": 0.90},
        "evidence": {"documented": 1.0, "client_attested": 0.75, "inferred": 0.30},
    }
    scenario.update(overrides)
    return scenario


# --------------------------------------------------------------------------
# Distributions
# --------------------------------------------------------------------------

def test_point_distribution_is_exact():
    rng = random.Random(1)
    assert pi.draw({"dist": "point", "value": 42.5}, rng) == 42.5


def test_pert_stays_inside_its_bounds():
    rng = random.Random(7)
    spec = {"dist": "pert", "low": 0.05, "mode": 0.22, "high": 0.40}
    values = [pi.draw(spec, rng) for _ in range(5000)]
    assert all(0.05 <= v <= 0.40 for v in values)
    # Mode-weighted, so the mean sits near the PERT mean, not the midpoint.
    expected = (0.05 + 4 * 0.22 + 0.40) / 6
    assert abs(sum(values) / len(values) - expected) < 0.01


def test_pert_rejects_mode_outside_bounds():
    with pytest.raises(ValueError):
        pi.draw({"dist": "pert", "low": 1.0, "mode": 0.5, "high": 2.0}, random.Random(1))


def test_unknown_distribution_raises():
    with pytest.raises(ValueError):
        pi.draw({"dist": "gaussian_ish"}, random.Random(1))


def test_lognormal_median_p95_hits_its_quantiles():
    rng = random.Random(3)
    spec = {"dist": "lognormal_median_p95", "median": 1000.0, "p95": 20000.0}
    values = sorted(pi.draw(spec, rng) for _ in range(20000))
    assert abs(pi.percentile(values, 0.50) / 1000.0 - 1.0) < 0.05
    assert abs(pi.percentile(values, 0.95) / 20000.0 - 1.0) < 0.10


def test_lognormal_mean_reconciles_ftc_median_with_ic3_mean():
    """The parameterisation is a fit to two independent sources, not a guess.

    FTC reports a median near $1,600; FBI IC3 reports a mean near $83,000 for
    adults 60+. Under a lognormal those two pin sigma at about 2.81. If this
    assertion ever fails, the loss model has drifted away from the published
    figures it claims to rest on.
    """
    sigma = math.sqrt(2 * math.log(83000 / 1600))
    assert 2.7 < sigma < 2.9
    assert abs(pi.lognormal_mean(1600.0, sigma) - 83000) < 1.0


# --------------------------------------------------------------------------
# Protected population
# --------------------------------------------------------------------------

def test_protection_decays_by_half_each_half_life():
    periods = [{"period": "m0", "reach": {"standard": 100}},
               {"period": "m1", "reach": {}},
               {"period": "m2", "reach": {}}]
    now = pi.protected_person_months(periods, "standard", 0, half_life_months=1.0)
    one = pi.protected_person_months(periods, "standard", 1, half_life_months=1.0)
    two = pi.protected_person_months(periods, "standard", 2, half_life_months=1.0)
    assert now == pytest.approx(100.0)
    assert one == pytest.approx(50.0)
    assert two == pytest.approx(25.0)


def test_protection_accumulates_across_cohorts_of_different_ages():
    periods = [{"period": "m0", "reach": {"standard": 100}},
               {"period": "m1", "reach": {"standard": 100}}]
    total = pi.protected_person_months(periods, "standard", 1, half_life_months=1.0)
    assert total == pytest.approx(150.0)


def test_a_program_that_stops_delivering_loses_its_number():
    """The decay is the anti-fiction term; assert it actually bites."""
    active = [{"period": f"m{i}", "reach": {"standard": 50}} for i in range(12)]
    stopped = active[:1] + [{"period": f"m{i}", "reach": {}} for i in range(1, 12)]
    a = pi.protected_person_months(active, "standard", 11, 9.0)
    b = pi.protected_person_months(stopped, "standard", 11, 9.0)
    assert b < a / 10


# --------------------------------------------------------------------------
# National-consistency filter
# --------------------------------------------------------------------------

def test_consistency_filter_rejects_an_absurd_national_total():
    params = minimal_config()["parameters"]
    absurd = fixed_scenario(incidence=0.5)   # implies trillions nationally
    assert not pi.scenario_is_consistent(absurd, params)


def test_consistency_filter_accepts_a_plausible_scenario():
    params = minimal_config()["parameters"]
    scenario = fixed_scenario()
    total = pi.national_total(scenario, 78_000_000)
    assert 10.1e9 <= total <= 81.5e9
    assert pi.scenario_is_consistent(scenario, params)


def test_consistency_filter_narrows_the_output_band():
    """The tether should do real work, not decorate the output."""
    with_filter = pi.simulate(minimal_config(), draws=1500, seed=11)
    without = minimal_config()
    without["national_consistency"] = {"enabled": False}
    no_filter = pi.simulate(without, draws=1500, seed=11)

    def width(sim):
        c = sim["cumulative_prevented_usd"]
        return c["p95"] - c["p05"]

    assert width(with_filter) < width(no_filter)


def test_impossible_priors_raise_rather_than_silently_narrow():
    config = minimal_config()
    config["parameters"]["national_annual_loss_low"]["value"] = 1e15
    config["parameters"]["national_annual_loss_high"]["value"] = 2e15
    with pytest.raises(RuntimeError, match="rejected every draw"):
        pi.simulate(config, draws=50, seed=5)


# --------------------------------------------------------------------------
# Interdiction discounts
# --------------------------------------------------------------------------

def test_every_discount_reduces_the_raw_exposure():
    case = {"stage": "in_transit", "exposure_usd": 100000,
            "evidence": "documented", "attribution": 1.0}
    value = pi.interdiction_case_value(case, fixed_scenario())
    assert value == pytest.approx(100000 * 0.90 * 0.90)
    assert value < 100000


def test_recovery_term_actually_subtracts():
    """Money the bank would have clawed back anyway is not prevented here."""
    case = {"stage": "in_transit", "exposure_usd": 100000, "evidence": "documented"}
    none_recovered = pi.interdiction_case_value(case, fixed_scenario(recovery=0.0))
    half_recovered = pi.interdiction_case_value(case, fixed_scenario(recovery=0.5))
    assert half_recovered == pytest.approx(none_recovered * 0.5)


def test_evidence_tiers_are_strictly_ordered():
    scenario = fixed_scenario()
    values = [pi.interdiction_case_value(
        {"stage": "persuaded", "exposure_usd": 10000, "evidence": tier}, scenario)
        for tier in ("inferred", "client_attested", "documented")]
    assert values[0] < values[1] < values[2]


def test_shared_attribution_halves_the_credit():
    scenario = fixed_scenario()
    base = {"stage": "funds_staged", "exposure_usd": 20000, "evidence": "documented"}
    sole = pi.interdiction_case_value({**base, "attribution": 1.0}, scenario)
    shared = pi.interdiction_case_value({**base, "attribution": 0.5}, scenario)
    assert shared == pytest.approx(sole * 0.5)


def test_unknown_stage_and_evidence_tier_raise():
    scenario = fixed_scenario()
    with pytest.raises(ValueError, match="stage"):
        pi.interdiction_case_value(
            {"stage": "vibes", "exposure_usd": 1, "evidence": "documented"}, scenario)
    with pytest.raises(ValueError, match="evidence"):
        pi.interdiction_case_value(
            {"stage": "persuaded", "exposure_usd": 1, "evidence": "trust me"}, scenario)


# --------------------------------------------------------------------------
# Provenance gate
# --------------------------------------------------------------------------

def test_unverified_parameter_blocks_publication():
    config = minimal_config()
    config["parameters"]["rrr_standard"]["verified"] = False
    report = pi.build_report(config, draws=400, seed=3)
    assert "rrr_standard" in report["unverified_parameters"]
    assert report["publishable"] is False


def test_grouped_parameters_are_gated_too():
    config = minimal_config()
    config["parameters"]["stage_loss_probability"]["_verified"] = False
    assert "stage_loss_probability" in pi.unverified_parameters(config["parameters"])


def test_example_periods_block_publication():
    periods = [{"period": f"2026-{m:02d}", "_example": True,
                "reach": {"standard": 25}, "interdictions": []}
               for m in range(1, 13)]
    report = pi.build_report(minimal_config(periods=periods), draws=400, seed=3)
    assert report["publishable"] is False
    assert len(report["example_periods"]) == 12


def test_fully_verified_real_data_can_publish():
    rng = random.Random(31)
    periods = [{"period": f"20{y}-{m:02d}",
                "reach": {"intensive": rng.randint(4, 12),
                          "standard": rng.randint(18, 50),
                          "brief": rng.randint(40, 260)},
                "interdictions": []}
               for y in (25, 26) for m in range(1, 13)]
    report = pi.build_report(minimal_config(periods=periods), draws=600, seed=3)
    assert report["unverified_parameters"] == []
    assert report["example_periods"] == []
    assert report["publishable"] is True, report["publication_blockers"]


def test_unvarying_reach_blocks_publication_for_want_of_limits():
    """An invariant cohort mix yields an invariant rate and no limits.

    Reported as a blocker rather than as success: a chart with no estimable
    band is not a chart that says everything is fine.
    """
    periods = [{"period": f"2026-{m:02d}",
                "reach": {"intensive": 5, "standard": 25, "brief": 100},
                "interdictions": []} for m in range(1, 13)]
    report = pi.build_report(minimal_config(periods=periods), draws=400, seed=3)
    primary = report["charts"]["primary_awareness_rate"]
    assert primary["status"] == "degenerate_no_variation"
    assert report["publishable"] is False
    assert "primary control limits not established" in report["publication_blockers"]


# --------------------------------------------------------------------------
# Control chart mechanics
# --------------------------------------------------------------------------

def test_chart_refuses_limits_below_minimum_points():
    points = [{"label": f"p{i}", "value": 100 + i} for i in range(5)]
    chart = pi.individuals_chart(points, min_points=8)
    assert chart["status"] == "insufficient_data"
    assert chart["points"] == []


def test_limits_are_flagged_provisional_below_twenty_points():
    points = [{"label": f"p{i}", "value": 100 + (i % 3)} for i in range(12)]
    chart = pi.individuals_chart(points, min_points=8, provisional_below=20)
    assert chart["status"] == "ok"
    assert chart["limits_provisional"] is True
    assert "stabilise" in chart["provisional_note"]


def _noisy(values, sd=0.01, seed=5):
    """Attach small multiplicative noise so moving ranges are non-degenerate."""
    rng = random.Random(seed)
    return [{"label": f"p{i}", "value": v * math.exp(rng.gauss(0, sd))}
            for i, v in enumerate(values)]


def test_sigma_uses_median_moving_range_not_standard_deviation():
    """A lone spike must not be allowed to inflate sigma into hiding itself."""
    points = _noisy([100.0] * 11 + [10000.0])
    robust = pi.individuals_chart(points, min_points=8, estimator="median_moving_range")
    fragile = pi.individuals_chart(points, min_points=8, estimator="mean_moving_range")
    assert robust["sigma"] < fragile["sigma"]
    assert robust["points"][-1]["beyond_limits"] is True


def test_flat_series_with_a_step_still_signals():
    """Regression: median moving range of a flat run is 0, blinding the chart.

    A zero-width band cannot be breached, so the step change most worth
    catching was the one guaranteed to be missed. The fallback to the mean
    moving range has to keep the chart able to fire.
    """
    points = [{"label": f"p{i}", "value": v}
              for i, v in enumerate([100.0] * 11 + [400.0])]
    chart = pi.individuals_chart(points, min_points=8)
    assert chart["status"] == "ok"
    assert chart["sigma"] > 0
    assert chart["sigma_fallback_note"] is not None
    assert chart["points"][-1]["beyond_limits"] is True


def test_perfectly_constant_series_reports_degenerate_rather_than_fake_limits():
    points = [{"label": f"p{i}", "value": 100.0} for i in range(12)]
    chart = pi.individuals_chart(points, min_points=8)
    assert chart["status"] == "degenerate_no_variation"
    assert chart["signals"] == []


def test_log_scale_produces_asymmetric_dollar_limits_above_zero():
    points = [{"label": f"p{i}", "value": 1000 * (1.05 ** (i % 4))} for i in range(12)]
    chart = pi.individuals_chart(points, min_points=8, log_scale=True)
    cl, ucl, lcl = chart["centre_line"], chart["ucl"], chart["lcl"]
    assert lcl > 0                       # a dollar limit below zero is meaningless
    assert (ucl - cl) > (cl - lcl)       # right-skewed, as loss data requires


def test_ramp_up_does_not_explode_limits():
    """Regression: weight scaling once produced a $230,000,000 upper limit.

    A twentyfold growth in the protected population must not widen the band,
    because the charted rate has no 1/n sampling term to widen it with.
    """
    points = [{"label": f"p{i}", "value": 2900.0 + (i % 3) * 40} for i in range(12)]
    chart = pi.individuals_chart(points, min_points=8, log_scale=True)
    assert chart["ucl"] < 4000
    assert chart["lcl"] > 2000


def test_two_of_three_rule_fires_and_is_graded_as_a_signal():
    points = _noisy([100.0] * 10 + [160.0, 165.0])
    chart = pi.individuals_chart(points, min_points=8)
    rules = {s["rule"]: s["severity"] for s in chart["signals"]}
    assert rules.get("two_of_three_beyond_2_sigma") == "signal"


def test_single_excursion_is_only_a_warning():
    points = _noisy([100.0] * 11 + [150.0])
    chart = pi.individuals_chart(points, min_points=8)
    single = [s for s in chart["signals"] if s["rule"] == "single_point_beyond_2_sigma"]
    assert single and all(s["severity"] == "warning" for s in single)


def test_run_of_eight_detects_a_level_shift():
    values = [100.0, 102.0, 98.0, 101.0] + [120.0 + i for i in range(8)]
    points = [{"label": f"p{i}", "value": v} for i, v in enumerate(values)]
    chart = pi.individuals_chart(points, min_points=8)
    assert any(s["rule"] == "run_of_8_same_side" for s in chart["signals"])


def test_trend_of_seven_detects_a_drift():
    values = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0,
              108.0, 109.0, 110.0, 111.0]
    points = [{"label": f"p{i}", "value": v} for i, v in enumerate(values)]
    chart = pi.individuals_chart(points, min_points=8)
    assert any(s["rule"] == "trend_of_7" for s in chart["signals"])


def test_stable_process_produces_no_signals():
    rng = random.Random(99)
    points = [{"label": f"p{i}", "value": 1000 * math.exp(rng.gauss(0, 0.02))}
              for i in range(24)]
    chart = pi.individuals_chart(points, min_points=8)
    assert [s for s in chart["signals"] if s["severity"] == "signal"] == []


# --------------------------------------------------------------------------
# Autocorrelation precondition
# --------------------------------------------------------------------------

def test_autocorrelation_warning_fires_on_a_strongly_correlated_series():
    values, v = [], 1000.0
    rng = random.Random(4)
    for _ in range(30):
        v = 0.95 * v + 0.05 * 1000 + rng.gauss(0, 5)
        values.append(v)
    chart = pi.individuals_chart(
        [{"label": f"p{i}", "value": v} for i, v in enumerate(values)], min_points=8)
    assert abs(chart["lag1_autocorrelation"]) > 0.5
    assert "over-signal" in chart["autocorrelation_warning"]


def test_no_autocorrelation_warning_on_independent_data():
    rng = random.Random(8)
    chart = pi.individuals_chart(
        [{"label": f"p{i}", "value": 1000 * math.exp(rng.gauss(0, 0.05))}
         for i in range(30)], min_points=8)
    assert chart["autocorrelation_warning"] is None


# --------------------------------------------------------------------------
# Count chart
# --------------------------------------------------------------------------

def test_poisson_limits_are_non_negative_integers():
    counts = [{"label": f"p{i}", "value": v}
              for i, v in enumerate([0, 1, 0, 2, 1, 0, 1, 0, 1, 2, 0, 1])]
    chart = pi.count_chart(counts, min_points=8)
    assert chart["lcl"] == 0
    assert isinstance(chart["ucl"], int) and chart["ucl"] >= max(c["value"] for c in counts)
    assert chart["lower_limit_note"] is not None


def test_count_chart_flags_a_genuine_surge():
    counts = [{"label": f"p{i}", "value": v}
              for i, v in enumerate([0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 12])]
    chart = pi.count_chart(counts, min_points=8)
    assert any(s["period"] == "p11" for s in chart["signals"])


def test_poisson_cdf_matches_known_values():
    assert pi._poisson_cdf(0, 1.0) == pytest.approx(math.exp(-1.0), rel=1e-9)
    assert pi._poisson_cdf(1, 1.0) == pytest.approx(2 * math.exp(-1.0), rel=1e-9)
    assert pi._poisson_cdf(50, 1.0) == pytest.approx(1.0, abs=1e-9)


# --------------------------------------------------------------------------
# Monte Carlo bookkeeping
# --------------------------------------------------------------------------

def test_cumulative_band_comes_from_per_draw_sums():
    """Regression: summing per-period percentiles overstates the band.

    Summing p05 across periods is only correct under perfect rank
    correlation. The periods here are strongly but not perfectly correlated,
    so the true cumulative band must be no wider than the naive sum.
    """
    sim = pi.simulate(minimal_config(), draws=2000, seed=13)
    true_width = (sim["cumulative_prevented_usd"]["p95"]
                  - sim["cumulative_prevented_usd"]["p05"])
    naive_width = sum(p["prevented_usd"]["p95"] - p["prevented_usd"]["p05"]
                      for p in sim["periods"])
    assert true_width <= naive_width


def test_variance_contributions_are_non_negative_and_sum_to_100():
    """Regression: freeze-and-rerun sensitivity returned negative shares."""
    sim = pi.simulate(minimal_config(), draws=2000, seed=17)
    contributions = pi.variance_contributions(sim)
    assert contributions
    assert all(c["share_of_explained_variance_pct"] >= 0 for c in contributions)
    assert abs(sum(c["share_of_explained_variance_pct"] for c in contributions) - 100) < 0.5


def test_variance_contributions_are_ranked():
    sim = pi.simulate(minimal_config(), draws=2000, seed=17)
    shares = [c["share_of_explained_variance_pct"] for c in pi.variance_contributions(sim)]
    assert shares == sorted(shares, reverse=True)


def test_same_seed_reproduces_the_same_report():
    a = pi.build_report(minimal_config(), draws=500, seed=21)
    b = pi.build_report(minimal_config(), draws=500, seed=21)
    assert a["estimate"] == b["estimate"]
    assert a["charts"]["primary_awareness_rate"]["points"] == \
        b["charts"]["primary_awareness_rate"]["points"]


def test_zero_reach_period_does_not_divide_by_zero():
    periods = [{"period": f"2026-{m:02d}", "reach": {}, "interdictions": []}
               for m in range(1, 13)]
    sim = pi.simulate(minimal_config(periods=periods), draws=200, seed=2)
    assert all(p["awareness_rate_per_1000_ppm"]["p50"] == 0 for p in sim["periods"])


def test_spearman_recovers_a_known_monotone_relationship():
    xs = [float(i) for i in range(200)]
    assert pi._spearman(xs, [x ** 3 for x in xs]) == pytest.approx(1.0, abs=1e-9)
    assert pi._spearman(xs, [-x for x in xs]) == pytest.approx(-1.0, abs=1e-9)


# --------------------------------------------------------------------------
# Integration against the committed inputs
# --------------------------------------------------------------------------

def test_real_inputs_file_is_valid_json_and_runs():
    config = pi.load_config(str(REAL_INPUTS))
    report = pi.build_report(config, draws=800, seed=pi.DEFAULT_SEED)
    assert report["periods"]
    assert report["charts"]["primary_awareness_rate"]["status"] == "ok"


def test_shipped_inputs_are_marked_unpublishable():
    """The committed file is example data. It must never read as a real claim."""
    config = pi.load_config(str(REAL_INPUTS))
    report = pi.build_report(config, draws=400, seed=pi.DEFAULT_SEED)
    assert report["publishable"] is False
    assert report["example_periods"]


def test_every_shipped_parameter_carries_a_source():
    """Rule 13: a control nobody checks is a claim. This one is checked."""
    params = json.loads(REAL_INPUTS.read_text())["parameters"]
    for name, spec in params.items():
        if not isinstance(spec, dict):
            continue
        if "dist" in spec:
            assert spec.get("source"), f"{name} has no source"
        elif any(k.startswith("_") for k in spec):
            assert spec.get("_source"), f"{name} group has no source"


def test_national_range_ordering_in_shipped_inputs():
    params = json.loads(REAL_INPUTS.read_text())["parameters"]
    assert (params["national_annual_loss_low"]["value"]
            < params["national_annual_loss_high"]["value"])
