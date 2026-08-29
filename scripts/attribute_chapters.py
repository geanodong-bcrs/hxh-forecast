#!/usr/bin/env python3
"""Assign a chapter number to every page_log post.

Method, in order of authority:

  1. ANCHOR   - the reviewer identified the chapter by matching the sketch to
                published pages. Recorded in reviewer_note as "Ch NNN".
  2. CYCLE    - page numbers run up through a chapter then reset. A reset starts
                a new cycle, so a cycle is a chapter's worth of drawing.
  3. ENUMERATE- Togashi does not skip chapters in the page log (reviewer's
                observation, and every anchored cycle confirms it), so an
                unanchored cycle takes the previous cycle's chapter + 1.

The manuscript page number and the published page number differ by up to one
(the reviewer's notes say things like "Ch 407 p. 7 matches p. 8 sketch"). We
keep the MANUSCRIPT number, which is what Togashi writes on the sheet, and never
rewrite it from a note.
"""
import csv
import os
import re
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
ANN = os.path.join(HERE, "..", "data", "annotations", "image_annotations.confirmed.csv")
REV = os.path.join(HERE, "..", "data", "annotations", "review_queue.csv")
OUT = os.path.join(HERE, "..", "data", "processed", "production_pages.csv")

CH_RE = re.compile(r"Ch\.?\s*(\d{3})")
# A gap this long means a production hiatus; never carry a cycle across it.
ERA_GAP_DAYS = 120


def load():
    ann = {r["tweet_id"]: r for r in csv.DictReader(open(ANN))}
    notes = {}
    for r in csv.DictReader(open(REV, encoding="utf-8-sig")):
        n = (r.get("reviewer_note") or "").strip()
        if n:
            notes[r["tweet_id"]] = n
    rows = []
    for tid, a in ann.items():
        if a["image_type"] != "page_log" and not a["pages_shown"].strip():
            continue
        pages = [int(x) for x in a["pages_shown"].split()] if a["pages_shown"].strip() else []
        note = notes.get(tid, "")
        m = CH_RE.search(note)
        rows.append({
            "tweet_id": tid,
            "date": a["date"],
            "pages": pages,
            "anchor_chapter": int(m.group(1)) if m else None,
            "reviewer_note": note,
            "image_type": a["image_type"],
            "milestone_text": a["transcribed_text"],
        })
    rows.sort(key=lambda r: (r["date"], r["tweet_id"]))
    return rows


def build_cycles(rows):
    """A cycle breaks when the page count resets, or across a long hiatus."""
    cycles, cur, prev_max, prev_date = [], [], None, None
    for r in rows:
        d = date.fromisoformat(r["date"])
        reset = False
        if cur:
            gap = (d - prev_date).days
            if gap > ERA_GAP_DAYS:
                reset = True
            elif r["pages"] and prev_max is not None and min(r["pages"]) < prev_max:
                reset = True
        if reset:
            cycles.append(cur)
            cur = []
        cur.append(r)
        if r["pages"]:
            prev_max = max(r["pages"])
        prev_date = d
    if cur:
        cycles.append(cur)
    return cycles


def main():
    rows = load()
    cycles = build_cycles(rows)

    # label cycles from anchors, then fill gaps by enumeration
    labels = [None] * len(cycles)
    conflicts = []
    for i, cyc in enumerate(cycles):
        anchors = {r["anchor_chapter"] for r in cyc if r["anchor_chapter"]}
        if len(anchors) == 1:
            labels[i] = anchors.pop()
        elif len(anchors) > 1:
            conflicts.append((i, sorted(anchors)))
            labels[i] = min(anchors)

    known = [i for i, v in enumerate(labels) if v is not None]
    if not known:
        raise SystemExit("no anchors found")
    for i in range(len(labels)):
        if labels[i] is None:
            ref = min(known, key=lambda k: abs(k - i))
            labels[i] = labels[ref] + (i - ref)

    out = []
    for i, cyc in enumerate(cycles):
        anchored = any(r["anchor_chapter"] for r in cyc)
        for r in cyc:
            out.append({
                "tweet_id": r["tweet_id"], "date": r["date"],
                "chapter": labels[i],
                "pages_manuscript": " ".join(str(p) for p in r["pages"]),
                "n_pages": len(r["pages"]),
                "cycle_id": i + 1,
                "chapter_source": ("reviewer_anchor" if r["anchor_chapter"]
                                   else ("cycle_anchor" if anchored else "enumerated")),
                "image_type": r["image_type"],
                "milestone_text": r["milestone_text"],
                "reviewer_note": r["reviewer_note"],
            })
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)

    # ---- report ----
    print("page-log posts: %d in %d cycles" % (len(out), len(cycles)))
    src = {}
    for r in out:
        src[r["chapter_source"]] = src.get(r["chapter_source"], 0) + 1
    print("chapter source:", src)
    if conflicts:
        print("\nCONFLICTING anchors in a cycle:")
        for i, a in conflicts:
            print("  cycle %d: %s" % (i + 1, a))

    print("\ncycle    chapter  posts  pages          dates")
    for i, cyc in enumerate(cycles):
        pgs = [p for r in cyc for p in r["pages"]]
        anchored = "*" if any(r["anchor_chapter"] for r in cyc) else " "
        print("  %2d %s    %4d   %4d  p%-3s..p%-3s   %s .. %s"
              % (i + 1, anchored, labels[i], len(cyc),
                 min(pgs) if pgs else "-", max(pgs) if pgs else "-",
                 cyc[0]["date"], cyc[-1]["date"]))

    seq = labels
    bad = [(seq[i], seq[i + 1]) for i in range(len(seq) - 1) if seq[i + 1] != seq[i] + 1]
    print("\nchapter sequence contiguous: %s" % ("YES" if not bad else "NO %s" % bad))
    print("wrote %s" % OUT)


if __name__ == "__main__":
    main()
