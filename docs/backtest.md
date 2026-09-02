# Backtest — Phase 1C

`scripts/backtest_prior.py`. Covers Agents.md §29 steps 14 (rolling-origin),
15 (leakage), 17 (calibration and sharpness) and 18 (select the decay).

## Method

Rolling origin over the 16 modeling-era batch gaps. For each batch *i*, fit the
Level 1 prior on `gaps[:i]` and score the prediction against `gaps[i]`. Training
starts at 5 observations, giving **11 test points**.

Leakage is prevented structurally — the training slice is `gaps[:i]` and the
test point is `gaps[i]` — and an assertion checks it rather than trusting the
slice. Level 1 reads no production data at all, so tweet-side leakage is
impossible by construction.

**Metrics.** CRPS (discrete ranked probability score) and log score are the
proper scoring rules and decide the ranking. Interval coverage checks
calibration against its 50/80/90 targets. MAE of the median is a sanity check
only — a point forecast is not what this model is for.

## Result 1 — recency weighting does not help

| half-life (batches) | CRPS | log score |
|---|---|---|
| **none** | **32.20** | **6.89** |
| 12 | 32.35 | 6.94 |
| 8 | 32.44 | 6.97 |
| 5 | 32.65 | 7.02 |
| 3 | 33.19 | 7.13 |
| 2 | 34.15 | 7.29 |

No decay wins on both rules, and performance degrades **monotonically** with
more aggressive decay. The ordering is identical at all five smoothing
bandwidths tested — 25 cells, same ranking every time. This is a consistent
signal, not a coin flip between close options.

This contradicts the working assumption. Recency weighting was adopted early as
the sensible way to handle possible regime drift, and it was reasonable a
priori. It simply does not survive out-of-sample testing, which is what §6's
"select by backtesting, not intuition" rule exists to catch.

**Why it likely fails.** Half-life is measured in batches, and batch steps span
75 days to four years. Worse, the three zero-gap observations sit adjacent in
the ordering — they are the split of runs 291–310 and 311–340 — so decay treats
one clustered 2010–2012 episode as three separate ages and strips the zero mode
faster than calendar time would justify.

## Result 2 — the smoothing bandwidth mattered far more, and was set wrong

`bw = 8` issues was an unexamined choice, never flagged as a hyperparameter.
It is the **worst** value in the grid.

| bandwidth | CRPS | log score | coverage 50/80/90 |
|---|---|---|---|
| 8 | 32.20 | 6.89 | 55 / 82 / 82 |
| 15 | 31.58 | 5.97 | 55 / 82 / 82 |
| 25 | 30.77 | 5.13 | 55 / 82 / 82 |
| 40 | 29.90 | 4.86 | 64 / 82 / 91 |
| **60** | **29.54** | **4.80** | 73 / 91 / 91 |

Widening it improves log score from 6.89 to 4.80 — a much larger gain than any
weighting choice — and repairs the tail under-coverage. The parameter that was
discussed at length did not matter; the one never mentioned did.

## Result 3 — calendar-time decay is better parameterised, still loses

Decay by batch position is a lumpy unit: one batch step spans 75 days to four
years. Re-parameterising the half-life in **calendar days** is more principled —
the underlying driver (working capacity, health) evolves in real time.

| weighting | CRPS | log score | ESS |
|---|---|---|---|
| **none** | **29.54** | 4.80 | 10.0 |
| calendar 12 yr | 29.59 | 4.80 | 9.6 |
| calendar 8 yr | 29.68 | 4.80 | 9.1 |
| batch 12 | 29.72 | 4.81 | 9.7 |
| calendar 3 yr | 31.01 | 4.80 | 6.3 |
| calendar 1 yr | 36.50 | 4.83 | 2.8 |

Calendar decay does beat batch decay at comparable ESS, so the unit was wrong.
But CRPS still improves monotonically as the half-life lengthens, converging on
no-decay from above.

The reading is not "recency is irrelevant to reality" but "16 observations
cannot detect the drift." Downweighting costs more in variance than it recovers
in bias.

A note on daily re-running: exponential decay in calendar time gives *relative*
weights that do not change as time passes — `wᵢ/wⱼ = 0.5^((tⱼ−tᵢ)/H)` has no
"today" in it. Daily drift in the live forecast comes from the truncation moving
forward, from new production events, and from new gap observations — not from
the decay.

## Result 4 — prior construction: keep the point mass, add cluster weights

Two changes tested against the same 11 points, bandwidth 60:

| construction | CRPS | log score | cov 50/80/90 |
|---|---|---|---|
| **point mass + cluster weights** | **28.75** | **4.75** | 64 / 91 / 91 |
| point mass, no cluster weights | 29.54 | 4.80 | 73 / 91 / 91 |
| single smooth KDE incl. zeros | 29.44 | 5.16 | 45 / 73 / 73 |

