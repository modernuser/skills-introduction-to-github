"""Tests for the MSA harness and the five-KPI panel.

The load-bearing ones: a deterministic pipeline must show EXACTLY zero
repeatability, and a source that disagrees with another must be caught
as reproducibility rather than absorbed into part variation.
"""

import json
import math
import random
from pathlib import Path

import pytest
from conftest import load


def bars(n=400, seed=3, drift=0.0005, vol=0.015, base_vol=5e6):
    rng = random.Random(seed)
    px, out = 100.0, []
    for i in range(n):
        px *= (1 + drift + rng.gauss(0, vol))
        out.append((f"d{i:04d}", round(px, 4), abs(rng.gauss(base_vol, 1e6))))
    return out


# ------------------------------------------------------------------ Gage R&R

def test_deterministic_pipeline_has_exactly_zero_repeatability():
    """The property that makes this diagnostic worth running: identical
    inputs must give identical outputs, so EV is 0 and any nonzero value
    is a bug signal rather than noise."""
    g = load("gage_rr")
    m = {f"T{i}": {"stooq": [10.0 + i] * 3} for i in range(6)}
    r = g.analyze(m)
    assert r["repeatability_sd"] == 0.0
    assert r["deterministic"] is True


def test_agreeing_sources_pass():
    g = load("gage_rr")
    m = {f"T{i}": {"stooq": [10.0 + i] * 2, "yahoo": [10.0 + i] * 2}
         for i in range(8)}
    r = g.analyze(m)
    assert r["pct_rr"] == 0.0
    assert r["verdict"] == "acceptable"
    assert g.acceptance(r)["status"] == "PASS"


def test_disagreeing_sources_are_caught_as_reproducibility():
    """The audit's latent defect: a per-symbol fallback can mix two
    price-adjustment conventions inside one ranking. A constant offset
    between sources must surface as reproducibility, and must FAIL when
    it swamps the spread between tickers."""
    g = load("gage_rr")
    m = {f"T{i}": {"stooq": [10.0 + i * 0.1] * 2,
                   "yahoo": [10.0 + i * 0.1 + 5.0] * 2}   # large offset
         for i in range(8)}
    r = g.analyze(m)
    assert r["reproducibility_sd"] > 0
    assert r["verdict"] == "unacceptable"
    gate = g.acceptance(r)
    assert gate["status"] == "FAIL"
    assert "%R&R" in gate["reason"]


def test_small_source_disagreement_is_acceptable():
    g = load("gage_rr")
    m = {f"T{i}": {"stooq": [10.0 + i] * 2, "yahoo": [10.0 + i + 0.01] * 2}
         for i in range(10)}
    r = g.analyze(m)
    assert r["verdict"] == "acceptable"
    assert g.acceptance(r)["status"] == "PASS"


def test_nondeterminism_fails_even_when_pct_rr_looks_fine():
    """A tiny within-source wobble can leave %R&R low while still meaning
    the pipeline is not reproducible. The gate must fail on it."""
    g = load("gage_rr")
    m = {f"T{i}": {"stooq": [10.0 + i, 10.0 + i + 0.0001]} for i in range(12)}
    r = g.analyze(m)
    assert r["deterministic"] is False
    gate = g.acceptance(r)
    assert gate["status"] == "FAIL"
    assert "deterministic" in gate["reason"]


def test_kpi_that_cannot_rank_anything_is_flagged():
    """Zero part variation means every ticker measures the same — the
    KPI is incapable of ranking, which must not read as success."""
    g = load("gage_rr")
    m = {f"T{i}": {"stooq": [7.0] * 2} for i in range(6)}
    r = g.analyze(m)
    assert g.acceptance(r)["status"] == "FAIL"


def test_too_few_parts_fails_rather_than_passing_silently():
    g = load("gage_rr")
    r = g.analyze({"ONLY": {"stooq": [1.0, 1.0]}})
    assert r["evaluated"] is False
    gate = g.acceptance(r)
    assert gate["status"] == "FAIL" and gate["root_cause_required"] is True


