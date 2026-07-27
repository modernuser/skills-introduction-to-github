import json
import sys
from pathlib import Path

from conftest import fabricated_quotes, load, write_quotes


def run_check(monkeypatch):
    cm = load("check_moves")
    monkeypatch.setattr(sys, "argv", ["check_moves.py", "b.md", "t.txt"])
    return cm.main()


def test_alert_dedupe_and_reset(workdir, monkeypatch, capsys):
    write_quotes(fabricated_quotes(flagged={"NVDA"}))
    assert run_check(monkeypatch) == 0
    assert "NVDA (new)" in Path("b.md").read_text()
    assert Path("t.txt").read_text() == "Significant moves 2026-07-27"
    Path("b.md").unlink(); Path("t.txt").unlink()

    # same day, same flags -> no re-notify
    assert run_check(monkeypatch) == 0
    assert not Path("b.md").exists()

    # same day, one more ticker -> only the new one marked (new)
    write_quotes(fabricated_quotes(flagged={"NVDA", "MU"}))
    assert run_check(monkeypatch) == 0
    body = Path("b.md").read_text()
    assert "MU (new)" in body and "NVDA |" in body and "NVDA (new)" not in body
    Path("b.md").unlink(); Path("t.txt").unlink()

    # new trading day -> state resets
    write_quotes(fabricated_quotes(flagged={"SPY"}, date="2026-07-28"))
    assert run_check(monkeypatch) == 0
    assert "SPY (new)" in Path("b.md").read_text()


def test_core_tickers_alert(workdir, monkeypatch):
    write_quotes(fabricated_quotes(flagged={"AAPL"}))
    assert run_check(monkeypatch) == 0
    assert "AAPL (new)" in Path("b.md").read_text()


def test_stale_dated_quote_never_alerts(workdir, monkeypatch):
    payload = fabricated_quotes(flagged={"NVDA"})
    for q in payload["quotes"]:
        if q["symbol"] == "NVDA":
            q["date"] = "2026-07-20"  # older than the rest
    write_quotes(payload)
    assert run_check(monkeypatch) == 0
    assert not Path("b.md").exists()
