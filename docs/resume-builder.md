# Resume builder

`resume.html` is a self-contained resume and cover-letter builder: paste a
job description, measure keyword coverage against a fixed taxonomy, lint the
document for the things that actually break applicant tracking systems, and
export to PDF, plain text, or JSON.

It is the one page on this site that is not about markets. It lives here
because the owner asked for it on this repo; it shares the stylesheet and the
zero-external-JS constraint with every other page.

## The privacy split — read this first

**This repository is public.** A resume is the opposite of public-safe data:
full name, phone number, home town, employment history. So the tool and the
data are deliberately separated.

| Public (committed here) | Private (never committed) |
|---|---|
| `resume.html` — the builder | The filled profile JSON |
| `assets/resume-rules.json` — ATS rules, skill taxonomy | Generated resumes and cover letters |
| `assets/resume-template.json` — placeholders only | The application log |

The profile is held in `localStorage` under `wofa.resume.v1` and in files the
user exports themselves. Nothing is transmitted: the page makes exactly two
network requests, both same-origin GETs for its own rule files, and neither
carries any user data. There is no analytics, no third-party script, no
backend.

`scripts/validate_resume_assets.py` enforces this in CI. Its
`check_template_has_no_pii()` walks every string in the committed template and
fails the build on a real-looking email address (anything outside the RFC 2606
`example.com` reserved domains) or a phone number whose digits are not all
zeros. If a filled profile is ever pasted over the template, CI catches it
before the data reaches a public commit.

### Deviation from docs/privacy-model.md

That document states the site uses no `localStorage`. This page is the
documented exception, scoped to `resume.html` alone. The distinction that
matters is direction of travel: `localStorage` here *keeps data on the
device* rather than sending it anywhere. It is a privacy mechanism, not a
tracking one. No other page reads or writes the key.

## What the page measures, and what it refuses to claim

No resume tool can promise an interview rate, so this one does not. It
optimises the inputs that are known to matter and then **measures the actual
outcome** in the application log — reply rate, interview count — so the owner
can tell which changes moved the needle instead of trusting a number invented
by a tool.

**Coverage.** The job description and the profile are each reduced to a set of
taxonomy ids; coverage is the size of the intersection over the size of the
posting's set. Because the taxonomy is fixed data, the same posting always
scores the same way. Terms the taxonomy does not know — company names,
in-house systems, sector jargon — are surfaced separately by frequency rather
than silently ignored.

**Requirement matching.** Each requirement line from the posting is paired
with the profile bullet sharing the most taxonomy ids, so an unanswered
requirement is visible rather than inferred.

**Lint.** Deterministic checks only: parser-hostile glyphs, missing contact
details in the body, weak bullet openers, bullet and summary length,
non-standard dates, skill count, and the quantified-bullet ratio.

**Credential honesty.** Education and certification entries carry a
`confirmed` flag that defaults to false, and unconfirmed entries are excluded
from every rendered document. Listing a credential you do not hold is
discovered at the background check; the page will not help you do it.

## Why all three templates are single-column

Two-column layouts are the most common cause of ATS parse failure — the
extractor reads across the columns and interleaves unrelated text. "Most
visually appealing" and "most machine-readable" genuinely point in opposite
directions here, so the three templates vary only in typography, spacing, and
rule weight. The page says so on screen rather than shipping a design that
looks impressive and parses as noise.

## Data flow

```
assets/resume-rules.json ──fetch──> resume.html ──renders──> #paper ──print──> PDF
assets/resume-template.json ─fetch─┘      │
                                          ├──> localStorage (wofa.resume.v1)
                                          └──> exported .json / .txt (user's disk)
```

Opened over `file://`, `fetch` is blocked by the browser. The page detects
this and offers a file picker for the rules file rather than sitting inert.

## Schema

The profile object is the single structure everything derives from:

```
contact  {name, headline, email, phone, location, links[{label, url}]}
summary  string
skills   [{category, items[]}]
experience [{title, organization, location, start, end, bullets[]}]
projects [{name, url, summary, bullets[]}]
education [{credential, institution, year, confirmed}]
certifications [{name, issuer, year, confirmed}]
applications [{date, company, role, source, status}]
job      {company, role, text}
cover    string
settings {template}
```

Dates must match one of the `date_formats` patterns in the rules file
(`Mar 2019`, `March 2019`, `03/2019`, `2019`, `Present`). The lint warns on
anything else, because inconsistent date formats are a routine parse failure.

## Rules file

`assets/resume-rules.json` is the single source of truth for scoring. The
scoring code runs in JavaScript because that is where it has to execute;
rather than maintain a second Python engine that would drift, the *rules
data* is validated in CI and the JS applies it through small pure functions
(`normalize`, `containsTerm`, `skillsIn`).

Validated on every push and PR by `tests/python/test_validate_resume_assets.py`:

- Taxonomy ids are unique, and every term belongs to exactly one group — a
  term claimed twice would credit two skills for one word.
- No term is also a stopword, which would be stripped before matching and
  score as dead coverage.
- Every date-format regex compiles **and matches its own example** — a format
  that fails its own example would reject every real date typed into it.
- Lint thresholds are numeric, non-negative, and internally consistent
  (`min_*` below `max_*`, ratios within 0–1).
- Banned-glyph entries are single characters that do not replace themselves.

## Extending the taxonomy

Add a group to `taxonomy` with a unique `id`, a human `label` (shown on the
coverage chips), a `category`, and lowercase `terms`. Run
`python3 scripts/validate_resume_assets.py` — it will reject a term that
collides with an existing group or with a stopword. Terms are matched as
whole space-delimited phrases after normalisation, which preserves `/`, `-`,
`&`, `+`, `#`, and `.` so `tcp/ip`, `p&l`, `ci/cd`, and `a/v` survive.

## Monthly refresh

`.github/workflows/resume-refresh.yml` opens a checklist issue on the 1st of
each month. A schedule cannot rewrite a resume it cannot see, and cron cannot
invent accomplishments — so the workflow prompts for the month's real wins and
for updating the application log, then gets out of the way.
