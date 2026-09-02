# How the Prediction Is Made

> **The live model is V11** — see "Two-sided ordered readiness (V11)" at the end
> of this file. Everything from here to that section is the historical record of
> V1–V8 and is kept unchanged so every forecast already written stays
> reproducible. In particular the "Current output (2026-08-28)" block below, with
> its 50.6% on 2026-09-14, is what an earlier model said, not what the site says.

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

#### Worked example (illustrative dates)

Suppose the forecast target is the start of batch `B`.  Three positions in `B`
have usable current reports, and historical batch `h` has reports at matching
positions and sufficiently similar progress coordinates:

| position | current report attained | historical matching report attained | historical batch `h` actually started | implied start from this position |
|---:|---|---|---|---|
| 1 | 1 Aug | 12 May | 1 Jun | 21 Aug |
| 4 | 4 Aug | 4 May | 1 Jun | 1 Sep |
| 7 | 7 Aug | 11 May | 1 Jun | 28 Aug |

For position 1, the historical report preceded `h`'s start by 20 days.  The
translation says: if the current position has the same remaining lag, its 1 Aug
report implies a 21 Aug start:

    1 Aug + (1 Jun - 12 May) = 21 Aug

The three translated dates are **not** three independent forecasts.  They are
three views of one analog batch.  The analog centre is their median, 28 Aug.
Its internal scale is the robust MAD-derived quantity, not the ordinary sample
standard deviation:

    mu_h = median_r implied_start(h, r)

    sigma_h = max(
        1.4826 * median_r | implied_start(h, r) - mu_h |,
        14 days
    )

The factor 1.4826 puts a median absolute deviation on the standard-deviation
scale for a Normal distribution; the 14-day floor prevents a small collection
of unusually similar translated dates from creating a spuriously narrow
component.  Thus this one historical batch contributes a broad component
centred near 28 Aug; it does not multiply three sharp likelihoods together.

At a candidate start date `W`, that component is approximately:

    L_h(W) = exp[-0.5 * ((W - 28 Aug) / sigma_h)^2]

after the stale-analog fade described below.  The direct readiness likelihood
is the average of the components from **all usable historical analog batches**.
Only then is it combined with the historical batch-gap prior.

Batch position and the chapter-progress coordinate are different quantities.
Position `r` is simply the slot within a ten-chapter batch and resets for every
batch (`r = 1, ..., 10`; for batch 49 these are chapters 411–420).  The chapter
coordinate is `C(c,t) = (c - 1) + p(c,t)`, where `p` is the reported
within-chapter progress.  The analog calculation first holds `r` fixed — for
example, position 4 against position 4 — then tests whether the fractional
progress values `p` are close enough to compare.  It does not compare the
absolute values of `C` across different chapter numbers.

Two details are important when interpreting a new production post.  First,
the progress coordinate decides whether a current and historical report are
comparable; it is not itself converted to a number of days remaining.  Second,
a new report can replace the matched state, add or remove a position, and use a
later attained date.  Therefore this analog construction has **no mathematical
guarantee** that a reported completion shifts the analogue centre earlier.  A
completion is favourable feasibility evidence in a physical sense, but this
small-sample date-translation procedure does not yet encode that monotonicity.

This example is the **direct target-batch** term.  The later preceding-batch
extension uses the same calculation with the preceding batch as the current
source and pairs historical batch `h` with the observed start of `h+1`; it is
the weak 10% context term.  It is not a likelihood built from the following
batch's chapters.  Following-batch readiness is preserved in snapshots but,
at this revision, is not yet part of the timing likelihood.

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

### All-pairs coordinate likelihood (2026-08-31)

This revision retains the coordinate mapping above but replaces the
same-position-only Level-2 likelihood.  Every usable chapter-stage or page-log
event is an observed point:

    (C_j, t_j),   C_j = chapter_j - 1 + p_j

For each resolved historical batch start `h`, with first published chapter
coordinate `C_h` and publication date `T_h`, construct all forward pairs from
events publicly observed at or before `T_h`:

    delta_C(h,j) = C_h - C_j
    lag(h,j)     = T_h - t_j

Pairs are retained when `-20 <= delta_C <= 35`.  Negative coordinate distance
is intentional: it represents reported work on later chapters that was already
available before a batch began, i.e. production buffer.

