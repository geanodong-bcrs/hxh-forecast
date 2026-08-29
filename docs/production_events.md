# Production Events — Phase 1A step 5

`data/processed/production_events.csv` — **486 events**, 2022-05-24 → 2026-08-27,
chapters 388–433. Built by `scripts/extract_events.py` from three inputs:
the text posts, the human-confirmed image transcriptions, and the page log.

| event class | n |
|---|---|
| `page_completed` | 218 |
| `chapter_stage` | 201 |
| `ancillary_work` | 25 |
| `batch_scope` | 19 |
| `disruption` | 15 |
| `batch_countdown` | 8 |

Stages: `character_inking` 40, `manuscript_complete` 35, `bg_spec` 34,
`dialogue` 32, `chapter_level` 24, `retouch` 16, `bg_work` 14, `panel_layout` 6.
Statuses: `complete` 120, `in_progress` 23, `started` 20, `awaiting_return` 18,
`retake` 8, `under_review` 3.

Provenance: 242 `text_explicit`, 203 `image_transcription`, 41 `inferred`
(page-log rows whose chapter came from enumeration rather than a reviewer anchor).
Every row keeps the verbatim Japanese it was derived from.

## The headline finding: production is not the bottleneck

Manuscript-completion → publication lag, by batch:

| batch | n | median lag | range |
|---|---|---|---|
| 47 (ch 391–400) | 9 | 61 d | 33–89 |
| 48 (ch 401–410) | 9 | 94 d | 16–578 |
| 49 (ch 411–420) | 7 | **191 d** | 181–197 |

The batch-49 lag looks impressively tight — ±8 days across seven chapters — but
that tightness is an artifact, and reading it as a predictive interval would be a
mistake. He completed those manuscripts at a weekly cadence (2025-12-14, 12-27,
2026-01-13, 01-14, 01-20, 01-23, 02-10) and Shueisha published them at a weekly
cadence starting six months later. Two weekly sequences offset by a constant give
a constant lag. **Nothing causal is being measured.**

The real relationship is the one Togashi states outright
(2024-09-29): 「掲載のペースは編集部の方に一任しております」 — *the publication pace
is left entirely to the editorial department.* Production ran roughly seven
chapters ahead of publication throughout batch 49 and is further ahead now.

**Consequence for Phase 1B.** Production evidence does *not* predict timing
within a batch, because manuscript readiness is not what gates a release. Its
predictive value is concentrated in a different question: whether enough finished
chapters exist for a batch to start at all. The §13 Level-2 design should treat
production state as evidence about **batch feasibility**, not as a countdown to
the next chapter.

## Current production state (2026-08-27)

Latest event per chapter, published through ch 418:

| chapters | furthest stage reached |
|---|---|
| 419–423, 425, 426 | `manuscript_complete` |
| 424 | `bg_spec` only — stalled since 2026-03-10 |
| 427, 428, 429 | `bg_spec` complete |
| 430–433 | `character_inking` complete |

Chapter 424 is the visible scar of a `disruption`: its manuscript went missing
(2025-10-12 「No.424の原稿捜索中。」) and was eventually found behind cardboard
boxes. It is the only chapter in 419–426 not marked complete, and it sits three
stages behind its neighbours. Whether that is a real stall or simply a missing
post is worth checking before the model treats it as a blocker.

## Extraction defects found and fixed

Building the extractor surfaced four bugs that inspection had missed:

**Duplicate stage hits.** 枠線 and フキダシ are separate patterns that both mean
`panel_layout`, so one phrase emitted the event twice. Fixed by collapsing hits
to one per stage id.

**Duplicated non-chapter events.** A line naming three chapters produces three
phrases; scanning each for disruptions fired the same disruption three times.
Non-chapter classes are now scanned once per distinct phrase per post.

**The 388 typo needed a sharper guard than a range check.** 「No388.399…完成」
(388 is a typo for 398) passes a static plausibility range — 388 is a real
chapter — and passes a distance check, since it is only nine chapters from its
neighbours. What catches it is publication: **ch 388 had been in print since
2018-11-12**, and a published chapter cannot be reaching manuscript completion.
`retouch` is exempt from that rule, because Togashi genuinely does rework
published chapters for the tankobon.

**Multi-stage phrases need positional pairing.** 「背景効果原稿返却。オレの加筆中。」
carries two stages with two different statuses. Each stage is paired with the
next status to its right, falling back to the last status in the phrase.

## Known gaps

- **9 `chapter_stage` events have no status** — all 2022 fragments like
  「オレの枠線・フキダシ」 where the status sits on a following line that the
  continuation heuristic did not join. Low volume, all in the era that will carry
  least weight.
- **No `manuscript_complete` for ch 417**, which published 2026-08-10. The corpus
  simply lacks the post; coverage is not uniform.
- **Disruption detection is keyword-based** and will over-fire on casual mentions
  (「回復」 appears in a post about a massage). 15 events is small enough to audit
  by hand, and worth doing before they enter a model.
