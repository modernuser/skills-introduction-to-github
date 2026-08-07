# Elder-fraud prevention impact: method

How `scripts/prevention_impact.py` estimates the money an awareness-and-action
programme kept out of criminals' hands, what the ±2σ band does and does not
mean, and where the estimate is weakest.

Inputs: `impact/prevention_inputs.json` (hand-maintained).
Output: `data/prevention_impact.json` (generated, never hand-edited).
Run: `python3 scripts/prevention_impact.py`.

---

## 1. The thing to be honest about first

**Prevented dollars are never observed.** A loss that did not happen leaves no
record. Every figure this produces is a model output conditioned on stated
priors — not a measurement, and not auditable the way revenue is auditable.

That is not a reason to refuse the question. Public health estimates prevented
infections, road safety estimates prevented collisions, and both are useful
because the assumptions are written down where someone can argue with them.
This does the same. What it will not do is let the number pass as a
measurement.

Three mechanisms enforce that, all of them code rather than prose:

| Mechanism | What it stops |
|---|---|
| Provenance gate | An uncited parameter blocks the headline from being marked publishable. |
| National-consistency filter | Parameter sets implying an impossible national loss total are discarded. |
| Two separate bands | Parameter uncertainty and process variation are never merged into one interval. |

---

## 2. Two bands that get confused, and must not be

This is the single most common error in impact reporting, so it is worth
being blunt about.

**The Monte Carlo band (p05–p95)** answers: *given what we assume about
incidence, loss severity and effect size, how uncertain is this month's
estimate?* It is wide because the underlying literature is thin. It shrinks
when you go and measure something.

**The control band (±2σ)** answers: *how much does this metric bounce around
month to month when nothing has actually changed?* It is narrow because it
describes a stable process. It shrinks when the programme becomes more
consistent.

They are different questions with different units of meaning. A point can sit
comfortably inside its Monte Carlo interval and still be a genuine process
signal, or vice versa. Plotting one and captioning it as the other is how
these reports lose their credibility with the first statistician who reads
them.

---

## 3. What is charted, and why not dollars

**Primary metric: prevented USD per 1,000 protected person-months.**

Charting raw monthly dollars would produce a chart that detects headcount.
Dollars rise when the programme grows and fall when it shrinks, so growth and
process change become indistinguishable. Dividing by the protected population
separates *how well it works* from *how big it got*.

The denominator is a **stock**, not a running total. Each month's reach adds
to it; everything already in it decays with an explicit half-life (default
mode: 9 months). The decay is load-bearing. Without it, a seminar delivered in
2019 keeps earning credit in 2026 — which is exactly how impact estimates turn
into fiction. With it, a programme that stops delivering watches its own
number fall, which is the behaviour you want from an honest metric.

What this buys, concretely: a programme drifting from 45-minute sessions
toward expo-table handouts holds its headline dollars roughly steady while the
rate falls. **The rate chart sees that drift. A dollars chart never would.**

---

## 4. Two processes, two charts

An earlier version of this charted *total* prevented dollars on one
individuals chart. It produced σ = 1.66 log-units and an upper control limit
of **$230,000,000** — not a control limit, a confession.

The arithmetic was fine. The series was a **mixture of two processes with
nothing in common**:

- **Awareness** — continuous accrual over a slowly-changing population.
  Observed spread on realistic inputs: ~2,700–3,200 per 1,000 person-months.
- **Interdiction** — rare, heavy-tailed events. Six in twelve months, one of
  them forty times another.

Alternating between them gives a bimodal series, and an individuals chart
fitted to a bimodal series estimates *the gap between the modes* as if it were
noise. The limits then grow wide enough to contain anything, and the chart can
never signal — the most dangerous failure available, because it still looks
like a working chart.

So the output carries three:

| Chart | Metric | Method | Answers |
|---|---|---|---|
| **Primary** | Awareness rate, USD / 1,000 protected person-months | XmR, log scale, ±2σ | Is the programme still doing what it did last month? |
| Count | Interdictions per period | c-chart, **exact Poisson** limits | Has intervention volume surged? |
| Severity | Exposure per interdiction event | XmR, log scale, ±2σ | Has the size of intercepted scams shifted? |

