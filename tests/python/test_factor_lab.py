"""Tests for the factor lab.

The load-bearing ones are the last two: they encode WHY this module
replaced the in-sample screen it came from. If someone reintroduces
in-sample scoring or drops the noise control, those fail.
"""

import json
import random
from pathlib import Path

import pytest
from conftest import load


def walk(n=400, s0=100.0, vol=0.02, seed=11, drift=0.0):
    """Geometric random walk: next-day return is unpredictable by design."""
    rng = random.Random(seed)
    px, bars = s0, []
    for i in range(n):
        px *= (1 + drift + rng.gauss(0, vol))
        bars.append((f"d{i:04d}", round(px, 4),
                     abs(rng.gauss(5e6, 1.2e6))))
    return bars


def predictable(n=400, seed=5):
    """A series where volume surge genuinely leads the next return.

    Used to prove the harness can DETECT signal — a diagnostic that
    always reports "no skill" is not measuring anything.
    """
    rng = random.Random(seed)
    px, bars, pending = 100.0, [], 0.0
    for i in range(n):
        px *= (1 + pending + rng.gauss(0, 0.004))
        surge = rng.choice([1.0, 1.0, 3.0])
        pending = 0.02 if surge > 2 else -0.002
        bars.append((f"d{i:04d}", round(px, 4), 5e6 * surge))
    return bars


# --------------------------------------------------------------------- units

def test_winsorize_clips_without_dropping_rows():
    fl = load("factor_lab")
    values = [0.01] * 50 + [5.0, -5.0]
    out, clipped = fl.winsorize(values)
    assert len(out) == len(values)      # time series stays continuous
    assert clipped == 2
    assert max(out) < 5.0 and min(out) > -5.0


def test_winsorize_is_not_dragged_by_the_outlier():
    """Mean/stdev move toward an extreme value; median/MAD do not."""
    fl = load("factor_lab")
    clean = [0.001 * ((i % 7) - 3) for i in range(200)]
    out, clipped = fl.winsorize(clean + [10.0])
    assert clipped == 1                 # only the planted value is touched
    assert out[:200] == clean


def test_winsorize_handles_degenerate_input():
    fl = load("factor_lab")
    assert fl.winsorize([0.5, 0.5, 0.5])[1] == 0
    assert fl.winsorize([1.0])[1] == 0


def test_spearman_detects_monotone_and_ignores_scale():
    fl = load("factor_lab")
    a = [1, 2, 3, 4, 5, 6]
    assert fl.spearman(a, [10, 20, 30, 40, 50, 60]) == 1.0
    assert fl.spearman(a, [-1, -2, -3, -4, -5, -6]) == -1.0
    assert fl.spearman(a, a[::-1]) == -1.0


def test_spearman_handles_ties():
    fl = load("factor_lab")
    assert fl.spearman([1, 1, 1, 2], [3, 3, 3, 9]) is not None


def test_oos_r2_can_go_negative():
    """The property that makes out-of-sample scoring honest: a model
    worse than the mean is reported as worse than the mean."""
    fl = load("factor_lab")
    assert fl.r_squared([1.0, 2.0, 3.0], [9.0, -9.0, 9.0]) < 0


def test_ols_recovers_known_coefficients():
    fl = load("factor_lab")
    X = [[1.0, float(i), float(i % 3)] for i in range(40)]
    y = [2.0 + 3.0 * r[1] - 1.5 * r[2] for r in X]
    beta = fl.ols(X, y)
    assert beta[0] == pytest.approx(2.0, abs=1e-3)
    assert beta[1] == pytest.approx(3.0, abs=1e-3)
    assert beta[2] == pytest.approx(-1.5, abs=1e-3)


def test_ols_survives_a_collinear_column():
    fl = load("factor_lab")
    X = [[1.0, float(i), float(i)] for i in range(30)]   # duplicated column
    y = [float(i) for i in range(30)]
    assert all(isinstance(b, float) for b in fl.ols(X, y))


# ------------------------------------------------------------------ features

def test_rows_never_use_the_future():
    """Each row's features must come from strictly before its target."""
    fl = load("factor_lab")
    bars = walk(n=200)
    rows, _ = fl.build_rows(bars)
    dates = [b[0] for b in bars]
    for r in rows:
        i = dates.index(r["date"])
        expected = (bars[i + 1][1] - bars[i][1]) / bars[i][1]
        # target is next-day return (post-winsorizing, so bounded not exact)
        assert abs(r["target"]) <= abs(expected) + 1e-9


def test_zero_volume_bars_do_not_produce_features():
    fl = load("factor_lab")
    bars = [(f"d{i}", 100.0 + i, 0.0) for i in range(60)]
    rows, _ = fl.build_rows(bars)
    assert rows == []


# -------------------------------------------------------------- walk-forward

def test_walk_forward_refuses_a_short_series():
    fl = load("factor_lab")
    rows, _ = fl.build_rows(walk(n=90))
    out = fl.walk_forward(rows, ["vol_surge", "vwap_momentum"])
    assert out["evaluated"] is False and "need" in out["reason"]


