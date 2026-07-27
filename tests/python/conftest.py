"""Shared fixtures: every test runs offline in an isolated temp repo.

Network functions are monkeypatched per-test; config files are copied
from the real repo so tests track the actual watchlist/constituents.
"""

import importlib
import json
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))


@pytest.fixture
def workdir(tmp_path, monkeypatch):
    """Chdir into a temp copy of the repo's config + empty data dir."""
    (tmp_path / "data").mkdir()
    shutil.copy(REPO / "watchlist.json", tmp_path / "watchlist.json")
    shutil.copy(REPO / "data" / "sp500_constituents.csv",
                tmp_path / "data" / "sp500_constituents.csv")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def load(module_name):
    """Fresh import so module-level config reads the current workdir."""
    if module_name in sys.modules:
        return importlib.reload(sys.modules[module_name])
    return importlib.import_module(module_name)


def long_history():
    """~300 sessions of synthetic closes (enough for 52-week logic)."""
    return [(f"2026-{m:02d}-{d:02d}", 100.0 + m + d / 100)
            for m in range(1, 12) for d in range(1, 29)][:300]


def fabricated_quotes(flagged=(), date="2026-07-27"):
    """A structurally valid quotes.json payload with optional flags."""
    def q(sym, name, sig):
        return {"symbol": sym, "name": name, "date": date, "close": 100.0,
                "d1": -5.0 if sig else 1.0, "w1": 0.5, "m1": 2.0,
                "significant": sig}
    watch = json.loads((REPO / "watchlist.json").read_text())
    return {
        "updated": date + "T20:00:00Z", "significant_pct": 3.0,
        "quotes": [q(s, n, s in flagged) for s, n in watch["watchlist"].items()],
        "core": [q(s, n, s in flagged) for s, n in watch["core"].items()],
        "sectors": [q(s, n, False) for s, n in watch["sectors"].items()],
        "errors": [],
    }


def write_quotes(payload):
    Path("data/quotes.json").write_text(json.dumps(payload))