Severity is charted **per event, not per period**. A month with no
interdiction is not a $0 observation; it is an *absence* of one. Feeding
zeroes in would drag the centre line toward a value no real event can take.

Total prevented dollars are still reported per period with Monte Carlo
bands — but explicitly **not** as a control chart. A sum of two processes with
different physics has no single stable voice to speak in.

---

## 5. Three technical choices that are easy to get wrong

### Log scale
Fraud losses are lognormal with σ ≈ 2.8, so the mean sits ~50× above the
median. A symmetric ±2σ band on raw dollars puts the lower limit **below
zero** (meaningless) and the upper limit where nothing ever lands — it can
only ever fire high. Charting log dollars restores the near-symmetry
Shewhart's constants assume; limits are exponentiated back into dollars and
arrive correctly asymmetric.

### Sigma from the moving range, not the standard deviation
For individuals data, σ̂ = MR̄ / 1.128, or the outlier-resistant
median(MR) / 0.954 used by default. The sample standard deviation **absorbs
the very special causes the chart exists to find**: one $118,000 interdiction
inflates it enough to swallow itself, and the chart goes quiet exactly when it
should shout.

### The zero-sigma trap
The median moving range hits zero whenever more than half of consecutive pairs
are identical — a flat stretch with one step change is precisely that, and
precisely the pattern most worth catching. A zero-width band can never be
breached, so the chart would be permanently blind. The code falls back to the
mean moving range, and if the series never moves at all it reports
`degenerate_no_variation` rather than emitting limits that cannot fire.

---

## 6. On "two sigma" specifically

At ±2σ, **4.55%** of in-control points fall outside by chance — roughly one
false alarm every 22 months on monthly data. A chart with *no* excursions over
two years is the surprising outcome, not the reassuring one.

So ±2σ is a **warning limit, not an action limit**. Signals are graded:

| Rule | Chance rate | Grade | Meaning |
|---|---|---|---|
| Single point beyond 2σ | 4.55% per point | `warning` | Investigate. Do not conclude. |
| 2 of 3 consecutive beyond same-side 2σ | ~0.16% per point | `signal` | Real change. Find the cause. |
| 8 consecutive on one side of centre | ~0.8% | `signal` | The level shifted. |
| 7 consecutive increases or decreases | ~0.4% | `signal` | A trend, not a shift. |

If you want a single-point rule you can act on directly, use ±3σ (0.27%). The
±2σ width was requested and is implemented, and the grading above is what
keeps it from being over-read.

### One caveat that limits all of the above
The protected population is a stock that carries most of its value from one
month into the next, so **consecutive points are not independent** — the
core assumption of an individuals chart. High autocorrelation shrinks moving
ranges, understates σ, and makes the chart fire on ordinary drift. The code
computes lag-1 autocorrelation and emits a warning above |r₁| > 0.5. It
reports rather than corrects, because the fix is a different instrument
(chart model residuals, or widen the sampling interval), and silently
rescaling σ inside a helper would hide a modelling decision.

---

## 7. The estimator

### Awareness channel — accrual, not attribution-at-delivery

```
averted events = protected person-months × (incidence / 12) × RRR
prevented USD  = averted events × E[loss]
```

Crediting all future benefit to the month of delivery would double-count
repeat attendees and make the series unchartably lumpy.

### Interdiction channel — four discounts on the raw exposure

```
exposure × P(loss | stage) × (1 − recovery) × evidence × attribution
```

| Term | Removes |
|---|---|
| `P(loss \| stage)` | Not every interrupted scam would have completed. |
| `(1 − recovery)` | Money the bank would have clawed back anyway. |
| `evidence` | Uncorroborated accounts are worth less than bank confirmations. |
| `attribution` | A save shared with a teller who also flagged it is not wholly yours. |

The `(1 − recovery)` term matters most and is the one usually missing.
**Omitting it is the single most common way interdiction tallies get
inflated** — it counts as prevented every dollar that a wire recall would have
returned regardless.

---

## 8. The national-consistency filter

Priors on incidence and loss severity are individually wide, because the
evidence genuinely is. But their **product** is pinned by published data:

