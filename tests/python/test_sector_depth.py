import json
import math
import statistics
from pathlib import Path

from conftest import load

sd = load("sector_depth")


def series(returns, start=100.0):
    """Build a close series that produces exactly these daily returns."""
    prices = [start]
    for r in returns:
        prices.append(prices[-1] * (1 + r))
    return prices


def test_flat_series_has_zero_volatility():
    vol, sessions = sd.realized_volatility([100.0] * 40)
    assert vol == 0.0 and sessions == 30


def test_volatility_matches_hand_computation():
    # Alternating ±1% daily returns for 40 sessions.
    returns = [0.01 if i % 2 == 0 else -0.01 for i in range(40)]
    prices = series(returns)
    vol, sessions = sd.realized_volatility(prices)
    expected = statistics.stdev(returns[-30:]) * math.sqrt(252) * 100
    assert sessions == 30
    assert vol == round(expected, 2)


def test_window_uses_only_the_most_recent_returns():
    calm = [0.0] * 60
    stormy = [0.05, -0.05] * 15
    vol_recent_storm, _ = sd.realized_volatility(series(calm + stormy))
    vol_recent_calm, _ = sd.realized_volatility(series(stormy + calm))
    assert vol_recent_storm > 50 and vol_recent_calm == 0.0


def test_short_history_is_refused():
    vol, sessions = sd.realized_volatility([100.0] * 10)
    assert vol is None and sessions == 0


def test_non_positive_prices_are_dropped():
    prices = [0.0, -5.0] + [100.0 + i for i in range(40)]
    vol, sessions = sd.realized_volatility(prices)
    assert vol is not None and sessions == 30


CONSTITUENTS = {
    f"S{i}": {"name": f"Name {i}", "sector": "Energy" if i < 15 else "Utilities"}
    for i in range(25)
}


def closes_factory(vol_by_symbol, missing=()):
    def closes_for(symbol):
        if symbol in missing:
            raise OSError("network down")
        amp = vol_by_symbol[symbol]
        return [(f"2026-07-{(i % 28) + 1:02d}", p)
                for i, p in enumerate(series([amp if i % 2 == 0 else -amp
                                              for i in range(40)]))]
    return closes_for


def test_ranking_keeps_top_ten_in_descending_order():
    amps = {s: 0.001 * (i + 1) for i, s in enumerate(CONSTITUENTS)}
    by_sector, errors, measured, closes = sd.build(CONSTITUENTS, closes_factory(amps))
    assert measured == 25 and errors == []
    assert len(closes) == 25 and closes["S0"]["close"] > 0
    top = sd.top_per_sector(by_sector)

    assert set(top) == {"Energy", "Utilities"}
    assert len(top["Energy"]) == 10 and len(top["Utilities"]) == 10
    for rows in top.values():
        vols = [r["vol_30d"] for r in rows]
        assert vols == sorted(vols, reverse=True)
    # Energy is S0..S14; the highest amplitudes there are S14, S13, S12...
    assert [r["symbol"] for r in top["Energy"]][:3] == ["S14", "S13", "S12"]


def test_sector_smaller_than_ten_is_kept_whole():
    small = {f"S{i}": {"name": f"N{i}", "sector": "Energy"} for i in range(4)}
    amps = {s: 0.01 for s in small}
    by_sector, _, _, _ = sd.build(small, closes_factory(amps))
    top = sd.top_per_sector(by_sector)
    assert len(top["Energy"]) == 4


def test_per_symbol_failures_are_collected_not_fatal():
    amps = {s: 0.01 for s in CONSTITUENTS}
    by_sector, errors, measured, _ = sd.build(
        CONSTITUENTS, closes_factory(amps, missing={"S1", "S2"}))
    assert measured == 23
    assert len(errors) == 2 and all("network down" in e for e in errors)


def test_low_coverage_aborts_without_writing(workdir, monkeypatch):
    module = load("sector_depth")
    monkeypatch.setattr(module, "load_constituents",
                        lambda: {"AAA": {"name": "A", "sector": "Energy"}})
    monkeypatch.setattr(module, "fetch_closes",
                        lambda s: [(f"2026-07-{i + 1:02d}", 100.0 + i)
                                   for i in range(40)])
    monkeypatch.setattr(module.time, "sleep", lambda s: None)
    assert module.main() == 1
    assert not Path("data/sector_depth.json").exists()


def test_main_writes_expected_contract(workdir, monkeypatch):
    module = load("sector_depth")
    constituents = {
        f"S{i}": {"name": f"Name {i}",
                  "sector": ["Energy", "Utilities", "Financials"][i % 3]}
        for i in range(120)
    }
    monkeypatch.setattr(module, "load_constituents", lambda: constituents)
    monkeypatch.setattr(module, "fetch_closes",
                        closes_factory({s: 0.01 for s in constituents}))
    monkeypatch.setattr(module.time, "sleep", lambda s: None)
    assert module.main() == 0

    data = json.loads(Path("data/sector_depth.json").read_text())
    assert data["coverage"] == 120
    assert data["window_sessions"] == 30 and data["per_sector"] == 10
    assert set(data["sectors"]) == {"Energy", "Utilities", "Financials"}
    assert all(len(v) == 10 for v in data["sectors"].values())
    assert "risk measure" in data["note"].lower()
    row = data["sectors"]["Energy"][0]
    assert row["vol_30d"] > 0 and row["last_close"] > 0
    assert set(row) == {"symbol", "name", "vol_30d", "sessions",
                        "last_close", "as_of"}


def test_writes_sp500_closes_state(workdir, monkeypatch):
    """The endpoint update_movers used began 404ing; this job's per-symbol
    fetches are the surviving source of the closes state that the dartboard,
    movers and rotation all depend on."""
    module = load("sector_depth")
    constituents = {f"S{i}": {"name": f"N{i}", "sector": "Energy"}
                    for i in range(120)}
    monkeypatch.setattr(module, "load_constituents", lambda: constituents)
    monkeypatch.setattr(module, "fetch_closes",
                        closes_factory({s: 0.01 for s in constituents}))
    monkeypatch.setattr(module.time, "sleep", lambda s: None)
    assert module.main() == 0

    closes = json.loads(Path("data/sp500_closes.json").read_text())
    assert len(closes) == 120
    assert set(closes["S0"]) == {"date", "close"} and closes["S0"]["close"] > 0


def test_closes_state_merges_rather_than_replaces(workdir, monkeypatch):
    """A symbol this run could not fetch keeps its previous close instead
    of disappearing from downstream features."""
    module = load("sector_depth")
    Path("data").mkdir(exist_ok=True)
    Path("data/sp500_closes.json").write_text(json.dumps(
        {"OLD": {"date": "2026-07-01", "close": 42.0}}))
    constituents = {f"S{i}": {"name": f"N{i}", "sector": "Energy"}
                    for i in range(120)}
    monkeypatch.setattr(module, "load_constituents", lambda: constituents)
    monkeypatch.setattr(module, "fetch_closes",
                        closes_factory({s: 0.01 for s in constituents}))
    monkeypatch.setattr(module.time, "sleep", lambda s: None)
    assert module.main() == 0

    closes = json.loads(Path("data/sp500_closes.json").read_text())
    assert closes["OLD"]["close"] == 42.0, "prior symbol was dropped"
    assert len(closes) == 121
