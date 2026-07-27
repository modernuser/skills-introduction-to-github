# Engineering audit — Wolf of Fairhope Avenue

Audited: 2026-07-26 (full-repo inspection by the maintaining agent, which
also authored the current codebase). Grading: Critical / High / Medium /
Low / Improvement opportunity. Status reflects the hardening PR series
that begins with this document's PR.

## Repository map

| Path | Purpose |
|---|---|
| `index.html`, `tracker.html`, `dartboard.html` | Static pages (GitHub Pages); tracker + dartboard fetch committed JSON from the raw GitHub URL |
| `styles.css` | Shared theme (dark, gold accent) |
| `watchlist.json` | Owner-editable config: theme watchlist, market core (one giant/sector), sector ETFs |
| `scripts/update_quotes.py` | Prices: stooq full-history CSV with Yahoo 3-mo fallback |
| `scripts/update_news.py` | Per-ticker RSS headlines, publisher shown; skip-write when unchanged |
| `scripts/update_movers.py` | Rolling 500 (bulk closes for ~503 constituents) + In Play ±5% rotation |
| `scripts/check_moves.py` | ±3% notifications: one deduped issue/day via state file |
| `scripts/morning_briefing.py` | Pre-market briefing markdown w/ corroboration tagging |
| `scripts/update_portfolios.py` | Dartboard experiment bookkeeping (paper $10k ×3, realized alpha) |
| `scripts/validate_data.py` | Pre-commit gate: schema/staleness/range checks |
| `scripts/atomic.py` | Atomic JSON writes (added by this PR) |
| `data/*` | Generated datasets, committed by the pipeline |
| `.github/workflows/update-quotes.yml` | Market-hours refresh + alerts + validation + commit |
| `.github/workflows/morning-briefing.yml` | Weekday 11:47 UTC briefing issue |
| `.github/workflows/deploy-pages.yml` | Pages deploy on push to main |

## Findings

### High

**H1 — XSS via RSS content rendered through innerHTML template strings.**
Files: `tracker.html` (news panel; also movers/core/rotation rows built
from the third-party constituents dataset), `dartboard.html` (holding
names). A malicious or compromised feed title like `<img src=x
onerror=…>` would execute in visitors' browsers; a `javascript:` link
would become a live href.
Impact: script execution on the public site.
Remediation: `esc()` on every external-origin string; `safeUrl()`
(https-only, else `#`) on every external URL; `encodeURIComponent` on
symbols in constructed URLs; ingestion-side drops of non-https links and
oversized titles in `update_news.py`. **Status: FIXED this PR.**
Validation: render test injecting a hostile fixture (`<img onerror>`
title + `javascript:` link) asserts inert rendering; automated in the
test suite in the next PR.

### Medium

**M1 — Actions pinned by tag, not SHA.** A hijacked `v4` tag would run
attacker code with `contents: write`. Remediation: pinned
`actions/checkout` to the v4.2.2 commit SHA in all workflows.
**Status: FIXED this PR.** Validation: next scheduled run checks out
successfully.

**M2 — Non-atomic JSON writes.** A crash mid-write could leave a
truncated dataset (the validation gate would block the commit, but the
local state would still be corrupted for that run). Remediation:
`scripts/atomic.py` (`tmp` + `os.replace`) used by every writer.
**Status: FIXED this PR.**

**M3 — No committed test suite.** Extensive tests exist but only ran in
the maintainer's session. Remediation: pytest suite + CI gate.
**Status: planned, next PR.**

### Low

**L1 — `rel="noopener"` without `noreferrer`** on some external links.
Fixed alongside H1.

**L2 — Briefing/moves issue bodies embed RSS titles.** Issue bodies are
inert text on GitHub (no script execution) and titles are length-capped
at ingestion; markdown link syntax could render oddly at worst.
Accepted risk; revisit if issues are ever machine-parsed.

**L3 — Yahoo RSS and stooq are unauthenticated free endpoints** — they
can throttle, drift, or disappear. Mitigations already present: two-source
price fallback, best-effort news step, validation gate, failure issues.
Accepted risk, monitored via run history.

### Improvement opportunities (tracked in roadmap)

- Data health report (`data/health.json`) + freshness badges (planned PR).
- Deterministic daily-ops workflow + quality scorecard (planned PR).
- Documentation suite + model-routing policy (planned PR).
- JS extraction into modules once the committed test suite lands.
- New asset classes (commodities/rates/crypto) — Research: requires
  source vetting; treated as high-risk per change policy.

## Facts documented, deliberately not "fixed"

- **The site is public GitHub Pages**, so the watchlist and paper
  portfolios are public data. This is a hosting-tier constraint (private
  Pages requires a paid plan), not an oversight. The privacy model doc
  (planned PR) covers the exposure and the options; changing repo
  visibility is an owner decision.
- **GitHub cron throttling** means the "every 20 min" schedule fires
  ~6×/day; copy already reflects measured behavior (CLAUDE.md rule 7).
- The pipeline never overwrites good data with bad: fetch failures leave
  the previous dataset in place (scripts return nonzero / skip write),
  and the validation gate blocks commits of malformed output.
