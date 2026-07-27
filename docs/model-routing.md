# Model routing & credit conservation

Configuration: `.claude/model-policy.yml`. Model names change; discover
what's available in the current environment rather than hard-coding.

## Tiers

| Tier | Class (July 2026) | Used for |
|---|---|---|
| 1 — highest capability | Fable/Mythos-class | Repo-wide audits, architecture, security-critical analysis, hard debugging, cross-cutting refactors, risky-PR review, major roadmap planning |
| 2 — standard coding | Sonnet-class | Default for feature work, refactors, tests, bug fixes, docs, review, daily improvement planning |
| 3 — lightweight | Haiku-class | Mechanical edits, formatting, labeling, summaries, changelog, report prose |
| 0 — none | deterministic scripts | Daily health checks, scorecard, reports — always free, always on (`daily-ops.yml`) |

**Never spend Tier-1 on:** formatting, renames, simple docs, routine test
generation, report formatting, straightforward bug fixes.

## Fallback ladder

Premium unavailable/exhausted/over budget → continue at Tier 2, record
the fallback in the daily report, defer only genuinely-Tier-1 tasks to
the backlog. Tier 2 unavailable → Tier 3 mechanical checks only, no
architectural changes, open an issue describing deferred work. All tiers
unavailable → Tier 0 keeps running (it needs no API at all). **Test,
security, and review standards never drop with the tier.**

## Cost controls (from model-policy.yml)

daily_run_limit 1 · max retries 2 · ≤8 files & ≤500 changed lines per
autonomous PR · one open agent PR at a time (`agent-maintenance` label) ·
no auto-merge above low risk · monthly spend limit 0 until the owner
raises it · no automatic credit purchase, ever · targeted file context
(changed files, failing checks, affected modules) — never ship the whole
repo to a model · generated files (`data/`, `reports/`) excluded from
model context.

## Enablement (owner action required — costs money)

The AI loop (`ai-maintenance.yml`) is **disabled by default** and runs
only when BOTH are true:
1. Repository variable `DAILY_AI_MAINTENANCE_ENABLED` = `true`
2. Repository secret `ANTHROPIC_API_KEY` is set

Optional variables: `AI_MODEL_TIER` (default `standard`),
`AI_MONTHLY_BUDGET_USD`, `ALLOW_PAID_CREDITS`. The workflow cannot read
account balances; the budget variables are owner-declared intent that the
loop reports against, not live billing data. Billing credentials never
go in repository files.
