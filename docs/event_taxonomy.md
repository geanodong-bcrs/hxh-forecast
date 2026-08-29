# Production-Event Taxonomy — Phase 1A step 4

Spec: `Agents.md` §8. Machine-readable: `data/taxonomy/production_events.yaml`.
Coverage test: `python3 scripts/check_taxonomy_coverage.py`.

## Why it isn't the taxonomy the spec originally guessed

`Agents.md` §8 originally proposed a flat list — `inking_complete`,
`dialogue_complete`, `manuscript_complete`, `delivered_to_jump`. Against the real
corpus that shape fails three ways:

1. **It has no way to say "started" or "blocked."** 20 of the observed events are
   `started` and 21 are `awaiting_return` (Togashi blocked on staff). A
   completions-only list drops a fifth of the evidence.
2. **It cannot represent rework.** リテイク appears 5 times and *regresses* a
   chapter that had already reached a later stage.
3. **It has no home for the largest evidence stream.** The 218 page-log posts are
   a production *rate*, not milestones.

So events are **(stage × status)**, plus five non-chapter classes.

`delivered_to_jump` was dropped: it appears nowhere in the corpus. Delivery is
implied by 原稿完成, and inventing an event type we never observe would create a
field that is always null.

## Coverage against the corpus

187 chapter-scoped phrases across 189 text posts and 23 image transcriptions:

| | count | share |
|---|---|---|
| stage + status resolved | 174 | **93%** |
| partial (one of the two) | 7 | 4% |
| unmatched | 6 | 3% |

Stage distribution: `character_inking` 40, `manuscript_complete` 31,
`dialogue` 31, `bg_spec` 29, `chapter_level` 22, `bg_work` 11, `retouch` 11,
`panel_layout` 6.

The 7 partials are truncation artifacts of the checker's 30-character window
(「オレの枠線・フキダシ・」 continues past the cut), not taxonomy gaps. The 6
unmatched are genuinely not production statements — a tankobon page count, two
sentence fragments, a note about a printing error, and 「段ボールの隙間で」
(*in the gap behind the cardboard boxes*), which is where the lost ch. 424
manuscript was eventually found.

## What the coverage test found that inspection missed

Running the check took the first draft from **71% to 93%**. Two real defects:

**A missing stage.** `panel_layout` (枠線・フキダシ — panel borders and empty
speech balloons) exists only in the 2022 posts and I had not noticed it. It sits
between inking and dialogue, which the vocabulary itself confirms: the balloons
are drawn first, then 「フキダシ内の台詞清書」 fair-copies dialogue *inside* them.

**A missing scoping rule.** A status reported with no stage is scoped to the
whole chapter, not to some unnamed stage: 「No391 完成。」 means the chapter is
done. Without `bare_status_scope`, about a quarter of the 2022 corpus failed to
classify — the era where he reports chapter-level state most often.

Neither would have surfaced from reading the taxonomy back to myself. That is the
argument for keeping the coverage test in the loop whenever the taxonomy changes.

## Traps for the extractor

**Match longest-first.** 人物ペン入れ must beat ペン入れ; 背景指定書 must beat 背景.
Naive matching silently mis-stages the entire 2022 era.

**Synonyms are era-dependent.** 2022 says 台詞清書 and 背景効果指定; 2024–26 say
台詞入れ and 背景指定書作成 for the same stages. A literal-string extractor loses
2022 entirely.

**One post → many events.** Up to 8 chapters in a single post, and a post can be
both a milestone and a page log (2025-11-10 reads 「No.426 ペン入れ 開始!」 *and*
shows manuscript page 1).

**Chapter numbers need a plausibility guard.** Togashi mistypes his own
(「No388.399…完成」, where 388 should be 398). Flag, never silently drop.

## Open question for Phase 1B

`bg_work` is performed by **staff**, and `awaiting_return` means Togashi is
blocked rather than working. Staff-blocked time and Togashi-limited time almost
certainly have different distributions, and the 2022 era is full of blocking
while the 2024+ era is not. Whether to model them as one queue or two is a real
modelling decision, not a taxonomy one — but the taxonomy now carries the `actor`
and `is_blocked` fields needed to answer it either way.