```
incidence × E[loss] × population(60+)  must fall within
the FTC's published $10.1B – $81.5B range for 2024
```

Draws violating this are discarded. This tightens the estimate **using data
rather than using preference** — and it constrains exactly the product that
drives the awareness channel, which is why the final band comes out narrower
than the marginal priors suggest. On the shipped example inputs about 42% of
draws survive.

A collapsing acceptance rate is diagnostic, not cosmetic: it means the stated
priors mostly contradict national totals. At zero the script raises rather
than handing back a confident number built from a surviving sliver.

---

## 9. Parameters and their provenance

| Parameter | Basis | Strength |
|---|---|---|
| Loss severity (median ~$1,600, σ_log ~2.8) | FTC median and FBI IC3 mean for 60+ reconcile at σ ≈ 2.81 under a lognormal | **Good** — two independent sources agree |
| National loss range ($10.1B–$81.5B) | FTC 2024 estimate | **Good** — published, though an 8× span |
| RRR, intensive (mode 0.22) | Langton & DeLiema RCT, N = 2,253: 22% relative reduction in revictimisation (5 pp absolute, p = 0.029) | **Fair** — real RCT, but a transfer |
| RRR, standard / brief | Scaled below the RCT anchor | **Weak** — dose-response assumed, not measured |
| Annual incidence | Wide prior, constrained by §8 | **Weak alone**, tolerable after the filter |
| Persistence half-life | Not measured in the literature | **Weak** |
| Stage-conditional loss probabilities | Elicited | **Weakest link in the interdiction channel** |

Two deliberate choices in that table:

- **`rrr_intensive`'s mode sits *at* the RCT point estimate, not above it.**
  The RCT measured a mailed campaign to prior mail-fraud victims; an in-person
  programme with follow-up is a different dose to a different population. It
  might well do better. Setting the mode higher would smuggle that hope into
  the arithmetic, so the transfer is stated instead of priced in.
- **`rrr_brief`'s lower bound is exactly zero.** A prior whose lower bound
  excludes zero *asserts the programme works*. A table at a health fair may
  change nothing, and the model has to be able to say so.

Every parameter carries a `source` and a `verified` flag. `verified: false`
means nobody has opened the primary document and confirmed the figure — the
shipped file ships entirely unverified, on purpose. **Verifying them is the
owner's job and the gate will keep failing until it is done.**

---

## 10. Where to spend measurement effort

`variance_contributions` ranks parameters by squared Spearman correlation with
the output, normalised to 100%. That ranking is a measurement roadmap: it
names which single number is worth money to pin down, instead of guessing
which assumption feels shakiest.

On the example inputs the recovery rate dominates at ~49%, which says: *go ask
two banks what fraction of wires at this stage actually get recalled.* That is
one afternoon of phone calls and it halves the uncertainty.

It is computed in a single pass on the accepted sample, deliberately **not**
by freeze-one-and-rerun. Freezing a parameter changes which draws survive the
consistency filter, so a re-run compares two different populations and reports
filter artefacts as sensitivity. The first version did exactly that and
returned *negative* contributions — an impossible result that was the bug
announcing itself.

---

## 11. What would make this defensible enough to publish

In rough order of value:

1. **Verify the cited parameters** against primary documents and flip the
   `verified` flags. The gate blocks publication until then.
2. **Replace the example periods** with a real service log.
3. **Measure the recovery rate** — the largest single lever (§10).
4. **Reach 20+ periods.** Below that the ±2σ limits are an estimate of noise
   made out of noise, and are marked `provisional`.
5. **Record known failures** — people reached who were defrauded anyway. This
   is the only input here that can *falsify* the effect size rather than
   assume it, and it converts `rrr_*` from a literature transfer into a
   locally measured quantity. It is the highest-value item on this list and
   the only one that makes the estimate self-correcting.

### What this must never be used for

Not for a marketing claim of dollars saved without the band and the
assumptions attached; not for grant reporting that presents a modelled
counterfactual as a measured outcome. Report it as: *"a model conditioned on
published national statistics and one RCT estimates X, with a 90% parameter
band of Y–Z."* That sentence is defensible. "We saved $165,797" is not.
