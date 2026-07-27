# Roadmap

Prioritized by value vs. effort. Boundaries that never change: real data
and primary sources only; no buy/sell signals, predictions, or
recommendations; no real-money connectivity. Model tier and autonomy
markers per docs/model-routing.md.

## Now
*(empty — hardening series complete; daily-ops selects from Next)*

## Next
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
- 2026-07-27 sector depth: 10 highest-volatility names per GICS sector
  (110 names) ranked daily after the close, priced intraday from existing
  data at zero extra fetch cost
- 2026-07-27 hardening series: XSS/URL security + atomic writes + SHA
  pins (#31), 24-test suite + CI gate (#32), health.json + source
  metadata + a11y (#33), deterministic daily-ops + scorecard (#34),
  docs suite + model policy + gated AI loop (this PR).
