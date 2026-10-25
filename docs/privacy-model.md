# Privacy model

## The central fact: this repository and site are PUBLIC

GitHub Pages on the free tier requires a public repository. Therefore
**everything committed here is public**, including:

- `watchlist.json` — the owner's tracked tickers (theme + core)
- `data/portfolios.json` — the paper portfolios and their performance
- ROADMAP/reports — project activity and history

None of this is real-money data, account data, or personally identifying
beyond "this GitHub user watches semiconductor stocks." The owner has
accepted this exposure to date. **Options if that changes:**
1. Make the repo private and lose Pages (or pay for GitHub Pro, which
   allows private-repo Pages).
2. Split: public site repo + private data repo (medium build).
3. Remove portfolios/watchlist from the repo entirely.

## What leaves the visitor's browser

Pages are static; the only outbound requests the pages make:
- `raw.githubusercontent.com` — the committed JSON data (GitHub sees
  standard request metadata: IP, user agent)
- Clicking a news/source link goes to that publisher (Yahoo Finance,
  Stooq, etc.) — normal link navigation, nothing prefetched

**There are none of:** cookies, analytics, tracking pixels, session
recording, ads, third-party scripts, fonts CDNs. The pages load zero
external JS.

Exceptions, both owner-facing personal pages:
- `dice.html` and `calendar.html` use **localStorage** to keep the
  dice-link list and the calendar settings in the visitor's own browser.
  Nothing from it gets sent anywhere or committed.
- `calendar.html` loads a **Google Calendar iframe**
  (`calendar.google.com`), but only after the visitor enters a calendar
  ID. Google then sees that request like any embed. The calendar ID is
  entered at runtime on purpose: committing it would publish the owner's
  address on this public site, and `tests/python/test_personal_pages.py`
  fails if an address is committed in either page.

## What the pipeline sends outward

GitHub Actions runners contact: stooq.com (price CSVs), Yahoo Finance
(RSS + chart fallback), raw.githubusercontent.com (constituents list).
These providers see runner IPs (GitHub's, not the owner's) and the
symbols requested. No credentials are sent — all endpoints are
unauthenticated.

## Rules

- Never commit API keys, tokens, or credentials (none exist today; the
  pipeline is deliberately key-free). Secrets, if ever needed, go in
  GitHub Actions secrets — never in files.
- Never add analytics or tracking to the pages.
- Personal research notes do NOT belong in this repo while it is public.
- To purge something sensitive from history: see docs/runbook.md.
