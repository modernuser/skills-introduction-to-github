"""Tests for the control auditor.

These matter more than most: this module is what stops the documented
security posture and the real one from drifting apart. If it silently
stops detecting things, every other control becomes unverified again.
"""

import os
from pathlib import Path

from conftest import REPO, load


def _workflows(tmp_path, files: dict) -> None:
    d = tmp_path / ".github" / "workflows"
    d.mkdir(parents=True)
    for name, body in files.items():
        (d / name).write_text(body)


def test_real_repo_passes_its_own_controls():
    ac = load("audit_controls")
    cwd = os.getcwd()
    os.chdir(REPO)
    try:
        assert ac.check_action_pins() == []
        assert ac.check_permissions() == []
    finally:
        os.chdir(cwd)


def test_unpinned_action_is_caught(workdir, monkeypatch):
    ac = load("audit_controls")
    _workflows(workdir, {"x.yml": (
        "permissions:\n  contents: read\n"
        "jobs:\n  a:\n    steps:\n      - uses: some/action@v3\n")})
    monkeypatch.setattr(ac, "PIN_EXCEPTIONS", {})
    problems = ac.check_action_pins()
    assert len(problems) == 1 and "some/action@v3" in problems[0]


def test_sha_pinned_action_passes(workdir):
    ac = load("audit_controls")
    _workflows(workdir, {"x.yml": (
        "permissions:\n  contents: read\n"
        "jobs:\n  a:\n    steps:\n      - uses: some/action@"
        + "a" * 40 + "  # v3\n")})
    assert ac.check_action_pins() == []


def test_exception_register_suppresses_only_what_it_lists(workdir,
                                                          monkeypatch):
    """The register must not become a blanket mute."""
    ac = load("audit_controls")
    _workflows(workdir, {"x.yml": (
        "permissions:\n  contents: read\n"
        "jobs:\n  a:\n    steps:\n"
        "      - uses: allowed/one@v1\n"
        "      - uses: sneaky/two@v2\n")})
    monkeypatch.setattr(ac, "PIN_EXCEPTIONS", {"allowed/one@v1": "reviewed"})
    problems = ac.check_action_pins()
    assert len(problems) == 1 and "sneaky/two@v2" in problems[0]


def test_blanket_write_permission_is_caught(workdir):
    ac = load("audit_controls")
    _workflows(workdir, {"x.yml": "permissions: write-all\njobs: {}\n"})
    assert any("every scope" in p for p in ac.check_permissions())


def test_missing_permission_block_is_caught(workdir):
    ac = load("audit_controls")
    _workflows(workdir, {"x.yml": "jobs:\n  a:\n    steps: []\n"})
    assert any("no permissions block" in p for p in ac.check_permissions())


# ------------------------------------------------- autonomous PR enforcement

def test_policy_limits_are_read_from_the_real_file():
    ac = load("audit_controls")
    cwd = os.getcwd()
    os.chdir(REPO)
    try:
        limits = ac.read_policy_limits()
    finally:
        os.chdir(cwd)
    assert limits["maximum_files_per_autonomous_pr"] == 8
    assert limits["maximum_changed_lines"] == 500


def _repo_with_policy(tmp_path, files: int, lines: int):
    """A real git repo with a base commit and one oversized change."""
    import subprocess as sp

    def run(*args):
        sp.run(args, cwd=tmp_path, check=True, capture_output=True)

    run("git", "init", "-q", "-b", "main")
    run("git", "config", "user.email", "t@example.com")
    run("git", "config", "user.name", "t")
    policy = tmp_path / ".claude"
    policy.mkdir()
    (policy / "model-policy.yml").write_text(
        "autonomous_limits:\n"
        "  maximum_files_per_autonomous_pr: 8\n"
        "  maximum_changed_lines: 500\n")
    (tmp_path / "seed.txt").write_text("seed\n")
    run("git", "add", "-A")
    run("git", "commit", "-qm", "base")
    run("git", "branch", "base-ref")
    for i in range(files):
        (tmp_path / f"f{i}.txt").write_text("x\n" * lines)
    run("git", "add", "-A")
    run("git", "commit", "-qm", "change")
    return tmp_path


def test_oversized_agent_pr_is_rejected(tmp_path, monkeypatch):
    ac = load("audit_controls")
    repo = _repo_with_policy(tmp_path, files=12, lines=80)
    monkeypatch.chdir(repo)
    problems = ac.check_agent_pr("base-ref")
    assert any("12 files" in p for p in problems)
    assert any("lines" in p for p in problems)


def test_compliant_agent_pr_passes(tmp_path, monkeypatch):
    ac = load("audit_controls")
    repo = _repo_with_policy(tmp_path, files=3, lines=10)
    monkeypatch.chdir(repo)
    assert ac.check_agent_pr("base-ref") == []


def test_limit_check_reports_a_bad_base_instead_of_passing_silently(
        tmp_path, monkeypatch):
    """A check that cannot run must fail loudly, never green."""
    ac = load("audit_controls")
    repo = _repo_with_policy(tmp_path, files=1, lines=1)
    monkeypatch.chdir(repo)
    problems = ac.check_agent_pr("no-such-ref")
    assert problems and "could not diff" in problems[0]
