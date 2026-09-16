# V13 Review — the slowest-observed envelope

Review of `scripts/build_v13.py` against snapshot
`data/forecasts/20260915T215921Z_batch50_posterior.json` (B=9.1, production
deadline 2027-02-09, median 2027-02-19). Two findings, both arising from the
same habit: adding together quantities that were never observed together.

Everything below is reproducible from the snapshot JSON alone, because each one
carries the full `deadline_history` and the per-cell `observations`.

> **Outcome (2026-09-16).** Both findings stand. The fix proposed below was
> implemented as `scripts/build_v14.py`, scored, and **rejected** — it is worse
> than V13, worse than V12, and worse than running no Level 2 at all, because
> measuring within a single batch needs a complete production path and the corpus
> contains at most two of those, one of which is always the target. V13's summing
> turns out to be load-bearing: it is what makes three sparsely reported runs
> usable. See "Per-analog countdowns (V14, not adopted)" in `docs/model.md`. The
> corrections to the *documentation* of V13 were applied. Two claims in the
> Recommendation below were wrong when written and are marked inline.

---

## Finding 1 — the envelope sums stalls from different batches

`transition_envelope` takes a per-cell maximum across batches 47–49
(`build_v13.py:37-68`), and `remaining_budget` then sums those cells
(`build_v13.py:71-74`). Each cell's maximum can come from a different batch, so
two unrelated production stalls both enter the same total.

| grid cell | days | source observation |
|---|---:|---|
| 2.0 → 2.5 | **422** | batch 48 — 420-day stall from 2023-03-09 |
| 5.5 → 6.0 | **280** | batch 49 — 279-day stall from 2024-11-20 |
| 18 other cells | 554 | mixed |
| scheduling delay | 125 | batch 49 — completion to publication |

The 0→10 envelope plus the scheduling delay is **1381 days**. Measured from
first production report to publication of the batch's first chapter, the runs it
was built from took:

| batch | days | note |
|---|---:|---|
| 48 | **800** | slowest run observed |
| 49 | 751 | |
| 47 | 152 | left-censored, path begins at B=3.0 |

So the "slowest observed" envelope is **581 days longer than the slowest
observation**, a factor of 1.7. `docs/model.md:1090` says only that "maxima from
different batches are added together"; that the total exceeds every observed run
belongs in the documentation rather than being left to be inferred.

### Why the cell boundaries are arbitrary

`ordered_trace` can jump several readiness levels on one reporting date. When B
moves 2.01 → 2.47 across a 420-day silence, the whole 420 days is charged to a
single half-chapter cell and the cells in between get zero. The grid position of
a stall therefore records when reporting stopped, not which work was slow.

The budget consequently has cliffs rather than a gradient — crossing 2.5 drops
it 1159 → 737, crossing 6.0 drops it 597 → 317. The live deadline is in effect
*the date the target crossed 6.0, plus 317 days*: fixed on 2026-04-08 at B=6.1
and unchanged for five months. One cell is doing the work, and which cell was
decided by where an unrelated batch happened to be when reporting went quiet.

`tests/test_ordered_readiness.py:91` encodes this attribution as expected
behaviour: a path jumping 0.0 → 9.0 in one step charges all 31 elapsed days to
cell 0.0–0.5.

---

## Finding 2 — the 125-day scheduling floor

The floor is a `max` over three observations of "last report to publication".
They span 6 to 125 days and are measured from three different readiness levels,
so they are not the same quantity:

| batch | last report | at B | published | days |
|---|---|---:|---|---:|
| 47 | 2022-10-18 | 9.10 | 2022-10-24 | 6 |
| 48 | 2024-07-21 | 9.50 | 2024-10-07 | 78 |
| 49 | 2026-02-24 | 10.00 | 2026-06-29 | **125** |

Batch 49's 125 days does run from completion, so today's figure double-counts
nothing. That is luck rather than construction: had batch 48's 78 days won the
`max`, the floor would have run from B=9.50 and overlapped the 9.5→10.0 cell
already inside the sum. The `max` should be taken over batches measured from a
common level.

### Near completion the floor is the whole forecast

