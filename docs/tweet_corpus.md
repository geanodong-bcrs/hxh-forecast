# Togashi X Corpus — Phase 1A steps 2–3

Account: **@Un4v5s8bgsVk9Xp** (冨樫義博), opened 2022-05-24. Self-description:
he will mainly report manuscript progress. That is exactly what the account is.

**477 posts, 2022-05-24 → 2026-08-25.** Raw JSON in `data/raw/tweets/`, one
immutable file per tweet; processed table in `data/processed/tweets.csv`.

## How the corpus was obtained

X's API is paywalled and the site itself requires JS and auth, so acquisition is
two stages that each do what the other cannot:

| stage | source | gives | does not give |
|---|---|---|---|
| discovery | Wayback Machine CDX index of `*/Un4v5s8bgsVk9Xp/status/*` | the set of tweet IDs that existed | any text — modern X captures are empty JS shells with zero CJK content in them |
| hydration | `cdn.syndication.twimg.com/tweet-result` (the endpoint X's own embed widget uses, unauthenticated) | full JSON: text, `created_at`, media, entities, author, counts | discovery — it answers per-ID only |

479 IDs discovered, **479 hydrated, 0 failures**. Two are by other accounts and
are flagged `is_togashi = 0`.

Tweet IDs are Twitter snowflakes, so each carries its own creation timestamp
(`id >> 22` + epoch). Every tweet has an exact time independent of any metadata,
which matters for the §19 requirement to reconstruct what was known at time *t*.

### Completeness is a lower bound

Discovery only sees what the Wayback Machine captured. Deleted posts and
never-archived posts are invisible, and there is no way to enumerate the true
timeline without paid API access. **Treat all counts as a floor.**

One concrete lesson: the first discovery pass filtered CDX rows to
`statuscode == 200` and silently lost 67 tweets, all recent — `twitter.com`
captures are mostly 301 redirects to `x.com`. The fix was to stop filtering and
let hydration be the availability test. Any future discovery change should be
checked against the monthly counts below rather than assumed additive.

## What the corpus actually looks like

| | count | share |
|---|---|---|
| posts by Togashi | 477 | |
| with attached media | ~96% | |
| **image-only (no text at all)** | **288** | **60.4%** |
| with real text | 189 | 39.6% |
| naming a chapter number | 118 | 24.7% |
| naming ≥2 chapters in one post | 26 | max 8 chapters in a single post |

Posting is bursty and tracks production, not the calendar: heavy 2022-05→11,
near-silent through 2023 (2 posts all year), heavy 2024-05→12, sparse 2025,
steady 2026. 30 active months out of 52.

## Findings that the §8 taxonomy does not yet cover

**1. Sixty percent of posts carry no text.** The milestone is often written on a
photo of the manuscript, or is the photo. Any claim that the corpus contains
*N* production events is really a claim about the 189 text-bearing posts unless
OCR or manual annotation is added. This is the single biggest limitation.

**2. The pipeline has rework loops, not a linear ladder.** Observed stages:

    ネーム storyboard
      -> 人物ペン入れ character inking
      -> 背景指定書作成 background specification
      -> [staff work] -> 返却待ち waiting for return
      -> 加筆 touch-ups
      -> 台詞清書 dialogue fair-copy
      -> 原稿完成 manuscript complete
                 ^
                 +-- リテイク retake, sends a chapter backwards (9 posts)

A chapter can reach 完成 and then go back. The §11 sequential-updating design
assumes later observations refine earlier ones; it needs to handle a milestone
being *revoked*.

**3. Waiting states are not milestones.** 返却待ち ("waiting for return", 9
posts) means he is blocked on staff, not that a stage completed. Modelling it as
a completion event would be wrong. The taxonomy needs states as well as events.

**4. He posts explicit countdowns — and these are the highest-value evidence in
the corpus.** Nine posts of the form 「あと N 話」 / 「次の10話分あと9話」
("N chapters to go"). This is a direct statement about batch completion, far
stronger than inferring from stage milestones, and it is absent from the §8
taxonomy entirely. It deserves its own event type.

**5. He states the publication decision is not his.** 2024-09-29:
「掲載のペースは編集部の方に一任しております」 — the publication pace is left
entirely to the editorial department. 2026-04-08: 「420話〜の掲載時期はジャンプ
編集部の発表をお待ちください」. This is the announcement mechanism in his own
words, and it confirms the §12 decision to treat announcements as a separate
class: production readiness and publication timing are decoupled by design.

**6. Two notation eras.** 2022 posts use `No391`, `No 397`, and multi-chapter
status lists with 「…」. 2024–2026 posts use `No.430、` one chapter per line. The
extraction regex must handle `No` with optional dot and optional space. At least
one post contains his own typo (`No388.399…完成` where 388 should be 398), so
chapter numbers need a plausibility check against known chapters.

## Current production state (as of 2026-08-27)

Read straight off the corpus, no modelling:

| chapter | latest reported state | date |
|---|---|---|
| 418 | **published** | 2026-08-24 |
| 419 | referenced, correction posted | 2026-08-25 |
| 420 | 原稿完成 manuscript complete | 2026-02-24 |
| 421 | 原稿完成 | 2026-05-26 |
| 422 | 原稿完成 | 2026-07-01 |
| 423 | 原稿完成 | 2026-07-07 |
| 425 | 原稿完成 | 2026-08-11 |
| 426 | 原稿完成 | 2026-08-25 |
| 428 | 背景指定書作成完了 | 2026-07-03 |
| 430–433 | 人物ペン入れ inking | 2026-04 → 2026-07 |

Manuscripts are complete roughly **eight chapters ahead of publication**, and
inking runs ~15 chapters ahead. Whatever the next batch-start forecast turns out
to be, it will not be constrained by manuscript availability — which is itself a
strong prior signal, and a change from the 2022 era when he was completing
chapters weeks before they shipped.

Whether the current run ends at 419 or 420 is unresolved and matters for the live
forecast target. Do not guess it from the aggregator sites; several of them
carry a "411–420 announced" claim that Togashi's own 2026-04-08 post contradicts.
