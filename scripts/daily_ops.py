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
    health = load_health()
    workflows = load_workflow_stats(runs_path)

    stale = [k for k, v in health.get("files", {}).items()
             if v.get("status") == "stale"]
    findings = []
    if not tests["ok"]:
        findings.append(f"tests failing: {tests['summary']}")
    if broken:
        findings.append(f"broken internal links: {broken}")
    if stale:
        findings.append(f"stale data sections: {stale}")

    scorecard = {
        "generated": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tests": tests,
        "broken_internal_links": broken,
        "data_health": {"overall": health.get("overall"), "stale_sections": stale},
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