For the current target coordinate `C*`, every current event `e` has
`delta_C* = C* - C_e`.  It is compared to every historical pair from each
historical start with a Gaussian coordinate kernel:

    w(e,h,j) = exp[-0.5 * ((delta_C* - delta_C(h,j)) / 1.0)^2]

The pair implies a candidate target-start date:

    T* = t_e + lag(h,j)

Within each current event, the compatible historical pairs are kernel-weighted.
Current events are then averaged, so a tweet with many extracted rows does not
receive extra total influence.  The resulting mixture is one broad likelihood
component for historical start `h`; its scale is the MAD-derived spread of the
translated pair dates, floored at 21 days.  Finally, the historical-start
components—not individual pairs—are averaged:

    L_all-pairs(W) = mean_h L_h(W)

This makes explicit use of all coordinate pairs while preserving the central
small-sample constraint: many pairs do not create many independent editorial
scheduling decisions.  The usual stale-component fade still makes an overdue
historical component neutral rather than producing a false next-issue spike.

Unlike V4, this likelihood directly admits current evidence from chapters in
the target, preceding, **and following** batches whenever its coordinate
distance lies in the observed support.  The old 90% direct / 10% preceding
blend is retained in the snapshot only as a V4 diagnostic and is not used by
this revision's likelihood.

The coordinate bandwidth (1 chapter), retained distance range, and 21-day
scale floor are provisional design choices.  They must be selected by
leakage-free replay and calibration, not tuned to make one historical curve
look intuitive.

### Initial leakage-free check

`scripts/backtest_level2_coordinates.py` now runs the actual V5 posterior
builder at the final public event before each resolved tweet-era start, while
intercepting its snapshot write in memory.  That is a real leakage-free
comparison against the same builder with the all-pairs likelihood disabled
(Level 1 only); it is not a retrospective fit of the likelihood to the known
start date.

The two currently independent targets are batch 48 (cutoff 2024-10-06) and
batch 49 (cutoff 2026-06-14).  At the fixed live settings V5 improves the mean
CRPS from 26.26 to 22.84 and mean log score from 4.25 to 3.89 relative to that
baseline.  Both observed starts nevertheless fell before V5's 80% interval.
Consequently the test is evidence that the coordinate information helps in
these two cases, **not** evidence that its width or calibration is established.
The defaults remain un-tuned; see `docs/backtest.md` for the full result.

### Continuous no-start conditioning (V6, 2026-08-31)

V5 made an invalid distinction between a day with a new tweet and a day with no
tweet: on the latter it could retain probability on WSJ issues already known to
have passed.  When the next tweet arrived, all of that overdue mass was removed
at once.  The dramatic August 2025 change in the historical figure was the
result — it was not evidence that `No.413 背景指定完了` delayed publication.

V6 separates the two updates.  At every forecast timestamp `t`, the posterior
is restricted to issues after the last issue publicly known not to contain the
batch:

    P(W | E_t, W > F_t) ∝ P(W | E_t) · I(W > F_t)

where `F_t` is the last observed eligible WSJ issue.  This is a factual
publication update, so it occurs even during silence.  The all-pairs production
evidence remains derived from the tweets themselves; no silence is reclassified
as a production-stage event.  The stale-analog robustness fade uses this same
continuously advancing no-start floor, causing an overdue analog to become
neutral gradually rather than only when a later tweet happens to arrive.

The historical chart's solid line is therefore now expected to move gradually
between tweets.  Its dashed comparison line holds the last event-time posterior
fixed; the separation represents continued non-publication, not a new judgment
that Togashi's production slowed.  Snapshots declare
`all_pairs_coordinate_likelihood_v6_continuous_no_start`, the date through
which no-start conditioning was applied, and the last production-event date.

### Predecessor gate for the following batch (current V6 work)

The forecast for the batch after the direct target has a different information
state. If batch `X` has not started publishing, batch `X+1` is conditional on
both the unknown start of `X` and on WSJ deciding that `X` is a continuing run,
not a one-batch return. Treating it as an ordinary convolution with the full
historical gap prior quietly grants the historical immediate-continuation mode
before there is any public evidence of that commitment.

