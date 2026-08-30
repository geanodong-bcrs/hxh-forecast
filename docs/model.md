# How the Prediction Is Made

State as of 2026-08-28. Target: **W_b**, the on-sale date of a batch's *first*
chapter (Agents.md §3). Everything else is derived from it.

```
chapters.csv  wsj_issues.csv          production_events.csv
        |                                     |
   build_batch_prior.py                 build_level2.py
   LEVEL 1: P(W_b | history)            LEVEL 2: analog likelihood
        |                                     |
        +----------- build_posterior.py ------+
                            |
              posterior + ten-chapter forecast
              -> data/forecasts/*.json (append-only)
```

`backtest_prior.py` selects the hyperparameters. Snapshots are never
overwritten (§16), so the record of what the model believed on a given day
survives being wrong.

---

## Level 1 — the historical prior

`P(W_b | publication history)`, from publication records **only**. This script
never reads the tweet corpus, event table or page log. If it did, the Level 2
update would not be an update.

**The observations.** 16 modeling-era batch gaps, in *issues skipped* between
the previous batch's last chapter and the next batch's first:

```
79, 9, 19, 50, 0, 56, 0, 0, 105, 80, 46, 18, 22, 184, 84, 73
```

**Shape: a mixture, not one smooth curve.**

| component | mass | meaning |
|---|---|---|
| point mass at gap = 0 | π₀ ≈ 0.13 | next batch follows with no break |
| Gaussian KDE over gap ≥ 1 | 1 − π₀ | everything else, bandwidth 60 issues |

I tried folding the zeros into a single smooth density on the grounds that
"gap 0" and "gap 1" are nearly the same event and shouldn't differ 29-fold in
probability. **The backtest rejected it** — log score worsened 4.75 → 5.16 and
coverage fell to 73% against 80/90 targets. The discontinuity is carrying real
structure; the two publication modes are genuinely distinct.

**Cluster weighting on the zeros.** Batches 40 and 41 are both zero-gap
continuations of the *same* run (ch 311–340, which our 10-chapter rule chopped
into three). Counting them as two independent "started immediately" events
double-counts one episode. Each run's zeros now share one observation's worth of
weight, dropping π₀ from 0.188 to 0.133. Backtest-confirmed: CRPS 29.54 → 28.75.

**Recency weighting: OFF.** See `backtest.md`. Tried in two parameterisations
(batches, then calendar days) across a grid; no decay beat both on CRPS and log
score. Retained in the code, switched off.

**Calendar.** Candidate gaps map to real WSJ issues, projected forward by
replaying one year — **49 issues, not 52** — of gap structure, so combined
issues stay roughly in place.

---

## Level 2 — production evidence, by analogy

Every production event on **any** chapter of a batch is evidence about that
batch's *start*, with the lag measured to W_b:

```
ch.396 manuscript_complete 2022-10-18 → batch 47 started 2022-10-24  =  +6
ch.398 retake              2022-11-08 → batch 47 started 2022-10-24  =  −15
```

Negative lags are not errors — they are the publisher starting a run while later
chapters are still in production. How willing they are to do that is precisely
what varies between batches, and it is what the forecast must capture.

**Analogs, not a fitted likelihood.** Production data covers exactly three batch
starts. Fitting `P(gap | production state)` to three points would yield a
confident number that is an artifact of the functional form. Instead each
historical batch is replayed onto current production dates: *if this batch
behaves like batch 47, when does it start?* Matching is on
`(position_in_batch, stage)`; an analog's median implied date is its estimate,
its MAD sets its σ.

Current analogs, replayed onto batch 50:

| analog | implied start | σ |
|---|---|---|
| 47 | 2026-08-27 | 54 d |
| 48 | 2026-08-08 | 101 d |
| 49 | 2027-01-25 | 148 d |

Analogs 47 and 48 imply a start already in the past. That is informative: it
means this batch is *not* behaving like them.

