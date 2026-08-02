#!/usr/bin/env python3
"""Keep generated data on its own branch, so `main` holds only code.

Why: the pipeline commits data several times a day. If those commits land
on `main`, then `main` can never carry "require a pull request" or
"require green CI" — every scheduled run would be rejected. Moving data
to a dedicated branch removes that conflict entirely: nothing automated
writes to `main`, so `main` can be fully protected.

Two operations, both safe to run from a normal `main` checkout:

  hydrate  restore generated files from the data branch into the working
           tree, so scripts that depend on persisted state
           (notified_moves, sp500_closes, portfolios, rotation, news)
           see it
  publish  commit the current generated files onto the data branch

publish builds the commit with git plumbing **inside the main checkout**
rather than in a linked worktree. That is not a style choice: this
repository's credentials are installed by actions/checkout behind an
`includeIf.gitdir:` rule keyed to the main worktree's git directory. A
linked worktree has a different git dir, the rule never matches, and the
push fails with "could not read Username for https://github.com" — which
silently broke publication for six days in July 2026.
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


def run(args, check=True, quiet=False, env=None):
    result = subprocess.run(args, capture_output=True, text=True,
                            env={**os.environ, **(env or {})})
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

    parent = None
    if branch_exists(remote, branch):
        run(["git", "fetch", "--depth=1", remote, branch], quiet=True)
        parent = run(["git", "rev-parse", "FETCH_HEAD"], quiet=True).stdout.strip()

    index = tempfile.mktemp(prefix="databranch-index-")
    env = {"GIT_INDEX_FILE": index}
    try:
        # Start from the branch's existing tree so files this run did not
        # regenerate are carried forward rather than dropped.
        if parent:
            run(["git", "read-tree", parent], env=env, quiet=True)

        for path in outputs:
            blob = run(["git", "hash-object", "-w", path],
                       env=env, quiet=True).stdout.strip()
            run(["git", "update-index", "--add", "--cacheinfo",
                 f"100644,{blob},{path}"], env=env, quiet=True)

        tree = run(["git", "write-tree"], env=env, quiet=True).stdout.strip()
        if parent:
            parent_tree = run(["git", "rev-parse", f"{parent}^{{tree}}"],
                              quiet=True).stdout.strip()
            if tree == parent_tree:
                print("data unchanged; nothing to publish")
                return 0

        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%MZ")
        commit_args = ["git", "commit-tree", tree, "-m",
                       message or f"Update data {stamp}"]
        if parent:
            commit_args[3:3] = ["-p", parent]
        commit = run(commit_args, env=env, quiet=True).stdout.strip()

        run(["git", "push", remote, f"{commit}:refs/heads/{branch}"])
        print(f"published {len(outputs)} file(s) to '{branch}' as {commit[:7]}")
        return 0
    finally:
        if os.path.exists(index):
            os.remove(index)


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
