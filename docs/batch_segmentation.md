# Batch Segmentation — **settled**

The open questions below were answered on 2026-08-27. The decisions are now
written into `Agents.md` §3 (batch definition) and §6 (modeling era, recency
weighting), and implemented in `scripts/build_chapter_dataset.py`.

Current rule, in three parts:

1. A **run** breaks when 4 or more WSJ issues elapse without a chapter.
2. Runs longer than 15 chapters are split into **10-chapter batches**.
3. Only chapters **261 onward** (2007+) feed the prior; earlier chapters are kept
   and flagged `modeling_era = 0`.

The sections below record the reasoning that led there, and are kept as the
audit trail rather than rewritten.

## Why a threshold is needed at all

Hunter × Hunter has two clearly different publication regimes, and no single
threshold serves both.

### The weekly regime (1998–2006, chapters 1–260)
Serialized more or less weekly with frequent short breaks of one to a few weeks.
"Batch" is not a meaningful concept here — the gaps are ordinary weekly-manga
irregularity, not scheduled runs. The threshold of 4 chops this era into 15
arbitrary segments of wildly varying size (38, 13, 2, 35, 13, 26, 18, 3, 66, 1,
6, 2, 32, 1, 4). Those numbers are artefacts of the cutoff, not structure.

### The burst regime (2007–present, chapters 261–418)
After the 2006–2007 hiatus the pattern changes completely: a run of consecutive
weekly issues, then a long silence. 13 such runs so far.

| batch | chapters | n | start | gap before (issues) |
|---|---|---|---|---|
| 16 | 261–270 | 10 | 2007-10-06 | 80 |
| 17 | 271–280 | 10 | 2008-03-03 | 10 |
| 18 | 281–290 | 10 | 2008-10-06 | 20 |
| 19 | 291–310 | 20 | 2010-01-04 | 51 |
| 20 | 311–340 | 30 | 2011-08-08 | 57 |
| 21 | 341–349 | 9 | 2014-06-02 | 106 |
| 22 | 350–360 | 11 | 2016-04-18 | 81 |
| 23 | 361–370 | 10 | 2017-06-26 | 47 |
| 24 | 371–380 | 10 | 2018-01-29 | 19 |
| 25 | 381–390 | 10 | 2018-09-24 | 23 |
| 26 | 391–400 | 10 | 2022-10-24 | 185 |
| 27 | 401–410 | 10 | 2024-10-07 | 85 |
| 28 | 411–418 | 8+ | 2026-06-29 | 74 |

In this regime the threshold barely matters: between-batch gaps are 10–185
issues while within-batch gaps are almost always exactly 1, so any cutoff from
about 3 to 9 produces the same segmentation.

## What the data already says

**Within-batch publication is near-deterministic.** Of 145 within-batch
intervals since 2007, **143 are exactly one issue (98.6%)**. The only two
exceptions are both inside batch 21 (2014). This is strong empirical support for
the Agents.md §3 decision to make batch-start the primary target and treat the
within-batch schedule as a tightly-constrained conditional — the uncertainty
really is concentrated in *when the run begins*.

**Batch size clusters hard at 10.** Ten of thirteen modern batches are 10, 9, or
11 chapters. The exceptions are batches 19 (20) and 20 (30) — and those look like
two and three 10-chapter runs published back-to-back without a qualifying gap,
rather than genuinely longer batches. Whether to split them is a real modelling
question, not a threshold-tuning question.

## Open questions for Phase 1B

1. **Restrict the model to the burst regime?** The 1998–2006 era may be a
   different data-generating process entirely. Including it would contaminate
   the batch-start prior. Recommendation: fit on 2007+, and use the early era
   only for questions where it is clearly relevant.
2. **Split batches 19 and 20?** If they are back-to-back 10-chapter runs, batch
   size is far more stable than the raw table suggests, and the count of batches
   available for fitting rises from 13 to ~16.
3. **Should batch size be modelled, or is 10 effectively a constant?** This
   matters for the §15 ten-chapter forecast: if a batch is 10 chapters, then
   chapters beyond the current batch's end require forecasting the *next* batch
   start too — a second, much wider layer of uncertainty that must not be hidden.
4. **Is the gap distribution stationary?** Gaps since 2014 (106, 81, 47, 19, 23,
   185, 85, 74) look different from 2007–2011 (80, 10, 20, 51, 57). With 13
   observations this is hard to establish, and it is the single biggest driver of
   the prior's width.

