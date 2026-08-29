# Next Session

Automation is **built and running**. See `docs/automation.md` for how it works.

## What got closed

- **The loop is closed.** `scripts/run_update.py` polls X, rebuilds only what
  changed, forecasts, and writes an append-only snapshot. Two LaunchAgents drive
  it: hourly 02:00–09:00 ET (the reviewer's sleep window), plus a daily rerun at
  09:30 ET, right after the last poll.
- **The vision pass exists.** `scripts/vision_pass.py` shells out to the `claude`
  CLI, so no human sits in the critical path. Validated against three
  human-confirmed readings; chapter, stage and pages all matched.
- **Snapshots can no longer be overwritten.** They were keyed by date, so two
  runs a day silently clobbered each other. Now UTC-timestamped, with
  `snapshot.py` refusing to write over an existing path, plus `run_id`,
  `trigger`, `evidence_asof`, `annotation_status` and input sha256s on every one.
- **Empty polls are free.** Measured: `/2/usage/tweets` held at 490 across a
  zero-result poll. The monthly cap is 3,000,000 posts. Poll frequency is not
  cost-constrained.
- **The macOS permission trap is handled.** `~/Documents` is TCC-protected and a
  LaunchAgent does not inherit Terminal's permission; anaconda python *hangs* in
  `open()` rather than erroring, so a broken install looks like a job that runs
  forever with empty logs. `launchd/preflight.sh` forces that consent decision at
  install time and `install.sh` runs it automatically.
- **Batch numbers are derived, not hardcoded.** `build_batch_prior.py` assumed
  "batch 49 ends two issues after the last observed one" — true only in August
  2026. It now reads the announcement record.

## Decisions still open

1. **Nothing publishes.** The loop ends at a snapshot on disk. No website, no X
   post, no notification — so a forecast that moves by weeks at 4am is something
   you find out about by looking. A "new snapshot ready" notification is the
   smallest useful next step; auto-publishing needs the review gate discussion in
   §16/§17 settled first.
2. **Write credentials are still not set up.** OAuth 2.0 user context with
   `tweet.write`. Only needed when the bot posts. **$0.20 per post containing a
   link** vs $0.015 without — put the URL in the bio, not each post.
3. **X automation labelling** — X requires automated accounts to say so in the bio.
4. **173 image posts carrying text are untranscribed** (README limitation 7).
   `vision_pass.py --include-text-posts` is the backfill, ~173 vision calls. §8
   rule 1 says these can carry page-log observations the text does not mention.

## Model work worth doing (from `model.md`)

Unchanged by automation; this is where accuracy would actually improve.

1. **Weight analogs by capacity similarity** rather than uniformly — measured
   from the page log (~1.16 pages/posting-day in 2022 vs ~2.07 in 2024). Targets
   the causal variable instead of using time as a proxy. Better than the recency
   weighting the backtest rejected.
2. **π₀ rests on two clustered observations from 2010–2012** and drives the
   headline 50.6% on 2026-09-14. Anything bearing on whether back-to-back
   batches are still possible would be the highest-value new information.
3. **Level 2 has never been scored against an outcome.** Batch 50's actual start
   will be the first real test — one data point, but the first honest one.

## Immediate resolution

Batch 49 ends with ch. 420 on **2026-09-07** (assumed, not confirmed). The model
says **50.6%** that ch. 421 follows immediately on **2026-09-14**. That resolves
within about two weeks and is the sharpest falsifiable claim the model has made.

The automation will now record how that belief moves on its own — every snapshot
between here and resolution, with the trigger that caused it. That series is the
first real input to the §17 evolution chart, and it exists whether or not anyone
is watching.
