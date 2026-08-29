# Validation Findings — Phase 1A step 1

## Why these two sources corroborate rather than echo

| | Hunterpedia | jajanken.net |
|---|---|---|
| Language / community | English fan wiki | Japanese WSJ magazine index |
| Date recorded | **on-sale** date | **cover** date (URL slug) |
| Issue identity | cumulative counter (`#2854`) + year issue no. | year issue no. + table of contents |
| Extra signal | arc, page count, English title | 掲載順 (TOC position), colour-page flag |

They record different quantities from different traditions, so agreement on
issue assignment is real evidence, not one copying the other.

## Checks run

**1. Internal consistency of the chapter dataset.** Dates and the cumulative
issue counter are both strictly increasing across all 418 chapters; no gaps in
chapter numbering; no missing dates or issue numbers.

**2. Sequence agreement.** For every consecutive pair of chapters, the gap in
Hunterpedia's cumulative issue counter was compared with the gap in jajanken's
independently-built issue sequence. **0 disagreements in 417 steps.** This is
the strongest single result: the two sources agree on exactly how many WSJ
issues elapsed between every pair of chapters, across 28 years.

**3. Issue assignment.** 415 of 416 chapters present in both sources agree on
year + issue number. The one mismatch is jajanken's own typo (below).

**4. Cover-vs-on-sale offset.** Every departure from the standard 14 days is now
accounted for by a named mechanism; **0 unexplained offsets remain.**

## Errors found and handled

### Hunterpedia: chapter 371 date wrong (corrected)
Recorded as 2018-01-26, a **Friday** — WSJ ships Monday, or Saturday when a
Monday holiday intervenes, and Jan 2018 had neither. Both the jajanken cover
date (2018-02-12 − 14 days) and contemporary Japanese coverage give
**2018-01-29**. Corrected via `data/corrections/chapter_corrections.csv`; the
raw snapshot is untouched and the original value is retained in
`publication_date_jp_raw_value`. The correction restores the standard 14-day
offset, which is independent confirmation that it is right.

This was the *only* date error found in 418 chapters.

### jajanken: two printed chapter numbers wrong (not corrected — we don't use them)
- `No.149` printed twice: at 2002年22・23号 (should be **146**) and at 2002年32号.
- `No.260` printed twice: at 2006年11号 and at 2007年45号 (should be **261**).

In both cases the issue *slot* agrees with Hunterpedia; only jajanken's printed
label is wrong. Since we take chapter numbers from Hunterpedia and use jajanken
only for issue identity, these do not propagate. The validation script keeps the
first occurrence and reports the collision rather than letting a later row win.

### jajanken: two non-chapter rows (correctly excluded)
2013年1号 and 2013年2号 carry the *Kurapika Tsuioku-hen* (クラピカ追憶編) one-shots.
These are not numbered chapters and are excluded from `chapters.csv`. They are
worth remembering: they are Togashi output that is **not** a Hunter × Hunter
chapter, so they should not count as publication events, but they may matter as
production-capacity evidence later.

### The 33 Saturday releases are not errors
Japanese magazines move the on-sale date to the preceding Saturday when the
normal Monday is a national holiday. These produce the 5-day/9-day interval
pairs in the raw data and a 16-day cover offset. They are real and the calendar
must keep them.

## Known weakness carried forward

`wsj_issues.csv` has genuine on-sale dates only for the 418 issues anchored to an
HxH chapter. The other 1,009 use `cover_date − 14 days`, which is demonstrably
wrong in New Year windows (observed offsets there run 17–31 days). Any forecast
that resolves on a non-HxH issue date inherits that error. Fixing it needs a
Japanese retail/publisher source with per-issue 発売日.
