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

Batch 49 ends with ch. 420 on **2026-09-07** (assumed, not confirmed). The model
says **50.6%** that ch. 421 follows immediately on **2026-09-14**. That resolves
within about two weeks and is the sharpest falsifiable claim the model has made.

It is also the first real test Level 2 has ever had. Whatever happens, every
snapshot between now and then is already on disk, append-only, with the trigger
that caused it — so the record survives being wrong.

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

1. **Chapters 431–440 — the model.** Currently the Level 1 gap prior carried
   forward from the first posterior, giving a median of May 2028 and an 80% range
   spanning three years. Honest, but it is the piece most worth revisiting.
2. **Weight analogs by capacity similarity** rather than uniformly — measured
   from the page log (~1.16 pages/posting-day in 2022 vs ~2.07 in 2024). Targets
   the causal variable instead of using time as a proxy. Better than the recency
   weighting the backtest rejected.
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
