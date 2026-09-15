# Story Prediction Dataset

## Purpose

This dataset represents the story's changing state so that narrative forecasts
can be made, preserved, and evaluated. It is separate from the publication and
production forecast. It does not attempt to reproduce the manga as scripts,
panel images, or exhaustive panel descriptions.

The first version has four tables:

1. `data/story/chapter_story_annotations.csv` — one narrative assessment per
   chapter.
2. `data/story/story_threads.csv` — the continuing objectives, conflicts,
   mysteries, threats, relationships, promised events, journeys, and processes
   that the story has opened.
3. `data/story/chapter_thread_events.csv` — what a chapter does to a thread.
4. `data/story/story_predictions.csv` — timestamped predictions that must not be
   rewritten after later chapters appear.

Controlled values live in `data/taxonomy/story_annotations.yaml`.

## Copyright and source policy

- Write short, original summaries. Do not copy a fan site's synopsis.
- Do not store or publish full chapter scripts.
- Do not archive manga panels in this dataset.
- Use chapter and page references as evidence pointers.
- Quote dialogue only when its exact wording is necessary, and keep quotations
  brief. Record which edition or translation was consulted in `notes` when the
  wording affects the interpretation.
- A citation does not by itself make extensive reproduction permissible.

Fan sites and community wikis can be used to locate relevant material, but the
manga is the evidence for story annotations. Community classifications such as
arc boundaries must be identified as conventions when they are disputed.

## Annotation workflow

### 1. Annotate the chapter

Add one row to `chapter_story_annotations.csv`.

- `chapter` is the canonical chapter number and joins to
  `data/processed/chapters.csv`.
- `arc` is copied mechanically from the canonical chapter dataset for convenient
  filtering. Do not edit it in this table; correct the canonical source instead.
- `short_summary` is one or two neutral sentences written for this project.
- `narrative_function` uses one controlled value. It records the chapter's
  dominant function, not every function present.
- `phase_assessment` is short, provisional expert language such as
  `late expansion` or `early convergence`. Leave it blank when the evidence is
  insufficient. Do not record a percentage merely to create precision.
- `major_state_change` describes the most consequential irreversible or
  decision-relevant change, if any.
- `notes` is free-form. Trivia candidates, visual observations, parallels,
  doubts, translation issues, and ideas for public posts belong here.

### 2. Create or update story threads

Each durable story question receives a stable `thread_id` in
`story_threads.csv`. Use lowercase snake case with an arc prefix where helpful,
for example `sw_woble_survival`. Do not create a thread for every conversation;
create one when the story has established an objective, conflict, mystery, or
other expectation that can meaningfully advance or resolve.

`current_status` is a convenience view of the latest reviewed state. Historical
state changes belong in `chapter_thread_events.csv` and must not be erased when
this field changes.

### 3. Record thread events

Add a row to `chapter_thread_events.csv` only when a chapter materially refers
to or changes a thread. Use an `event_id` such as `STE-000001`.

- `event_type` describes the change.
- `evidence_summary` is a brief original description of the evidence.
- `page_reference` points to the relevant chapter pages. Page numbering can
  vary by edition; identify the edition in `notes` when necessary.
- `confidence` concerns the interpretation, not confidence that the chapter
  exists.

Absence is normally not an event. A thread going unmentioned is derived from
the lack of rows rather than recorded repeatedly as `deferred`. Use `deferred`
only when the story explicitly postpones or redirects it.

### 4. Register predictions

Predictions live separately from annotations. Use a stable ID such as
`SP-000001`, an ISO 8601 timestamp, and a probability from 0 through 1.
`forecast_after_chapter` defines the information cutoff.

Never edit a prediction's probability or reasoning after observing a later
chapter. A changed belief is a new prediction whose `notes` points to the prior
prediction. When the target resolves, fill in `actual_outcome`,
`resolved_chapter`, and `status` without changing the original forecast.

Avoid literal probabilities of 0 or 1 unless the outcome is logically settled.

## Human and AI roles

AI may draft summaries, propose thread events, surface parallels, or add trivia
candidates to `notes`. Such rows begin with `review_status = ai_proposed`.

A human reviewer checks the manga evidence before changing the status to
`human_reviewed`. Interpretive disagreement is preserved as `disputed`; it is
not silently overwritten. `annotator` identifies the person or system that made
the current proposal, and `reviewed_at` uses an ISO 8601 timestamp.

Only `human_reviewed` records should be used in published numerical summaries
or formal story forecasts by default.

## Historical comparison and leakage

Completed arcs are useful comparisons, but their later chapters must be hidden
when simulating an earlier forecast. An assessment made "after chapter 250"
may use only material through chapter 250. Do not label that state using
knowledge of the later climax or ending.

The safest procedure is:

1. choose the historical cutoff;
2. expose annotations and thread events only through that cutoff;
3. produce and save the assessment or prediction;
4. reveal later chapters and score the result.

This makes the structured expert forecast auditable without pretending that a
small number of completed arcs constitutes a large statistical sample.

## Example rows (documentation only)

The CSV files intentionally start empty. Examples below illustrate shape and
must not be treated as reviewed annotations.

```csv
chapter,arc,short_summary,narrative_function,phase_assessment,major_state_change,notes,annotator,review_status,reviewed_at
407,"Succession Contest arc","Original factual summary written after review",complication,"provisional phase language","Concise state change","Possible trivia goes here",human0,human_reviewed,2026-09-14T00:00:00-04:00
```

```csv
event_id,chapter,thread_id,event_type,importance,evidence_summary,page_reference,confidence,notes,annotator,review_status,reviewed_at
STE-000001,407,example_thread,advanced,major,"Original evidence summary","ch. 407, pp. X-Y",high,"Example only",human0,human_reviewed,2026-09-14T00:00:00-04:00
```

## Mechanical prefill

Run `python3 scripts/sync_story_chapters.py` after the canonical chapter dataset
changes. It adds missing chapters and refreshes their arc labels without
overwriting summaries or other human-authored fields. It also removes no rows,
so a canonical-data problem cannot silently delete story annotations.
