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
    "retouch": 0.99,
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
