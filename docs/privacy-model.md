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

**One scoped exception — `localStorage` on `resume.html`.** The resume
builder keeps the owner's profile in `localStorage` under the key
`wofa.resume.v1`. This is a privacy mechanism, not a tracking one: the
repository is public, so the resume data is deliberately kept *on the
device* instead of being committed. The page's only network requests are
two same-origin GETs for its own rule files, and neither carries user
data. No other page reads or writes that key.

The invariant is enforced, not just documented:
`scripts/validate_resume_assets.py` fails CI if the committed template
ever contains a real-looking email address or phone number — so a filled
profile cannot reach a public commit by accident. Details:
[docs/resume-builder.md](resume-builder.md).

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
- Resume/CV content (name, phone, address, employment history) is never
  committed. The builder ships as code; the data stays on the device.
- To purge something sensitive from history: see docs/runbook.md.