---

## The posterior

```
P(W_b | H, production) ∝ L(W_b | production) · P(W_b | H) · 1[W_b ≥ floor]
```

**The correlation rule (§11) is the load-bearing decision.** Batch 50 has ~28
observed `(position, stage)` events. They are **not** 28 independent
observations — they are one production process seen 28 times. Multiplying them
would give a posterior about a week wide: spectacular and false.

So **each analog contributes one likelihood factor**, summarising its fit across
all events at once. Evidence strength scales with the number of analogs (3), not
events (28). An analog's internal spread sets σ and is deliberately *not* shrunk
by √n.

**Truncation.** The batch demonstrably has not started, so mass below the first
eligible issue is removed and the rest renormalised. Real conditioning, not a
patch. A consequence to anticipate: the forecast slides later every week the
batch does not start. That is correct, and will read to a casual observer as the
model changing its mind.

---

## Ten-chapter forecast (§15)

Within-batch spacing is near-deterministic — 143 of 145 intervals since 2007 are
exactly one issue. Chapter *k* sits at W_b plus *k* issues, with a 1.4% chance of
one extra skipped issue per step, convolved forward.

**These are not ten independent forecasts.** Nearly all of each chapter's
uncertainty is inherited from W_b, exactly as §3 anticipated.

---

## Current output (2026-08-28)

```
W_50 = publication of ch. 421
  median          2026-09-14
  50% interval    2026-09-14 .. 2027-01-15
  80% interval    2026-09-14 .. 2027-05-21
  90% interval    2026-09-14 .. 2027-07-23

  P(started by)   2026-12-31  72%   2027-03-31  85%   2027-06-30  93%
```

**50.6% of the posterior sits on 2026-09-14** — the issue immediately after
batch 49 ends. This survived every check I ran, and I believe it is a real
inference rather than a bug: the likelihood eliminates the prior's long tail
(the analogs agree it will not be 2029), and among what remains the zero-gap
mode dominates a thinly-spread continuum.

It is also **the claim I would least want to defend.** It rests on two clustered
observations from 2010–2012 and asserts an even chance that Shueisha rolls
straight from batch 49 into batch 50 with no break — which has not happened
since 2012, though Togashi does have six chapters finished. It resolves within
about two weeks.

---

## Where this is weakest — candidates for improvement

1. **π₀ rests on two clustered observations from fourteen years ago**, and it
   drives the headline number. The most valuable new information would be
   anything that bears on whether back-to-back batches are still possible.
2. **Level 2 has never been scored against an outcome.** n=3 analogs; §29 step 16
   (baseline vs production-informed) is unanswerable. The component doing most of
   the work in the live forecast is validated only by construction.
3. **The 50% credible interval is over-covered** (64% actual vs 50% target). The
   prior is under-confident in its middle.
4. **Analog weighting is uniform.** A better idea than time decay: weight analogs
   by *capacity similarity*, measured from the page log (≈1.16 pages/posting-day
   in 2022 vs ≈2.07 in 2024). That targets the causal variable — Togashi's
   working capacity — instead of using time as a proxy for it.
5. **Batch 49's end date is assumed**, not announced-and-confirmed: ch. 420 on
   2026-09-07 under the reading that the batch is 411–420. Togashi's 2026-04-08
   post reads literally as *420 onward*, which would shift everything.
6. **Announcement lead time is only 7–13 days**, so announcements close the
   forecast only at the very end. Good for the model's usefulness, but it means
   there is no early-warning signal to exploit.

---

## Level 2 revision — readiness-coordinate analog model (2026-08-30)

This section **supersedes the live Level 2 implementation above**.  The prior
description and the original exact-stage analog model are retained above as a
reproducible record of the first design and of every forecast already written.
The historical Level-1 prior is unchanged.

### Why revise Level 2

