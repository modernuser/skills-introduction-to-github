# Roadmap — Wolf of Fairhope Avenue

The product backlog, prioritized by value vs. effort. Items move to "Shipped"
when merged. Boundaries that don't change: the site displays real data and
links primary sources — it never gives buy/sell signals or predictions.

## Next up (high value, low-to-medium effort)

1. **Significant-move notifications** — when the scheduled data run detects a
   ±3% day move, automatically open a GitHub issue (which emails the repo
   owner) naming the ticker, the move, and a news link. Turns the tracker
   from "check it yourself" into "it tells you."
2. **52-week high/low context** — show each ticker's distance from its
   52-week high and low on the tiles. Pure fact, answers "is this move big?";
   the data source already returns full history (we currently keep ~30 days).
   Also the enabler for the Charts page below.
3. **Fairhope FSBO real-estate leads — investigated 2026-07-26.** Verdict:
   a scraping workflow is NOT viable (Zillow/Trulia/craigslist terms forbid
   automated collection; Gulf Coast Media and alabamapublicnotices.com
   bot-block fetchers). The outcome IS achievable via each source's own
   alert feature — see the setup checklist in the session notes: Zillow/
   ByOwner saved-search FSBO email alerts for Fairhope, and Alabama Public
   Notices "Smart Search" (paid, daily email) for foreclosure/estate/tax
   notices from Baldwin County newspapers including the Fairhope Courier.
   Optional future build: monitor Baldwin County government tax-sale lists
   (public data; needs direct verification of page structure).
4. **Dartboard vs. benchmark experiment** — three paper portfolios with the
   same fake $10,000 start: owner's picks, random picks, and plain SPY.
   Tracked live on their own page. Tests whether stock-picking beats
   no-strategy — the classic index-fund lesson, run on real data.
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
