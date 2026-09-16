# V13 Review — the slowest-observed envelope

Review of `scripts/build_v13.py` against snapshot
`data/forecasts/20260915T215921Z_batch50_posterior.json` (B=9.1, production
deadline 2027-02-09, median 2027-02-19). Two findings, both arising from the
same habit: adding together quantities that were never observed together.

Everything below is reproducible from the snapshot JSON alone, because each one
carries the full `deadline_history` and the per-cell `observations`.

---

## Summary (2026-09-16)

**Both findings stand. The proposed fix was built, measured and rejected. V13
remains live, now with its two defects quantified in `docs/model.md` instead of
left implicit.**

What the review found:

1. V13's envelope takes a per-cell maximum across batches and sums the cells, so
   two unrelated production stalls — batch 48's from 2023-03-09 and batch 49's
   from 2024-11-20 — both enter one total. The 0→10 envelope plus the scheduling
   delay is **1381 days** against a slowest observed run of **800**: 581 days
   longer than anything that happened, a factor of 1.7.
2. The 125-day scheduling floor is a `max` over three observations spanning 6 to
   125 days, measured from three *different* readiness levels, and it is additive
   and never decays: 125 of 147 remaining days at B=9.1 (**85%**) and all 125 at
   B=10.00.

What was built: `scripts/build_v14.py`, which replaces both with one quantity
measured inside a single batch, `r_b(x) = publication_b − date_b(x)`, then gives
each analog one 120-day component and averages them (§11). This removes the
summing, dissolves the additive floor (at x = 10.0, `r_b` *is* the
completion-to-publication wait), and makes the countdown decay with readiness.

Why it was rejected — the 21-day trajectory diagnostic:

| model | target | mean absolute error | mean CRPS |
|---|---|---:|---:|
| V13 summed envelope | batch 48 | **92 days** | **9.46** |
| V13 summed envelope | batch 49 | **34 days** | **3.78** |
| V14 uncensored analogs only | batch 48 | 379 days | 31.13 |
| V14 uncensored analogs only | batch 49 | 237 days | 21.49 |
| V14 all analogs | batch 48 | 266 days | 22.87 |
| V14 all analogs | batch 49 | 246 days | 22.29 |
| Level 1, no Level 2 | batch 48 | 212 days | 18.65 |
| Level 1, no Level 2 | batch 49 | 158 days | 16.62 |

Two correlated trajectories cannot *select* a model — V12 and V13 were each
adopted on semantics for that reason — but they can reject one, and a Level 2
beaten by its own absence on every available outcome has not earned the live slot.

The cause is data starvation, not the formulation. Production reporting begins
with batch 47, whose reported trajectory is left-censored and compressed: 146 days
from B=3.00 to B=9.10 against 722 and 626 for batches 48 and 49. So `r_47(x)` is
small at every level and not comparable. Excluding it leaves **one** usable analog
when forecasting batch 49 and **none** when forecasting batch 48 — batches 45 and
46 have no production reports at all.

**So V13's summing is load-bearing.** Per-cell maxima let any batch that covered
any cell contribute to it, which is what makes three sparsely and unevenly
reported runs yield a full budget. The 581-day inflation is the price of that
robustness: a real trade, not a mistake to be removed.

What V14 would have predicted for ch 421 (= W_50), had it shipped:

| model | median | 80% interval |
|---|---|---|
| V13 (live, published) | 2027-02-19 | 2026-11-02 .. 2027-07-16 |
| V14 uncensored analogs | 2027-01-29 | 2026-10-19 .. 2027-06-25 |
| V14 all analogs | 2027-01-15 | 2026-10-12 .. 2027-06-11 |

Three weeks earlier than V13, because V13 takes the slower of the two components
(batch 49's 2027-02-06) as its centre while V14 averages it with batch 48's
2026-12-03.

What changed on disk: the V13 section of `docs/model.md` now quantifies both
defects; a new "Per-analog countdowns (V14, not adopted)" section records the
negative result; `build_v14.py` is retained as a selectable comparison mode and
every live snapshot carries an `analog_countdown` block, so what V14 would have
said is on the record at each forecast date without being published. Two claims in
the Recommendation below were wrong when written and are struck through inline.

Still unaddressed, from the original review: V13 discards the Level-1 prior
(`post = v13_pmf.copy()`), centres a symmetric Gaussian on a date it calls the
slowest observed, and its `record_hiatus` branch overwrites the countdown without
a guard.

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

## Tests

`tests/test_ordered_readiness.py`, 20 tests, all passing. Ten were added for
V14 in a `V14AnalogCountdown` case; they still run because the module is retained
as a comparison mode, and they pin the properties the review asked for so a future
attempt does not have to rediscover them.

**Finding 1 — no summing across batches**

| test | what it pins |
|---|---|
| `test_remaining_is_measured_within_one_batch` | `r_b(x)` comes from one batch's own two dates: 20 and 60 days for the two fixtures |
| `test_remaining_never_exceeds_that_batch_own_run` | at every level, no analog's remaining wait exceeds that batch's whole observed run — the invariant V13's 1381-day envelope violates |
| `test_left_censored_analog_is_excluded_outright` | a run first reported at B=4.0 contributes nothing, and with the requirement off only levels *above* its first observation do |

**Finding 2 — no additive scheduling floor**

| test | what it pins |
|---|---|
| `test_no_additive_scheduling_floor_at_completion` | at B=10.0 the remaining wait *is* the completion-to-publication delay, not that delay plus a residue |
| `test_remaining_decays_with_readiness` | the countdown is non-increasing in readiness, so the floor cannot stand as a constant |

**Monotonicity — the one-step rule that replaced the minimum over history**

| test | what it pins |
|---|---|
| `test_one_step_monotonicity_keeps_the_earlier_candidate` | the V11 defect: a report after a long silence with a small readiness gain implies a later date (2027-03-02) and is clamped to the preceding state's candidate (2026-06-02) |
| `test_progress_without_silence_is_left_alone` | the mirror case — an already-earlier candidate passes through untouched, so the constraint costs nothing when not needed |
| `test_refuted_previous_candidate_does_not_bind` | a preceding candidate the publication floor has passed is refuted and must not pin the forecast to a date that cannot happen |

**Combination and degenerate inputs**

| test | what it pins |
|---|---|
| `test_components_are_averaged_not_multiplied` | two far-apart components both keep mass; multiplying would collapse onto their overlap and starve the later one (§11) |
| `test_empty_target_path_is_neutral` | no readiness observations yields no components, a null slowest date, and a flat likelihood rather than a crash |

One existing V13 test, `test_v13_uses_longest_observed_transition`, was annotated
rather than changed: both its fixture paths jump 0.0 → 9.0 in one step, so every
elapsed day before the jump is charged to cell 0.0–0.5 and the cells between get
zero. That is exactly the attribution artifact Finding 1 describes, and the test
asserted it as correct behaviour without noting it. It now pins V13's behaviour
for replay while recording that it is an artifact.

**Not covered by tests.** The two claims that need data rather than fixtures: that
the envelope exceeds every observed run (checked against the live analog paths, in
the tables above) and the trajectory scores (`scripts/backtest_trajectory.py`,
settings `V14 analog countdown` and `V14 all analogs`). Cross-run non-regression
of the deadline (Finding 6) remains unenforced and therefore untested.

---

## What holds up

The left-censoring guard (`build_v13.py:28-34`) correctly drops batch 47's
sub-3.0 cells rather than crediting that run with instant early progress.
Persisting `deadline_history` and the per-cell `observations` in every snapshot
is what made both findings above checkable from the JSON without re-running the
model — the auditability is working as intended.
