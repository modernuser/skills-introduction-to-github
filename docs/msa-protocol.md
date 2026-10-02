# Measurement system analysis & the PASS/FAIL protocol

## The standing loop

    IF PASS  -> apply the change and document it
    IF FAIL  -> document root cause, corrective action and evidence;
                repeat until PASS

A FAIL is a finding, not an error. What is forbidden is recording PASS
without the evidence, or reaching PASS by changing what counts as
passing. The verdict is produced by `scripts/gage_rr.py`, not asserted in
prose, so it cannot be talked into existence.

## Why Gage R&R, and what it is not

Before a KPI is trusted to rank tickers, the measurement system itself
has to be sound. MSA vocabulary maps onto this project directly:

| MSA term | Here |
|---|---|
| part | a ticker |
| operator | a data source (stooq / yahoo-fallback) |
| trial | one computation of the KPI |
| measurement | the KPI value |

**Repeatability (EV)** — same source, same ticker, repeated runs. This
pipeline is deterministic, so EV must be **exactly zero**. Nonzero
repeatability is not measurement noise; it is hidden state, ordering
dependence, or an unseeded RNG. The gate fails on it independently of
%R&R, because a small wobble can leave %R&R looking fine while still
meaning results are not reproducible.

**Reproducibility (AV)** — different sources, same ticker. This is the
question a per-symbol fallback forces: `fetch_closes` can serve one
ticker from stooq and the next from Yahoo, so a single ranking may mix
price-adjustment conventions.

Acceptance bands are AIAG: **≤10% acceptable, ≤30% marginal, >30%
unacceptable**.

MSA answers *"can this be measured consistently?"* It never answers
*"does this predict anything?"* — that is `factor_lab`, and its answer is
approximately no.

## What this procedure deliberately refuses to do

An earlier specification asked for: remove 6-sigma outliers, repeat five
times, and keep adjusting until r² ≥ 0.9990. Tested on a geometric random
walk (zero true relationship between price and time):

| iteration | n | removed | r² |
|---|---|---|---|
| 0 | 252 | — | 0.4725 |
| 1–5 | 252 | **0** | 0.4725 |

Across 30 series × 252 sessions — **7,560 points — zero residuals exceeded
6σ** (two exceeded 3σ). The filter is a no-op: 6σ is roughly 1 in 500
million under normality, and financial fat tails do not close that gap at
this sample size.

Forcing the target requires destroying the sample:

| σ threshold | kept | of | % kept | r² |
|---|---|---|---|---|
| 6.0 | 252 | 252 | 100% | 0.4725 |
| 2.0 | 230 | 252 | 91% | 0.5379 |
| **1.5** | **17** | 252 | **6.7%** | **0.9992** |
| 0.35 | 3 | 252 | 1.2% | 0.9998 |

Any r² target is reachable by deleting enough rows, on data where nothing
was ever there. This is the same defect as an in-sample `min_r2` gate
wearing different clothes: one adds noise columns until the fit rises,
the other deletes rows until the fit rises. **A procedure that guarantees
its own success is not evidence.**

r² is a goodness-of-fit statistic, not a confidence level. 0.9990 does
not mean "99.9% evidence-based".

Outliers are therefore **MAD-winsorized at 4σ** (shared with
`factor_lab`): clipped, never deleted, with the clip count reported.

## Result — 2026-08-04

Harness validated on 200 synthetic tickers. Real cross-source numbers
require stooq back online; it currently serves a bot-detection
interstitial, so every symbol is on the Yahoo fallback and reproducibility
cannot yet be measured on live data.