That last point deserves emphasis: **the entire batch-start prior rests on 13
observations.** Sharpness will have to come from the production-evidence layer
(§10–13), not from the historical prior.

## Human0 answers to the open questions for Phase 1B
1. Yes. Please ignore 1998-2006 era data. These data are valuable though. We may use them for calculating and visualizing some statistics later. We may discover a trend/pattern in the data when working on the batch-start prior. 
2. Yes. We can treat them as multiple 10-chapter batches with no waiting time.
3. To simplify the problem, probably no. Doing #2 is easier and cleaner.
4. Probably not. I'm thinking about putting weights on the data (or something else) so that most recent data will have more influence on the prediction. Let me know what you think.

---

## Settled state, after those answers

### What the data looks like now

Splitting runs 19 and 20 raises the modeling era from 13 batches to **16**, and
makes batch size far more stable: 14 of 16 are exactly 10 (the exceptions are the
9-chapter 2014 run and the 11-chapter 2016 run; batch 49 is at 8 and still open).

| batch | chapters | n | start | gap before (issues) |
|---|---|---|---|---|
| 34 | 261–270 | 10 | 2007-10-06 | 79 |
| 35 | 271–280 | 10 | 2008-03-03 | 9 |
| 36 | 281–290 | 10 | 2008-10-06 | 19 |
| 37 | 291–300 | 10 | 2010-01-04 | 50 |
| 38 | 301–310 | 10 | 2010-03-20 | **0** |
| 39 | 311–320 | 10 | 2011-08-08 | 56 |
| 40 | 321–330 | 10 | 2011-10-24 | **0** |
| 41 | 331–340 | 10 | 2012-01-16 | **0** |
| 42 | 341–349 | 9 | 2014-06-02 | 105 |
| 43 | 350–360 | 11 | 2016-04-18 | 80 |
| 44 | 361–370 | 10 | 2017-06-26 | 46 |
| 45 | 371–380 | 10 | 2018-01-29 | 18 |
| 46 | 381–390 | 10 | 2018-09-24 | 22 |
| 47 | 391–400 | 10 | 2022-10-24 | 184 |
| 48 | 401–410 | 10 | 2024-10-07 | 84 |
| 49 | 411–418 | 8+ | 2026-06-29 | 73 |

Gap-before-batch, sorted: `0, 0, 0, 9, 18, 19, 22, 46, 50, 56, 73, 79, 80, 84, 105, 184`

### The consequence worth naming

**The gap distribution is now bimodal**, and deliberately so. Three of sixteen
batches follow the previous one with *zero* wait. The prior must be a mixture —

    P(gap = 0)     ~ 3/16, the batch continues straight on
    P(gap = long)  ~ 13/16, spread from 9 to 184 issues

— not a single unimodal distribution. Fitting one smooth distribution over
`0, 0, 0, 9, ..., 184` would produce a shape that describes none of the actual
behaviour. This is the most important structural consequence of decision #2.

All three zeros are from 2010–2012. Whether the "continue straight on" mode is
still live in the current regime, or is an artefact of a period that ended
fourteen years ago, is a real question — and one the recency weighting below will
answer implicitly by nearly zeroing those observations out. That interaction
between decisions #2 and #4 should be checked, not assumed.

### On recency weighting (answer to #4)

Weighting is the right instinct, and better than the alternatives. With 16
observations, fitting an explicit trend or a changepoint would overfit badly;
weighting degrades gracefully instead of inventing structure.

Three conditions on it:

1. **Choose the decay by backtesting, not by taste.** The decay rate is a
   hyperparameter. Fit several, including no decay at all, and pick by
   out-of-sample calibration and sharpness. This is also the honest test of
   whether recency helps at all — it may not.
2. **Report effective sample size.** For weights `w`, `n_eff = (Σw)² / Σw²`.
   With 16 observations, a half-life of ~3 batches drops `n_eff` to roughly 5.
   Past some point, downweighting widens the posterior faster than it corrects
   for drift, and you have paid sharpness for nothing.
3. **Compute weights as of the forecast timestamp.** In a backtest, a forecast
   made in 2018 must weight by recency *relative to 2018*. Applying today's
   weights to a historical forecast is leakage, and a subtle kind that will not
   announce itself.

A reasonable starting grid: exponential decay with half-life ∈ {∞ (no decay), 8,
5, 3 batches}. Decay in **batches**, not calendar years — the hiatuses are so
uneven that calendar decay would penalise the 2022 and 2024 batches for the
series' own inactivity.
