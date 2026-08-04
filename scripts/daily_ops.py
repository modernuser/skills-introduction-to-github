#!/usr/bin/env python3
"""Deterministic daily operations: health checks, scorecard, daily report.

No AI model is involved — this is the free, always-on tier of the
continual-improvement system. It inspects project health and writes:

  reports/daily/YYYY-MM-DD.md      human-readable daily report
  reports/quality-scorecard.json   machine-readable scorecard
  reports/quality-scorecard.md     readable summary
  reports/improvement-history.json rolling history (appended)

If a workflow-run summary (runs.json) is provided by the caller, workflow
reliability is included; otherwise it is reported as unavailable.
"""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from atomic import write_json

# Updated when the engineering audit is revised — not recomputed daily.
AUDIT_OPEN = {"critical": 0, "high": 0,
              "note": "per docs/engineering-audit.md (H1/M1/M2 fixed, M3 fixed by test suite)"}


def run_tests() -> dict:
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/python", "-q", "--tb=no"],
        capture_output=True, text=True)
    tail = proc.stdout.strip().splitlines()[-1] if proc.stdout.strip() else ""
    passed = int(m.group(1)) if (m := re.search(r"(\d+) passed", tail)) else 0
    failed = int(m.group(1)) if (m := re.search(r"(\d+) failed", tail)) else 0
    return {"passed": passed, "failed": failed, "ok": proc.returncode == 0,
            "summary": tail}


def scan_internal_links(root=".") -> list:
    """Local hrefs/srcs in committed HTML that point at missing files."""
    broken = []
    for name in os.listdir(root):
        if not name.endswith(".html"):
            continue
        text = open(os.path.join(root, name)).read()
        for ref in re.findall(r'(?:href|src)="([^"]+)"', text):
            if ref.startswith(("http", "#", "mailto:", "data:")) or "${" in ref:
                continue  # external, anchor, or JS template literal
            target = ref.split("#")[0]
            if target and not os.path.exists(os.path.join(root, target)):
                broken.append(f"{name} -> {ref}")
    return broken


