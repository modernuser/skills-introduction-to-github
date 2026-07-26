# Roadmap — Wolf of Fairhope Avenue

The product backlog, prioritized by value vs. effort. Items move to "Shipped"
when merged. Boundaries that don't change: the site displays real data and
links primary sources — it never gives buy/sell signals or predictions.

## Next up (high value, low-to-medium effort)

1. **Fairhope FSBO real-estate leads — investigated 2026-07-26.** Verdict:
   a scraping workflow is NOT viable (Zillow/Trulia/craigslist terms forbid
   automated collection; Gulf Coast Media and alabamapublicnotices.com
   bot-block fetchers). The outcome IS achievable via each source's own
   alert feature — see the setup checklist in the session notes: Zillow/
   ByOwner saved-search FSBO email alerts for Fairhope, and Alabama Public
   Notices "Smart Search" (paid, daily email) for foreclosure/estate/tax
   notices from Baldwin County newspapers including the Fairhope Courier.
   Optional future build: monitor Baldwin County government tax-sale lists
   (public data; needs direct verification of page structure).
## Later (bigger builds)

4. **Charts page** — full-size historical charts (6mo/1yr), each ticker
   indexed against SPY = 100 so over/under-performance is visible at a glance.
5. **Installable app (PWA)** — manifest + service worker so the tracker can
   live on a phone home screen like a native app.

## Housekeeping

7. Remove the leftover GitHub-course workflow files (inert but noisy).
8. Consider a dedicated data branch if quote-commit history gets heavy.
   (Measured 2026-07-26: ~5 data commits/day — not needed yet.)

## Shipped

- Landing page with dark theme (June 2026)
- GitHub Pages auto-deploy pipeline (June 2026)
- Live market tracker: 6 symbols, 20-min refresh, ±3% flags, news links,
  benchmark comparison (July 2026)
- Sparklines, stale-data self-alarm, favicon, SEO meta (July 2026)
- Editable watchlist.json + Sector pulse: all 11 SPDR sector ETFs ranked by
  observed daily move (July 2026)
- Headlines panel: per-ticker news on the 20-min cycle with publisher
  visible + signal-vs-noise checklist (July 2026)
- Pre-market briefing: weekday 7:47am ET email (via auto-issue) with prior
  close, sector leaders/laggards, and corroboration-tagged overnight
  headlines (July 2026)
- The Rolling 500: top-10 observed gainers/decliners across all ~503 S&P
  constituents, self-rolling daily, on the tracker (July 2026)
- Significant-move notifications: each ticker's ±3% day opens/updates one
  daily issue (emails the owner) with the move and a news link (July 2026)
- 52-week closing range + distance-from-high on every tile (July 2026)
- Dartboard experiment: owner picks vs seeded-random 11 vs SPY, same paper
  $10,000, live realized alpha on dartboard.html (July 2026)
- Market core: one giant per GICS sector (largest-by-cap rule) tracked at
  company level with the same ±3% alerts (July 2026)
- In Play auto-rotation: ±5% observed S&P days admit a ticker for ~2 weeks
  then rotate out — the ticker set updates itself on verified news
  footprints (July 2026)