**Scenario A — single source (today's reality): PASS.** All five KPIs,
%R&R 0.0%, repeatability exactly 0 across 200 tickers.

**Scenario B — first attempt: FAIL, root cause in the test.** A uniform
×1.015 offset between sources produced 0.0 disagreement. Investigated
rather than accepted: all five KPIs are **scale-invariant**, so a uniform
multiplicative offset is genuinely invisible to them. The harness was
correct; the stimulus was wrong. Real dividend adjustment is a
*cumulative, time-varying* factor — older bars scaled down more — not a
uniform scaling.

**Scenario B — corrected: PASS, with the defect quantified.** Response is
monotone and exact at zero:

| dividend yield | reproducibility SD (slope) | %R&R |
|---|---|---|
| 0.0% | 0.0 (exactly) | 0.0% |
| 1.5% | 1.005 pp | 1.44% |
| 3.0% | 2.025 pp | 2.88% |

**Breaking point.** Mixing raw and dividend-adjusted closes is tolerable
while the universe is diverse, and fails when the names resemble each
other:

| cross-ticker spread | %R&R (slope) | verdict | gate |
|---|---|---|---|
| 1.00× (S&P-like) | 3.0% | acceptable | PASS |
| 0.30× | 9.6% | acceptable | PASS |
| 0.10× | 27.9% | marginal | PASS |
| 0.03× | 69.6% | **unacceptable** | **FAIL** |

**Conclusion.** The source-mixing defect is real and now measured rather
than asserted. At S&P-wide dispersion it costs ~3% of total variation —
detectable, not disqualifying. It becomes disqualifying when ranking a
narrow, homogeneous set, which is exactly what a single-sector or
top-10 screen does. Carrying raw and adjusted closes separately remains
the correct fix; this quantifies its priority rather than guessing at it.


## Result — 2026-10-02 (first live run)

The harness ran against real constituents for the first time after the
tuple fix (#113). **OVERALL: FAIL**, correctly.

| KPI | gate | parts | %R&R | repeatability |
|---|---|---|---|---|
| vol_30d | PASS | 501 | 0.0% | exactly 0 |
| trend_r2_90d | PASS | 501 | 0.0% | exactly 0 |
| slope_annual_pct | PASS | 501 | 0.0% | exactly 0 |
| max_drawdown_90d | PASS | 501 | 0.0% | exactly 0 |
| **volume_surge** | **FAIL** | **0** | — | not evaluable |

Repeatability came back exactly zero on 501 real tickers, which is the
property the gate exists to assert: the pipeline is deterministic.

**Root cause — two faults, one shape.** The panel declared more than the
wired source could supply:

1. `volume_surge` 0/501. `sector_depth` fetched through
   `update_quotes.fetch_closes`, which returns `(date, close)` — no
   volume column exists, so the KPI could never be computed.
2. `r200` and `r360` 0/501. `HISTORY_KEEP` was 120 bars, so the two
   longest declared return windows were structurally unreachable.

A declared column with no reachable data is a promise the pipeline cannot
keep. Neither fault could fail: both produced nulls, and nulls read as
"nothing happened".

**Corrective actions.**

- `sector_depth` now sources `market_data.fetch_ohlcv`, which carries
  volume, at the same request cost.
- It passes `drop_zero_volume=False`: zero-volume bars are a hazard for
  volume-weighted features but are perfectly good closes, and dropping
  them would silently shorten the series the volatility and trend fits
  depend on.
- `market_data` gains the circuit breaker `update_quotes` already had.
  Without it, swapping the source would have cost ~503 futile round-trips
  per run against a dead primary instead of 3 — a regression hidden
  inside a fix.
- `HISTORY_KEEP` 120 → 400, covering the 360-session window with margin.
- Four guards added: retention must exceed the longest declared window;
  the job must source a volume-bearing fetch; the zero-volume flag must
  exist; the breaker must be set. The `sector_depth` test factory now
  yields the producer's real 3-tuples and accepts its real kwarg, so
  wiring drift fails in the suite rather than in production.

**Evidence of PASS.** Re-run over 501 tickers with the corrected source
shape: all five KPIs evaluated, 501 parts each, `OVERALL: PASS`, and no
return window reporting null.
