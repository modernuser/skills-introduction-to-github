# Roadmap — Wolf of Fairhope Avenue

The product backlog, prioritized by value vs. effort. Items move to "Shipped"
when merged. Boundaries that don't change: the site displays real data and
links primary sources — it never gives buy/sell signals or predictions.

## Next up (high value, low-to-medium effort)

1. **Significant-move notifications** — when the scheduled data run detects a
   ±3% day move, automatically open a GitHub issue (which emails the repo
   owner) naming the ticker, the move, and a news link. Turns the tracker
   from "check it yourself" into "it tells you."
2. **Dartboard vs. benchmark experiment** — three paper portfolios with the
   same fake $10,000 start: owner's picks, random picks, and plain SPY.
   Tracked live on their own page. Tests whether stock-picking beats
   no-strategy — the classic index-fund lesson, run on real data.
3. **Custom watchlist without code** — move the ticker list into a simple
   `watchlist.json` so adding/removing symbols is a one-line edit in the
   GitHub web UI.

## Later (bigger builds)

4. **Charts page** — full-size historical charts (6mo/1yr), each ticker
   indexed against SPY = 100 so over/under-performance is visible at a glance.
5. **News panel** — pull each ticker's RSS headlines into the tracker page
   itself, with source names visible, so headline-vs-reality comparison is
   one page instead of six tabs.
6. **Installable app (PWA)** — manifest + service worker so the tracker can
   live on a phone home screen like a native app.

## Housekeeping

7. Remove the leftover GitHub-course workflow files (inert but noisy).
8. Consider a dedicated data branch if quote-commit history gets heavy.

## Shipped

- Landing page with dark theme (June 2026)
- GitHub Pages auto-deploy pipeline (June 2026)
- Live market tracker: 6 symbols, 20-min refresh, ±3% flags, news links,
  benchmark comparison (July 2026)
- Sparklines, stale-data self-alarm, favicon, SEO meta (July 2026)
