# The forecast's own history — replay, three bugs, and what the charts show

Three visualisations were added on 2026-08-29: a density beside the existing
CDF, the predicted date over time, and the probability over time. The first
needed no new data. The other two needed a forecast history, and the model had
only existed for two days, so it was replayed — which turned out to be the most
useful thing done all session, because replaying it broke it three times.

## The density (PDF)

`pdf_chart` in `scripts/build_site.py`. Same pmf, same x-axis and same 0.99
clip as the CDF, so the two stack and read as one picture.

The CDF's docstring used to argue against a density outright: half the mass
sits on a single issue, so a per-issue density is one spike and a hundred
invisible bars. Per issue that is correct — 50.6% on 2026-09-14 against ~0.4%
average for the other 115 candidate issues is a 126:1 range, and the tail
renders at one pixel. **Binned by calendar month it is about 8:1**, which a
linear axis shows honestly (54%, 6%, 7%, 5%, 5% for Sep–Jan). So the chart bins
by month, and labels the September bar with the single-issue probability so the
bin does not hide the spike that is the actual story.

## The replay

`scripts/replay_forecast.py`. For each past date it calls
`build_posterior.main(asof=...)`, which filters every input to what existed
then, and writes a normal snapshot carrying `provenance: replay` and
`replay_asof`.

It starts at **the first production event reported for the chapter being
forecast** — ch. 421's `character_inking started`, 2024-09-30 — rather than at
the batch's own start. 187 sample points to 2026-08-25, at issue on-sale dates
and production-event dates, the days something could have moved the forecast.
The live record takes over on 2026-08-28.

Chapter 421 does not enter the model's horizon until 2024-10-07, when batch 48
began and 421 became part of the batch-after-next. So 180 of the 187 replayed
snapshots say something about it; the first seven do not.

### What is filtered

| input | filter |
|---|---|
| `chapters.csv` | published on or before the date |
| `production_events.csv` | `event_date` on or before the date |
| `wsj_issues.csv` | on sale on or before the date |

Filtering the issue calendar means dates past the replay point are *projected*
from the preceding year's gap structure rather than read off the real calendar,
which is correct — those on-sale dates were not known — but it does mean a
replayed floor can sit a few days off the true issue.

### What is not, and why

**The batch's length.** Ten chapters, by the §3 convention, anchored on the
batch's observed start. This is structure, not evidence, and it is the same
assumption the live model makes.

**The model itself.** Hyperparameters were selected by a backtest over
historical batch gaps, not over this batch's outcome, so replaying August's code
onto 2024 is not circular. It is still August's code, which is worth saying
plainly rather than implying the 2024 points are what 2024 would have produced.

**Know date vs. event date.** An event enters the replay on the day it happened,
not the day we learned of it. Some events come from image transcriptions that
were human-confirmed later; some posts were only discovered through the Wayback
Machine. **The replay is therefore very slightly better informed than the live
run would have been.** Recorded rather than engineered around: one field on the
snapshot, one paragraph on the method page, this note.

## Three bugs the replay found

None of them affected the live forecast, which is why none had been noticed.

**1. The forecast target slid.** `build_level2.load` decided where the running
batch ended by walking `announcements.csv` forward from the last published
chapter. That reaches ch. 420 only while the file lists every unpublished
chapter of the batch contiguously — true today, false at every earlier date.
Replayed to 2026-06-29, with chapters published to 411 and the file naming only
419 and 420, the walk stopped at 411 and the model forecast **ch. 412**. The
whole replayed history was a moving target: 412, 413, 414 … 421. Fixed by taking
the extent from the convention.

**2. Announcements dragged unrelated batches forward.** The first fix let
announcements extend a batch past ten chapters — batch 43 really did run to
eleven — but without checking the announcement was *about* that batch. Replayed
to 2024-09-30 the file's ch. 419/420 rows stretched batch 47 from 391–400 to
391–420, and the model reported "W_48 — publication of ch 421". Announcements
now only extend the running batch if they fall inside it.

