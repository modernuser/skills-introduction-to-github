"""End-to-end tests against real local git repos — this is git plumbing,
so mocking subprocess would test nothing that matters."""

import json
import subprocess
from pathlib import Path

import pytest

from conftest import load


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True,
                          text=True, check=True)


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """A clone with an 'origin' remote, positioned on a main branch."""
    origin = tmp_path / "origin.git"
    subprocess.run(["git", "init", "--bare", "-q", "-b", "main", str(origin)],
                   check=True)
    work = tmp_path / "work"
    subprocess.run(["git", "clone", "-q", str(origin), str(work)], check=True)
    for key, value in (("user.email", "t@example.com"), ("user.name", "T"),
                       ("commit.gpgsign", "false")):
        git("config", key, value, cwd=work)
    (work / "data").mkdir()
    (work / "data" / "sp500_constituents.csv").write_text("Symbol\nAAA\n")
    (work / "code.py").write_text("print('hi')\n")
    git("add", "-A", cwd=work)
    git("commit", "-qm", "initial", cwd=work)
    git("push", "-q", "origin", "main", cwd=work)
    monkeypatch.chdir(work)
    return work


def write_data(repo, **files):
    for name, payload in files.items():
        (repo / "data" / f"{name}.json").write_text(json.dumps(payload))


def data_branch_files(repo):
    git("fetch", "-q", "origin", "data", cwd=repo)
    out = git("ls-tree", "-r", "--name-only", "FETCH_HEAD", cwd=repo).stdout
    return sorted(out.split())


def test_hydrate_is_noop_when_branch_absent(repo, capsys):
    db = load("data_branch")
    assert db.hydrate() == 0
    assert "does not exist yet" in capsys.readouterr().out


def test_publish_creates_branch_and_hydrate_restores(repo):
    db = load("data_branch")
    write_data(repo, quotes={"updated": "t0"}, notified_moves={"symbols": ["A"]})
    assert db.publish("first publish") == 0

    files = data_branch_files(repo)
    assert "data/quotes.json" in files and "data/notified_moves.json" in files

    # Simulate a fresh CI checkout: generated files gone, input file stays.
    for f in (repo / "data").glob("*.json"):
        f.unlink()
    assert db.hydrate() == 0
    assert json.loads((repo / "data" / "quotes.json").read_text())["updated"] == "t0"
    assert json.loads(
        (repo / "data" / "notified_moves.json").read_text())["symbols"] == ["A"]


def test_main_branch_never_receives_data_commits(repo):
    db = load("data_branch")
    write_data(repo, quotes={"updated": "t0"})
    db.publish()
    db.hydrate()
    # main's tree must still contain only the code and the committed input
    main_files = sorted(git("ls-tree", "-r", "--name-only", "origin/main",
                            cwd=repo).stdout.split())
    assert main_files == ["code.py", "data/sp500_constituents.csv"]
    # and the index on main must be clean after hydrate (nothing staged)
    assert git("diff", "--cached", "--name-only", cwd=repo).stdout.strip() == ""


def test_committed_inputs_are_not_published(repo):
    db = load("data_branch")
    write_data(repo, quotes={"updated": "t0"})
    db.publish()
    assert "data/sp500_constituents.csv" not in data_branch_files(repo)


def test_unchanged_data_creates_no_commit(repo, capsys):
    db = load("data_branch")
    write_data(repo, quotes={"updated": "t0"})
    db.publish()
    git("fetch", "-q", "origin", "data", cwd=repo)
    before = git("rev-parse", "FETCH_HEAD", cwd=repo).stdout.strip()

    assert db.publish() == 0
    assert "nothing to publish" in capsys.readouterr().out
    git("fetch", "-q", "origin", "data", cwd=repo)
    assert git("rev-parse", "FETCH_HEAD", cwd=repo).stdout.strip() == before


def test_successive_publishes_accumulate_history(repo):
    db = load("data_branch")
    write_data(repo, quotes={"updated": "t0"})
    db.publish()
    write_data(repo, quotes={"updated": "t1"})
    db.publish()

    git("fetch", "-q", "origin", "data", cwd=repo)
    count = int(git("rev-list", "--count", "FETCH_HEAD", cwd=repo).stdout)
    assert count == 2
    latest = git("show", "FETCH_HEAD:data/quotes.json", cwd=repo).stdout
    assert json.loads(latest)["updated"] == "t1"


def test_publish_with_no_generated_files_is_noop(repo, capsys):
    db = load("data_branch")
    assert db.publish() == 0
    assert "no generated data files" in capsys.readouterr().out


def test_worktree_is_cleaned_up(repo):
    db = load("data_branch")
    write_data(repo, quotes={"updated": "t0"})
    db.publish()
    assert git("worktree", "list", cwd=repo).stdout.count("\n") == 1


def test_publish_surfaces_auth_failure(repo, tmp_path):
    """The bug that broke publication for six days in July 2026.

    The real failure was a push with no usable credentials. Local file://
    remotes never exercise auth, so this points the remote at an https URL
    with a credential helper that refuses — publish must RAISE, not
    silently 'succeed'."""
    db = load("data_branch")
    write_data(repo, quotes={"updated": "t0"})
    git("remote", "set-url", "origin",
        "https://127.0.0.1:1/modernuser/nonexistent.git", cwd=repo)
    git("config", "credential.helper", "", cwd=repo)

    with pytest.raises(RuntimeError) as exc:
        db.publish("should not reach the remote")
    assert "git push" in str(exc.value)


def test_publish_carries_forward_untouched_files(repo):
    """A run that regenerates only some files must not delete the rest."""
    db = load("data_branch")
    write_data(repo, quotes={"updated": "t0"}, portfolios={"seeded": True})
    db.publish()

    # Next run regenerates quotes only; portfolios.json is absent locally.
    (repo / "data" / "portfolios.json").unlink()
    write_data(repo, quotes={"updated": "t1"})
    db.publish()

    files = data_branch_files(repo)
    assert "data/portfolios.json" in files, "state file was dropped"
    latest = git("show", "FETCH_HEAD:data/quotes.json", cwd=repo).stdout
    assert json.loads(latest)["updated"] == "t1"


def test_no_worktrees_are_created(repo):
    """Publication must happen in the main checkout, where credentials live."""
    db = load("data_branch")
    write_data(repo, quotes={"updated": "t0"})
    db.publish()
    assert git("worktree", "list", cwd=repo).stdout.count("\n") == 1
