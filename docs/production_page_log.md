# The Production Page Log

`data/processed/production_pages.csv` — 218 posts, chapters **397–426**, from
2022-05-25 to 2025-11-10. The single richest evidence stream in the project.

## What it is

Togashi photographs finished manuscript pages on his own branded paper, with the
page number handwritten in the corner. Reading those numbers gives a near-daily
record of *which pages of which chapter were drawn on which day* — a production
**rate**, not a sparse sequence of milestones.

## How chapters were assigned

Three sources, in order of authority:

| source | posts | how |
|---|---|---|
| `reviewer_anchor` | 111 | Human matched the sketch to published pages and recorded "Ch NNN" |
| `cycle_anchor` | 66 | In the same page cycle as an anchored post |
| `enumerated` | 41 | Unanchored cycle; takes previous cycle + 1 |

Enumeration is safe because Togashi does not skip chapters in the page log —
the reviewer's observation, and every one of the 30 cycles bears it out. The
resulting chapter sequence 397→426 is **contiguous with no conflicts**.

Manuscript page numbers are kept as Togashi writes them. They differ from
published page numbers by up to one (the reviewer's notes record cases like
"Ch 407 p. 7 matches p. 8 sketch"), and are never rewritten from a note.

## Validation: the enumerated cycles were confirmed independently

The eight cycles assigned purely by enumeration were checked against
`人物ペン入れ開始` / `完了` text posts that played **no part** in the attribution:

| chapter | 開始 | pages drawn | 完了 |
|---|---|---|---|
| 419 | 2024-09-09 | 09-10 → 09-19 | 2024-09-22 |
| 420 | 2024-09-23 | 09-25 → 09-28 | 2024-09-29 |
| 421 | 2024-09-30 | 10-01 → 10-08 | 2024-10-09 |
| 422 | — | 10-10 → 10-12 | 2024-10-19 |
| 423 | — | 10-21 → 10-27 | 2024-10-28 |
| 424 | 2024-10-29 | 10-30 → 11-05 | — |
| 425 | — | 2025-10-15 → 10-23 | 2025-11-09 |
| 426 | — | 2025-11-10 | image reads 「No.426 ペン入れ 開始!」 |

**8 of 8** fall strictly inside their start/complete bracket. Chapter 426 is the
cleanest case: enumeration assigned it with no anchor, and the milestone written
on that very image says 426.

## What the rate looks like

| era | posts | pages | pages / posting-day | pages / calendar-day |
|---|---|---|---|---|
| 2022, ch 397–404 | 88 | 102 | 1.16 | 0.71 |
| 2024, ch 405–424 | 124 | 257 | 2.07 | 1.37 |
| 2025+, ch 425–426 | 6 | 7 | 1.17 | 0.26 |

Output roughly **doubled** between 2022 and 2024. Median cycle length is
**7 calendar days per chapter**, and chapters run about 17–19 manuscript pages.

### Coverage caveat

Within a chapter's observed span the log is essentially a census — median
coverage **100%**, i.e. while he is posting he posts every page. But the span
often starts mid-chapter (p4, p6) and sometimes stops early, so page counts are
a **lower bound** on pages drawn, and the rate figures describe posting-while-
active rather than true throughput. Do not treat `n_pages` as chapter length.

## Things the §8 taxonomy still does not cover

**1. `page_completed` is a rate event, not a milestone.** It has a page number
and belongs to a chapter, and there are hundreds of them. Nothing in the current
taxonomy holds this shape.

**2. An image can be two things at once.** The 2025-11-10 post carries the
milestone 「No.426 ペン入れ 開始!」 *and* shows manuscript page 1. `image_type` is
single-valued, which under-describes it — the row keeps both fields, but the type
should become a set, or gain a `has_page_log` flag.

**3. Work is not strictly sequential.** On 2024-11-08, while drawing ch 424, he
posted 「No.408、加筆完了。修正指定書作成完了。」 — going back to touch up ch 408.
A chapter can receive work long after its pages are drawn.

**4. Production can be disrupted.** 2025-10-12: 「No.424の原稿捜索中。」 — *searching
for the No.424 manuscript*, which had gone missing. This is a distinct event
class (disruption) with obvious forecasting relevance, and it partly explains the
near-silent 2025.

## Provenance

Every row carries `chapter_source` so anchored and enumerated attributions stay
distinguishable, per Agents.md §8's rule that inference is never recorded as
fact. Human confirmations live in `data/annotations/review_queue.csv`, which no
script writes; the merge into
`data/annotations/image_annotations.confirmed.csv` pins them so a later vision
pass cannot overwrite them.