Let `G` be the issue gap after batch `X` ends. The secondary forecast remains:

    S_(X+1) = S_X + 9 issues + G,

but, while `X` has not publicly started, its gap prior is conditioned on a
positive gap:

    P_pre(G=g) = P(G=g | G>0).

This removes only the data-derived `G=0` back-to-back mode (currently 13.3% of
the cluster-weighted modern-era prior); it does not choose or invent a longer
hiatus length. Once `X` begins, `X+1` becomes the direct next-batch target and
uses the ordinary Level 1 + Level 2 model. The resulting jump is intentional:
uncertainty about the predecessor and its publication commitment has resolved.

This gate applies only to the following-run distribution. It does not alter the
primary batch-start posterior or reinterpret production events. It is a
conservative structural prior, pending backtests with more independently
resolved publication runs.

### Conditional following-run display (current V6 work)

The predecessor gate alone still leaves a moving marginal date for `X+1`,
because any movement in the unresolved start of `X` propagates through

    S_(X+1) = S_X + 9 issues + G.

That marginal is mathematically valid but not a useful standalone promise to a
reader. While `X` has not started, the site therefore does **not** display a
publication-date history, density, or headline median for `X+1`. It instead
shows three conditional scenarios: if `X` begins at the 10th, 50th, or 90th
percentile of its direct forecast, the implied median and 80% interval for
`X+1` are shown using the positive-gap distribution.

When `X` starts publishing, `X+1` becomes the direct target. Only then does the
site begin its ordinary probability history and headline forecast. This changes
the display and scope of the secondary forecast; it does not change the primary
posterior for `X`.

### Buffer-mixture following-run model (current V6 work)

The conditional-display experiment above is retained as an earlier design. The
current working model restores the full following-run history, but changes its
prior from a fixed gap distribution to a conservative two-mode mixture:

    P(G) = q(t) I(G=0) + [1-q(t)] P(G | G>0).

The first term is the historical back-to-back-continuation mode; the second is
the historical positive-gap (hiatus) mode. `q(t)` is **not** interpreted as a
publisher promise. It is the model's weight on a continuation-ready production
buffer:

    q(t) = pi_0 + (0.45 - pi_0) * B(t),

where `pi_0 = 0.133` is the cluster-weighted historical immediate-continuation
frequency, and `B(t)` is the mean readiness coordinate across the ten chapters
of the following batch (zero for no public work; approaching one only for a
visible late-stage buffer). The 45% cap leaves the long-gap mode dominant even
when all ten chapters appear advanced, because Togashi's posts do not reveal
WSJ editorial scheduling intent.

The expected history is therefore event-responsive rather than merely
translated: following-batch production reports raise the early-mode weight and
can move probability earlier; ordinary silence does not raise that weight. The
unresolved predecessor start still propagates through the timing calculation,
so this is not a claim that all gradual movement disappears. The model records
`B(t)`, the baseline and current continuation weights, and the chapter count
behind them in every snapshot. This is an explicitly provisional structural
assumption, not a fitted publisher-behavior model.

### Direct two-gap following-run prior (current V7 work)

The buffer-mixture design is retained above as the prior V6 design. V7 replaces
it for a batch that is still two publication runs away. Rather than convolving
two independently fitted one-gap variables, it models their observed adjacent
sum directly:

    H_i = G_i + G_(i+1).

The modern-era data currently supplies the 15 chronological two-gap outcomes:

    88, 28, 69, 50, 56, 56, 0, 105, 185, 126, 64, 40, 206, 268, 157.

These pairs overlap and are consequently not fifteen independent experiments;
they are nevertheless the directly relevant empirical trajectories for the
question "when does the batch after next begin?". V7 smooths this empirical
distribution with the same 60-issue discrete Gaussian kernel used by the
one-gap positive component, on `H = 0..280`. The bound 280 is deliberately
pragmatic: it is just above the largest observed two-gap value, 268. It is not
backtest-selected.

Before predecessor batch `X` begins, let `a` be the number of known eligible
issues after the preceding batch's end that did not carry `X`. The two-gap
prior is conditioned on historical pairs whose first component can have
survived that long:

    P(H=h | G_1 >= a).