The replay revealed a specific failure.  When an analog implied a start well
before the observed non-start floor, its Gaussian tail declined over every
remaining candidate issue.  Truncation then put almost all mass on the first
eligible issue: “this analog failed months ago” was misread as “the batch is
almost certain next week.”  This produced the mechanically declining forecast
before batch 49 began in June 2026.  It is a model error, not a chart effect.

The corpus also contains substantially more information than an exact
`(position_in_batch, stage)` match.  It has page logs, statuses, blocked waits,
retakes, and batch-level name reports.  The revision uses a simple, auditable
coordinate so this information can be compared without fitting a high-
dimensional model to three resolved tweet-era batches.

### Derived chapter coordinate

The immutable event table remains the source of truth.  `build_readiness.py`
derives, rather than writes back, a chapter progress coordinate:

    C(c, t) = (c - 1) + p(c, t),       0 <= p < 1

`c` is the chapter number.  `p` is the furthest observed within-chapter
production progress.  The initial endpoints follow the observed page-log
behaviour and the corpus taxonomy; they are a transparent first specification,
not estimated units of labour.

| observation | p value or interval |
|---|---:|
| manuscript page log | `0.01 × largest observed page`, capped at `0.19` |
| panel borders / speech balloons | 0.30 |
| character inking | 0.50 |
| background specification | 0.60 |
| background work | 0.70 |
| dialogue | 0.80 |
| manuscript complete | 0.90 |
| retouch | 0.99 |

An explicit `complete` report fixes its endpoint.  `started`, `in_progress`,
waiting, and no-status reports create an interval over that stage; the midpoint
is only used to compare analogs.  For example, a page-6 log supplies `p=0.06`,
not an assertion that the preceding production stages were separately reported
complete.

The coordinate is deliberately **not** the whole state.  The snapshot keeps
`awaiting_return`, `under_review`, and `retake` as flags with their latest
dates.  Work can overlap or be revisited: chapter 411 has dialogue complete on
2024-11-17 and background specification complete on 2024-11-18; chapter 398
has retouch in progress before a later dialogue-complete report.  Therefore
the coordinate means “furthest observed progress,” not “a strictly serial,
irreversible workflow.”

### Revised analog calculation

For the target batch, retain one readiness state for each of its ten chapter
positions.  For each historical analog batch `h`, reconstruct its states using
only events dated on or before that batch's actual start.  At the same chapter
position, compare current and historical progress coordinates.  Matches whose
progress differs by more than 0.35 are excluded; closer matches receive a
diagnostic compatibility weight.

For every retained position `r`:

    implied_start(h, r)
        = current_attained_date(r)
        + [ actual_start(h) - historical_attained_date(h, r) ]

The analog's centre is the median of its implied starts and its spread is the
MAD-derived scale across positions.  One analog remains one likelihood
component: ten chapter states are not treated as ten independent observations.

This still does not fit a regression of publication time on progress.  With
three resolved batches, an apparently precise fitted relationship would mostly
be its assumed functional form.

### Falsified analogs are neutral

Let `F` be the first issue the batch can still start in, and let a Normal analog
have centre `mu_h` and scale `sigma_h`.  Its probability of surviving continued
non-publication is:

    S_h(F) = P_h(W >= F)

When `S_h(F) < 0.05`, the analog is exhausted.  Its likelihood is replaced by a
flat factor over candidate future issues:

    L_h(W) = 1

rather than its decreasing Gaussian tail.  It then contributes no timing
preference.  This fixes the invalid inference that an overdue analog makes the
next issue near-certain.  If every analog is exhausted, Level 2 is neutral and
the posterior is the truncated Level-1 prior.

The 5% threshold is a declared provisional robustness setting.  It must be
varied in future leakage-free replays and selected only if outcomes justify it.

### Data retained for the next revision

The posterior now records readiness states for both the target batch and the
following ten chapters, plus unassigned batch-level `name` reports.  The latter
are not forced into chapter-specific coordinates because Togashi does not name
their chapter numbers.  They represent pipeline depth:

    N(t) = number of chapters reported at the name/storyboard level

