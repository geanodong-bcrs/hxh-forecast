# Automation

The forecast updates itself: once a day, and again whenever Togashi posts.

    launchd ──┬── poll   hourly 02:00-09:00 ET   run_update.py --poll
              └── daily  09:30 ET                run_update.py --no-poll --daily
                             |
                    scripts/run_update.py
                             |
        ┌────────────────────┼────────────────────┐
    new post?          review verdict?        new JST day?
        |                    |                     |
    ingest + vision      merge + events         (nothing)
        └────────────────────┼─────────────────────┘
                             |
       prior -> level2 -> posterior -> snapshot -> site/index.html

Everything runs from one entry point, `scripts/run_update.py`. It decides what
needs doing rather than running thirteen scripts unconditionally.

## Schedule

| job | when | what |
|---|---|---|
| `com.togashi.forecast.poll` | hourly 02:00–09:00 **Eastern**, 8×/day | polls X; reruns the model if anything arrived |
| `com.togashi.forecast.daily` | 09:30 **Eastern** | the daily rerun, half an hour after the last poll |

**Why that poll window.** It is the window the reviewer is asleep and cannot
trigger a run by hand; outside it, a manual run is one command. It is not chosen
from Togashi's posting distribution — see "Posting times" below, which argues
against optimising for that at all.

**Why 09:30 and not a Tokyo hour.** Half an hour after the last poll, so the
last thing that happened before the daily snapshot was a fresh look at X.
Daylight saving drifts it against JST by an hour twice a year and that does not
matter — the daily run exists to guarantee one snapshot a day, not to land on a
Tokyo instant, and nothing in the model is a function of the hour it runs at.
It passes `--no-poll`, so it costs nothing at the API: it re-forecasts on
evidence already on disk, which is what moves when a chapter ships and the
truncation floor advances.

The 8 polls never trigger on the date — only on evidence. `--daily` is what
guarantees the snapshot, and it is guarded on the local date so that a run
launchd replays after the Mac slept still produces one snapshot, not two.

## Install

```bash
./launchd/install.sh              # install, load, and preflight both jobs
./launchd/install.sh uninstall    # remove them
./launchd/preflight.sh            # permission check on its own
launchctl list | grep togashi     # check they are loaded
```

The plists in `launchd/` are templates carrying `__REPO__` / `__PYTHON__` /
`__HOME__`; the installer substitutes real paths into `~/Library/LaunchAgents`.

### macOS permissions — read this before debugging a silent job

The repo lives under `~/Documents`, which macOS protects with TCC, and **the
permission your Terminal holds does not extend to a LaunchAgent.** The failure
mode is genuinely nasty, and it bit this install during development:

| binary | what happens |
|---|---|
| `/bin/bash` | fast, clear `Operation not permitted` |
| anaconda `python3` | **hangs in `open()`** — no output, no error, forever |

So a broken install does not look broken. It looks like a job that started and
never finished, with two empty log files. The first launchd read of the repo can
block on a consent decision rather than failing, and it blocks *before* Python
has executed a single line of the script — which is why nothing appears in the
run log either.

`launchd/preflight.sh` bootstraps a throwaway job that tries the same read the
same way and reports `ok`, `denied` or `hang`. `install.sh` runs it automatically,
so the consent decision is forced at install time with someone watching, rather
than at 03:00 with nobody. If it fails it prints the exact path to add to
System Settings → Privacy & Security → Full Disk Access. Adding *Terminal* there
does not help — TCC attributes the access to the binary launchd executes.

Re-run `./launchd/preflight.sh` after moving the repo, changing interpreter, or
upgrading anaconda.

These are **LaunchAgents**, so they run only while you are logged in and the Mac
is awake. launchd fires a missed run once on wake rather than replaying each one.
Given the forecast resolves in weeks, a slept-through window costs nothing.

## Running it by hand

```bash
python3 scripts/run_update.py                 # poll, rebuild what changed, forecast
python3 scripts/run_update.py --no-poll       # same, without touching the API
python3 scripts/run_update.py --daily         # guarantee today's daily snapshot
python3 scripts/run_update.py --force         # forecast even if nothing changed
python3 scripts/run_update.py --dry-run       # show what would run, touch nothing
python3 scripts/run_update.py --no-vision     # skip auto-transcription
```

## What counts as a change