# Compensating control: GitHub Advanced Security secret scanning is not
# available on this repo, so scan for credential shapes ourselves. Free,
# deterministic, always on. Patterns split so this file never matches
# itself.
SECRET_PATTERNS = [
    ("AWS access key", r"AKIA[0-9A-Z]{16}"),
    ("GitHub token", r"gh[pousr]_[A-Za-z0-9]{36,}"),
    ("GitHub fine-grained PAT", r"github" + r"_pat_[A-Za-z0-9_]{50,}"),
    ("Slack token", r"xox[baprs]-[A-Za-z0-9-]{10,}"),
    ("Slack webhook", r"hooks\.slack\.com/services/T[A-Za-z0-9]+/B[A-Za-z0-9]+/[A-Za-z0-9]+"),
    ("private key block", r"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
    ("Google API key", r"AIza[0-9A-Za-z_-]{35}"),
    ("hardcoded credential", r"(?i)(api[_-]?key|secret|passwd|password|token)\s*[=:]\s*['\"][A-Za-z0-9/+_-]{24,}['\"]"),
]
SCAN_SKIP_DIRS = {".git", "node_modules", "__pycache__", "reports"}
# These two legitimately contain credential-shaped literals: the pattern
# list itself and the test that plants fake keys to prove the scan works.
SCAN_SKIP_NAMES = {"daily_ops.py", "test_daily_ops.py"}


def scan_for_secrets(root=".") -> list:
    """Credential-shaped strings in tracked text files."""
    hits = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SCAN_SKIP_DIRS]
        for name in filenames:
            if name in SCAN_SKIP_NAMES or name.endswith((".png", ".jpg", ".ico")):
                continue
            path = os.path.join(dirpath, name)
            try:
                with open(path, encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            except OSError:
                continue
            for label, pattern in SECRET_PATTERNS:
                if re.search(pattern, text):
                    hits.append(f"{label} in {os.path.relpath(path, root)}")
    return hits


def check_published_freshness(branch="data") -> dict:
    """Is what the SITE serves current — not what this runner just built?

    July/Aug 2026: the pipeline generated fresh data every run, validation
    reported OK every run, and yet nothing reached the site for six days
    because the publish step was failing. Every check looked at the
    runner's scratch space. This one looks at the published artefact.
    """
    import subprocess
    fetch = subprocess.run(["git", "fetch", "--depth=1", "origin", branch],
                           capture_output=True, text=True)
    if fetch.returncode != 0:
        return {"checked": False, "reason": "could not fetch data branch"}
    show = subprocess.run(["git", "show", f"FETCH_HEAD:data/quotes.json"],
                          capture_output=True, text=True)
    if show.returncode != 0:
        return {"checked": True, "ok": False,
                "reason": "no data/quotes.json on the data branch"}
    try:
        published = json.loads(show.stdout)
        newest = max(q["date"] for q in published["quotes"])
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        return {"checked": True, "ok": False,
                "reason": f"published quotes unreadable: {exc}"}

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from market_session import last_session_close
    expected = last_session_close(datetime.now(timezone.utc)).date()
    behind = (expected - datetime.strptime(newest, "%Y-%m-%d").date()).days
    return {"checked": True, "ok": behind <= 1, "published_newest": newest,
            "expected_through": expected.isoformat(), "sessions_behind": behind}


def load_health() -> dict:
    if os.path.exists("data/health.json"):
        with open("data/health.json") as f:
            return json.load(f)
    return {"overall": "unknown", "files": {}}


def load_workflow_stats(path) -> dict:
    if not path or not os.path.exists(path):
        return {"available": False}
    with open(path) as f:
        runs = json.load(f)
    total = len(runs)
    ok = sum(1 for r in runs if r.get("conclusion") == "success")
    return {"available": True, "recent_runs": total, "successes": ok,
            "reliability_pct": round(ok / total * 100, 1) if total else None}


def main() -> int:
    runs_path = sys.argv[1] if len(sys.argv) > 1 else None
    now = datetime.now(timezone.utc)
    date = now.strftime("%Y-%m-%d")

    tests = run_tests()
    broken = scan_internal_links()
    secrets = scan_for_secrets()
    published = check_published_freshness()
    health = load_health()
    workflows = load_workflow_stats(runs_path)

    stale = [k for k, v in health.get("files", {}).items()
             if v.get("status") == "stale"]
    findings = []
    if not tests["ok"]:
        findings.append(f"tests failing: {tests['summary']}")
    if secrets:
        findings.append(f"POSSIBLE SECRETS COMMITTED: {secrets}")
    if broken:
        findings.append(f"broken internal links: {broken}")
    if stale:
        findings.append(f"stale data sections: {stale}")
    fallbacks = health.get("primary_source_failures_count")
    if isinstance(fallbacks, int) and fallbacks > 0:
        findings.append(
            f"primary price source degraded: {fallbacks} symbol(s) served by "
            "the fallback (52-week ranges are unavailable on fallback data)")
    ranges = health.get("week52_ranges") or {}
    present, expected = ranges.get("present"), ranges.get("expected")
    if isinstance(present, int) and isinstance(expected, int) and expected:
        # Silent feature loss: the tiles keep rendering without a 52-week
        # range and every run still reports success. Aug 2026: 0 of 13.
        if present < expected / 2:
            findings.append(
                f"52-week ranges missing on {expected - present}/{expected} "
                "tiles — the price source is not supplying enough history")

    if published.get("checked") and not published.get("ok", True):
        findings.append(
            "PUBLISHED DATA IS STALE — the site is serving "
            f"{published.get('published_newest', 'unknown')} but the last "
            f"session closed {published.get('expected_through', '?')} "
            f"({published.get('reason', '')})".strip())

    scorecard = {
        "generated": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tests": tests,
        "broken_internal_links": broken,
        "secret_scan": {"method": "in-repo pattern scan (GHAS unavailable)",
                        "hits": secrets},
        "data_health": {"overall": health.get("overall"),
                        "stale_sections": stale,
                        "week52_ranges": health.get("week52_ranges")},
        "published_freshness": published,
        "workflow_reliability": workflows,
        "open_findings": AUDIT_OPEN,
        "last_successful_maintenance": date,
    }
    write_json("reports/quality-scorecard.json", scorecard, indent=1)

    action = ("Findings require attention: " + "; ".join(findings)
              if findings else "No justified code change identified today.")
    reliability = (f"{workflows['successes']}/{workflows['recent_runs']} recent runs green"
                   if workflows.get("available") else "not available to this run")

    md = f"""# Daily report — {date} (UTC)

Mode: deterministic scripts only — no AI model invoked (tier: none, cost: $0).

## Checks executed
- pytest suite: {tests['summary'] or 'no output'}
- internal link scan: {len(broken)} broken
- secret-pattern scan: {len(secrets)} hit(s) [in-repo control; GHAS unavailable]
- published data (what the site serves): {published}
- data health: overall **{health.get('overall')}**{', stale: ' + ', '.join(stale) if stale else ''}
- workflow reliability: {reliability}
- open audit findings: {AUDIT_OPEN['critical']} critical, {AUDIT_OPEN['high']} high

## Outcome
{action}
"""
    os.makedirs("reports/daily", exist_ok=True)
    with open(f"reports/daily/{date}.md", "w") as f:
        f.write(md)
    with open("reports/quality-scorecard.md", "w") as f:
        f.write(f"# Quality scorecard — {date}\n\n"
                f"- Tests: {tests['summary'] or 'none'}\n"
                f"- Broken internal links: {len(broken)}\n"
                f"- Secret-pattern hits: {len(secrets)}\n"
                f"- Data health: {health.get('overall')}\n"
                f"- Workflow reliability: {reliability}\n"
                f"- Open findings: {AUDIT_OPEN['critical']} critical / {AUDIT_OPEN['high']} high\n")

    history = []
    if os.path.exists("reports/improvement-history.json"):
        with open("reports/improvement-history.json") as f:
            history = json.load(f)
    history = [h for h in history if h["date"] != date]
    history.append({"date": date, "tests_passed": tests["passed"],
                    "tests_failed": tests["failed"],
                    "health": health.get("overall"), "action": action})
    write_json("reports/improvement-history.json", history[-90:], indent=1)

    print(f"daily ops {date}: {action}")
    return 0 if not findings else 1


if __name__ == "__main__":
    raise SystemExit(main())
