# Panel Annotation Workflow

## Purpose

This document defines the shared human–AI workflow for producing panel-level
Hunter × Hunter annotations. The immediate goals are to:

- make manga evidence easy to locate by chapter, page, and panel;
- support panel statistics such as panels per page (PPP);
- support character-appearance and relationship analysis;
- preserve searchable dialogue for private research;
- provide reviewed inputs for later story analysis and forecasting.

The workflow deliberately separates transcription from interpretation. Panel
records describe what is visible and what text appears. Narrative conclusions,
trivia, theories, and prediction ideas belong in `notes` or in the separate
story-prediction datasets.

## Data locations

| Purpose | Location |
|---|---|
| Working database | `private/story/story_annotations.sqlite` |
| Page images being annotated | `private/story/image_working/` |
| Canonical reviewed chapter CSV | `private/story/chapter_NNN_panel_transcription.csv` |
| Deterministic app export | `private/story/exports/chapter_NNN_panels.csv` |
| Chapter statistics | `data/story/chapter_annotation_stats.csv` |
| Character prototype | `data/story/characters.csv` |
| Chapter character suggestions | `data/story/chapter_character_appearances.csv` |
| Local annotation interface | `http://127.0.0.1:8765/` |

The database and manga images are private working materials. Do not publish
full scripts, page images, or panel crops as part of the public dataset.

## Roles and authority

### Human reviewer

The human reviewer is the authority on the manga evidence. The human:

1. supplies and checks the page images;
2. corrects panel boundaries and reading order;
3. transcribes or verifies exact text;
4. resolves uncertain speakers and character identities when possible;
5. decides whether a small inset is a separate panel;
6. distinguishes real errors from intentional translation wording;
7. approves the chapter for finalization.

Human edits must not be overwritten by rerunning an old seed script.

### AI agent

The AI agent assists with repetitive and structural work. The AI:

1. verifies the image inventory and page sequence;
2. prefills panels, visible characters, locations, visual descriptions, and
   text segments;
3. follows manga reading order: right to left, then top to bottom;
4. flags ambiguity instead of inventing certainty;
5. cleans grammar in descriptions after human review;
6. preserves dialogue verbatim rather than rewriting it;
7. standardizes stable and temporary character IDs across chapters;
8. exports the reviewed CSV and refreshes chapter statistics;
9. verifies counts, page coverage, review status, and valid segment data.

The AI may correct an obvious transcription typo only when the page image makes
the correction unambiguous. Otherwise it should preserve the human entry and
flag the uncertainty.

## Record structure

### Chapter

Each chapter record includes:

- chapter number;
- title;
- printed page count;
- edition, when relevant;
- transcription language.

### Panel

Each panel record includes:

- stable `panel_id`;
- chapter;
- `page_start` and `page_end`;
- order within the page or spread;
- panel type;
- characters shown and mentioned;
- location;
- tags;
- visual description;
- notes;
- review status;
- silent-panel flag.

Normal panel IDs use `chNNN-pPP-OO`, for example `ch353-p08-03`.
A double-page spread includes both pages, for example `ch407-p06-07-04`.

### Text segment

A segment is one independently attributable block of text inside a panel. A
panel can contain zero, one, or many segments.

Create separate segments when:

- two characters speak;
- one character has two separate balloons and preserving the separation is
  useful;
- a panel contains dialogue plus a sound effect;
- a caption, written sign, or interface text is distinct from dialogue;
- speaker or mode differs.

Do not create separate panels merely because a panel contains several balloons.

Common segment modes are:

- `dialogue`;
- `thought`;
- `caption`;
- `sound_effect`;
- other written text when supported by the interface.

Use `no_speaker` for sound effects and unattributed text. Use the character's
stable ID when the speaker is known.

## Core annotation conventions

### Page order

Page images should be named with two-digit chapter-relative page numbers:

```text
NNN-01.png
NNN-02.png
...
NNN-19.png
```

Before prefill, the AI must verify:

1. every expected page exists;
2. filenames are unique and sequential;
3. the visual story advances continuously from one file to the next;
4. printed book page numbers, when visible, agree with the sequence;
5. spreads and intentionally blank page records are identified.

Do not assume that correct-looking filenames prove correct page order.

### Reading order

Number panels right to left, then top to bottom. For irregular layouts, follow
the visual reading path rather than sorting only by panel coordinates.

Before finalization, compare the first and last panel on every page with its
image. This catches one-page shifts that otherwise propagate through a chapter.

### Panel counting

Count each bordered narrative image as a panel. If small reaction panels are
drawn over or inside a larger panel and function as distinct visual beats, count
the page as `1 + n`: one base panel plus the separate reaction panels.

Use `panel_types` to distinguish layouts where appropriate:

