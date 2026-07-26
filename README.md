# Wolf of Fairhope Avenue

_Bold. Local. Relentless._

**Live site:** [modernuser.github.io/skills-introduction-to-github](https://modernuser.github.io/skills-introduction-to-github/)

---

## About

Wolf of Fairhope Avenue is an open project built in public, one commit at a time.
Rooted in the spirit of Fairhope, Alabama — a town known for independent thinkers
and creative makers — this project grows iteratively and openly on GitHub.

## What's Here

| File | Purpose |
|------|---------|
| `index.html` | Main landing page |
| `tracker.html` | Live market tracker (educational data display) |
| `dartboard.html` | Dartboard experiment: picks vs random vs SPY, realized alpha |
| `styles.css` | Site styles (dark theme, gold accent) |
| `watchlist.json` | Theme watchlist + diversified market core + sector ETFs — edit here, no code |
| `data/quotes.json` | Auto-refreshed market data (committed by the scheduled workflow) |
| `scripts/update_quotes.py` | Data fetcher (stooq with Yahoo fallback) |
| `scripts/update_news.py` | Headline fetcher (per-ticker RSS, publisher shown) |
| `scripts/morning_briefing.py` | Weekday pre-market briefing (emailed via auto-issue) |
| `scripts/update_movers.py` | Rolling 500: observed top movers across all S&P constituents |
| `scripts/check_moves.py` | ±3% move notifications (one daily issue, emailed) |
| `scripts/update_portfolios.py` | Dartboard experiment bookkeeping (paper portfolios) |
| `ROADMAP.md` | Prioritized backlog and shipped history |
| `CLAUDE.md` | Working agreements and lessons learned for AI sessions |

## Getting Started

1. Clone the repo
   ```bash
   git clone https://github.com/modernuser/skills-introduction-to-github.git
   cd skills-introduction-to-github
   ```
2. Open `index.html` in your browser — no build step needed.

## Contributing

This project is developed on feature branches and merged via pull requests.
To contribute:

1. Create a branch from `main`
2. Make your changes
3. Open a pull request describing what you improved

## License

[MIT](LICENSE) &copy; 2026 Wolf of Fairhope Avenue
