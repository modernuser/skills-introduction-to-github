# Roadmap

Prioritized by value vs. effort. Boundaries that never change: real data
and primary sources only; no buy/sell signals, predictions, or
recommendations; no real-money connectivity. Model tier and autonomy
markers per docs/model-routing.md.

## Now
*(empty — hardening series complete; daily-ops selects from Next)*

## Next
- **Elder-fraud impact: verify parameters and load the real service log** —
  owner action, not code. `scripts/prevention_impact.py` ships with every
  parameter flagged `verified: false` and twelve example periods, and the
  provenance gate blocks any headline figure until both are fixed. Highest-
  value single measurement is the bank recovery rate (~49% of output
  variance); highest-value new input is a log of *known failures* — people
  reached who were defrauded anyway — which is the only quantity here that
  can falsify the effect size rather than assume it. See
  docs/prevention-impact.md §11.
- **Trend-quality + dartboard page updates** — show the `trend` arm on
  dartboard.html alongside the other three, and surface
  `trend_quality.json` (slope, r2, rank) as a sortable table. Display
  only. Tier 2, low risk, autonomous-safe.
- **Factor lab page** — surface `factor_lab.json` as a table (OOS R²,
  IC, t-stat, each beside its noise control). The point of the page is
  the comparison: a reading only means something next to what no-skill
  looks like on the same data. Display-only, no new fetching. Tier 2,
  low risk, autonomous-safe.
- **Second-generation features for the lab** — the harness is generic;
  only the feature functions are specific. Candidates worth *measuring*
  (not assuming): overnight-gap reversal, volume-weighted range
  compression, sector-relative momentum. Each is accepted or rejected on
  its out-of-sample IC vs. control, not on plausibility.
- **More risk measures on sector depth** — max drawdown (1y), beta vs
  SPY, and a ±5% news-event footprint per name. The volatility pipeline
  already fetches the history these need; each is a display-only add.
  Tier 2, low risk, autonomous-safe.
- **Fairhope FSBO alert setup** — owner action, not code: enable native
  email alerts (Zillow/ByOwner saved searches; Alabama Public Notices
  Smart Search). Checklist delivered 2026-07-26. Complexity: none.
- **Charts page** — 6mo/1yr historical charts, each ticker indexed to
  SPY=100. Data already fetched (full stooq history). Tier 2, medium
  complexity, autonomous-safe behind tests. Acceptance: page renders
  from committed data with no new requests, no console errors, a11y par.

## Later
- **Installable app (PWA)** — manifest + service worker. Tier 2, low risk.
- **JS extraction to assets/js/ modules** — now that the test suite
  exists. Tier 2/3, behavior-preserving, autonomous-safe in slices.
- **Auto-merge for low-risk agent PRs** — needs branch protection and an
  explicit owner decision. Blocked on owner.

## Research
- **New asset classes** (commodities, rates, crypto, more indexes):
  stooq symbols exist (^spx, xauusd, btcusd) but new providers/classes
  are HIGH-RISK per policy — needs terms review, ingestion validation,
  display-labeling design, and human approval. Tier 1 review.
- **Economic-calendar context** — no vetted key-free source identified;
  revisit. Tier 1 review before any build.
- **Public/private repo split** — if the owner wants the watchlist or
  portfolios out of public view (docs/privacy-model.md).

## Blocked
- **Slack webhook activation** — code shipped and inert; owner adds the
  `SLACK_WEBHOOK_URL` secret to switch it on (docs/slack-integration.md).
- **Slack AI bot (level 3)** — requires ANTHROPIC_API_KEY, budget, and a
  signature-verified Slack app; high-risk change, human approval gate.
- **AI maintenance loop activation** — built and gated; needs owner to
  set ANTHROPIC_API_KEY + DAILY_AI_MAINTENANCE_ENABLED=true (costs money).

## Completed
- 2026-08-07 elder-fraud prevention impact estimator: Monte Carlo
  counterfactual model with a national-consistency filter tied to published
  FTC totals, a provenance gate that blocks unpublishable claims, and three
  separated control charts (awareness rate ±2σ, exact-Poisson interdiction
  counts, per-event severity). 50 tests. Method: docs/prevention-impact.md.
- 2026-06/07: landing page, Pages deploy, live tracker (13 tickers,
  sparklines, 52-wk range, ±3% flags, stale alarm), sector pulse (11
  ETFs), editable watchlist, headlines panel with corroboration-free
  display + signal-vs-noise checklist, pre-market briefing (corroboration
  tags), Rolling 500, In Play ±5% rotation, market core (1 giant/sector),
  move-alert issues, dartboard experiment (live realized alpha),
  course-file cleanup, measured-cadence honesty pass.
- 2026-07-27 all-session coverage: market-session engine (pre/regular/
  after/closed, holidays, half-days), extended-hours prices on tiles
  (labeled, never blended into closes), weekend headline cadence,
  session-aware staleness; GitHub security test (push protection verified
  live, in-repo secret scan, checkout v6 SHA pin)
- 2026-07-27 data-branch split: generated data and reports moved to a
  dedicated `data` branch; workflows hydrate/publish via
  scripts/data_branch.py; `main` is now code-only and fully protectable
  with no bypass list
- 2026-07-27 sector depth: 10 highest-volatility names per GICS sector
  (110 names) ranked daily after the close, priced intraday from existing
  data at zero extra fetch cost
- 2026-07-27 hardening series: XSS/URL security + atomic writes + SHA
  pins (#31), 24-test suite + CI gate (#32), health.json + source
  metadata + a11y (#33), deterministic daily-ops + scorecard (#34),
  docs suite + model policy + gated AI loop (this PR).