- `standard` for an ordinary panel;
- `floating` for an inset or overlaid panel that does not replace the base
  layout panel.

The chapter statistics preserve both total PPP and base-layout PPP so floating
reaction panels can be included without losing the underlying page structure.

When the boundary is genuinely ambiguous, the human reviewer's decision is
final. Apply the same rule consistently within the sequence being compared.

### Transcription

- Transcribe text verbatim.
- Do not summarize, paraphrase, modernize, or improve dialogue.
- Preserve punctuation, symbols, hearts, diamonds, capitalization, and repeated
  lettering when legible.
- Do not silently reconstruct unreadable text. Mark it uncertain in `notes`.
- Split text into segments by speaker and mode, not by sentence count alone.
- Mark a panel silent only when it has no transcribed text.

The final cleanup may fix whitespace, segment mode, speaker ID, and an obvious
lettering typo. It must not rewrite the translation.

### Visual description

Describe only visible artwork. Use simple present tense and neutral wording.

Good:

> Chrollo crouches above Hisoka while holding Skill Hunter open.

Avoid:

> Chrollo anticipates Hisoka's strategy and prepares his next trap.

The second sentence adds interpretation that is not directly visible.

Do not repeat dialogue as context. Do not describe a panel as “the same moment
as the previous panel”; describe what is visible in the current panel.

### Notes

Use `notes` for:

- interpretation;
- uncertain identity;
- translation questions;
- continuity observations;
- trivia candidates;
- visual parallels;
- possible prediction relevance.

Notes are not part of verbatim transcription.

### Characters

- Use the character picker and stable `char_...` ID for known characters.
- Use `crowd` for a visually generic group when individual identity is not
  analytically useful.
- Do not treat organizations or categories such as `military` as individual
  characters. Put them in the visual description, tags, or notes.
- Create a temporary ID for a distinct recurring unidentified person.
- Temporary IDs should describe the identity across its useful scope, not only
  the chapter where it was first noticed.

Examples:

```text
temp_heavens_arena_commentator
temp_heavens_arena_referee
temp_ch352_spectator_01
```

Before finalization, search the neighboring chapters for equivalent temporary
identities. A recurring commentator or referee must keep the same ID across the
sequence.

Community-wiki identities are suggestions, not automatic canon. Verify them
against the manga when the distinction affects analysis.

### Location

Default a new panel to the preceding panel's location, then change it at the
first visible scene transition. Do not keep a narrow sub-location after the
characters visibly leave it.

Use consistent location strings across adjacent chapters. Prefer a location
that is specific enough for retrieval but not more precise than the artwork
supports.

## End-to-end workflow

### Phase 1 — Select and prepare a chapter

**Human**

1. Selects the chapter or sequence to study.
2. Places private page images in `private/story/image_working/`.
3. Renames them `NNN-01` through `NNN-PP`.
4. Notes double-page spreads, missing pages, or unusual pagination.

**AI**

1. Lists the complete image set.
2. Checks sequence continuity and page count.
3. Checks whether the chapter already exists in the database.
4. Makes a recoverable database backup before replacing existing annotations.

### Phase 2 — AI prefill

The AI reads every supplied page and creates a `needs_review` draft.

For each page it should:

1. establish panel boundaries;
2. order panels right to left, then top to bottom;
3. transcribe readable text without summarizing;
4. add separate segments for different speakers or modes;
5. identify visible known characters;
6. use cautious temporary IDs for recurring unknowns;
7. carry forward the location until a visible transition;
8. write visual-only descriptions;
9. leave uncertainty for human review.

After prefill, the AI reports the draft panel and segment counts and opens a
versioned annotation URL such as:

```text
http://127.0.0.1:8765/?v=ch353-prefill
```

### Phase 3 — Human review

The human works page by page in the local interface.

For every panel, check:

- panel boundary and order;
- text against the page image;
- segment speaker and mode;
- characters shown;
- location;
- silent-panel status;
- visual description;
- uncertain or interpretive material moved to `notes`.

The human may review a partial range and ask the AI to clean it before
continuing. The handoff should name the completed range explicitly, for example:

> Pages 1–7 are finished. Clean those pages and verify pages 8–19.

### Phase 4 — Partial AI cleanup

When only part of a chapter is complete, the AI must preserve the human's panel
structure and transcription in that range. It may:

- correct grammar in visual descriptions;
- remove interpretation from visual descriptions;
- normalize character IDs;
- correct segment modes and speakers;
- add missing generic character tags such as `crowd`;
- check page-to-image alignment.

It must not mark the chapter reviewed or regenerate the unfinished pages from
an old seed.

