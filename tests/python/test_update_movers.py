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
