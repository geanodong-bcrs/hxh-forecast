#!/usr/bin/env python3
"""Dataset-derived chapter-readiness summaries for Level 2.

The raw event table remains canonical.  This module deliberately derives a
small, inspectable *progress coordinate* from it instead of overwriting event
history.  A coordinate is useful for comparing analogous chapter positions,
but it is not a claim that production is strictly serial: blocking, review and
retake are returned separately as flags.
"""
from collections import defaultdict
from datetime import date


# Locations are an explicit first model specification, based on the corpus:
# page logs precede the formal character-inking-complete reports, then the
# chapter-stage terms used in the event table.  They are deliberately easy to
# revise and are recorded in every posterior snapshot.
STAGE_END = {
    "panel_layout": 0.30,
    "character_inking": 0.50,
    "bg_spec": 0.60,
    "bg_work": 0.70,
    "dialogue": 0.80,
    "manuscript_complete": 0.90,
}
BLOCKING = {"awaiting_return", "under_review", "retake"}


def _pages(value):
    """Largest manuscript-page number in an event row, or zero."""
    out = 0
    for s in (value or "").split():
        try:
            out = max(out, int(s))
        except ValueError:
            pass
    return out


def progress_of(row):
    """(point estimate, lower bound, upper bound) from one production event.

    A completed stage fixes its endpoint.  Started, in-progress and unlabelled
    reports establish an interval over that stage; the midpoint is only a
    comparison aid.  Page logs are early-stage evidence and preserve the
    user's simple 0.01-per-page coordinate, capped at 19 pages.
    """
    if row.get("event_class") == "page_completed":
        p = min(_pages(row.get("pages_manuscript")), 19) / 100.0
        return p, p, p

    end = STAGE_END.get(row.get("stage"))
    if end is None:
        return None
    start = max((v for v in STAGE_END.values() if v < end), default=0.19)
    status = row.get("status") or ""
    if status == "complete":
        return end, end, end
    if status == "started":
        return start, start, end
    if status == "in_progress":
        return (start + end) / 2.0, start, end
    # Waiting and unlabelled reports establish that this part of the pipeline
    # exists, but not where inside it the chapter currently lies.
    return (start + end) / 2.0, start, end


def coordinate_events(events, asof=None):
    """Event-level observations ``(chapter - 1 + progress, date)``.

    Unlike :func:`states`, this intentionally retains every usable event.  It is
    the input to the all-pairs coordinate likelihood: repeated page logs and
    milestones are observations of the path, not candidates for a single
    chapter's furthest state.  Low-confidence extractions and non-production
    classes stay out.
    """
    out = []
    for r in events:
        if r.get("event_class") not in {"chapter_stage", "page_completed"}:
            continue
        if r.get("confidence") == "low" or not r.get("chapter") or not r.get("event_date"):
            continue
        if asof and date.fromisoformat(r["event_date"]) > asof:
            continue
        try:
            ch = int(float(r["chapter"]))
        except ValueError:
            continue
        p = progress_of(r)
        if p is None:
            continue
        out.append({"event_id": r.get("event_id"), "chapter": ch,
                    "coordinate": round((ch - 1) + p[0], 4),
                    "progress": round(p[0], 4),
                    "date": date.fromisoformat(r["event_date"]),
                    "event_class": r.get("event_class"), "stage": r.get("stage"),
                    "status": r.get("status"), "tweet_id": r.get("tweet_id")})
    return out


