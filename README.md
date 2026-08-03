# Wolf of Fairhope Avenue

_Bold. Local. Relentless._

**Live site:** [modernuser.github.io/skills-introduction-to-github](https://modernuser.github.io/skills-introduction-to-github/)

A private-use financial market dashboard that runs itself on GitHub:
real delayed market data, transparent sources, honest labeling — and a
hard rule that it **never** gives buy/sell signals, predictions, or
investment advice, no matter how a request is framed.

## Capabilities

- **[Market tracker](https://modernuser.github.io/skills-introduction-to-github/tracker.html)** —
  13-ticker theme watchlist (tiles, sparklines, 52-week ranges, ±3%
  flags), an 11-company diversified market core (one giant per sector),
  the 11 SPDR sector ETFs ranked by observed move, the **Rolling 500**
  (top movers across all ~503 S&P constituents), the **In Play** list
  (±5% observed days auto-admit tickers for two weeks), per-ticker
  headlines with publishers shown, a data-health strip, and a
  stale-data alarm, market-session clock with pre/after-hours prices
  (labeled, never blended into closes), and **sector depth** — the 10
  highest-volatility names in each of the 11 GICS sectors (110 companies),
  ranked daily by realized 30-day volatility and priced every session
- **[Dartboard experiment](https://modernuser.github.io/skills-introduction-to-github/dartboard.html)** —
  three paper portfolios (owner picks / seeded-random 11 / SPY), same
  fake $10,000, live **realized** alpha vs SPY
- **[Resume builder](https://modernuser.github.io/skills-introduction-to-github/resume.html)** —
  paste a job description and get keyword coverage against a 38-group
  skill taxonomy, each requirement paired with your strongest matching
  bullet, deterministic ATS lint (parser-hostile glyphs, weak openers,
  quantified-bullet ratio), three single-column templates, a cover-letter
  draft, and an application log that measures your **real** reply rate.
  The tool is public; **your profile never leaves your browser** and is
  never committed ([docs/resume-builder.md](docs/resume-builder.md))
- **Notifications by email and Slack**: weekday pre-market briefing with
  corroboration-tagged headlines; same-day alerts when any tracked ticker
  moves ±3%; pipeline-failure alerts. Email arrives via auto-created
  GitHub issues; Slack mirrors the same events once a webhook secret is
  set ([docs/slack-integration.md](docs/slack-integration.md))
- **Self-maintenance**: validation gate before every data commit,
  `data/health.json`, deterministic daily-ops reports and quality
  scorecard, CI on every PR

## How it works

Static pages + scheduled GitHub Actions; no server, no database, no
framework, no API keys. `main` holds code only — all generated data and
reports live on a separate `data` branch, so `main` can be fully
protected without any automation needing a bypass. See [docs/architecture.md](docs/architecture.md).
Data: [Stooq](https://stooq.com) end-of-day/delayed prices (Yahoo chart
fallback), Yahoo Finance RSS headlines (publisher shown per item), public
S&P constituents dataset. Formats: [docs/data-contracts.md](docs/data-contracts.md).
Refresh: market-hours cron; GitHub throttles congested slots, so measured
cadence is several runs/day — the site says so, honestly.
([docs/automation.md](docs/automation.md))

## File map

| Path | Purpose |
|---|---|
| `index.html` / `tracker.html` / `dartboard.html` / `resume.html` | The site |
| `watchlist.json` | Theme watchlist + market core + sectors — edit, no code |
| `assets/` | Resume builder rules + placeholder template — **never personal data** |
| `scripts/` | Pipeline (fetch, validate, rank, notify, report) — stdlib Python only |
| `data/` | Committed inputs only; **generated datasets live on the `data` branch** |
| `tests/python/` | 116 offline tests (`python3 -m pytest tests/python -q`) |
| `.github/workflows/` | Refresh, briefing, daily-ops, CI, deploy, gated AI loop |
| `docs/` | Architecture, contracts, privacy, security, automation, model routing, runbook, roadmap, audit |
| `reports/` | Daily reports + quality scorecard (generated) |
| `CLAUDE.md` | Working agreements + rules for coding agents |

## Setup, privacy, security

Local: clone, `python3 -m pytest tests/python -q`, `python3 -m http.server`
→ open `/tracker.html`. **This is a public repo backing a public Pages
site** — the watchlist and paper portfolios are public data; the full
exposure analysis and options are in
[docs/privacy-model.md](docs/privacy-model.md). No cookies, analytics,
tracking, or third-party scripts on any page. Threat model and defenses:
[docs/security-model.md](docs/security-model.md) and
[docs/engineering-audit.md](docs/engineering-audit.md).

## Maintenance model

A free deterministic daily-ops workflow inspects health, runs tests, and
writes reports every morning. An **opt-in** AI maintenance loop exists
but ships disabled — enabling it requires the owner's API key and flag
(costs money): [docs/model-routing.md](docs/model-routing.md). Rollback
of any change: revert its squash commit
([docs/runbook.md](docs/runbook.md)).

## Known limitations

Prices are end-of-day/delayed, never real-time. Free data sources can
throttle or drift (two-source fallback + validation + alerts mitigate).
GitHub cron is best-effort. Paper portfolios ignore dividends, fees, and
slippage — they are an educational experiment, not brokerage records.

## License

[MIT](LICENSE) © 2026 Wolf of Fairhope Avenue
