# Data Dictionary — Phase 1A

Two processed datasets, plus a validation report. All are rebuildable from
`data/raw/` by re-running the scripts; nothing here is hand-edited.

---

## `data/processed/chapters.csv` — canonical publication record (Agents.md §5)

418 rows, chapters 1–418, 1998-03-02 → 2026-08-24.

### Identity
| column | meaning |
|---|---|
| `chapter` | Chapter number as printed (`No.NNN`). Primary key. |
| `title_en` | English chapter title (Hunterpedia). |
| `arc` | Story arc. |
| `page_length` | Pages, where recorded. |

### Dates — deliberately *not* interchangeable (§5 "do not conflate")
| column | meaning |
|---|---|
| `publication_date_jp` | **The modelling target.** Day the Japanese WSJ issue carrying the chapter went on sale. |
| `na_release_date` | Viz/English simulpub date. Present only for the simulpub era. Not a forecast target. |
| `volume_release_date` | Tankōbon release. A different event; never use as a publication date. |
| `date_provenance` | `hunterpedia` or `corrected`. |
| `publication_date_jp_raw_value` | Original value when superseded by a correction. |
| `correction_note` | Source URL justifying the correction. |

### Issue calendar (§4)
| column | meaning |
|---|---|
| `wsj_issue_cumulative` | WSJ's running issue counter across its whole history (#1487 … #2854). Increments by exactly 1 per published issue, so differences count *issues*, not weeks. |
| `wsj_issue_year` | Year the issue belongs to. **Not always the on-sale year** — late-December issues carry the following year (e.g. ch. 400 on sale 2022-12-26 is *2023* No. 4-5). |
| `wsj_issue_no` | Issue number within the year; hyphenated when combined (`4-5`). |
| `is_combined_issue` | 1 for a 合併号, which occupies two calendar weeks but one issue slot. |

### Intervals
| column | meaning |
|---|---|
| `prev_chapter_pub_date` | Previous chapter's on-sale date. |
| `interval_days` | Calendar days since the previous chapter. |
| `interval_issues` | **Issues** since the previous chapter. The honest unit: `interval_days` conflates combined issues and New Year breaks with actual publication skips. |
| `issues_skipped_before` | `interval_issues - 1`. Zero inside an uninterrupted run. |

### Batch structure (§3)
| column | meaning |
|---|---|
| `run_id` | Uninterrupted stretch of issues carrying a chapter. Breaks at `interval_issues >= 4`. 28 runs. |
| `batch_id` | Batch. Equals the run, except runs longer than 15 chapters are split into 10-chapter batches. 49 batches, 16 in the modeling era. |
| `position_in_batch` | 1-indexed position. |
| `is_batch_start` | 1 for the first chapter of a batch — the primary prediction target `W_b`. |
| `batch_size` | Chapters in this batch (in-progress batches under-count). |
| `issues_gap_before_batch` | Issues elapsed before this batch began. **0** when the batch continues a run with no wait. This is the quantity the batch-start prior models, and it is bimodal. |
| `prev_batch_start_date`, `interval_from_prev_batch_days` | Batch-to-batch spacing. |
| `modeling_era` | 1 for chapters ≥ 261 (2007+), the burst regime the prior is fitted on. 0 for the 1998–2006 weekly era, which is retained for description and trend work but excluded from the prior. |

Splitting runs 291–310 and 311–340 puts three genuine zeros into
`issues_gap_before_batch` — see `batch_segmentation.md`.

### Provenance (§27)
`source_url`, `source_type`, `source_revid`, `source_rev_timestamp`,
`release_date_raw` (the unparsed source string, so parsing can be re-audited).

---

## `data/processed/wsj_issues.csv` — the publication calendar (§4)

1,427 issues, 1997–2026, of which 123 are combined. This is the set of slots a
forecast is allowed to land on; calendar weeks without an issue are not eligible.

| column | meaning |
|---|---|
| `seq` | Position in the global issue sequence. |
| `issue_year`, `issue_label`, `issue_no_first`, `issue_no_last`, `is_combined` | Issue identity. |
| `cover_date` | Nominal date printed on the issue (jajanken). |
| `on_sale_date` | Actual on-sale date. |
| `on_sale_provenance` | `observed_hunterpedia` (418 issues, anchored to a real chapter) or `inferred_cover_minus_14d` (1,009). |
| `days_to_next_issue` | Spacing to the next slot — 7 normally, 14 after a combined issue. |
| `hxh_chapter`, `hxh_issue_cumulative` | The HxH chapter in this issue, when there is one. |

⚠️ The 1,009 inferred on-sale dates use a flat 14-day offset, which is wrong in
New Year windows. Only the 418 anchored dates are trustworthy at day resolution.
Fixing this properly needs per-issue on-sale dates from a Japanese retail source.

---

## `data/processed/validation_report.csv`

Per-chapter comparison against jajanken. Key column `offset_explanation`:

| value | n | meaning |
|---|---|---|
| `standard` | 344 | cover − on-sale = 14 days. |
| `holiday_saturday_shift` | 30 | 16 days: a Monday national holiday pushed the issue to the preceding Saturday. |
| `new_year_window` | 23 | New Year issues carry stretched nominal dates. |
| `combined_issue` | 19 | 合併号 nominal-date stretch. |
| `unexplained` | **0** | Anything here is a candidate data error. |