**3. The likelihood underflowed to zero.** Level 2 is a sum of Gaussians over
candidate issues. When every analog implies a start date the truncation has
already ruled out, each term underflows to exactly `0.0`, `post.sum()` is zero,
and the posterior is `0/0`. Found at 2025-06-02. The likelihood is now rescaled
by its peak — free, since it cancels in the normalisation — and if nothing
survives the truncation the model falls back to Level 1 and says so, rather than
returning a silent `nan`.

There was a fourth, found before the replay ran: `end_seq = last_obs + len(ann)`
inferred the batch end from the **row count** of `announcements.csv`. Replayed to
2026-08-10 it put the floor an issue early. The batch end is now derived from the
batch's observed start plus the convention, and `announcements.csv` no longer
determines it at all. See `docs/announcement_record.md` for the same row-count
coupling seen from the other side.

## What the charts show

Two lines, no shading: the median and the 80% upper bound. y is inverted —
further into the future sits lower, so a rising line means the forecast moved
nearer. Every axis tick and line label carries a four-digit year, because "Sep
26" reads as a day when the other axis is also dates.

| as of | median for ch. 421 | P(by Dec 2026) |
|---|---|---|
| 2024-10-07 | 2026-06-29 | 64% |
| 2025-04-21 | 2026-10-17 | 57% |
| 2025-10-09 | 2027-04-29 | 40% |
| 2026-03-15 | 2027-09-17 | 28% |
| 2026-06-08 | 2027-12-03 | 22% |
| 2026-08-10 | **2026-09-14** | **73%** |

### Why the forecast drifted later for two years

Not the production evidence. **The truncation floor advances one issue every
week**, because each week that passes is a fresh observation that the batch has
*still* not started, and the mass below the floor is discarded and
renormalised. The median therefore moves roughly one day per day:

    as of 2025-09-22  ->  median 2027-03-18
    as of 2025-09-29  ->  median 2027-03-25     (+7 days for +7 days)
    as of 2025-10-08  ->  median 2027-04-15

That is the model working, not failing: with a bimodal gap prior whose near mode
keeps being ruled out, the remaining mass can only sit further out. It is also
the honest picture of what this model does during a hiatus — it says "soon",
then says "soon" again a week later.

The jump on 2026-06-29 is batch 49 actually starting: ch. 421 stops being a
chapter in the batch-after-next and becomes the first chapter after the running
one, and the estimate collapses from December 2027 to September 2026.

### The widening that was not real

Before the fixes, the last ten weeks appeared to show the 80% bound stretching
from 2026-10-12 out to 2027-05-21 — the model apparently getting *less* certain
as production evidence arrived. That was bug 1: the target was sliding from
ch. 412 to ch. 421, nine chapters further out. With the target held fixed the
same window is flat from 2026-08-10 onward.

## The thing the replay actually exposes

The declining stretch before June 2026 does not look right, and it is not right.
Decomposing it:

| as of | ch. 411 median (Level 1+2) | ch. 421 median | gap between them |
|---|---|---|---|
| 2025-01-15 | 2025-01-22 | 2026-07-08 | 532 d |
| 2025-06-09 | 2025-06-16 | 2026-11-28 | 530 d |
| 2025-10-13 | 2025-10-20 | 2027-05-27 | 584 d |
| 2026-03-09 | 2026-03-16 | 2027-09-17 | 550 d |
| 2026-06-22 | 2026-06-29 | 2027-12-14 | 533 d |

**The ch. 411 median is always exactly one issue after the replay date.** For
twenty months the model's answer was "next week", every week. And the gap added
on top to reach ch. 421 is a near-constant ~545 days that production evidence
barely touches, even as the observed event count goes 14 → 43. So the whole
declining curve is `(today + 7 days) + 18 months`, which marches forward one day
per day by construction. It is not a forecast responding to evidence.