Likewise, later-batch states can be useful evidence of available production
buffer even though WSJ does not require all ten current-batch chapters to be
finished before starting publication.

Neither `N(t)` nor following-batch readiness yet changes the timing likelihood.
There are not enough resolved historical batches to calibrate their effect
without manufacturing certainty.  They are saved at every forecast timestamp
so that the next outcome can test whether they improve analog similarity or
predict batch feasibility.

### Operational status

`scripts/build_posterior.py` is the live implementation of this revision.
`scripts/build_level2.py` is preserved unchanged as the original v1 exact-stage
analog implementation for reproducing historical artifacts; the automated live
update no longer runs it.  Forecast snapshots declare their Level-2 design,
readiness states, progress mapping, analog diagnostics, and any exhausted
analogs so the transition remains auditable.

### Preceding-batch context extension (2026-08-30)

The target batch's own readiness remains the primary Level-2 signal.  Production
in its preceding batch is now added as a weak contextual signal, not treated as
an equal direct timing analog.  Historical comparison pairs source batch `h`
with the observed start of `h+1`; this estimates how a preceding batch's state
related to the next batch beginning.

    L_total(W) = L_same_batch(W)^0.75 * L_preceding_batch(W)^0.25

The 0.25 context weight is provisional and deliberately conservative.  It has
physical meaning: preceding-batch work can reveal capacity and production
buffer, but cannot establish that the next batch is ready.  The original hard
5% exhaustion switch has also become a smooth fade from an analog likelihood
to a flat likelihood as continued non-publication makes that analog stale.

### Event-conditioned no-start update and record-hiatus regime (2026-08-30)

This is the current live refinement.  The preceding-batch term is reduced to
10%, so the timing likelihood is now:

    L_total(W) = L_same_batch(W)^0.90 * L_preceding_batch(W)^0.10

The difference is intentional rather than cosmetic.  The target batch's own
work is evidence about whether that batch can be scheduled; the preceding
batch is only indirect evidence about capacity or buffer.  A later backtest can
change this coefficient, but it must do so through out-of-sample performance,
not because a particular historical chart looks smoother.

The second change fixes a separate meaning problem in the historical graph.
Let `E(t)` be the timestamp of the last public production event at a forecast
time `t`.  The normal non-publication floor is now evaluated only through the
last issue on sale at or before `E(t)`, not through every intervening calendar
week.  Thus, in the absence of a new public production event (or a publication
that advances the prediction target), the distribution is unchanged:

    P(W | evidence at t + silence) = P(W | evidence at t)

The fact that an issue did not contain Hunter × Hunter is known to readers, but
using each additional silent week as a fresh likelihood update made the model
revise its view without a corresponding production observation.  This is
especially misleading while the model is still within the range of historically
observed hiatuses.  The site retains a dashed *event-only* trace as a diagnostic;
for this revision it should coincide with the full trace between public updates.

There is one explicit exception.  If the gap since the preceding batch exceeds
the largest positive inter-batch gap in the 2007-onward training data, the model
enters a **record-hiatus regime**.  It assigns 20% probability to the next
eligible issue and 80% to the ordinary truncated Level-1 long-tail prior:

    P_record(W) = 0.20 * I(W = next eligible issue)
                + 0.80 * P_Level1(W | W >= next eligible issue)

This is not applied during an ordinary silence and it does not replace the long
tail.  It makes the "perhaps next week" intuition explicit only after a delay
outside the observed regime, while still admitting that an unprecedented hiatus
cannot be extrapolated reliably from the three tweet-era analog batches.

Snapshots using this design declare
`readiness_coordinate_context_record_hiatus_v4`, their
`conditioning_through` date, `record_hiatus` flag, and the 0.10 context weight.
Earlier V1–V3 snapshots and documentation remain unchanged.
