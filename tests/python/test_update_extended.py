import json
from datetime import datetime, timezone
from pathlib import Path

from conftest import load


def chart_payload(bars):
    """Yahoo chart shape: [(unix_ts, close_or_None), ...]."""
    return {"chart": {"result": [{
        "meta": {"chartPreviousClose": 100.0},
        "timestamp": [ts for ts, _ in bars],
        "indicators": {"quote": [{"close": [c for _, c in bars]}]},
    }]}}


def patch_fetch(monkeypatch, module, payload):
    class FakeResp:
        def read(self):
            return json.dumps(payload).encode()
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False
    monkeypatch.setattr(module.urllib.request, "urlopen",
                        lambda req, timeout=0: FakeResp())
    monkeypatch.setattr(module.json, "load", lambda f: json.loads(f.read()))


def ts(y, m, d, hh, mm=0):
    return int(datetime(y, m, d, hh, mm, tzinfo=timezone.utc).timestamp())


def test_picks_latest_premarket_print(workdir, monkeypatch):
    ue = load("update_extended")
    # 2026-07-27 08:30 and 12:00 UTC are both pre-market ET; 14:00 is regular.
    patch_fetch(monkeypatch, ue, chart_payload([
        (ts(2026, 7, 27, 8, 30), 101.0),
        (ts(2026, 7, 27, 12, 0), 104.0),
        (ts(2026, 7, 27, 14, 0), 999.0),   # regular session: must be ignored
    ]))
    out = ue.fetch_extended("NVDA")
    assert out["price"] == 104.0 and out["session"] == "pre"
    assert out["pct"] == 4.0 and out["prev_close"] == 100.0
    assert out["source"] == "yahoo-chart-prepost"


def test_regular_session_only_returns_none(workdir, monkeypatch):
    ue = load("update_extended")
    patch_fetch(monkeypatch, ue, chart_payload([(ts(2026, 7, 27, 15, 0), 110.0)]))
    assert ue.fetch_extended("NVDA") is None


def test_null_bars_tolerated(workdir, monkeypatch):
    ue = load("update_extended")
    patch_fetch(monkeypatch, ue, chart_payload([
        (ts(2026, 7, 27, 8, 30), None),
        (ts(2026, 7, 27, 9, 0), 102.5),
    ]))
    assert ue.fetch_extended("NVDA")["price"] == 102.5


def test_malformed_payload_raises_but_main_survives(workdir, monkeypatch):
    ue = load("update_extended")
    patch_fetch(monkeypatch, ue, {"chart": {"result": []}})
    monkeypatch.setattr(ue, "session_at", lambda when: "pre")
    assert ue.main() == 0                      # per-symbol errors collected
    assert not Path("data/extended.json").exists()


def test_main_skips_outside_extended_sessions(workdir, monkeypatch):
    ue = load("update_extended")
    monkeypatch.setattr(ue, "session_at", lambda when: "regular")
    assert ue.main() == 0
    assert not Path("data/extended.json").exists()


def test_main_writes_file_during_premarket(workdir, monkeypatch):
    ue = load("update_extended")
    monkeypatch.setattr(ue, "session_at", lambda when: "pre")
    monkeypatch.setattr(ue, "fetch_extended", lambda sym: {
        "price": 1.0, "prev_close": 1.0, "pct": 0.0,
        "time": "2026-07-27T12:00:00Z", "session": "pre",
        "source": "yahoo-chart-prepost"})
    assert ue.main() == 0
    data = json.loads(Path("data/extended.json").read_text())
    assert data["session"] == "pre" and len(data["quotes"]) == 24
