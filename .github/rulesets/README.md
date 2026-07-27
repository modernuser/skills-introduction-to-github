# Branch ruleset (import this, don't hand-tick it)

`protect-main.json` is the intended protection for `main`, in GitHub's
ruleset import format. Importing it avoids the misconfigurations that
cost real time when this was set by hand: a target that matched every
branch (which blocks pull requests from ever being opened), a non-zero
approval count (which deadlocks a solo maintainer, since GitHub forbids
self-approval), and a bypass list containing `Repository admin` (which
lets the rule be overridden by the very account it should bind).

## How to apply

1. Settings → Rules → Rulesets → **New ruleset ▾ → Import a ruleset**
2. Choose `.github/rulesets/protect-main.json`
3. **Create**

## What it enforces on `main`

| Rule | Effect |
|---|---|
| `pull_request` (0 approvals) | No direct pushes; changes arrive by PR. Zero approvals because a single maintainer cannot approve their own PR. |
| `required_status_checks` → `test` | A red CI run blocks the merge. |
| `non_fast_forward` | No force-pushes — history cannot be rewritten. |
| `deletion` | `main` cannot be deleted. |
| `bypass_actors: []` | **Empty on purpose.** Binds everyone, including the owner and any automation acting as them. |

## Why an empty bypass list is safe here

Generated data and reports live on the `data` branch, not `main` (see
docs/architecture.md). No workflow pushes to `main`, so nothing
legitimate needs an exception. Before that split, the same rules would
have rejected every scheduled data commit.

If you ever genuinely need a force-push to `main`: set Enforcement to
`Disabled`, do it, set it back to `Active`. That is a deliberate,
logged, thirty-second action — which is the point.

## Keeping this file honest

This JSON is the source of truth for intended posture. If you change the
ruleset in the UI, update this file too, or it becomes documentation of
something that is no longer true.
