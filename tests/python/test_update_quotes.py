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


# --------------------------------------------- the Aug 2026 stooq degradation

def test_diagnose_names_what_arrived_instead_of_csv():
    """"returned no rows" could not tell a rate-limit from a dead ticker,
    which is why the outage went undiagnosed for days."""
    uq = load("update_quotes")
    assert "rate-limited" in uq.diagnose_stooq("Exceeded the daily hits limit")
    assert "HTML" in uq.diagnose_stooq("<html><body>error</body></html>")
    assert "empty" in uq.diagnose_stooq("   \n  ")
    assert "no such symbol" in uq.diagnose_stooq("No data found")
    assert "unparsable" in uq.diagnose_stooq("garbage,text")


def test_fallback_now_carries_a_52_week_range(workdir, monkeypatch):
    """The actual product fix: a 3-month fallback silently stripped the
    52-week range off every tile. A 2-year one keeps it."""
    uq = load("update_quotes")
    two_years = long_history()[-300:]
    monkeypatch.setattr(uq, "fetch_closes_stooq", lambda s: [])
    monkeypatch.setattr(uq, "fetch_closes_yahoo", lambda s: two_years)

    assert uq.main() == 0
    data = json.loads((workdir / "data" / "quotes.json").read_text())
    assert data["ranges_present"] == data["ranges_expected"] > 0
    assert all("hi52" in q and "lo52" in q for q in data["quotes"])
    assert "range=2y" in uq.YAHOO_URL


def test_short_history_still_refuses_to_fake_a_range(workdir, monkeypatch):
    """The gate must survive the URL change: a short reply from ANY source
    must not be presented as a year."""
    uq = load("update_quotes")
    monkeypatch.setattr(uq, "fetch_closes_stooq", lambda s: [])
    monkeypatch.setattr(uq, "fetch_closes_yahoo", lambda s: long_history()[-60:])

    assert uq.main() == 0
    data = json.loads((workdir / "data" / "quotes.json").read_text())
    assert data["ranges_present"] == 0
    assert all("hi52" not in q for q in data["quotes"])


def test_circuit_breaker_stops_hammering_a_dead_source(workdir, monkeypatch):
    """35 futile round-trips per run against a host that may be rate-
    limiting us makes the problem worse, not better."""
    uq = load("update_quotes")
    calls = []

    def dead(symbol):
        calls.append(symbol)
        return []
    monkeypatch.setattr(uq, "fetch_closes_stooq", dead)
    monkeypatch.setattr(uq, "fetch_closes_yahoo", lambda s: long_history()[-300:])

    assert uq.main() == 0
    assert len(calls) == uq.STOOQ_GIVE_UP_AFTER
    assert any("skipping it for the rest of this run" in m
               for m in uq.PRIMARY_FAILURES)


def test_fallback_count_covers_symbols_the_breaker_never_reported(workdir,
                                                                  monkeypatch):
    """The counter and the message list measure different things: once the
    breaker trips there is no per-symbol message, but those symbols are
    still on the fallback and health must say so."""
    uq = load("update_quotes")
    monkeypatch.setattr(uq, "fetch_closes_stooq", lambda s: [])
    monkeypatch.setattr(uq, "fetch_closes_yahoo", lambda s: long_history()[-300:])

    assert uq.main() == 0
    data = json.loads((workdir / "data" / "quotes.json").read_text())
    assert data["fallback_count"] == 35            # every symbol
    assert len(data["primary_source_failures"]) < 35   # only the first few


def test_a_recovering_source_resets_the_breaker(workdir, monkeypatch):
    """One bad symbol must not condemn the rest of the run."""
    uq = load("update_quotes")
    hist = long_history()[-300:]
    seen = []

    def flaky(symbol):
        seen.append(symbol)
        return [] if len(seen) == 1 else hist
    monkeypatch.setattr(uq, "fetch_closes_stooq", flaky)
    monkeypatch.setattr(uq, "fetch_closes_yahoo", lambda s: hist)

    assert uq.main() == 0
    data = json.loads((workdir / "data" / "quotes.json").read_text())
    assert data["fallback_count"] == 1
    assert len(seen) == 35                          # never gave up
