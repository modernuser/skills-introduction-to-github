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

## Local development
```
git clone <repo> && cd <repo>
python3 -m pytest tests/python -q         # full offline suite
python3 -m http.server 8000               # then open /tracker.html
```
Pages read live data from the raw GitHub URL even when served locally;
kill the network and they fall back to the checked-out `data/` copies.

## Verify a deploy
Actions → "Deploy Pages" → conclusion success, then hard-refresh the
site. Data commits do NOT redeploy (by design — raw URL serving).