The floor is additive and does not shrink as readiness rises. At B=9.1 the
remaining budget is 147 days, of which **125 (85%) is the floor** and 22 is
production progress. At B=10.00 — every chapter complete — the budget is still
125 days. V13 structurally cannot forecast publication sooner than four months
out, however finished the run is, and above roughly B=9 the headline number is
one observation from one batch restated.

A retrospective check: at batch 47's own final state (B=9.10 on 2022-10-18) the
envelope implies publication on **2023-03-14** against an actual
**2022-10-24**, 141 days late. Batch 47 sits inside the envelope that produced
this, so it is illustrative, not an out-of-sample score.

---

## Recommendation

Replace the summed per-cell maxima with a **direct** envelope: for each batch,
the observed time from reaching level *x* to that batch's publication, then the
maximum across batches.

It never adds two batches together, so it cannot exceed the slowest observed
run. It stays monotone non-increasing in readiness — each batch's own curve is
non-increasing, and dropping a batch can only lower the maximum — so V13's
countdown semantics survive. And it subsumes the separate floor: at B=10.0 the
direct envelope *is* the 125-day delay, with no additive term to reconcile.

Computed on the live analog paths:

| level | V13 budget | direct | batch 47 | batch 48 | batch 49 |
|---|---:|---:|---:|---:|---:|
| 2.0 | 1159 | **718** | — | 578 | 718 |
| 3.0 | 724 | **698** | — | 148 | 698 |
| 5.0 | 648 | **638** | 89 | 125 | 638 |
| 6.0 | 317 | **307** | 82 | 121 | 307 |
| 8.0 | 194 | **184** | 52 | 114 | 184 |
| 9.1 | 147 | **144** | 6 | 93 | 144 |
| 10.0 | 125 | **125** | — | — | 125 |

~~**This barely moves the live number.** 144 days instead of 147 today; 307
instead of 317 at B=6.1, where the deadline was actually set.~~ **Wrong.** That
compares budgets at the current readiness level, but the deadline is the running
minimum over the target's whole observation history, not the current budget. On
the direct envelope the running minimum returns **2026-10-19**, set by an
observation from October 2024 at B=1.30 — three and a half months earlier than
V13, and within a month of the truncation floor.

The reason is instructive and was missed above: V13's minimum over every
candidate ever formed stays well behaved *only because* the envelope is inflated.
Deflate it and the minimum locks onto pre-stall estimates which the run's own
eleven-month silence at B≈2.0 has already refuted. So fixing Finding 1 forces a
third change — replacing the minimum-over-history with a one-step check against
the preceding readiness state, which is also what Finding 6 needed.

The gap does open at low readiness — 718 against 1159 at B=2.0 — which is where
replays operate.

**It does not fix Finding 2.** At B=9.1 the direct maximum is still batch 49's
144 days, because it remains a maximum over three batches whose values span 6 to
144. That is a sample-size problem, not a formulation problem. Two options:

* fold the scheduling lag into the forecast's width rather than its centre —
  three clean observations support a 3-point mixture, which widens the
  distribution honestly instead of pushing the centre out to the slowest one;
* keep the maximum, and record in `docs/model.md` that above roughly B=9 the
  forecast is dominated by a single scheduling observation and is no longer
  meaningfully responsive to production progress.

The mixture option was scored and rejected — see the Outcome note at the top. The
second option, documenting the limit, was applied to `docs/model.md`.

~~It never adds two batches together, so it cannot exceed the slowest observed
run.~~ This part is true, but the Recommendation omitted the cost of that
property: measuring inside one batch requires a batch whose whole run was
reported. Production reporting begins with batch 47, and batch 47's reported
trajectory is left-censored and compressed — 146 days from B=3.00 to B=9.10
against 722 and 626 for batches 48 and 49 — so `r_47(x)` is small at every level
and not comparable. Excluding it leaves **one** usable analog when forecasting
batch 49 and **none** when forecasting batch 48. The summing that inflates V13 is
what makes it robust to exactly this sparsity.

---

## What holds up

The left-censoring guard (`build_v13.py:28-34`) correctly drops batch 47's
sub-3.0 cells rather than crediting that run with instant early progress.
Persisting `deadline_history` and the per-cell `observations` in every snapshot
is what made both findings above checkable from the JSON without re-running the
model — the auditability is working as intended.