def test_walk_forward_detects_real_signal():
    """Guards against the opposite failure: a harness that reports
    'no predictive power' unconditionally proves nothing."""
    fl = load("factor_lab")
    rows, _ = fl.build_rows(predictable())
    out = fl.walk_forward(rows, ["vol_surge", "vwap_momentum"])
    assert out["evaluated"] is True
    assert out["oos_r2"] > 0.05
    assert abs(out["ic_t_stat"]) > 3


def test_walk_forward_reports_no_skill_on_a_random_walk():
    """The headline correction. The method this replaced scored its own
    training rows and could not produce this answer."""
    fl = load("factor_lab")
    rows, _ = fl.build_rows(walk(seed=3))
    out = fl.walk_forward(rows, ["vol_surge", "vwap_momentum"])
    assert out["evaluated"] is True
    assert out["oos_r2"] < 0.02          # nothing meaningful is found
    assert abs(out["ic_t_stat"]) < 3     # and it is not distinguishable


def test_in_sample_r2_would_have_claimed_skill_where_there_is_none():
    """Documents the defect being corrected, so it cannot quietly return.

    Same zero-signal data, same features. Scoring the training rows
    reports a positive fit; the walk-forward does not.
    """
    fl = load("factor_lab")
    rows, _ = fl.build_rows(walk(seed=3))
    names = ["vol_surge", "vwap_momentum"]
    cols = fl.standardize([[r[n] for r in rows] for n in names])
    X = [[1.0] + [cols[c][i] for c in range(len(names))]
         for i in range(len(rows))]
    y = [r["target"] for r in rows]
    beta = fl.ols(X, y)
    in_sample = fl.r_squared(y, [sum(b * v for b, v in zip(beta, row))
                                 for row in X])
    oos = fl.walk_forward(rows, names)["oos_r2"]
    assert in_sample >= 0                # in-sample fit cannot be negative
    assert in_sample > oos               # and it always flatters the model


def test_adding_noise_columns_inflates_in_sample_fit_toward_any_threshold():
    """Why a `min_r2` gate on in-sample fit is backwards: on data with no
    signal at all, the score rises with the number of junk regressors, so
    passing a high threshold is evidence of overfitting, not of skill."""
    fl = load("factor_lab")
    rows, _ = fl.build_rows(walk(n=300, seed=9))
    rng = random.Random(1)
    scores = []
    for n_noise in (2, 60, 150):
        names = []
        for j in range(n_noise):
            key = f"n{j}"
            for r in rows:
                r[key] = rng.gauss(0, 1)
            names.append(key)
        cols = fl.standardize([[r[n] for r in rows] for n in names])
        X = [[1.0] + [cols[c][i] for c in range(len(names))]
             for i in range(len(rows))]
        y = [r["target"] for r in rows]
        beta = fl.ols(X, y)
        scores.append(fl.r_squared(y, [sum(b * v for b, v in zip(beta, row))
                                       for row in X]))
    assert scores[0] < scores[1] < scores[2]
    assert scores[2] > 0.4               # pure noise, "explaining" the tape


# ------------------------------------------------------------------ end-to-end

def test_main_writes_a_report_with_a_noise_control(workdir, monkeypatch):
    fl = load("factor_lab")
    monkeypatch.setattr(fl, "PACE_SECONDS", 0)
    out = fl.main(bars_for=lambda symbol: walk(seed=len(symbol)))
    assert out == 0

    report = json.loads(Path("data/factor_lab.json").read_text())
    assert report["symbols_evaluated"] > 0
    assert "not a recommendation" in report["note"]
    for r in report["results"]:
        assert r["noise_control"]["evaluated"] is True
        # No direction, no confidence score, no target flag anywhere.
        assert not {"direction", "likelihood", "target_acquired",
                    "signal"} & set(r["features"])


def test_main_records_errors_without_dying(workdir, monkeypatch):
    fl = load("factor_lab")
    monkeypatch.setattr(fl, "PACE_SECONDS", 0)
    calls = {"n": 0}

    def flaky(symbol):
        calls["n"] += 1
        if calls["n"] % 2:
            raise RuntimeError("upstream 404")
        return walk(seed=calls["n"])

    assert fl.main(bars_for=flaky) == 0
    report = json.loads(Path("data/factor_lab.json").read_text())
    assert report["errors"] and "upstream 404" in report["errors"][0]


def test_main_fails_when_nothing_can_be_fetched(workdir, monkeypatch):
    fl = load("factor_lab")
    monkeypatch.setattr(fl, "PACE_SECONDS", 0)

    def dead(symbol):
        raise RuntimeError("no route to host")

    assert fl.main(bars_for=dead) == 1
    assert not Path("data/factor_lab.json").exists()


def test_validation_rejects_a_report_that_emits_direction(workdir):
    """The boundary is enforced by the pipeline, not just by convention:
    if a future edit reintroduces a buy/sell signal here, publish fails."""
    import json as _json
    vd = load("validate_data")
    Path("data/factor_lab.json").write_text(_json.dumps({
        "results": [{"symbol": "AAA",
                     "features": {"evaluated": True, "oos_sessions": 40,
                                  "direction": "BULLISH"},
                     "noise_control": {"evaluated": True}}]}))
    Path("data/quotes.json").write_text(_json.dumps({
        "updated": "2026-08-04T00:00:00Z", "quotes": [], "sectors": [],
    }))
    with pytest.raises(SystemExit) as exc:
        vd.main()
    assert exc.value.code == 1
