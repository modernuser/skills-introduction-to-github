"""Tests for trend quality and the dartboard's trend arm.

The r2 here is goodness-of-fit of log(price) on time — a description of
how straight the past path was. These tests pin that meaning: a perfect
exponential must score 1.0, and a random walk must not clear 0.88.
"""

import json
import math
import random
from pathlib import Path

import pytest
from conftest import load


def exponential(n=120, daily=0.001):
    """A perfectly straight line in log space."""
    return [(f"d{i:04d}", round(100.0 * math.exp(daily * i), 6))
            for i in range(n)]


def noisy_trend(n=120, daily=0.001, jitter=0.004, seed=2):
    rng = random.Random(seed)
    return [(f"d{i:04d}", round(100.0 * math.exp(daily * i)
                                * (1 + rng.gauss(0, jitter)), 6))
            for i in range(n)]


def walk(n=120, seed=4, vol=0.02):
    rng = random.Random(seed)
    px, out = 100.0, []
    for i in range(n):
        px *= (1 + rng.gauss(0, vol))
        out.append((f"d{i:04d}", round(px, 6)))
    return out


# ------------------------------------------------------------------- the fit

def test_perfect_exponential_scores_r2_of_one():
    tq = load("trend_quality")
    stats = tq.fit([c for _, c in exponential()])
    assert stats["r2"] == pytest.approx(1.0, abs=1e-9)


def test_annualized_slope_matches_the_compounded_rate():
    tq = load("trend_quality")
    stats = tq.fit([c for _, c in exponential(daily=0.001)])
    expected = (math.exp(0.001 * 252) - 1) * 100      # ~28.7%
    assert stats["slope_annual_pct"] == pytest.approx(expected, rel=1e-4)


def test_a_random_walk_does_not_clear_the_r2_floor():
    """The floor has to actually exclude something, or it is decoration."""
    tq = load("trend_quality")
    scores = [tq.fit([c for _, c in walk(seed=s)])["r2"] for s in range(15)]
    assert sum(1 for r in scores if r >= tq.MIN_R2) <= 3   # rarely, by chance


def test_noise_lowers_r2_without_moving_the_slope_much():
    tq = load("trend_quality")
    clean = tq.fit([c for _, c in exponential()])
    noisy = tq.fit([c for _, c in noisy_trend()])
    assert noisy["r2"] < clean["r2"]
    assert noisy["slope_annual_pct"] == pytest.approx(
        clean["slope_annual_pct"], rel=0.25)


def test_downtrend_gets_a_negative_slope_and_high_r2():
    """A straight line DOWN is also a straight line: r2 says nothing
    about direction, which is why selection also requires slope > 0."""
    tq = load("trend_quality")
    stats = tq.fit([c for _, c in exponential(daily=-0.001)])
    assert stats["r2"] == pytest.approx(1.0, abs=1e-9)
    assert stats["slope_annual_pct"] < 0


def test_fit_rejects_short_or_invalid_series():
    tq = load("trend_quality")
    assert tq.fit([100.0] * 10) is None                  # too short
    assert tq.fit([100.0, 0.0] + [100.0] * 70) is None   # non-positive price
    assert tq.fit([100.0] * 80) is None                  # flat: no variance


# -------------------------------------------------------------- the selection

def test_selection_requires_both_straightness_and_a_rising_slope():
    tq = load("trend_quality")
    rows = [
        {"symbol": "UP", "r2": 0.95, "slope_annual_pct": 40.0},
        {"symbol": "DOWN", "r2": 0.99, "slope_annual_pct": -40.0},
        {"symbol": "CHOPPY", "r2": 0.40, "slope_annual_pct": 90.0},
    ]
    assert [r["symbol"] for r in tq.select(rows)] == ["UP"]


def test_ranking_prefers_a_steady_climb_over_a_violent_one():
    tq = load("trend_quality")
    steady = {"symbol": "STEADY", "r2": 0.95, "slope_annual_pct": 120.0}
    violent = {"symbol": "VIOLENT", "r2": 0.30, "slope_annual_pct": 300.0}
    assert tq.score(steady) > tq.score(violent)


def test_empty_selection_when_nothing_qualifies():
    tq = load("trend_quality")
    assert tq.select([{"symbol": "X", "r2": 0.5, "slope_annual_pct": 10.0}]) == []


def test_build_ranks_and_writes(workdir):
    tq = load("trend_quality")
    histories = {"AAA": exponential(daily=0.002),
                 "BBB": exponential(daily=0.0005),
                 "CCC": walk(seed=9)}
    assert tq.main(histories=histories) == 0
    out = json.loads(Path("data/trend_quality.json").read_text())
    assert out["measured"] == 3
    assert [r["symbol"] for r in out["ranked"]][:2] == ["AAA", "BBB"]
    assert "not a forecast" in out["note"]


# ----------------------------------------------------- the dartboard trend arm

def _prices(symbols, date="2026-08-04", close=50.0):
    return {s: {"date": date, "close": close} for s in symbols}