If no historical pair survives this conditioning, the broad unconditional
two-gap prior is truncated to `H >= a`. The snapshot explicitly records that
fallback; it is an extrapolation rather than an inferred speed change.

For ten-chapter batches, the start of the following batch is then:

    S_(X+1) = E + H + O_9 + 2,

where `E` is the issue of the earlier batch's end and `O_9` is the empirical
within-batch offset from its first to tenth chapter. Consequently, as long as
`X` has not begun, `X+1` cannot begin for at least another ten eligible issue
slots. Removing dates that violate this constraint is a factual publication
update, not an inference from silence.

V7 deliberately does not use the following batch's production events a second
time in this secondary calculation. The previous all-pairs target likelihood
can admit those events when forecasting `X`; using them again to modify a
separate `G_2` mixture double-counted the same public evidence. A future
production-informed two-gap likelihood must be trained directly on historical
two-gap outcomes and used once.

### Smooth-zero-gap sensitivity variant (current V7 experiment)

This retained V7 variant removes the special point mass at zero. The one-gap
prior is a single kernel-smoothed distribution over `G = 0..200`:

    P(G=g) proportional to sum_i w_i exp[-0.5 ((g - G_i) / 60)^2].

The direct two-gap prior applies the same construction to `H = G_1 + G_2` on
`0..280`. Thus zero is still present in the data but is no longer a distinct
continuation regime; its kernel spreads some mass to nearby short positive
gaps. With the current data, the one-gap probability at exactly zero falls from
the separated-mode 13.3% to about 0.6%.

This is intentionally a sensitivity experiment, not a claim that short
unobserved hiatuses have occurred. It lets the historical prediction figure
show how strongly the sharp continuation mode is driving the forecast. The
same censoring rule `G_1 >= a` and the ten-issue physical floor still apply to
the direct two-gap forecast.

### Parametric Level-1, event-anchored analog fade (V8 experiment)

V8 returns to the V6-style following-batch convolution but changes only Level
1. A single shifted-lognormal latent gap is fitted at every forecast cutoff:

    log(G + 0.5) ~ Normal(mu, sigma^2).

The fitted continuous distribution is discretized into issue bins. Zero is the
first bin, not a separate point mass. Only gaps whose publication outcomes were
known by that cutoff enter the fit; rolling-origin replay therefore does not
use later gaps.

The direct production likelihood remains the all-pairs coordinate likelihood.
V8 separates its two uses of passing time: every observed WSJ issue still
removes impossible start dates from posterior support, but the stale-analog
fade is anchored at the last public production event and held fixed until the
next such event. Once the elapsed gap exceeds the historical maximum, the
record-hiatus rule resumes the continuously advancing fade and its explicit
next-issue component.

This is intentionally an event-responsive display/robustness choice. It does
not claim that a missed issue is uninformative; it prevents the analog
likelihood from being repeatedly weakened by the same kind of non-start
observation between production reports. The following-batch forecast is the
convolution of the predecessor posterior, the within-batch schedule, and the
same parametric one-gap prior. No following-batch production event is reused.

### Readiness-feasibility Level 2 (V9, 2026-08-31)

V9 replaces both halves of the model that produced the shape the history chart
kept showing: a first forecast far too early, then a median receding about one
day per day until the run finally began, with production reports barely moving
it — and moving it *later* when they did.

#### Level 1: the parametric prior is off

The V8 shifted-lognormal is reverted to the kernel mixture (point mass at gap 0
plus a 60-issue KDE on `g >= 1`, cluster-weighted) that Result 4 of the
backtest had already selected.

The reason is a hazard argument. What the site displays during a hiatus is not
`P(G)` but `P(G | G >= a)`, and conditioning moves the median at a rate

    d(median)/da = h(a) / h(median).

A distribution whose hazard *falls* has `h(a) > h(median)` and must therefore
recede faster than the calendar advances. Fitting `log(G + 0.5)` to a sample
containing three zeros put `mu` at 3.20 and `sigma` at 1.76 — median 20 issues,
very heavy tail, falling hazard across the whole range the forecast lives in.
`scripts/backtest_conditional_prior.py` scores that conditional family
leakage-free over 11 rolling-origin batches and measures the consequence
directly: **1.56 issues of recession per issue waited, against 0.61 for the
mixture, with a day-one median of 15 issues against 53** (docs/backtest.md,
Result 6). The two complaints are one defect seen at two moments.