def test_run_reports_overall_fail_if_any_kpi_fails():
    g = load("gage_rr")
    good = {f"T{i}": {"s": [1.0 + i] * 2} for i in range(6)}
    bad = {f"T{i}": {"s": [1.0 + i * 0.001] * 2,
                     "y": [1.0 + i * 0.001 + 9.0] * 2} for i in range(6)}
    rep = g.run({"good_kpi": good, "bad_kpi": bad})
    assert rep["gates"]["good_kpi"]["status"] == "PASS"
    assert rep["gates"]["bad_kpi"]["status"] == "FAIL"
    assert rep["overall"] == "FAIL"


# ----------------------------------------------------------------- KPI panel

def test_all_five_kpis_are_produced():
    kp = load("kpi_panel")
    row = kp.measure(bars())
    assert set(row["kpis"]) == set(kp.KPI_NAMES)
    assert all(v is not None for v in row["kpis"].values())


def test_every_requested_window_is_present():
    kp = load("kpi_panel")
    row = kp.measure(bars(n=400))
    assert [int(k[1:]) for k in row["returns"]] == kp.RETURN_WINDOWS
    assert all(v is not None for v in row["returns"].values())


def test_windows_longer_than_history_report_null_not_a_short_window():
    """A 360-session return computed from 200 sessions is a different
    number wearing the same label."""
    kp = load("kpi_panel")
    row = kp.measure(bars(n=120))
    assert row["returns"]["r90"] is not None
    assert row["returns"]["r200"] is None
    assert row["returns"]["r360"] is None


def test_drawdown_is_negative_and_bounded():
    kp = load("kpi_panel")
    closes = [100, 120, 60, 80]           # peak 120 -> trough 60 = -50%
    assert kp.max_drawdown(closes) == pytest.approx(-50.0, abs=0.01)
    assert kp.max_drawdown([100, 101, 102]) == 0.0


def test_drawdown_and_volatility_answer_different_questions():
    """A steady grind down has low volatility and a large drawdown."""
    kp = load("kpi_panel")
    grind = [100 * (0.997 ** i) for i in range(120)]
    assert kp.max_drawdown(grind) < -20
    assert kp.realized_volatility(grind) < 5


def test_volume_surge_matches_the_ratio():
    kp = load("kpi_panel")
    vols = [1000.0] * 20 + [3000.0]
    assert kp.volume_surge(vols) == pytest.approx(3.0, abs=1e-6)


def test_short_history_yields_nulls_not_exceptions():
    kp = load("kpi_panel")
    row = kp.measure(bars(n=8))
    assert row["kpis"]["vol_30d"] is None
    assert row["kpis"]["trend_r2_90d"] is None


def test_gage_input_shape_round_trips(workdir):
    kp = load("kpi_panel")
    g = load("gage_rr")
    hist = {f"T{i}": bars(seed=i) for i in range(6)}
    panels = {"stooq": kp.build(hist, {}), "yahoo": kp.build(hist, {})}
    kpis = kp.as_gage_input(panels)
    assert set(kpis) == set(kp.KPI_NAMES)
    rep = g.run(kpis)
    # identical inputs from both "sources" => perfect agreement
    assert rep["overall"] == "PASS"


def test_panel_emits_no_direction_or_recommendation(workdir):
    kp = load("kpi_panel")
    hist = {f"T{i}": bars(seed=i) for i in range(4)}
    assert kp.main({"stooq": hist}, names={}) in (0, 1)
    out = json.loads(Path("data/kpi_panel.json").read_text())
    banned = {"direction", "likelihood", "signal", "target_acquired",
              "recommendation", "buy", "sell"}
    for row in out["panel"].values():
        assert not banned & set(row) and not banned & set(row["kpis"])
    assert "forecast" in out["note"] and "advice" in out["note"]
