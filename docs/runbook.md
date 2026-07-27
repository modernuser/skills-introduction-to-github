# Runbook

## The data stopped updating
1. Check Actions → "Update market quotes" run history. Failed run? The
   failure issue in Issues has the run link; read the failing step's log.
2. Common causes: stooq throttling (errors array in quotes.json names
   the symbols; yahoo fallback usually covers), GitHub cron throttling
   (no runs at all — wait, it's congestion, not breakage).
3. Page shows a stale banner at ≥100h and per-file status in the health
   strip. Data on the page is last-known-good, never corrupted.

## A workflow failure issue appeared
Read the linked run log. Fix on a branch, PR, merge (CI gates it).
Close the issue after the next green run. Issues are deduped — one open
per failure type.

## Roll back a bad change
Every merge is a squash commit: `git revert <sha>` on a branch → PR →
merge. Data files are regenerated on the next scheduled run, so
reverting code never strands data.

## Re-seed the dartboard experiment
Delete `data/portfolios.json` on main (small PR). The next market-hours
run seeds fresh with a new date-derived rng_seed. History is lost —
that's the point of a re-seed.

## Reset move-notification state
Delete `data/notified_moves.json`; next run re-arms (may re-notify
today's already-notified moves once).

## Purge sensitive data from Git history
Committed-then-deleted files remain in history. To truly remove:
`git filter-repo --path <file> --invert-paths` on a fresh clone, force
push, then rotate anything that was exposed. GitHub support can purge
cached views. Prevention beats purging — see docs/privacy-model.md.

## Inspect or repair the data branch
Generated output lives on `data`, not `main`:
`git fetch origin data && git show origin/data:data/quotes.json`.
To reset a corrupted state file, delete it on the `data` branch; the next
run regenerates it (portfolios re-seed, movers need one more session to
rebuild a comparison). To roll back a bad dataset:
`git push origin <good-sha>:data`. `main` is unaffected either way.

## Local development
```
git clone <repo> && cd <repo>
python3 -m pytest tests/python -q         # full offline suite
python3 -m http.server 8000               # then open /tracker.html
```
Pages read live data from the `data` branch's raw GitHub URL. A `main`
checkout has no generated `data/*.json`, so the local fallback simply
finds nothing and the page shows its empty state — run
`python3 scripts/data_branch.py hydrate` to pull real data in locally.

## Verify a deploy
Actions → "Deploy Pages" → conclusion success, then hard-refresh the
site. Data commits do NOT redeploy (by design — raw URL serving).