Rising-hazard families (gamma, Weibull with shape > 1) were fitted for exactly
this reason and rejected: they hold drift near 0.7 but lose more in CRPS and
coverage than they recover. Recency weighting was retested on the conditional
family and again loses on CRPS, though it does move the forecast in the
conservative direction. Both are recorded rather than adopted.

#### Level 2: one monotone state, used as a floor

The all-pairs coordinate likelihood (V5–V8) turns each production event into an
implied start date by adding a historical event-to-start lag. Two consequences
follow from that form:

* a report arriving later than the analog expected pushes the forecast **later**,
  so a finished page — physically always progress — usually reads as bad news;
* components were averaged after being rescaled to peak height 1, so an
  analog's weight was proportional to its own vagueness. In the batch-49 replay
  the batch-47 component (centre 2024-11-25, sigma 53 d) and the batch-48
  component (centre 2026-06-22, sigma 250 d) entered the average at a 1:4.7
  mass ratio purely because one was sharper than the other — and the batch-48
  component was sitting within a week of the eventual outcome for eighteen
  months while the average ignored it.

V9 summarises the target run by a single **monotone** state instead:

    B(t) = mean over the run's ten chapters of the furthest observed
           within-chapter progress, zero where nothing has been reported.

`B` cannot decrease, so at equal calendar time more production always implies
an earlier forecast. That is what "a production report can only move the date
earlier" has to mean once the calendar is held fixed; a strictly flat trajectory
between reports is not available, because a report that arrives late genuinely
*is* evidence of slowness.

Measured at the three resolved tweet-era starts, `B` is remarkably stable:

| run | B at its start | reached B = 0.90 | lead before starting |
|---|---:|---|---:|
| 47 | 0.902 | 2022-10-18 | 6 days |
| 48 | 0.902 | 2024-09-24 | 13 days |
| 49 | 0.900 | 2026-02-24 | 125 days |

so "essentially every manuscript finished" is close to the go condition, and
the 6-to-125-day spread above it is the editorial decision the model cannot
see. Production is therefore used as a **floor**, not as a date. For each
analog `h`, `scripts/build_feasibility.py` builds the empirical remaining-time
curve from events public before `h` started,

    R_h(b) = start[h] - (first date at which B_h reached b),

and at forecast time, with the run at level `b` first attained on a known date,

    still_required_h = max(0, R_h(b) - days already spent at level b)
    floor_h          = today + still_required_h
    L(W)             = mean_h  Phi( (W - floor_h) / 30 days ).

One analog is one component, per the correlation rule. The ramps are averaged,
not multiplied, so three analogs cannot compound into a hard wall. When the
required work is already done the term is inert and says so, rather than
inventing a start date from three past runs — which is the honest description
of most of batch 49's hiatus, and matches the project's own finding that
production is not the bottleneck.

#### What it does to the trajectory

`scripts/backtest_trajectory.py` replays the real posterior builder across the
whole gap preceding each resolved start. For batch 49 (outcome 2026-06-29):

| model | first forecast | drift | median moved per quiet day | mean \|error\| |
|---|---|---:|---:|---:|
| V8 (live until now) | 2025-03-10 | 1.28 | 1.8 d | 121 d |
| V9 | **2026-07-20** | **0.54** | **0.3 d** | 180 d |

The first forecast of the hiatus moves from sixteen months early to three weeks
late; the recession halves; and the trajectory now has flat stretches — it holds
at 2026-12-12 through all of October 2025, and steps *earlier* at reports on
2025-10-08 and 2026-02-17. Batch 48 behaves the same way (first forecast
2023-03-08 → 2024-06-14, drift 0.94 → 0.62).

**The cost is stated plainly: mean absolute error gets worse, and CRPS with it**
(13.69 → 17.98 on batch 49). V9 starts near the truth and then recedes past it,
so it is late for most of the hiatus; V8 started far too early and crossed the
truth in the middle, which flatters an error averaged over the trajectory. The
remaining recession of about 0.55 issues per issue waited is what sixteen
observed gaps support; it is not removable by choosing a different family.