def states(events, chapters, asof=None):
    """One furthest-observed state per requested chapter.

    The coordinate never decreases.  Later retakes/waits remain visible in
    ``flags`` and ``latest_flag_date`` rather than falsely erasing work already
    observed.  ``attained_date`` is the date of the evidence supplying p_hat.
    """
    wanted = set(chapters)
    grouped = defaultdict(list)
    all_chapter_events = defaultdict(list)
    for r in events:
        if not r.get("chapter"):
            continue
        try:
            ch = int(float(r["chapter"]))
        except ValueError:
            continue
        if ch not in wanted or r.get("event_class") not in {"chapter_stage", "page_completed"}:
            continue
        if asof and (not r.get("event_date") or date.fromisoformat(r["event_date"]) > asof):
            continue
        all_chapter_events[ch].append(r)
        p = progress_of(r)
        if p is not None:
            grouped[ch].append((r, p))

    out = {}
    for ch in sorted(wanted):
        xs = grouped.get(ch, [])
        best = max(xs, key=lambda x: (x[1][0], x[0].get("event_date") or ""), default=None)
        flags = sorted({r.get("status") for r in all_chapter_events[ch]
                        if r.get("status") in BLOCKING})
        latest_flag = max((r.get("event_date") for r in all_chapter_events[ch]
                           if r.get("status") in BLOCKING and r.get("event_date")), default=None)
        if best is None:
            out[ch] = {"chapter": ch, "p_hat": None, "p_interval": None,
                       "attained_date": None, "source_event": None,
                       "flags": flags, "latest_flag_date": latest_flag}
            continue
        r, (p, lo, hi) = best
        out[ch] = {"chapter": ch, "p_hat": round(p, 4),
                   "p_interval": [round(lo, 4), round(hi, 4)],
                   "attained_date": r.get("event_date"),
                   "source_event": {k: r.get(k) for k in
                                    ("event_id", "event_class", "stage", "status", "tweet_id")},
                   "flags": flags, "latest_flag_date": latest_flag}
    return out


def ordered_trace(events, chapters, upto):
    """Return the ordered batch-readiness path ``[(date, B, detail), ...]``.

    ``B`` is a 0--N sum of chapter-equivalent readiness, not an average.  The
    direct coordinate remains the furthest non-retouch observation for each
    chapter.  Two conservative order constraints then supply inferred floors:

    * any production report for a later chapter puts every earlier chapter at
      least at character-inking complete (0.50);
    * a later chapter's explicit manuscript completion puts every earlier
      chapter at 1.00.  Manuscript completion of the final chapter also sets
      that final chapter to 1.00.

    Retouch is absent from ``STAGE_END`` and therefore cannot move either the
    direct or inferred coordinate.  Re-completions after retouch consequently
    do not manufacture a new stage in this simplified first-pass ordering.
    """
    chapters = sorted(chapters)
    if not chapters:
        return []
    wanted, final_chapter = set(chapters), chapters[-1]
    rows = []
    for row in events:
        if row.get("event_class") not in {"chapter_stage", "page_completed"}:
            continue
        if not row.get("chapter") or not row.get("event_date"):
            continue
        try:
            chapter = int(float(row["chapter"]))
            when = date.fromisoformat(row["event_date"])
        except (ValueError, TypeError):
            continue
        if chapter not in wanted or when > upto:
            continue
        progress = progress_of(row)
        if progress is None:
            continue
        rows.append((when, chapter, progress[0],
                     row.get("stage") == "manuscript_complete" and
                     row.get("status") == "complete"))

    rows.sort()
    direct = {chapter: 0.0 for chapter in chapters}
    reported, manuscripts, out = set(), set(), []
    i = 0
    while i < len(rows):
        when = rows[i][0]
        while i < len(rows) and rows[i][0] == when:
            _, chapter, progress, manuscript_complete = rows[i]
            direct[chapter] = max(direct[chapter], progress)
            reported.add(chapter)
            if manuscript_complete:
                manuscripts.add(chapter)
            i += 1

        inferred_floor = {chapter: 0.0 for chapter in chapters}
        for later in reported:
            for earlier in chapters:
                if earlier < later:
                    inferred_floor[earlier] = max(inferred_floor[earlier], 0.50)
        for later in manuscripts:
            for earlier in chapters:
                if earlier < later:
                    inferred_floor[earlier] = 1.0
        if final_chapter in manuscripts:
            inferred_floor[final_chapter] = 1.0

        ordered = {chapter: min(1.0, max(direct[chapter], inferred_floor[chapter]))
                   for chapter in chapters}
        detail = {
            "direct": dict(direct),
            "inferred_floor": inferred_floor,
            "ordered": ordered,
        }
        value = sum(ordered.values())
        if out and abs(out[-1][1] - value) < 1e-12:
            continue
        out.append((when, value, detail))
    return out


def batch_scope(events, asof=None):
    """Unassigned name/storyboard reports; retained as batch-level capacity."""
    rows = []
    for r in events:
        if r.get("event_class") != "batch_scope" or r.get("stage") != "name":
            continue
        if asof and date.fromisoformat(r["event_date"]) > asof:
            continue
        rows.append({k: r.get(k) for k in ("event_date", "n_chapters", "status", "tweet_id", "source_text_ja")})
    return rows