**In 175 of 187 replayed points the median sits exactly on the truncation
floor** — the first issue the batch could possibly start on.

### Why: an overdue analog is read as an imminent one

Level 2 estimates, for each analog batch, the start date this batch's production
events imply. Compare those against the floor:

    as of 2025-06-09    floor 2025-06-16
                        analog 47 implies 2024-09-12
                        analog 48 implies 2024-12-24

Both implied dates are six to nine months **in the past**. The likelihood is a
sum of Gaussians centred on them, so across the candidate grid — every issue at
or after the floor — it decreases monotonically and steeply, and essentially all
the posterior mass lands on the single first eligible issue. That run put
**0.999** on 2025-06-16. The peak across the replay is **1.0000, on 2025-07-28**,
which Agents.md §3 forbids outright. Chapter 411 published on 2026-06-29.

86 of 187 replayed points put ≥90% on the very next issue; the median across the
hiatus is 80%.

The statistical error is specific and fixable: an analog whose implied date has
already passed carries **no information about which future issue** the batch
starts on. The current form treats "this should already have happened" as "this
is maximally imminent" and concentrates on the boundary. It should flatten the
likelihood instead — the evidence is exhausted, not sharp.

This is adjacent to the π₀ concern already logged (`docs/next_session.md` item 3)
but distinct: π₀ ≈ 0.5 is the Level 1 zero-gap mass, whereas these are Level 2
posteriors of 0.93–1.00. Level 2 is doing the over-sharpening, and the earlier
underflow guard only catches the case where the mass reaches exactly zero, not
the far commoner near-miss that produces 0.999.

**Not fixed here.** It changes what the live forecast says, and it is a modelling
decision rather than a bug fix.

## Not done

- Batches 47 and 48 are **not** replayed as separate targets, deliberately —
  batch 49's own history is the thing to sanity-check first.
- Nothing here is scored. Scoring needs an outcome, and ch. 421 has not
  published yet.
- The replayed issue calendar is projected past each replay date, so replayed
  floors can differ by a few days from the true issue dates.

---

## Revision replay — readiness-coordinate Level 2 (2026-08-30)

The preceding sections document the original exact-stage analog model and are
kept unchanged.  Its boundary-spike defect is now fixed in the live model; this
section records the replacement replay rather than rewriting history.

The revised model uses one derived, furthest-observed readiness state per
chapter position and treats an analog whose surviving probability beyond the
non-start floor is below 5% as neutral.  It does not retain that analog's tiny
right tail and renormalise it into a false next-issue prediction.

187 revision snapshots were written alongside the original midnight replays,
using a distinct noon-UTC run id.  No earlier snapshot was overwritten.  The
site displays one model-version series at a time so it does not draw the old and
new algorithms as a single continuous belief history.

Sanity check at 2025-06-09: the two available analogs implied starts in January
and February 2025, while the batch had still not begun.  Both were exhausted;
Level 2 became neutral and the posterior equalled the truncated Level-1 prior.
The revised median for chapter 411 was 2026-09-12, rather than a near-certain
2025-06-16 next-issue prediction.  This does not prove accuracy — the model is
still unscored — but it removes the mechanical error that generated the
pre-June-2026 declining curve.

## Revision replay — continuous no-start conditioning (2026-08-31)

The event-only V4/V5 rule created a different problem: during a long quiet
stretch, a reconstructed forecast could retain probability on issues already in
the past.  At the first later production post it then discarded the entire
accumulated interval in one step.  For example, the batch-49 median changed
from 2025-08-18 to 2026-09-05 on 2025-08-19, mostly because the no-start floor
jumped from January to late August—not because chapter 413's background
specification completion was negative evidence.

V6 conditions on the fact of non-publication through every observed issue while
keeping production reports distinct from that fact.  The resulting line may
move gradually during silence, but it cannot report a predicted publication
date already past or turn several months of known non-publication into a single
tweet-driven cliff.  These snapshots use a distinct 23:00 UTC replay id and
are displayed separately from V1–V5.