#### Consequence for the live number

The change is large and public. For ch. 421, at the same evidence:

| model | median | 80% interval | P(next issue, 2026-09-14) |
|---|---|---|---|
| V8 | 2026-12-07 | 2026-09-21 .. 2027-12-10 | 4.4% |
| Level 1 fix only | 2027-04-30 | 2026-09-14 .. 2028-11-21 | 23.9% |
| Level 1 fix, no Level 2 | 2027-12-14 | 2026-09-14 .. 2029-08-18 | 13.3% |
| **V9** | **2028-04-18** | 2027-03-19 .. 2029-10-06 | **0.9%** |

A 2028-04 median is a gap of about 82 issues on a run ending 2026-09-07, which
sits between the two most recent observed gaps (84 and 73). The V8 answer
required a 13-issue gap, shorter than anything since 2018. The feasibility floor
supplies the last four months and nearly removes the immediate-continuation
mode, because batch 50 stands at `B = 0.78` and no observed run has begun from
that level without another 47 to 261 days.

#### Known weakness of B

`B` counts a chapter Togashi has not posted about as zero, so it is a **lower
bound** on true readiness, and the feasibility floor is correspondingly
pessimistic whenever he posts less. The bias partly cancels — analogs are
measured on the same lower-bound scale — but it does not cancel if his posting
behaviour changes. The level is recorded in every snapshot and shown on the
method page so the assumption is visible rather than buried.

#### Not done, and the highest-value next step

Once `B` reaches the go level the term goes inert and the forecast reverts to
the historical gap prior, which is why V9 still recedes to ten months late by
the end of a long hiatus. The three resolved runs started 6, 13 and 125 days
after reaching `B = 0.90` — all far shorter than the prior's remaining median at
that point. Turning that into a **two-sided** readiness term (a hazard
multiplier once the run is demonstrably ready, rather than a floor) is the
obvious next improvement, and the one most likely to fix the late-hiatus
overshoot. It rests on three observations, so it needs a fourth resolved run,
or an explicitly stated prior, before it can be shipped.

### Ordered readiness and shared cadence (V10, 2026-09-01)

V10 keeps V9's central decision: production is a one-sided feasibility signal,
not a translation from tweet dates to publication dates. It changes the state
used by that signal and the conditional within-batch schedule.

#### Ordered, retouch-free batch readiness

The reader-facing progress chart and the statistical model now use the same
derived state. For chapter `c`, `p_c(t)` is the furthest explicit production
coordinate at time `t`, with retouch excluded. Let `A_c(t)` indicate any usable
production report and `M_c(t)` an explicit manuscript-complete report. Define

    q_c(t) = min(1, max(
        p_c(t),
        0.5 * I(any later chapter has a production report),
        1.0 * I(any later chapter is manuscript-complete),
        1.0 * I(c is the tenth chapter and it is manuscript-complete)
    ))

and

    B(t) = sum_c q_c(t),       0 <= B(t) <= 10.

`B` is measured in chapter-equivalents. Dividing it by ten would change only
the units, not the information or posterior, provided every historical curve
were rescaled consistently.

The order constraints are lower-bound imputations, not new observations. Every
forecast snapshot records the direct coordinate, inferred floor, and resulting
ordered coordinate separately. A later-chapter report establishes that earlier
chapters have at least completed character inking; a later manuscript completion
establishes that earlier chapters have completed the simplified first-pass
pipeline.

Retouch is omitted from this coordinate. It can occur at many points after
inking and can cause a stage to be reported complete a second time. Those later
re-completions do not refute the first-pass chapter ordering and must not create
a later attainment date for readiness.

At the three resolved starts, the ordered sum is 9.1 for batch 47, 9.5 for batch
48, and 10.0 for batch 49. The current ch. 421–430 run is 8.7 as of 2026-09-01.
These values replace V9's old 0–1 mean-readiness figures; old forecast snapshots
remain unchanged and reproducible.

#### Threshold-crossing feasibility

For historical analog `h`, readiness is replayed using only reports public by
its start date. The relevant attainment time is a threshold crossing:

    T_h(b) = inf {t : B_h(t) >= b}
    R_h(b) = S_h - T_h(b).

