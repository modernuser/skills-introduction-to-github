# Security model

## Threat model

| Threat | Vector | Defense |
|---|---|---|
| XSS on the site | Malicious RSS title/link; poisoned constituents dataset | `esc()` on every external string, `safeUrl()` https-only, `encodeURIComponent` in built URLs; ingestion-side drops of non-https links and oversized titles; verified by hostile-fixture test |
| Tab-nabbing | External links | `rel="noopener noreferrer"` on all external anchors |
| Supply chain | Hijacked action tag | `actions/checkout` pinned to full commit SHA |
| Token abuse | Compromised workflow | Least-privilege permissions per workflow (`contents: read` for CI; write + issues only where needed); default GITHUB_TOKEN, no PATs, no secrets |
| Data poisoning | Bad/partial API responses | Validation gate before commit (schema, ranges, staleness, 52-wk sanity); coverage guards; atomic writes; last-known-good preserved on failure |
| Workflow injection | Issue/PR content reaching shell | Scheduled workflows never interpolate user-controlled content into shell; issue bodies are written from script-generated files |
| Corrupted state | Crash mid-write | `scripts/atomic.py` (tmp + os.replace) for every dataset |

## Standing rules

- No third-party JavaScript on any page, ever. No CDNs.
- New external data sources are **high-risk changes**: require the terms
  check, ingestion validation, escaping review, and human approval.
- Workflow permissions are reviewed in any PR that touches `.github/`.
- `pull_request_target` is never used; untrusted PRs get no secrets.
- Automated agents must not modify `data/*` by hand or grant themselves
  broader workflow permissions (see CLAUDE.md agent rules).
- Real-money order execution and brokerage connectivity are permanently
  out of scope.

## Repository settings (owner-controlled, not code)

| Setting | State | Action |
|---|---|---|
| Branch protection on `main` | configurable with **no bypass needed** | Since generated data moved to the `data` branch, nothing automated writes to `main`. Safe to require a pull request + the `test` check, and to block force-pushes and deletions, with an empty bypass list. |
| Push protection | **ACTIVE** (verified: it rejected a real push containing a webhook-shaped test fixture) | Keep enabled. Never click the "allow secret" unblock link — fix the content instead |
| Secret scanning API/alerts | unavailable (no GHAS) | `daily_ops.py` runs an in-repo pattern scan daily as the compensating control |
| Dependabot | active | Resolve dependency PRs by updating the **SHA pin**, not by accepting a tag bump |
| Repository visibility | public | See docs/privacy-model.md before committing anything personal |

## Verification

The hostile-fixture XSS test and validator accept/reject tests run in CI
on every PR. The engineering audit (docs/engineering-audit.md) tracks
finding status; re-audit after any security-relevant change.