Three things trigger a rerun and a new snapshot. A human confirmation is one of
them — a reviewer accepting an image reading changes the evidence with no new
tweet, and gets its own revised snapshot.

| trigger | detected by | rebuilds |
|---|---|---|
| `tweet` | new ids in `data/raw/tweets/` after the poll | media → corpus → vision → merge → events → intervals |
| `annotation` | `review_queue.csv` sha changed | merge → events → intervals |
| `daily` | `--daily`, once per local date | nothing; re-forecasts on current data |
| `manual` | `--force` | nothing |

**An empty poll writes no snapshot.** §16 wants every forecast preserved, and it
is: a run with no new evidence and no new day produces a forecast identical to
the one already on disk. Writing it eight times a day would bury the §17
evolution chart under ~2,900 duplicate points a year. Empty polls append to
`data/automation/poll_log.csv`, the honest record of "we looked, nothing there".

## Snapshots are append-only, and now actually enforced

Snapshot filenames were date-only (`2026-08-28_batch50_posterior.json`), so two
runs in one day silently overwrote each other. Survivable at one hand-run per
day, fatal at eight. Snapshots are now keyed by UTC timestamp:

    data/forecasts/20260828T195458Z_batch50_posterior.json

`scripts/snapshot.py` **refuses to write if the path exists** rather than
trusting the convention. The batch number is derived from the data, not
hardcoded — `build_batch_prior.py` used to assume "batch 49 ends two issues
after the last observed one", true only in August 2026.

Every snapshot carries provenance (§28): `run_id` (shared by the prior, level 2
and posterior of one run), `trigger`, `trigger_detail`, `evidence_asof`,
`annotation_status`, and the sha256 of all seven input files.

`data/forecasts/index.csv` is one row per artifact, so the §17 evolution chart
does not have to glob and parse every JSON.

## The vision pass

~60% of Togashi's posts are image-only, and the page log — the highest-volume
evidence in the corpus — exists only as photographs. `scripts/vision_pass.py`
calls the `claude` CLI headless and writes what it reads as a **proposed**
annotation. It never promotes its own reading.

    image_annotations.csv            MODEL owns   <- vision_pass appends
    review_queue.csv                 HUMAN owns   <- never written by any script
    review_pending.csv               script-owned <- what awaits your verdict
    image_annotations.confirmed.csv  the join, by merge_review.py

The forecast does **not** wait for you. A snapshot built on unconfirmed readings
is labelled `provisional:N_unconfirmed`; your later verdict triggers a second,
revised snapshot rather than editing the first. `review_pending.csv` is written
in `review_queue.csv`'s exact column layout with `verdict` blank, so reviewing is:
fill in verdicts, paste the rows across, rerun. The human's file stays human-owned.

**Scope.** The default matches the existing corpus: image-only posts. The 299
existing annotations are exactly those; the 173 image posts that also carry text
were deliberately skipped. That is not strictly safe — §8 rule 1 gives a
counterexample, a post reading 「No.426 ペン入れ 開始!」 that *also* shows
manuscript page 1 — so page-log observations inside text posts are being lost.
`vision_pass.py --include-text-posts` is that backfill; it is not the routine path.

Validated against three human-confirmed readings before deployment: chapter
number, stage phrase and page numbers all matched.

## API cost

**An empty `since_id` poll is not billed.** Measured, not assumed: the
`/2/usage/tweets` counter held at 490 across a zero-result poll. Check it with
`python3 scripts/x_usage.py`. The cap on this tier is 3,000,000 posts/month, so
polling frequency is bounded by rate limits and reviewer preference, not cost —
the 8-poll window could be widened for free if that ever seemed worthwhile.

The `claude` vision calls are the only real per-post cost, and only for
image-only posts (~5.5 posts/month at his current rate).

## Posting times

The 17:00 JST spike everyone knows is a 2022–24 artifact. It has dissolved, and
he now posts about 5.5 times a month spread across the clock:

| period | n | 16:00–24:00 JST share |
|---|---|---|
| 2022-01 → 2024-12 | 424 | 55% |
| 2025-01 → 2026-08 | 66 | 41% |

Which is the argument for *not* tuning the poll window to his habits. If latency
ever does matter, evenly-spaced 3-hourly polls beat any evening window on every
metric (mean 1.5 h vs 5.6 h, worst case 3 h vs 16 h) — and cost nothing extra.

