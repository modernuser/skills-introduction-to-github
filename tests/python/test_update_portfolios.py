import csv
import json
from pathlib import Path

from conftest import REPO, fabricated_quotes, load, write_quotes


def setup_market(day, bump=0.0):
    """Fabricate quotes.json + sp500_closes.json for one trading day."""
    cons = [r["Symbol"].strip() for r in
            csv.DictReader(open(REPO / "data" / "sp500_constituents.csv"))]
    sp = {s: {"date": day, "close": round(50 + (hash(s) % 400) * (1 + bump), 2)}
          for s in cons}
    Path("data/sp500_closes.json").write_text(json.dumps(sp))
    payload = fabricated_quotes(date=day)
    for q in payload["quotes"]:
        base = 100 + (hash(q["symbol"]) % 300)
        mult = 1 + bump * (2 if q["symbol"] != "SPY" else 1)
        q["close"] = round(base * mult, 2)
    write_quotes(payload)


def test_seed_shape_and_determinism(workdir):
    up = load("update_portfolios")
    setup_market("2026-07-27")
    assert up.main() == 0
    d = json.loads(Path("data/portfolios.json").read_text())
    assert len(d["portfolios"]["owner"]["holdings"]) == 11
    assert len(d["portfolios"]["dartboard"]["holdings"]) == 11
    assert len(d["portfolios"]["spy"]["holdings"]) == 1
    for p in d["portfolios"].values():
        assert abs(p["value"] - 10000) < 0.5
        assert p["alpha_pp"] == 0.0
    darts = [h["symbol"] for h in d["portfolios"]["dartboard"]["holdings"]]

    Path("data/portfolios.json").unlink()
    assert up.main() == 0
    d2 = json.loads(Path("data/portfolios.json").read_text())
    assert [h["symbol"] for h in d2["portfolios"]["dartboard"]["holdings"]] == darts


def test_alpha_math_and_history(workdir):
    up = load("update_portfolios")
    setup_market("2026-07-27")
    assert up.main() == 0
    setup_market("2026-07-28", bump=0.10)
    assert up.main() == 0
    d = json.loads(Path("data/portfolios.json").read_text())
    assert len(d["history"]) == 2 and d["asof"] == "2026-07-28"
    spy_ret = d["portfolios"]["spy"]["return_pct"]
    for k in ("owner", "dartboard"):
        p = d["portfolios"][k]
        assert p["alpha_pp"] == round(p["return_pct"] - spy_ret, 2)
    assert d["portfolios"]["spy"]["alpha_pp"] == 0.0

    # same-date rerun replaces the last history point instead of appending
    assert up.main() == 0
    d = json.loads(Path("data/portfolios.json").read_text())
    assert len(d["history"]) == 2


def test_seed_degrades_when_closes_state_missing(workdir, capsys):
    """Aug 2026: this raised FileNotFoundError and failed the whole step
    whenever the S&P closes state was absent."""
    up = load("update_portfolios")
    payload = fabricated_quotes(date="2026-08-01")
    write_quotes(payload)
    assert not Path("data/sp500_closes.json").exists()

    assert up.main() == 0
    assert "cannot seed yet" in capsys.readouterr().out
    assert not Path("data/portfolios.json").exists()
