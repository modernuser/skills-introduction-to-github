#!/usr/bin/env python3
"""Keep generated data on its own branch, so `main` holds only code.

Why: the pipeline commits data several times a day. If those commits land
on `main`, then `main` can never carry "require a pull request" or
"require green CI" — every scheduled run would be rejected. Moving data
to a dedicated branch removes that conflict entirely: nothing automated
writes to `main`, so `main` can be fully protected.

Two operations, both safe to run from a normal `main` checkout:

  hydrate  copy data/*.json from the data branch into the working tree,
           so scripts that depend on persisted state (notified_moves,
           sp500_closes, portfolios, rotation, news) see it
  publish  commit the current data/*.json onto the data branch and push

publish uses a detached worktree, so the main working tree is never
switched or disturbed mid-run.
"""

import glob
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

BRANCH = os.environ.get("DATA_BRANCH", "data")
REMOTE = os.environ.get("DATA_REMOTE", "origin")
# Directories whose generated contents live on the data branch. `data/`
# holds market datasets and pipeline state; `reports/` holds daily-ops
# output and its rolling history.
DEFAULT_DIRS = ("data", "reports")
# Committed *inputs* live on main and must never be published as output.
INPUT_FILES = {"sp500_constituents.csv"}


def run(args, cwd=None, check=True, quiet=False):
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"{' '.join(args)} failed ({result.returncode}): "
            f"{result.stderr.strip() or result.stdout.strip()}")
    if not quiet and result.stdout.strip():
        print(result.stdout.strip())
    return result


def branch_exists(remote=REMOTE, branch=BRANCH) -> bool:
    out = run(["git", "ls-remote", "--heads", remote, branch],
              check=False, quiet=True).stdout
    return branch in out


def hydrate(dirs=DEFAULT_DIRS, remote=REMOTE, branch=BRANCH) -> int:
    """Restore persisted generated files from the data branch. Never fatal."""
    if not branch_exists(remote, branch):
        print(f"data branch '{branch}' does not exist yet; nothing to hydrate")
        return 0
    run(["git", "fetch", "--depth=1", remote, branch], quiet=True)
    total = 0
    for directory in dirs:
        os.makedirs(directory, exist_ok=True)
        # FETCH_HEAD is the tip we just fetched; restore only this dir.
        restored = run(["git", "checkout", "FETCH_HEAD", "--", directory],
                       check=False, quiet=True)
        if restored.returncode != 0:
            print(f"no {directory}/ on '{branch}' yet; starting clean")
            continue
        # Unstage: the working copy is what the scripts read, while the
        # index on main stays clean so no generated file is ever
        # committed here by accident.
        run(["git", "reset", "-q", "HEAD", "--", directory],
            check=False, quiet=True)
        total += len(glob.glob(f"{directory}/**/*", recursive=True))
    print(f"hydrated {total} path(s) from '{branch}'")
    return 0


def _outputs(dirs):
    found = []
    for directory in dirs:
        for path in glob.glob(f"{directory}/**/*", recursive=True):
            if os.path.isfile(path) and os.path.basename(path) not in INPUT_FILES:
                found.append(path)
    return sorted(found)


def publish(message=None, dirs=DEFAULT_DIRS, remote=REMOTE, branch=BRANCH) -> int:
    """Commit current generated files onto the data branch and push."""
    outputs = _outputs(dirs)
    if not outputs:
        print("no generated data files to publish")
        return 0

    staged = tempfile.mkdtemp(prefix="databranch-")
    worktree = os.path.join(staged, "wt")
    try:
        for path in outputs:                      # snapshot before switching
            dest = os.path.join(staged, path)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy(path, dest)

        if branch_exists(remote, branch):
            run(["git", "fetch", "--depth=1", remote, branch], quiet=True)
            run(["git", "worktree", "add", "--detach", worktree, "FETCH_HEAD"],
                quiet=True)
        else:
            run(["git", "worktree", "add", "--detach", worktree], quiet=True)
            run(["git", "checkout", "--orphan", branch], cwd=worktree, quiet=True)
            run(["git", "rm", "-rq", "--cached", "."], cwd=worktree,
                check=False, quiet=True)
            for entry in os.listdir(worktree):
                if entry != ".git":
                    full = os.path.join(worktree, entry)
                    shutil.rmtree(full) if os.path.isdir(full) else os.remove(full)

        for path in outputs:
            dest = os.path.join(worktree, path)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy(os.path.join(staged, path), dest)

        # -f: main's .gitignore is inherited by this branch and ignores
        # generated files on purpose; here they are the payload.
        run(["git", "add", "-Af", *[d for d in dirs if os.path.isdir(
            os.path.join(worktree, d))]], cwd=worktree, quiet=True)
        if run(["git", "diff", "--cached", "--quiet"], cwd=worktree,
               check=False, quiet=True).returncode == 0:
            print("data unchanged; nothing to publish")
            return 0

        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")
        run(["git", "commit", "-q", "-m", message or f"Update data {stamp}"],
            cwd=worktree)
        run(["git", "push", remote, f"HEAD:refs/heads/{branch}"], cwd=worktree)
        print(f"published {len(outputs)} file(s) to '{branch}'")
        return 0
    finally:
        run(["git", "worktree", "remove", "--force", worktree],
            check=False, quiet=True)
        shutil.rmtree(staged, ignore_errors=True)


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] not in ("hydrate", "publish"):
        print(__doc__)
        print("usage: data_branch.py hydrate | publish [message]", file=sys.stderr)
        return 2
    if sys.argv[1] == "hydrate":
        return hydrate()
    return publish(sys.argv[2] if len(sys.argv) > 2 else None)


if __name__ == "__main__":
    raise SystemExit(main())