## Where it writes

```
site/index.html                 the public page, rebuilt from the newest snapshot
data/automation/state.json      last daily local date, review_queue sha, last run
data/automation/poll_log.csv    one row per run, including the empty ones
data/automation/runs/<id>.log   per-step stdout (gitignored)
data/forecasts/<id>_batch<N>_*.json   append-only snapshots
data/forecasts/index.csv        one row per snapshot
data/annotations/review_pending.csv   what awaits your verdict
```

## When something breaks

`run_update.py` stops at the first failed step, prints the tail of its stderr,
exits non-zero and writes **no** snapshot — a forecast from a half-rebuilt
dataset would be worse than no forecast. The poll log records `forecast_failed`.

```bash
tail -50 data/automation/runs/$(ls -t data/automation/runs | head -1)
tail -20 data/automation/launchd.poll.err.log
column -s, -t < data/automation/poll_log.csv | tail -20
```

A post that the vision pass cannot read is left unannotated and retried next
run; it does not block the forecast.

## The pages

`scripts/build_site.py` renders two pages from the newest posterior snapshot,
at the end of every successful forecast, so they are never staler than the model.

    site/index.html    the forecast, for readers
    site/method.html   how it works, and where it is weak

**Two pages on purpose.** The audience is manga readers who want a date. The
method and the caveats are real and stay published — the headline is a strong
claim and the caveats are what make it a forecast rather than a guess — but they
do not belong in front of the answer. `index.html` carries one footer line
pointing at `method.html`.

It **reads the snapshot, never the model**: it re-renders what was forecast and
cannot recompute it, so presentation is structurally incapable of disagreeing
with the record. Self-contained files — no external requests, no framework, no
build step.

### Language

The model thinks in batches and numbers them; readers do not, and "batch 50"
means nothing outside this repo. Every user-facing string names a chapter range
instead — "Chapters 421–430", "the run starting at chapter 391". That mapping is
read from `chapters.csv`, not computed as `(id-47)*10+391`, which is right today
and would drift the first time a run is not exactly ten chapters.

### The charts

Cumulative, not density: half the mass sits on a single issue, so a density plot
is one spike and a hundred invisible bars. The curve is a true step function —
each step is one weekly Jump issue — and the x-axis **stops once the curve passes
99%**, because beyond that the answer is "almost certainly yes" and the extra
years of flat line only shrink the informative part. Ticks are monthly, thinned
to quarterly when the range is long.

### Production status

The page leads with the **four tiers the fandom already uses** (the @togashiactu
chart): delivered / backgrounds &amp; dialogue specified / drawn only / nothing
reported. Our event pipeline reproduces that chart chapter-for-chapter from a
completely independent derivation — 421–426, 427–429, 430–433, 434–440 — which is
a real cross-check, not a coincidence, and it means the page speaks in colours
readers already recognise. See `docs/resources/other sites.md`.

Below it, a per-stage matrix with a glossary giving each stage's English name,
its Japanese term, and what actually happens in it — "ネーム" is a storyboard, and
nobody outside the industry knows that from the label alone.

**Assumed-done cells.** Togashi does not post every stage of every chapter, so a
bare matrix is full of holes that read as skipped work. Pipeline order licenses
the inference: if he has written the background brief, the characters were
inked. Those cells are drawn **hollow with a dashed border**, never solid — §8
forbids inferring anything without recording that it is an inference.

### Two batches

`build_posterior.py` also forecasts the run *after* the one in progress, by
carrying the posterior through one more inter-batch gap. This is **Level 1 only**
and labelled as such on the page: production events exist for those chapters, but
every one is at `character_inking`, the earliest pipeline stage, which does not
constrain a start date. Presenting it as production-informed would misstate its
provenance.

### What it deliberately omits

**Step 25, model performance and calibration.** §20 requires partitioning
forecasts into pre- and post-announcement subsets, and the announcement record
is step 6a, still deferred. Without that split the metrics would measure
announcement timing rather than skill, and would flatter the model. The method
page says so rather than omitting it silently.

Neither page ever prints a literal 100%: §3 forbids presenting a near-certainty
as certain, so probabilities above 0.99 render as `>99%`.

### Publishing

Nothing is deployed yet. `site/` is two static files, so GitHub Pages or any
static host serves them as-is.
