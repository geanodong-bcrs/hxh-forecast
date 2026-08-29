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