## Revision replay — readiness-feasibility Level 2 (V9, 2026-08-31)

The V6 note above fixed *where* the no-start conditioning was applied. It did
not fix the two things this chart had shown from the beginning: the first
forecast of a hiatus was far too early, and the median then receded about one
day per day for as long as the hiatus lasted. V9 addresses both, and the
diagnosis turned out to be a single mechanism seen twice.

### The mechanism

Conditioning on continued non-publication moves the median at a rate set by the
hazard, `d(median)/da = h(a)/h(median)`. A distribution whose hazard falls must
therefore recede *faster* than the calendar advances. V8's shifted-lognormal
Level 1 — `log(G + 0.5)` fitted to a sample containing three zeros — has
`mu = 3.20`, `sigma = 1.76`: a median of 20 issues and a very heavy tail. Its
hazard falls across the whole range where a forecast lives, so its day-one
answer was too early *and* it had to recede at more than one day per day. The
same parameter did both.

`scripts/backtest_conditional_prior.py` was written to measure exactly this,
leakage-free, over the 11 rolling-origin batches: 1.56 issues of recession per
issue waited for the lognormal, 0.61 for the kernel mixture, with day-one
medians of 15 and 53 issues. See `docs/backtest.md`, Result 6.

### What the replay shows

187 V9 snapshots were written alongside the earlier series, at run id 23:55 UTC.
No earlier snapshot was overwritten. For batch 49 (outcome 2026-06-29):

| as of | V8 median | V9 median |
|---|---|---|
| 2024-12-21 | 2025-03-10 | **2026-07-20** |
| 2025-06-02 | 2025-12-01 | 2026-09-05 |
| 2025-10-08 | 2026-05-30 | 2026-12-12 |
| 2025-11-10 | 2026-06-27 | 2026-12-12 |
| 2026-02-17 | 2026-10-26 | 2027-02-05 |
| 2026-06-14 | 2027-02-19 | 2027-04-23 |

The first forecast moves from sixteen months early to three weeks late. The line
holds flat at 2026-12-12 through the whole of October 2025 — a stretch the V8
line spent receding — and steps *earlier* at the reports of 2025-10-08 and
2026-02-17. Overall recession falls from 1.28 to 0.54, and movement during
silence from 1.8 days per day to 0.3.

### What it costs, said plainly

V9's mean absolute error over the batch-49 trajectory is **worse**: 180 days
against V8's 121, and CRPS 17.98 against 13.69. The reason is visible in the
table. V9 starts near the truth and recedes past it, so it is late for most of
the hiatus. V8 started sixteen months early and crossed the truth somewhere in
the middle, which flatters any error averaged over a trajectory. A model that is
right on day one and drifts late is not obviously worse than one that is wrong
on day one and passes through the answer on its way to being wrong again — but
the scores prefer the second, and that should be recorded rather than hidden.

The residual recession of ~0.55 issues per issue waited is what sixteen observed
gaps support. Rising-hazard families were fitted to try to remove it and were
rejected on CRPS; it is not a bug left in.

### Where the signal actually was

The most uncomfortable finding of the replay. Through the whole batch-49
hiatus, V8's batch-48 all-pairs component sat within about a week of the correct
answer — centre 2026-06-01 to 2026-07-01 against an outcome of 2026-06-29 — for
eighteen consecutive months. It was averaged away, because components were
rescaled to peak height 1 before averaging, so the sharp and wrong batch-47
component (centre 2024-11-25, sigma 53 days) dominated the vague and right one
(sigma 250 days) wherever the two disagreed. The model had the answer and its
combination rule discarded it.

V9 does not recover that by fixing the weighting. It abandons the
date-translation form entirely, because the same form is what makes a
production report read as bad news when it arrives later than an analog
expected. See `docs/model.md`, "Readiness-feasibility Level 2".
