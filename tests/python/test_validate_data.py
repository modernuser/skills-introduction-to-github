import json
from pathlib import Path

import pytest

from conftest import fabricated_quotes, load, write_quotes


def run_validator():
    vd = load("validate_data")
    try:
        return vd.main()
    except SystemExit as exc:
        return exc.code


def test_accepts_valid_data(workdir):
    write_quotes(fabricated_quotes(date="2026-07-27"))
    # freshness check compares against today; use a dynamic recent date
    import datetime
    payload = fabricated_quotes(
        date=datetime.date.today().isoformat())
    write_quotes(payload)
    assert run_validator() == 0


def test_rejects_stale_data(workdir):
    write_quotes(fabricated_quotes(date="2026-01-01"))
    with pytest.raises(SystemExit) as exc:
        load("validate_data").main()
    assert exc.value.code == 1


def test_rejects_wrong_sector_count(workdir):
    import datetime
    payload = fabricated_quotes(date=datetime.date.today().isoformat())
    payload["sectors"] = payload["sectors"][:5]
    write_quotes(payload)
    with pytest.raises(SystemExit) as exc:
        load("validate_data").main()
    assert exc.value.code == 1


def test_rejects_close_outside_52_week_range(workdir):
    import datetime
    payload = fabricated_quotes(date=datetime.date.today().isoformat())
    payload["quotes"][0]["hi52"] = 90.0   # close is 100.0 -> outside range
    payload["quotes"][0]["lo52"] = 80.0
    write_quotes(payload)
    with pytest.raises(SystemExit) as exc:
        load("validate_data").main()
    assert exc.value.code == 1


def test_rejects_broken_portfolio(workdir):
    import datetime
    write_quotes(fabricated_quotes(date=datetime.date.today().isoformat()))
    Path("data/portfolios.json").write_text(json.dumps({
        "portfolios": {"owner": {"value": -5,
                                 "holdings": [{"shares": 1, "last_close": 1}]}}}))
    with pytest.raises(SystemExit) as exc:
        load("validate_data").main()
    assert exc.value.code == 1


def test_health_report_written(workdir):
    import datetime
    write_quotes(fabricated_quotes(date=datetime.date.today().isoformat()))
    assert run_validator() == 0
    h = json.loads(Path("data/health.json").read_text())
    assert h["files"]["quotes"]["status"] == "ok"
    assert h["files"]["quotes"]["records"] == 35
    assert h["files"]["news"]["status"] == "missing"
    # A missing expected file is a fault, not a shrug. Until Sep 2026 only
    # "stale" counted toward `overall`, so kpi_panel and gage_rr were absent
    # for eight weeks while health reported "ok" every single run.
    assert h["overall"] == "degraded"
    assert "news" in h["missing_unexpected"]
    assert "generated" in h and "duration_ms" in h


def test_rejects_unordered_sector_depth(workdir):
    import datetime
    write_quotes(fabricated_quotes(date=datetime.date.today().isoformat()))
    Path("data/sector_depth.json").write_text(json.dumps({
        "per_sector": 10,
        "sectors": {"Energy": [
            {"symbol": "A", "vol_30d": 20.0, "last_close": 10.0},
            {"symbol": "B", "vol_30d": 45.0, "last_close": 10.0},  # out of order
        ]}}))
    with pytest.raises(SystemExit) as exc:
        load("validate_data").main()
    assert exc.value.code == 1


def test_accepts_wellformed_sector_depth(workdir):
    import datetime
    write_quotes(fabricated_quotes(date=datetime.date.today().isoformat()))
    Path("data/sector_depth.json").write_text(json.dumps({
        "generated": "2026-07-27T22:20:00Z", "per_sector": 10,
        "sectors": {"Energy": [
            {"symbol": "B", "vol_30d": 45.0, "last_close": 10.0},
            {"symbol": "A", "vol_30d": 20.0, "last_close": 10.0},
        ]}}))
    assert run_validator() == 0
    h = json.loads(Path("data/health.json").read_text())
    assert h["files"]["sector_depth"]["records"] == 2


def test_session_gated_file_absence_is_never_a_fault(workdir):
    """extended.json exists only once a pre/after session has printed, so
    its absence must never appear as a fault — an alarm that cries wolf
    stops being read, which is how the real one got ignored."""
    import datetime
    vd = load("validate_data")
    assert "extended" in vd.OPTIONAL_FILES
    write_quotes(fabricated_quotes(date=datetime.date.today().isoformat()))
    assert run_validator() == 0
    h = json.loads(Path("data/health.json").read_text())
    assert h["files"]["extended"]["status"] == "missing"
    assert "extended" not in h["missing_unexpected"]
    # ...while a genuinely unexpected absence IS reported.
    assert "kpi_panel" in h["missing_unexpected"]
    assert "gage_rr" in h["missing_unexpected"]
