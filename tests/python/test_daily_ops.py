import json
import shutil
from pathlib import Path

from conftest import REPO, load


def test_link_scan_on_real_repo_finds_nothing_broken():
    do = load("daily_ops")
    assert do.scan_internal_links(str(REPO)) == []


def test_reports_generated(workdir, monkeypatch):
    do = load("daily_ops")
    monkeypatch.setattr(do, "run_tests", lambda: {
        "passed": 21, "failed": 0, "ok": True, "summary": "21 passed"})
    for page in ("index.html", "tracker.html", "dartboard.html", "styles.css"):
        shutil.copy(REPO / page, Path(page))
    Path("runs.json").write_text(json.dumps(
        [{"conclusion": "success"}] * 9 + [{"conclusion": "failure"}]))
    import sys
    monkeypatch.setattr(sys, "argv", ["daily_ops.py", "runs.json"])
    assert do.main() == 0

    sc = json.loads(Path("reports/quality-scorecard.json").read_text())
    assert sc["tests"]["passed"] == 21
    assert sc["workflow_reliability"]["reliability_pct"] == 90.0
    assert sc["broken_internal_links"] == []

    daily = list(Path("reports/daily").glob("*.md"))
    assert len(daily) == 1
    body = daily[0].read_text()
    assert "No justified code change identified today." in body
    assert "no AI model invoked" in body

    hist = json.loads(Path("reports/improvement-history.json").read_text())
    assert len(hist) == 1 and hist[0]["tests_passed"] == 21

    # second run same day replaces, not duplicates, the history entry
    assert do.main() == 0
    hist = json.loads(Path("reports/improvement-history.json").read_text())
    assert len(hist) == 1


def test_findings_produce_nonzero_exit(workdir, monkeypatch):
    do = load("daily_ops")
    monkeypatch.setattr(do, "run_tests", lambda: {
        "passed": 20, "failed": 1, "ok": False, "summary": "1 failed, 20 passed"})
    import sys
    monkeypatch.setattr(sys, "argv", ["daily_ops.py"])
    assert do.main() == 1
    body = next(Path("reports/daily").glob("*.md")).read_text()
    assert "tests failing" in body


def test_secret_scan_clean_on_real_repo():
    do = load("daily_ops")
    assert do.scan_for_secrets(str(REPO)) == []


def test_secret_scan_detects_planted_credentials(workdir):
    do = load("daily_ops")
    # Credential shapes are ASSEMBLED AT RUNTIME so this source file never
    # contains a literal secret — GitHub push protection blocks those, as
    # it did when this test was first written (see docs/engineering-audit).
    planted = "\n".join([
        "AWS_KEY=" + "AKIA" + "Q" * 16,
        "GH=" + "ghp" + "_" + "b" * 36,
        "SLACK=https://hooks." + "slack.com/services/" + "T01ABCDEF/B02GHIJKL/" + "x" * 24,
    ])
    Path("leak.env").write_text(planted + "\n")
    hits = do.scan_for_secrets(".")
    labels = {h.split(" in ")[0] for h in hits}
    assert {"AWS access key", "GitHub token", "Slack webhook"} <= labels


def test_secret_findings_fail_the_run(workdir, monkeypatch):
    do = load("daily_ops")
    monkeypatch.setattr(do, "run_tests", lambda: {
        "passed": 1, "failed": 0, "ok": True, "summary": "1 passed"})
    Path("bad.txt").write_text("token: 'A" + "b" * 30 + "'\n")
    import sys
    monkeypatch.setattr(sys, "argv", ["daily_ops.py"])
    assert do.main() == 1
    body = next(Path("reports/daily").glob("*.md")).read_text()
    assert "secret-pattern scan: 1 hit" in body


def test_published_freshness_flags_a_stale_site(workdir, monkeypatch):
    """The check that would have caught the six-day July 2026 outage:
    the runner's data was always fresh, but the SITE was not."""
    do = load("daily_ops")
    monkeypatch.setattr(do, "run_tests", lambda: {
        "passed": 1, "failed": 0, "ok": True, "summary": "1 passed"})
    monkeypatch.setattr(do, "check_published_freshness", lambda branch="data": {
        "checked": True, "ok": False, "published_newest": "2026-07-24",
        "expected_through": "2026-07-31", "sessions_behind": 7})
    import sys
    monkeypatch.setattr(sys, "argv", ["daily_ops.py"])

    assert do.main() == 1
    body = next(Path("reports/daily").glob("*.md")).read_text()
    assert "PUBLISHED DATA IS STALE" in body
    sc = json.loads(Path("reports/quality-scorecard.json").read_text())
    assert sc["published_freshness"]["sessions_behind"] == 7


def test_published_freshness_silent_when_current(workdir, monkeypatch):
    do = load("daily_ops")
    monkeypatch.setattr(do, "run_tests", lambda: {
        "passed": 1, "failed": 0, "ok": True, "summary": "1 passed"})
    monkeypatch.setattr(do, "check_published_freshness", lambda branch="data": {
        "checked": True, "ok": True, "published_newest": "2026-07-31",
        "expected_through": "2026-07-31", "sessions_behind": 0})
    import sys
    monkeypatch.setattr(sys, "argv", ["daily_ops.py"])

    assert do.main() == 0
    body = next(Path("reports/daily").glob("*.md")).read_text()
    assert "No justified code change identified today." in body
