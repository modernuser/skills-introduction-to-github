import json

from conftest import load, long_history


def test_schema_and_52_week_range(workdir):
    uq = load("update_quotes")
    hist = long_history()
    uq.fetch_closes = lambda s: hist
    assert uq.main() == 0
    data = json.loads((workdir / "data" / "quotes.json").read_text())
    assert len(data["quotes"]) == 13
    assert len(data["core"]) == 11
    assert len(data["sectors"]) == 11
    year = [c for _, c in hist[-252:]]
    q0 = data["quotes"][0]
    assert q0["hi52"] == max(year) and q0["lo52"] == min(year)
    assert len(q0["recent"]) == 30
    assert all("recent" not in c and "hi52" not in c for c in data["core"])


def test_short_history_omits_52_week(workdir):
    uq = load("update_quotes")
    uq.fetch_closes = lambda s: long_history()[-30:]
    errors = []
    q = uq.build_quote("NVDA", "NVIDIA", errors, with_recent=True)
    assert "hi52" not in q and errors == []


def test_significant_flag(workdir):
    uq = load("update_quotes")
    hist = long_history()
    spiked = hist[:-1] + [(hist[-1][0], hist[-2][1] * 1.05)]
    uq.fetch_closes = lambda s: spiked
    q = uq.build_quote("NVDA", "NVIDIA", [], with_recent=True)
    assert q["significant"] is True and q["d1"] == 5.0


def test_all_fetches_failed_returns_error(workdir):
    uq = load("update_quotes")
    def boom(sym):
        raise OSError("network down")
    uq.fetch_closes = boom
    assert uq.main() == 1
    assert not (workdir / "data" / "quotes.json").exists()


def test_fallback_reason_is_recorded_not_swallowed(workdir, monkeypatch):
    """Aug 2026: every symbol silently fell to the 3-month Yahoo fallback,
    quietly dropping 52-week ranges, because the reason was discarded."""
    uq = load("update_quotes")
    hist = long_history()

    def dead_stooq(symbol):
        raise OSError("HTTP Error 404: Not Found")
    monkeypatch.setattr(uq, "fetch_closes_stooq", dead_stooq)
    monkeypatch.setattr(uq, "fetch_closes_yahoo", lambda s: hist[-60:])

    assert uq.main() == 0
    data = json.loads((workdir / "data" / "quotes.json").read_text())
    assert data["fallback_count"] == 35          # 13 watchlist + 11 core + 11 sectors
    assert "404" in data["primary_source_failures"][0]
    assert all(q["source"] == "yahoo-fallback" for q in data["quotes"])
    # Short fallback history must not fabricate a 52-week range.
    assert all("hi52" not in q for q in data["quotes"])
