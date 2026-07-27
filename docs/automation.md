# Automation

All schedules are UTC (GitHub Actions cron has no timezone support).
Off-round minutes are deliberate — GitHub throttles congested slots, and
measured reality is a handful of fires per day regardless of the spec.

| Workflow | Schedule (UTC) | Purpose | Permissions |
|---|---|---|---|
| `update-quotes.yml` | all sessions: pre (8-13 UTC), regular (14-20), after (21-01), weekend 2×/day | Prices, extended-hours, news, movers, rotation, move alerts, portfolios, validation gate, health.json, commit | contents+issues write |
| `morning-briefing.yml` | 47 11 Mon-Fri | Pre-market briefing issue (emails owner) | contents read, issues write |
| `daily-ops.yml` | 17 11 daily | Deterministic health run: tests, link scan, scorecard, daily report | contents+issues write |
| `sector-depth.yml` | 17 22 Mon-Fri | Daily realized-volatility ranking, top 10 per GICS sector | contents+issues write |
| `ci.yml` | PRs + push to main | pytest, YAML/JSON validation | contents read |
| `deploy-pages.yml` | push to main | Pages deploy | pages standard |
| `ai-maintenance.yml` | 47 12 daily, **gated off** | Opt-in AI improvement loop (see model-routing.md) | contents read + PR write when enabled |

## Slack mirror

Briefings, move alerts, and failures also post to Slack when the
`SLACK_WEBHOOK_URL` secret exists — see docs/slack-integration.md.
Without the secret the notifier exits silently; a Slack outage never
affects the pipeline.

## Where output goes

Every data-producing workflow hydrates from the `data` branch, runs,
validates, then publishes back to `data` via `scripts/data_branch.py`.
**No workflow pushes to `main`**, which is why `main` can be fully
protected. Publication is a no-op when nothing changed, so identical
data never creates a commit.

## Failure handling

- Any scheduled job failure → one **deduped** GitHub issue (no new issue
  while one is open) → GitHub emails the owner.
- Data fetch failures preserve the previous dataset; the validation gate
  blocks malformed output from ever being committed; sections go
  visibly stale on the page (banner ≥100h; health strip per-file).
- `[skip ci]` on data/report commits keeps deploys and CI out of the
  data path. Never put that literal string in a merge-bound commit
  message (it would silently skip the Pages deploy — burned once).
- Manual dispatch: every scheduled workflow also supports
  `workflow_dispatch` (note: the repo owner can dispatch from the
  Actions tab; automation tokens here historically could not).

## Verification discipline

The reliable verifier is IN the repo: workflows validate their own
output and alert when it's wrong. Session-scheduled checks by a
maintaining agent are a courtesy layer, not the system of record.
