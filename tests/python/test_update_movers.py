import json
from pathlib import Path

from conftest import load


def mover(sym, pct, close):
    return {"symbol": sym, "name": sym + " Inc", "sector": "Tech",
            "pct": pct, "close": close}


def test_fetch_closes_skips_unknown_symbols(workdir, monkeypatch):
    um = load("update_movers")
    rows = ("Symbol,Date,Time,Open,High,Low,Close,Volume\n"
            "mmm.us,2026-07-24,22:00,1,1,1,150.5,100\n"
            "zzzz.us,2026-07-24,22:00,1,1,1,99.9,100\n")

    class FakeResp:
        def read(self):
            return rows.encode()
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    monkeypatch.setattr(um.urllib.request, "urlopen",
                        lambda req, timeout=0: FakeResp())
    monkeypatch.setattr(um.time, "sleep", lambda s: None)
    closes = um.fetch_closes(["MMM"])
    assert closes == {"MMM": {"date": "2026-07-24", "close": 150.5}}
    assert None not in closes


def test_coverage_guard_aborts_without_changes(workdir, monkeypatch):
    um = load("update_movers")
    monkeypatch.setattr(um, "load_constituents",
                        lambda: {"MMM": {"name": "3M", "sector": "Industrials"}})
    monkeypatch.setattr(um, "fetch_closes",
                        lambda syms: {"MMM": {"date": "2026-07-24", "close": 1.0}})
    assert um.main() == 1
    assert not Path("data/sp500_closes.json").exists()


def test_rotation_lifecycle(workdir):
    um = load("update_movers")
    um.update_rotation([mover("AAA", 6.5, 100), mover("BBB", 1.0, 50)],
                       "2026-07-27")
    rot = json.loads(Path("data/rotation.json").read_text())
    assert [e["symbol"] for e in rot["entries"]] == ["AAA"]
    assert rot["entries"][0]["trigger_pct"] == 6.5

    # persists inside window; last_close refreshes; new trigger joins
    um.update_rotation([mover("AAA", 0.5, 104), mover("CCC", -5.2, 80)],
                       "2026-08-01")
    rot = json.loads(Path("data/rotation.json").read_text())
    assert {e["symbol"] for e in rot["entries"]} == {"AAA", "CCC"}
    aaa = next(e for e in rot["entries"] if e["symbol"] == "AAA")
    assert aaa["last_close"] == 104 and aaa["entered"] == "2026-07-27"

    # expires after the 14-day window
    um.update_rotation([mover("AAA", 0.1, 105), mover("CCC", 0.1, 81)],
                       "2026-08-12")
    rot = json.loads(Path("data/rotation.json").read_text())
    assert {e["symbol"] for e in rot["entries"]} == {"CCC"}

    # re-trigger refreshes the clock but preserves first_entered
    um.update_rotation([mover("CCC", 7.7, 90)], "2026-08-13")
    ccc = json.loads(Path("data/rotation.json").read_text())["entries"][0]
    assert ccc["entered"] == "2026-08-13"
    assert ccc["first_entered"] == "2026-08-01"


def test_falls_back_to_closes_state_when_bulk_fails(workdir, monkeypatch):
    """Aug 2026: the bulk endpoint began 404ing on every chunk, silently
    killing movers and the In Play rotation. sector_depth.py rebuilds the
    closes state daily from the endpoint that still works."""
    um = load("update_movers")
    cons = {f"S{i}": {"name": f"N{i}", "sector": "Energy"} for i in range(150)}
    monkeypatch.setattr(um, "load_constituents", lambda: cons)
    monkeypatch.setattr(um, "fetch_closes", lambda syms: {})  # bulk dead

    Path("data").mkdir(exist_ok=True)
    Path("data/sp500_closes.json").write_text(json.dumps(
        {s: {"date": "2026-08-04", "close": 100.0} for s in cons}))
    # A prior baseline from the day before, so moves are computable.
    Path("data/movers_prior.json").write_text(json.dumps(
        {s: {"date": "2026-08-03", "close": 90.0} for s in cons}))

    assert um.main() == 0
    movers = json.loads(Path("data/movers.json").read_text())
    assert movers["coverage"] == 150
    assert len(movers["gainers"]) == 10 and len(movers["losers"]) == 10
    assert movers["gainers"][0]["pct"] == 11.11  # 90 -> 100


def test_baseline_is_separate_from_the_daily_closes_state(workdir, monkeypatch):
    """The daily rebuild must not erase what a move is measured from."""
    um = load("update_movers")
    cons = {f"S{i}": {"name": f"N{i}", "sector": "Energy"} for i in range(150)}
    monkeypatch.setattr(um, "load_constituents", lambda: cons)
    monkeypatch.setattr(um, "fetch_closes", lambda syms: {})

    Path("data").mkdir(exist_ok=True)
    closes = {s: {"date": "2026-08-04", "close": 100.0} for s in cons}
    Path("data/sp500_closes.json").write_text(json.dumps(closes))
    assert um.main() == 0

    # The shared closes state is untouched; our own baseline is written.
    assert json.loads(Path("data/sp500_closes.json").read_text()) == closes
    assert Path("data/movers_prior.json").exists()


def test_aborts_when_neither_source_is_usable(workdir, monkeypatch):
    um = load("update_movers")
    monkeypatch.setattr(um, "load_constituents",
                        lambda: {"AAA": {"name": "A", "sector": "Energy"}})
    monkeypatch.setattr(um, "fetch_closes", lambda syms: {})
    assert um.main() == 1
    assert not Path("data/movers.json").exists()
