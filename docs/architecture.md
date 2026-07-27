# Architecture

A deliberately simple static-site + scheduled-pipeline design. No server,
no database, no framework — GitHub is the runtime.

```
Browser ── reads ──> GitHub Pages (index/tracker/dartboard .html)
   │                        ▲ deploy on push to main
   └─ fetches JSON ──> raw.githubusercontent.com/…/main/data/*.json
                            ▲ committed by scheduled workflows
GitHub Actions (UTC cron):
  update-quotes.yml ──> scripts/update_quotes.py   (prices: stooq→yahoo)
                   └──> scripts/update_news.py     (RSS headlines)
                   └──> scripts/update_movers.py   (S&P closes + rotation)
                   └──> scripts/check_moves.py     (±3% notifications)
                   └──> scripts/update_portfolios.py (dartboard paper $)
                   └──> scripts/validate_data.py   (gate + health.json)
  morning-briefing.yml ─> scripts/morning_briefing.py (pre-market issue)
  daily-ops.yml ───────> scripts/daily_ops.py      (scorecard + reports)
  ci.yml ──────────────> pytest + YAML/JSON validation on PRs & main
```

## Boundaries

- **Pages never compute market logic** — pages render committed JSON only.
  All calculation lives in `scripts/`, which run only in Actions (or tests).
- **Data flows one way**: fetch → validate → commit → render. The
  validation gate (`validate_data.py`) sits between fetch and commit; a
  failed gate fails the run (alert issue) and nothing bad is committed.
- **State lives in `data/*.json`**, committed with `[skip ci]` so data
  commits don't trigger deploys or CI (the tracker reads the raw URL, so
  no redeploy is needed for data updates).
- **Notifications are GitHub issues** — issue creation emails the owner;
  every alert path is deduped against open issues.
- **Hard product rule** (never violated, however requested): real data
  and primary sources only; no buy/sell signals, predictions, or
  recommendations; no real-money or brokerage connectivity.

## Why no framework

One person maintains this. The pages are ~400 lines each of plain HTML/JS
with shared CSS; the pipeline is dependency-free Python (stdlib only).
Introducing React/Vue/build tooling would add a build step, dependency
surface, and upgrade treadmill with no capability gain at this size.
Revisit only if interactivity outgrows vanilla DOM rendering.