At forecast time the current run's own `T_now(b)` determines how long it has
already spent at or above `b`. Each analog supplies one soft feasibility ramp;
the three ramps are averaged rather than multiplied. Thus the independent
evidence count remains three production regimes, not ten chapters or hundreds
of posts.

#### One cadence regime per batch

The old Level 3 schedule assigned an independent 1.4% extra-issue probability
to each chapter transition. That independence assumption is contradicted by the
record: both non-consecutive modern intervals occurred in the same completed
batch. V10 instead draws one shared schedule regime:

    P(regular batch)   = 14/15
    P(disrupted batch) =  1/15.

The regular regime advances one eligible WSJ issue per chapter. The disrupted
regime replays the only observed pattern: one extra issue before position 6 and
another before position 9. This is intentionally empirical. One disrupted run
cannot support a fitted distribution over the number or placement of delays.

Uncertainty in the batch start remains shared by all ten chapters, and schedule
uncertainty is now shared as well. The chapters are conditional marginals of one
batch process, never ten independent release forecasts.

#### Validation status

V10 is a structural revision motivated by the corpus and by the known missing-
report bias in V9. Its Level 2 component still has only three resolved analog
starts. Historical readiness paths and the full forecast trajectory must be
rebuilt and compared with V9 without treating multiple dates from one hiatus as
independent outcomes. Until another run resolves, any apparent score improvement
is weak evidence and the feasibility ramps must remain broad.

A 21-day trajectory replay gives the following diagnostic results:

| target | first median | drift | mean absolute error | mean CRPS |
|---|---|---:|---:|---:|
| batch 48 | 2024-07-19 | 0.55 | 233 days | 20.72 issues |
| batch 49 | 2026-07-27 | 0.52 | 183 days | 18.21 issues |

These are correlated trajectory diagnostics for two outcomes, not independent
validation cases. Compared with documented V9, ordered readiness changes the
path modestly but does not establish an accuracy improvement. V10 is adopted
for state validity and interpretability, not because two historical trajectories
prove superior predictive performance.

### Two-sided ordered readiness (V11, 2026-09-02)

V10 corrected the readiness state but used it only as a lower feasibility
boundary. Once all three ramps became flat, Level 2 assigned the same relative
compatibility to a date six months away and a date three years away. The broad
Level-1 hiatus prior therefore produced a 2028 median even though no resolved
batch had remained at comparable readiness for more than 160 days.

V11 retains V10's ordered, retouch-free `B(t)` and shared within-batch cadence.
It replaces the one-sided ramp with a two-sided analog mixture. At readiness
`b`, historical batch `h` supplies

    T_h(b) = first date B_h reached b
    R_h(b) = S_h - T_h(b)
    m_h(t) = T_now(b) + R_h(b).

The readiness likelihood is

    L_ready(s) = mean_h NormalKernel(s; m_h(t), 120 days).

The 120-day component scale is a declared conservative setting, not an
estimated standard error. Three historical starts cannot identify a precise
tail or justify narrow components. Components are averaged rather than
multiplied, so the evidence count remains three batch regimes.

At `B=8.7` on 2026-09-02, the analog centres are 2026-09-13, 2026-12-03,
and 2027-02-08. Combining their broad mixture with Level 1 gives a median of
2026-11-09 and an 80% interval of 2026-09-14 through 2027-05-14. The long
historical hiatus tail remains possible but no longer controls the median after
the production state has become highly advanced.

#### Replay result and limitation

A 21-day trajectory replay gives:

| target | first median | drift | early share | mean absolute error | mean CRPS |
|---|---|---:|---:|---:|---:|
| batch 48 | 2023-02-01 | 1.44 | 37% | 180 days | 17.25 issues |
| batch 49 | 2025-01-27 | 1.55 | 73% | 198 days | 18.52 issues |

This does not establish an accuracy improvement over V10. In particular, a
newly attained readiness level can move an implied centre later if the report
arrives much later than the historical analog reached it. The current forecast
is much more consistent with the cross-sectional readiness evidence, but the
trajectory results show that the dynamic update rule remains provisional. With
only two resolved replay targets, selecting the 120-day width or adding a
monotonicity correction based on these scores would be overfitting.
