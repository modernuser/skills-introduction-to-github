# Working notes for Claude sessions on this repo

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
   evaporating in chat. Check it before proposing work; update Shipped
   after merging.
4. **Verify after shipping.** Never assume a deploy or scheduled workflow
   worked — check the run conclusion and the artifact it should produce.

## Architecture notes

- `tracker.html` reads `data/quotes.json` from the **raw GitHub URL**
  (not the Pages deploy), so data commits don't need a redeploy.
- `.github/workflows/update-quotes.yml` cron-runs every 20 min during US
  market hours and commits refreshed data with `[skip ci]`.
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
