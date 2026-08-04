# Working notes for Claude sessions on this repo

## Rules for coding agents (any model, any session)

- Read `docs/architecture.md` and `docs/data-contracts.md` before
  touching pipeline or page code; `.claude/model-policy.yml` governs
  autonomous limits and model tiers (`docs/model-routing.md`).
- **Never modify by hand:** `data/*` (pipeline-owned),
  `.claude/model-policy.yml` (owner-owned), workflow `permissions:`
  blocks (security review required).
- **Definition of done:** problem stated; tests added/updated; full
  suite green (`python3 -m pytest tests/python -q`); YAML/JSON valid;
  page changes render-tested with no console errors; docs updated;
  rollback = revert of one squash commit; no secrets; no fake market
  claims; PR explains model/cost choice. Backlog: `docs/roadmap.md`.
- Autonomous PRs: label `agent-maintenance`, one open at a time, ≤8
  files, ≤500 lines, low/medium risk only, never auto-merge.

## What this project is

"Wolf of Fairhope Avenue" — a static site on GitHub Pages
(https://modernuser.github.io/skills-introduction-to-github/) with a live
market tracker. The owner sometimes says "index fund" when they mean
`index.html`; clarify gently if ambiguous.

Hard boundary that never changes: the site displays real market data and
links to primary sources. It never gives buy/sell signals, price
predictions, or investment recommendations, no matter how the request is
framed. Offer data-display alternatives instead.

## Working agreements with the owner

1. **Obvious mistakes: fix, don't discuss.** When a mistake (mine or
   theirs) has a clear-cut correction, apply the corrective action directly
   and mention it in one line. No rabbit holes, no multi-option essays.
2. **Checkpoints.** At the start of any multi-step task, restate the goal
   in one sentence. If the conversation drifts to a new subject mid-task,
   flag it: finish or park the current task explicitly before switching.
3. **Backlog lives in ROADMAP.md.** New ideas go there instead of
   evaporating in chat. Check it before proposing work. After merging a
   user-visible feature, update BOTH the ROADMAP Shipped section AND the
   "Latest Updates" list in index.html (this was missed twice).
4. **Verify the PUBLISHED artefact, not the working tree.** Aug 2026:
   the pipeline generated correct data every run and validation printed
   "OK" every run, while nothing reached the site for six days — the
   publish push was failing and every check looked at the runner's
   scratch space. A check that cannot observe the user-visible outcome
   is not a check. `daily_ops.check_published_freshness` now fetches the
   `data` branch and compares it against the market calendar.
5. **A recurring failure must keep shouting.** The dedupe on failure
   issues ("one is already open, stay quiet") turned that outage into
   silence. Alerts now comment on the open issue every ~12h. Silence
   must require *no failures*, never merely a *previous* failure.
6. **Test the transport that production uses.** The publish bug was a
   missing credential in a linked git worktree; the tests passed because
   they used `file://` remotes needing no auth. When a code path depends
   on credentials, network, or a service, at least one test must fail if
   that dependency is absent.
7. **Verify after shipping.** Never assume a deploy or scheduled workflow
   worked — check the run conclusion and the artifact it should produce.
   Session-scheduled self-checks die with the session (happened twice):
   the reliable verifier is IN the repo — workflows validate their own
   output and open an issue when it's wrong.
8. **Read the data before coding against it.** A schema assumed from
   memory cost a test cycle (pct_1d vs the actual d1). Open the real file
   first.
9. **Reset the branch after every squash-merge** (`git fetch origin main
   && git checkout -B <branch> origin/main`). Merging main back into a
   long-lived branch after squash-merges breeds phantom conflicts.
10. **Definition of done includes CI green.** The committed pytest suite
   (`tests/python/`, offline, network monkeypatched) plus YAML/JSON
   validation runs on every PR and push to main via ci.yml. Run locally
   with `python3 -m pytest tests/python -q` before pushing.
11. **A degraded fallback must not silently drop features.** Aug 2026:
   stooq began answering 200 with a non-CSV body for every symbol, so
   everything fell to the Yahoo fallback — which requested only 3 months
   and therefore dropped every 52-week range. Runs stayed green, the page
   kept rendering, and 0/13 tiles had a range for days. A fallback should
   degrade the *source*, never the *contract*. Where output can quietly
   shrink, emit a count (`ranges_present`) and alarm on it.
12. **Record what arrived, not just that it was wrong.** "stooq returned
   no rows" was true and useless — it could not separate a rate-limit
   notice from an HTML error page from a dead ticker. Log a snippet of
   the actual body; one line of evidence beats a day of guessing.
13. **A control nobody checks is a claim.** Aug 2026 audit: the
   autonomy limits in `.claude/model-policy.yml` (max files, max lines)
   existed only as prose inside the agent's prompt, so an agent that
   ignored them met no barrier. `scripts/audit_controls.py` now measures
   the real diff in CI. Before writing a limit down, ask what mechanically
   enforces it — and if nothing does, say so plainly rather than implying
   it is enforced.
14. **Mark a control fixed only when the control is fixed.** M5 was
   recorded "(FIXED)" after pinning one action while four stayed on
   mutable tags. Remediation status describes the control, not the
   hardest instance of it. Where something genuinely cannot be fixed now,
   contain it on an explicit register that CI enforces — never leave it
   implied-complete.
15. **Measure claims, don't repeat them.** The site said "every 20 min"
   because the cron said so; run history showed ~6 fires/day (GitHub
   throttles busy cron slots). Copy must describe observed behavior.

## Architecture notes

- `tracker.html` reads `data/quotes.json` from the **raw GitHub URL**
  (not the Pages deploy), so data commits don't need a redeploy.
- `.github/workflows/update-quotes.yml` cron-runs during US market hours
  (measured: ~6 fires/day — GitHub throttles cron slots) and commits refreshed data with `[skip ci]`.
- `.github/workflows/deploy-pages.yml` deploys on push to `main`.

## Mistakes already made — do not repeat

- **Never put the literal string "skip ci" (bracketed) in a commit message
  or PR body that will become a merge commit** — it silently skips the
  Pages deploy. It belongs only in the data-update workflow's own commits.
- `git diff --quiet <file>` reports nothing for a brand-new untracked
  file — `git add` first, then `git diff --cached --quiet`.
- The GitHub token here cannot enable Pages, dispatch workflows, or re-run
  runs (403). To trigger a deploy, merge a commit to `main`.
- GitHub Actions can't be tested from this sandbox (finance APIs are
  proxy-blocked locally); test scripts for logic locally, verify fetch
  behavior via the workflow run logs after merging.