**Folding the zeros into one smooth density was rejected.** It was proposed on
the aesthetic objection that "gap 0" and "gap 1" are near-identical events that
should not differ 29-fold in probability. Log score worsened and coverage fell
to 73% against 80/90 targets. The discontinuity carries real structure.

**Cluster weighting was accepted.** Batches 40 and 41 are zero-gap continuations
of the same split run, so each run's zeros share one observation's weight. π₀
falls 0.188 → 0.133, CRPS improves, and the 50% over-coverage eases from 73% to
64%.

## Selected settings

```
recency half-life    none        (no decay, either parameterisation)
smoothing bandwidth  60 issues
prior construction   point mass at 0 + KDE on g>=1
zero handling        cluster-weighted by run
```

## Result 5 — calibration, stated plainly

At the selected settings, actual coverage against targets:

| nominal | actual |
|---|---|
| 50% | **64%** |
| 80% | 91% |
| 90% | 91% |

The 80 and 90 bands are close to right. The **50% band is still over-covered** —
64% of outcomes land inside what should contain half, improved from 73% by the
cluster weighting but not fixed. The prior remains under-confident in its middle.

Point-forecast error is poor and expected to be: **MAE ≈ 47 issues**, roughly
eleven months. Per-point errors at the selected settings run from −155 to +39
issues, and are predominantly negative — the prior systematically **under**-predicts
gap length, having been fit on a history that includes the zero mode and several
short gaps the recent era has not repeated.

## Not fixed, and why

The 50% over-coverage is a genuine defect. It was left alone deliberately: with
11 test points, tuning further would fit noise, and the 16 observations are
better spent as evidence than as a hyperparameter search space. The sharpening
should come from Level 2, not from squeezing Level 1.

## What the Level-1 backtest cannot tell you

## Level 2 — leakage-free coordinate diagnostic (2026-08-31)

`scripts/backtest_level2_coordinates.py` is a separate, leakage-free test of
the V5 all-pairs coordinate likelihood.  It calls the same posterior builder as
the site, but intercepts snapshot writes in memory.  It therefore cannot alter
the append-only public forecast record.

For each resolved tweet-era target, the cutoff is the **last usable production
event before its batch start**.  At that cutoff the replay sees only production
events and publication starts already public then.  The resolved starts are not
made available to the fitted side of the forecast.

| target batch | historical cutoff | resolved WSJ issue sequence |
|---|---:|---:|
| 48 | 2024-10-06 | 1336 |
| 49 | 2026-06-14 | 1419 |

There are only two independent targets.  Earlier time points within either gap
can be useful for plotting forecast evolution, but are correlated forecasts of
the same outcome and must not be treated as additional independent tests.

### Result — evidence helps, but remains too late

At the fixed live V5 settings (coordinate bandwidth 1 chapter, window
−20 to +35 chapters, 21-day robust-spread floor), the average scores are:

| forecast | CRPS ↓ | log score ↓ | 50% coverage | 80% coverage |
|---|---:|---:|---:|---:|
| Level 1 only | 26.26 | 4.25 | 0% | 0% |
| V5 all-pairs coordinate evidence | **22.84** | **3.89** | 0% | 0% |

For batch 48, V5 assigned the realized issue probability 3.16% (Level 1:
1.53%) and had median issue 1359 versus the realized 1336.  For batch 49, it
assigned 1.61% (Level 1: 1.33%) and had median 1453 versus 1419.  Thus the
production evidence moved probability in the right direction relative to the
prior, but both return batches happened sooner than even the V5 80% interval.

A small exploratory grid found a lowest two-target CRPS of 19.94 at bandwidth
2, window −20 to +35, and 14-day floor.  It is **not adopted**: selecting those
settings after looking at two outcomes would be parameter fitting, not
validation.  The documented live settings remain unchanged until more resolved
production-era targets exist.

The honest headline is now narrower than before: Level 2 has a positive,
leakage-free two-target signal versus its own Level-1 baseline, but it is not
yet calibrated and has far too little independent history to establish a
production-to-publication relationship reliably.

---

## The backtest that was missing (2026-08-31)

Both backtests above score the model **once per batch**: `backtest_prior.py` at
the moment the previous run ends, `backtest_level2_coordinates.py` at the last
production event before the next one begins. Neither can see the defect the
history chart shows, because that defect is a property of the *sequence* of
forecasts rather than of any one of them:

1. the first forecast of a hiatus is far too early;
2. the forecast then recedes roughly one day per day until the run starts;
3. production reports barely move it, and when they do they move it later.