If a page shift is found, identify the first mismatched page. Recompare every
remaining page against the same-numbered image; do not blindly shift the entire
remainder, because later pages may already align.

### Phase 5 — Final human approval

The human finishes the remaining pages and explicitly requests final cleanup.
That request authorizes the AI to perform the final review pass and mark the
chapter reviewed.

### Phase 6 — Final AI cleanup

The AI:

1. cleans grammar in visual descriptions;
2. removes story context and interpretation from visual descriptions;
3. preserves verbatim dialogue and thoughts;
4. fixes obvious speaker and mode errors;
5. normalizes character order and recurring temporary IDs;
6. verifies location continuity;
7. verifies silent-panel flags against text segments;
8. confirms pages, panel IDs, and panel order are complete;
9. sets every panel in the approved chapter to `reviewed`;
10. exports the reviewed chapter CSV;
11. refreshes chapter statistics.

The AI should use a chapter-specific finalization script when edits involve more
than a few records. The script makes the cleanup reproducible and reviewable.

### Phase 7 — Export and statistics

Finalization produces both:

```text
private/story/chapter_NNN_panel_transcription.csv
private/story/exports/chapter_NNN_panels.csv
```

Then run:

```sh
python3 scripts/update_story_annotation_stats.py
```

Only chapters whose exported rows are all `reviewed` enter
`data/story/chapter_annotation_stats.csv`.

Statistics include:

- printed pages;
- total panels;
- floating panels;
- base-layout panels;
- total PPP;
- base-layout PPP;
- text and silent panels;
- text segments;
- transcribed English words;
- unique characters shown and mentioned.

## Final quality checklist

### Image and page integrity

- [ ] Every expected image exists.
- [ ] Images are in chapter-relative page order.
- [ ] Every printed page is represented once.
- [ ] Spreads use the correct `page_start` and `page_end`.
- [ ] The first and last panel on every page match the same-numbered image.

### Panel structure

- [ ] Panel order follows right-to-left, top-to-bottom reading.
- [ ] Insets and floating reaction panels follow the agreed counting rule.
- [ ] Panel IDs are unique and match their page and order.
- [ ] No accidental extra panel remains.
- [ ] No visible panel is omitted.

### Text

- [ ] Dialogue and thoughts are verbatim.
- [ ] Different speakers use different segments.
- [ ] Segment modes are correct.
- [ ] Sound effects use `no_speaker` unless attribution is meaningful.
- [ ] Silent panels contain no text segments.
- [ ] Non-silent panels contain at least one segment.

### Annotation

- [ ] Visual descriptions contain only visible information.
- [ ] Interpretive material is in `notes`.
- [ ] Known characters use stable IDs.
- [ ] Recurring temporary identities are consistent across chapters.
- [ ] Generic groups use `crowd` rather than invented individual identities.
- [ ] Locations change at the correct visible transition.

### Finalization

- [ ] All panels are marked `reviewed` only after human approval.
- [ ] Canonical and deterministic CSV exports exist.
- [ ] Export rows parse successfully.
- [ ] Page and panel counts match the database.
- [ ] Statistics were refreshed.
- [ ] The final PPP and word count come from the reviewed export.

## Recovery and error handling

### An old seed overwrites human edits

Stop immediately. Restore the latest database backup or recover the reviewed
rows from the most recent chapter CSV. Seed scripts are for initial drafts and
must not be rerun after human review without an explicit preservation plan.

### A page is shifted

Compare the suspect annotation with the same-numbered image and its neighbors.
Find the earliest mismatch, then verify each later page independently. Insert,
delete, or move only the affected page records.

### An extra panel was added

Confirm the exact page and panel visually, delete its text segments first when
required by the database relationship, remove the panel, and renumber later
panels on that page.

### A recurring person has multiple temporary IDs

Choose one scope-appropriate stable temporary ID, replace it in both
`characters_on_panel` and text-segment speakers, then re-export every affected
reviewed chapter.

### The local page expires or stops responding

Restart the annotator:

```sh
python3 scripts/story_annotator.py --no-open
```

Reload the chapter with a new version query to avoid stale browser state:

```text
http://127.0.0.1:8765/?v=chNNN-reloaded
```

## Relationship to story forecasting

The panel database is an evidence-location and quantitative-analysis layer. It
does not itself constitute a story forecast. Reviewed panel records can support:

- character co-appearance and interaction graphs;
- dialogue and mention searches;
- location and scene retrieval;
- PPP and visual-density comparisons;
- identification of recurring motifs or unresolved details;
- later chapter summaries, thread events, trivia, and prediction hypotheses.

Interpretive story records remain governed by
`docs/story_prediction_dataset.md`. A panel annotation may point analysts to the
relevant evidence, while the story dataset records the reviewed interpretation
and the prediction history.
