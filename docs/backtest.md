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

## What this backtest cannot tell you

**Level 2 is untested.** Production evidence exists for three batch starts;
leave-one-out over three analogs would score a model against itself. So §29
step 16 — baseline versus production-informed — is **not answerable yet**. The
posterior's shape rests on the correlation argument in `model.md` and on the
truncation being valid, neither of which this backtest validates.

That is the honest headline: the historical prior is calibrated in the tails,
timid in the middle, and weak as a point forecast — and the component doing most
of the work in the live forecast has never been scored against an outcome.
