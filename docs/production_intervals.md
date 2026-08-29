# Production → Publication Intervals (Agents.md §9)

`data/processed/production_intervals.csv` — **333 observations** over the 28
published chapters we have production evidence for (391–418). Every individual
observation is preserved; §9 forbids reducing these to an average, and the
reason turns out to be concrete rather than hygienic.

Sanity check: **zero negative lags.** No production event lands after its
chapter published, across all 333.

## Pooling across batches destroys the signal

`manuscript_complete` → publication, in days:

| batch | n | min | p25 | median | p75 | max | skew |
|---|---|---|---|---|---|---|---|
| 47 (391–400) | 9 | 33 | 34 | **61** | 82 | 89 | 0.20 |
| 48 (401–410) | 9 | 16 | 83 | **94** | 142 | 578 | 2.07 |
| 49 (411–420) | 7 | 181 | 188 | **191** | 194 | 197 | −0.42 |
| **pooled** | 25 | 16 | 61 | 90 | 187 | 578 | **2.56** |

The three batches have medians of 61, 94 and 191 days. The pooled distribution
has a median of 90 and a skew of 2.56 — a shape that describes none of the three
and would hand the model a fictitious long tail. Every stage shows the same
pattern; `character_inking` runs 181–185 days in batch 48 and **737–750** in
batch 49.

**Rule: fit per batch, or on the most recent batch. Never pool.** The recency
weighting already agreed for the batch-start prior applies here for the same
reason.

## The lag–position slope reveals *how* a batch was published

Correlation between a chapter's position in its batch and its manuscript→
publication lag:

| batch | corr(position, lag) | lags in order |
|---|---|---|
| 47 | **−0.90** | 89, 89, 61, 82, 62, 41, 33, 34, 34 |
| 48 | **−0.58** | 578, 83, 90, 94, 156, 137, 142, 16, 23 |
| 49 | **+0.10** | 197, 191, 181, 187, 188, 192, 195 |

In batches 47 and 48 the lag **declines through the batch**: early chapters were
finished long before publication, later ones were completed just-in-time while
the batch was already running. That is the arithmetic signature of Shueisha
starting a run before Togashi had finished it — which the inventory count says
outright (batch 47 began with 6 of 10 done, batch 48 with 7).

In batch 49 the slope is flat and the lag is nearly constant at ~190 days. The
batch was fully stocked before it started, so publication simply walked through
finished inventory at a weekly cadence.

**This slope is a usable diagnostic.** A steep negative slope means just-in-time
publishing and production genuinely constrains the schedule. A flat slope means
publishing from inventory, and production tells you nothing about timing. The
regime flipped between batch 48 and batch 49.

## Consequence for the forecast

Under just-in-time publishing (47, 48) a batch can start while under-stocked, so
the batch-start question is roughly "has he got about 6–7 done?". Under inventory
publishing (49) that question is irrelevant — everything was ready months early
and Shueisha waited anyway.

The current inventory for 421–430 is 6 chapters at `manuscript_complete`
(421–423, 425, 426, plus 424 inferred), with 427–429 at `bg_spec` and 430 inked.
That is **exactly the level at which batches 47 and 48 began**, and nowhere near
what batch 49 waited for. Which regime applies is the forecast, and with three
observations it cannot be settled from data alone — which is the honest argument
for a wide, explicitly bimodal predictive interval rather than a point estimate.

## Sample sizes, stated plainly

Per stage per batch: n between 1 and 10. `bg_work` in batch 48 has n=1. Any
quantile from these is a description of a handful of points, not an estimate of a
distribution, and the interval widths reported by the model must reflect that
rather than the tightness of, say, batch 49's ±8-day spread — which is an
artifact of two weekly cadences running in parallel, not evidence of precision.