def test_trend_arm_is_skipped_when_no_file_exists(workdir):
    up = load("update_portfolios")
    state = {"portfolios": {"spy": {"return_pct": 1.0}}}
    assert up.add_trend_portfolio(state, _prices(["A"]), {}) is False
    assert "trend" not in state["portfolios"]


def test_trend_arm_is_skipped_when_nothing_qualifies(workdir):
    up = load("update_portfolios")
    Path("data/trend_quality.json").write_text(json.dumps({"selected": []}))
    state = {"portfolios": {"spy": {"return_pct": 1.0}}}
    assert up.add_trend_portfolio(state, _prices(["A"]), {}) is False


def test_trend_arm_funds_equal_weight_from_the_selection(workdir):
    up = load("update_portfolios")
    picks = ["AAA", "BBB", "CCC"]
    Path("data/trend_quality.json").write_text(json.dumps(
        {"selected": [{"symbol": s} for s in picks]}))
    state = {"portfolios": {"spy": {"return_pct": 4.0}}}
    assert up.add_trend_portfolio(state, _prices(picks), {}) is True

    arm = state["portfolios"]["trend"]
    assert [h["symbol"] for h in arm["holdings"]] == picks
    # equal weight: each leg funded with the same dollar amount
    legs = {round(h["shares"] * h["start_close"], 2) for h in arm["holdings"]}
    assert legs == {round(up.START_CASH / 3, 2)}
    # SPY's standing at funding time is recorded for the alpha window
    assert arm["spy_return_at_start"] == 4.0


def test_alpha_for_a_late_arm_is_measured_from_its_own_start(workdir):
    """The correction that makes a late-funded arm comparable: it must not
    be credited with SPY's gains from before it held anything."""
    up = load("update_portfolios")
    state = {
        "start_cash": 100.0,
        "start_date": "2026-01-01",
        "portfolios": {
            "spy": {"holdings": [{"symbol": "SPY", "shares": 1.0,
                                  "last_close": 110.0}]},
            "trend": {"holdings": [{"symbol": "T", "shares": 1.0,
                                    "last_close": 105.0}],
                      "spy_return_at_start": 8.0},
        },
        "history": [],
    }
    up.revalue(state, {"SPY": {"date": "2026-08-04", "close": 110.0},
                       "T": {"date": "2026-08-04", "close": 105.0}})
    # SPY is +10% overall but only +1.85% since the arm was funded at +8%.
    # Naive subtraction would report 5 - 10 = -5.0pp; the true figure is
    # 5 - 1.85 = +3.15pp.
    assert state["portfolios"]["spy"]["return_pct"] == 10.0
    assert state["portfolios"]["trend"]["alpha_pp"] == pytest.approx(3.15, abs=0.01)


def test_alpha_unchanged_for_arms_seeded_at_inception(workdir):
    """The new window logic must reduce to the old formula when a
    portfolio started alongside SPY."""
    up = load("update_portfolios")
    state = {
        "start_cash": 100.0,
        "start_date": "2026-01-01",
        "portfolios": {
            "spy": {"holdings": [{"symbol": "SPY", "shares": 1.0,
                                  "last_close": 110.0}]},
            "owner": {"holdings": [{"symbol": "O", "shares": 1.0,
                                    "last_close": 125.0}]},
        },
        "history": [],
    }
    up.revalue(state, {"SPY": {"date": "2026-08-04", "close": 110.0},
                       "O": {"date": "2026-08-04", "close": 125.0}})
    assert state["portfolios"]["owner"]["alpha_pp"] == pytest.approx(15.0)
    assert state["portfolios"]["spy"]["alpha_pp"] == pytest.approx(0.0)


def test_validation_rejects_a_selection_below_the_floor(workdir):
    """The label says r2 >= 0.88; the publish must fail if it isn't true."""
    vd = load("validate_data")
    Path("data/trend_quality.json").write_text(json.dumps({
        "min_r2": 0.88, "select_count": 10,
        "selected": [{"symbol": "X", "r2": 0.55, "slope_annual_pct": 30.0}]}))
    Path("data/quotes.json").write_text(json.dumps({
        "updated": "2026-08-04T00:00:00Z", "quotes": [], "sectors": []}))
    with pytest.raises(SystemExit) as exc:
        vd.main()
    assert exc.value.code == 1


def test_validation_rejects_a_falling_name_in_the_selection(workdir):
    vd = load("validate_data")
    Path("data/trend_quality.json").write_text(json.dumps({
        "min_r2": 0.88, "select_count": 10,
        "selected": [{"symbol": "X", "r2": 0.99, "slope_annual_pct": -30.0}]}))
    Path("data/quotes.json").write_text(json.dumps({
        "updated": "2026-08-04T00:00:00Z", "quotes": [], "sectors": []}))
    with pytest.raises(SystemExit) as exc:
        vd.main()
    assert exc.value.code == 1
