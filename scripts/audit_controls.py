#!/usr/bin/env python3
"""Enforce the controls this project claims to have.

A control that is written down but never checked is a claim, not a
control. Everything here is mechanical and runs in CI, so the documented
posture and the actual posture cannot drift apart silently.

Checks:
  1. Every `uses:` in a workflow is pinned to a full commit SHA, except
     entries on an explicit, justified exception register.
  2. Workflow permission blocks stay least-privilege (no write-all, no
     bare `permissions: write`).
  3. An autonomous agent PR respects the numeric limits in
     .claude/model-policy.yml — enforced against the real diff, not
     against the agent's willingness to follow a prompt.

Exit non-zero on any violation.
"""

import os
import re
import subprocess
import sys

WORKFLOW_DIR = ".github/workflows"
POLICY_PATH = ".claude/model-policy.yml"

# Actions not yet pinned to a SHA, with the reason each is tolerated.
# Adding to this register is a deliberate, reviewable act; the checker
# below fails on anything unpinned that is NOT listed here, so the set
# cannot grow by accident.
#
# Aug 2026 audit: SHAs could not be resolved from the build environment
# (the egress proxy blocks api.github.com for repositories outside the
# session scope). Owner action to pin — see docs/engineering-audit.md.
PIN_EXCEPTIONS = {
    "actions/configure-pages@v5":
        "first-party GitHub action, Pages deploy job",
    "actions/upload-pages-artifact@v3":
        "first-party GitHub action, Pages deploy job",
    "actions/deploy-pages@v4":
        "first-party GitHub action, Pages deploy job",
    "anthropics/claude-code-action@v1":
        "THIRD-PARTY and credentialed (ANTHROPIC_API_KEY, contents:write, "
        "pull-requests:write) — highest-priority pin; mitigated only by the "
        "workflow being disabled by default",
}

SHA_PIN = re.compile(r"@[0-9a-f]{40}\b")
USES = re.compile(r"^\s*-?\s*uses:\s*(\S+)", re.MULTILINE)


def check_action_pins() -> list[str]:
    problems = []
    for name in sorted(os.listdir(WORKFLOW_DIR)):
        if not name.endswith((".yml", ".yaml")):
            continue
        path = os.path.join(WORKFLOW_DIR, name)
        with open(path) as f:
            text = f.read()
        for ref in USES.findall(text):
            ref = ref.strip("\"'")
            if ref.startswith("./") or SHA_PIN.search(ref):
                continue
            if ref in PIN_EXCEPTIONS:
                continue
            problems.append(
                f"{name}: `{ref}` is not pinned to a commit SHA and is not "
                "on the exception register in scripts/audit_controls.py")
    return problems


def check_permissions() -> list[str]:
    """Least privilege: no blanket write, no missing block."""
    problems = []
    for name in sorted(os.listdir(WORKFLOW_DIR)):
        if not name.endswith((".yml", ".yaml")):
            continue
        with open(os.path.join(WORKFLOW_DIR, name)) as f:
            text = f.read()
        if "permissions:" not in text:
            problems.append(f"{name}: no permissions block (inherits broad "
                            "default token scope)")
            continue
        for line in text.splitlines():
            stripped = line.strip()
            if stripped in ("permissions: write-all",
                            "permissions: write"):
                problems.append(f"{name}: `{stripped}` grants every scope")
    return problems


def read_policy_limits() -> dict:
    """Parse the two numeric limits without a YAML dependency.

    Deliberately narrow: this reads the policy, it does not interpret it.
    """
    limits = {}
    if not os.path.exists(POLICY_PATH):
        return limits
    with open(POLICY_PATH) as f:
        for line in f:
            m = re.match(r"\s*(maximum_files_per_autonomous_pr|"
                         r"maximum_changed_lines)\s*:\s*(\d+)", line)
            if m:
                limits[m.group(1)] = int(m.group(2))
    return limits


def check_agent_pr(base_ref: str) -> list[str]:
    """Hold an autonomous PR to the policy's numbers, using the real diff.

    Before this existed, `maximum_files_per_autonomous_pr` and
    `maximum_changed_lines` lived only inside a prompt — an agent that
    ignored, misread, or never received that text met no barrier at all.
    A limit the controlled party enforces on itself is not a control.
    """
    limits = read_policy_limits()
    if not limits:
        return ["could not read numeric limits from .claude/model-policy.yml"]

    stat = subprocess.run(
        ["git", "diff", "--numstat", f"{base_ref}...HEAD"],
        capture_output=True, text=True)
    if stat.returncode != 0:
        return [f"could not diff against {base_ref}: {stat.stderr.strip()}"]

    files = added = removed = 0
    for row in stat.stdout.strip().splitlines():
        parts = row.split("\t")
        if len(parts) != 3:
            continue
        files += 1
        if parts[0] != "-":                      # "-" marks a binary file
            added += int(parts[0])
            removed += int(parts[1])

    problems = []
    max_files = limits.get("maximum_files_per_autonomous_pr")
    max_lines = limits.get("maximum_changed_lines")
    if max_files and files > max_files:
        problems.append(f"agent PR touches {files} files, limit {max_files}")
    if max_lines and (added + removed) > max_lines:
        problems.append(f"agent PR changes {added + removed} lines "
                        f"({added}+/{removed}-), limit {max_lines}")
    return problems


def main() -> int:
    agent_mode = "--agent-pr" in sys.argv
    base_ref = "origin/main"
    for i, arg in enumerate(sys.argv):
        if arg == "--base" and i + 1 < len(sys.argv):
            base_ref = sys.argv[i + 1]

    sections = [("action pinning", check_action_pins()),
                ("workflow permissions", check_permissions())]
    if agent_mode:
        sections.append(("autonomous PR limits", check_agent_pr(base_ref)))

    total = 0
    for label, problems in sections:
        if problems:
            total += len(problems)
            print(f"FAIL {label}:")
            for p in problems:
                print(f"  - {p}")
        else:
            print(f"ok   {label}")

    if PIN_EXCEPTIONS:
        print(f"\nnote: {len(PIN_EXCEPTIONS)} action(s) on the pin-exception "
              "register (tracked, not silent):")
        for ref, why in sorted(PIN_EXCEPTIONS.items()):
            print(f"  - {ref}: {why}")

    return 1 if total else 0


if __name__ == "__main__":
    raise SystemExit(main())
