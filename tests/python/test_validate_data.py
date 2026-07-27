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
    assert h["overall"] == "ok"
    assert "generated" in h and "duration_ms" in h
