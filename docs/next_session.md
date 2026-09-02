# Next Session

Everything built so far runs unattended. This is what is left.

## State

| piece | where |
|---|---|
| forecast | updates daily 09:30 ET + on every Togashi post |
| site | <https://geanodong-bcrs.github.io/hxh-forecast/> |
| public repo | `geanodong-bcrs/hxh-forecast` (1.5 MB; vault stays private) |
| X account | [@GDforecast](https://x.com/GDforecast) — authorised, **not yet posting** |

## Immediate resolution

Batch 49 ends with ch. 420 on **2026-09-07** (assumed, not confirmed). Whether
ch. 421 follows immediately on **2026-09-14** resolves within about two weeks,
and the model has changed its mind about it twice:

| model | P(ch. 421 on 2026-09-14) | median |
|---|---|---|
| the original zero-gap mixture | 50.6% | 2026-09-14 |
| V8 (live until 2026-08-31) | 4.4% | 2026-12-07 |
| **V9** | **0.9%** | **2028-04-18** |

V9's near-zero comes from the readiness floor: batch 50 stands at `B = 0.78`, and
no observed run has begun from that level without another 47 to 261 days. Every
snapshot behind all three answers is on disk, append-only, with the trigger that
caused it — so the record survives whichever is wrong.

## Before the bot posts

1. **Bio: the site URL.** A reply containing a link costs $0.20 against $0.015,
   so the reply text carries no URL by design.
2. **Bio: the automation disclosure.** X requires automated accounts to say so.
3. **One test post**, ideally standalone on the account's own timeline rather
   than a reply, to see the card in situ. Then delete it.
4. **Watch a few real cards** from actual production posts in dry-run before
   enabling posting from the scheduler — that is a one-line change in
   `run_update.py` and should be the last thing switched on, not the first.

## Open work, roughly in value order

0. **A two-sided readiness term (V9's own next step).** V9 uses readiness as a
   *floor* — how much work is still required — so once a run is demonstrably
   ready the term goes inert and the forecast reverts to the historical gap
   prior and keeps receding. But the three resolved runs started 6, 13 and 125
   days after reaching `B = 0.90`, all far shorter than the prior's remaining
   median at that point. Turning that into a hazard multiplier is what would fix
   V9's late-hiatus overshoot (batch 49 ends the trajectory ~10 months late).
   It rests on three observations; it needs a fourth resolved run or an
   explicitly declared prior. See `docs/model.md`.
0a. **Decide whether to ship V9's headline.** It moves ch. 421 from a 2026-12-07
   median with 4.4% on the next issue to **2028-04-18 with 0.9%**. The model
   change is documented and backtested, but this is a large public reversal and
   it is a call to make deliberately, not a side effect. `site/` has been rebuilt
   locally; nothing has been pushed.

1. **Chapters 431–440 — the model.** Currently the Level 1 gap prior carried
   forward from the first posterior, giving a median of May 2028 and an 80% range
   spanning three years. Honest, but it is the piece most worth revisiting.
2. **Weight analogs by capacity similarity** rather than uniformly — measured
   from the page log (~1.16 pages/posting-day in 2022 vs ~2.07 in 2024). Targets
   the causal variable instead of using time as a proxy. Better than the recency
   weighting the backtest rejected.
2a. ~~**Level 2 spikes on the truncation floor when its analogs are overdue.**~~
   Fixed by the V4 fade, then made moot by V9, which abandons the analog
   date-translation altogether. See `docs/model.md`.
3. **π₀ rests on two clustered observations from 2010–2012** and drives the
   headline 50.6%. Anything bearing on whether back-to-back batches are still
   possible would be the highest-value new information available.
4. **The announcement record (step 6a).** Blocks all calibration reporting (§20),
   which is the one thing that would let the site show whether the model has any
   skill. The single biggest unlock for credibility.
5. **A publication-history grid**, in the style of hiatus-hiatus.github.io: WSJ
   issues by year, released vs. hiatus. `wsj_issues.csv` and `chapters.csv`
   already hold everything it needs, and it would *show* why the gap prior is
   bimodal — which the site currently only asserts in prose. See
   `docs/resources/other sites.md`.
5a. **Replay batches 47 and 48** as separate targets — *deferred on purpose*.
   Batch 49's own replayed history comes first, as the check on whether the
   model behaves sensibly. See `docs/prediction_history.md`.
6. **173 image posts carrying text are untranscribed** (README limitation 7).
   `vision_pass.py --include-text-posts` is the backfill, ~173 vision calls.

## Things worth not forgetting

- **Poll cadence is free.** An empty `since_id` poll is not billed (measured: the
  usage counter held at 490 across one), and the cap is 3,000,000 posts/month. If
  reply latency ever matters, tighten the window at no cost.
- **`media.write` is required and not implied by `tweet.write`.** Without it
  `/2/media/upload` returns a bare 403 naming no permission.
- **Refresh tokens rotate on every use.** `x_post.refresh()` writes the new one
  back before returning; breaking that locks the bot out permanently.
- **The vault must stay private.** It holds 776 of Togashi's manuscript photos.
  `deploy_site.py`'s denylist is the guard, and it aborts rather than publishing.