What the site displays every day is not `P(G)`. It is the conditional family

    P(G | G >= a),   a = eligible issues already known not to carry the run,

so that is what `scripts/backtest_conditional_prior.py` scores. Rolling origin
over the same 16 modeling-era gaps, the same `gaps[:i]` training slice and the
same assertion against leakage — but every batch contributes its whole
trajectory, `a = 0, 5, 10, ...` up to its outcome, instead of a single point.

Two extra diagnostics accompany CRPS and log score:

| metric | meaning |
|---|---|
| **drift** | `d(median)/d(issues waited)`. 1.0 is "recedes one day per day". |
| **drift10** | the same slope refitted from `a >= 10`, which separates the one-off loss of the zero mode at `a = 1` from a sustained recession. |
| **early%** | share of displayed forecasts whose median is *before* the outcome — the "not conservative enough" defect, measured. |
| **med@0** | the day-one median, in issues. |

Trajectory points share one outcome, so these are display-quality diagnostics
over 11 batches, not 100 independent tests. The ranking is still meaningful:
every setting is scored on exactly the same points.

### Result 6 — the V8 parametric Level 1 is the cause of both complaints

| family | bw | CRPS ↓ | log ↓ | cov 50/80/90 | drift | drift10 | early% | med@0 |
|---|---|---|---|---|---|---|---|---|
| kde-smooth | 60 | **24.04** | 4.95 | 50/75/85 | 0.61 | 0.65 | 42% | 65 |
| **mixture (point mass + KDE)** | **60** | **24.27** | **4.92** | 51/75/87 | 0.81 | **0.61** | 40% | 53 |
| mixture | 40 | 24.90 | 5.03 | 47/70/78 | 0.74 | 0.60 | 52% | 46 |
| mixture, no cluster weights | 60 | 24.33 | 4.93 | 52/75/87 | 0.92 | 0.61 | 40% | 46 |
| gamma on positives + π₀ | — | 26.98 | 5.18 | 43/65/74 | 0.73 | 0.72 | 65% | 35 |
| Weibull on positives + π₀ | — | 27.56 | 5.34 | 43/62/70 | 0.72 | 0.70 | 65% | 36 |
| **shifted lognormal (V8 live)** | — | **29.44** | 5.16 | 59/88/96 | **1.73** | **1.56** | 45% | **15** |

The V8 shifted lognormal is last on CRPS, and it is not close on the two
diagnostics that matter here. Its day-one median is **15 issues** against an
empirical median near 50, and it recedes **1.56 issues for every issue waited**
against 0.61 for the kernel mixture.

The mechanism is not mysterious. Conditioning a distribution on `G >= a` moves
its median at a rate set by the hazard:

    d(median)/da = h(a) / h(median)

A falling hazard means `h(a) > h(median)` and the median must recede *faster*
than the calendar advances. Fitting `log(G + 0.5)` to a sample containing three
zeros drags `mu` down to 3.20 and pushes `sigma` up to 1.76 — a distribution
with a median of 20 issues and a very heavy tail, so its hazard falls
throughout the range where the forecast actually lives. The two complaints —
"the first prediction is not conservative enough" and "it declines
monotonically" — are the same defect seen at two moments.

The hazard-shaped families (gamma, Weibull with shape > 1) were tested for
exactly this reason and do not win: their rising hazard does hold drift near
0.7, but a two-parameter fit to thirteen positive gaps loses more in CRPS and
coverage than it recovers.

**Selected: revert to the mixture at bandwidth 60 with cluster weights** — the
setting Result 4 already chose. This is a revert, not a new tuning.

### Result 7 — recency weighting, again, and the same answer

Adding decay to the conditional backtest reproduces Result 1: CRPS degrades
monotonically (60/none 24.27, hl 8 25.15, hl 5 25.77, hl 3 26.92). It does move
`early%` in the intuitively right direction — 40% → 36% → 36% → 35% — because
recent gaps are longer, so decay makes the prior more conservative. That is a
real effect and it is why the intuition keeps recurring, but it is bought with
sharpness, and 16 observations cannot pay for it. **Still off.**

### Result 8 — the point mass at zero is a day-one effect only

`drift` and `drift10` disagree for the mixture (0.81 vs 0.61) and agree for the
smooth kernel (0.61 vs 0.65). The mixture's extra apparent recession is one
step: the whole zero mode dies the first time an issue passes without the run
starting. Beyond `a >= 10` the two constructions are within a couple of issues
of each other at every elapsed value. So the choice between them is a choice
about the **day-one headline** (`P(gap = 0)` of 13.3% against 0.6%), not about
the shape of the hiatus trajectory, and Result 4's decision to keep the point
mass stands.
