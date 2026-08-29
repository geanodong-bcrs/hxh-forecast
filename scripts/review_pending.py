#!/usr/bin/env python3
"""What still needs a human verdict -> data/annotations/review_pending.csv

The ownership boundary in merge_review.py is strict: review_queue.csv is HUMAN
owned and "never written by any script, including this one". Automation must not
breach that — but it does have to answer "what has the vision pass proposed that
I haven't ruled on?", or auto-transcribed readings pile up unreviewed and the
forecast stays provisional forever.

So this writes a SEPARATE, script-owned file in exactly review_queue.csv's column
layout, with the model's proposal filled in and `verdict` left blank. Reviewing
is then: open it, fill in verdicts, paste the rows into review_queue.csv. The
human's file is still only ever written by the human.

Rows are ordered newest first — a proposed reading about the batch being
forecast right now is worth more than one from 2022.
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
D = lambda *p: os.path.join(HERE, "..", *p)
CONFIRMED = D("data", "annotations", "image_annotations.confirmed.csv")
OUT = D("data", "annotations", "review_pending.csv")

COLS = ["tweet_id", "date", "priority", "my_image_type", "my_pages", "my_text",
        "my_confidence", "my_note", "verdict", "fix_image_type", "fix_pages",
        "fix_text", "reviewer_note", "image", "url"]


def main():
    if not os.path.exists(CONFIRMED):
        print("review_pending: no confirmed file yet; run merge_review.py first")
        return 0

    with open(CONFIRMED, encoding="utf-8-sig") as fh:
        rows = [r for r in csv.DictReader(fh) if r.get("status") != "confirmed"]
    rows.sort(key=lambda r: r.get("date", ""), reverse=True)

    out = []
    for r in rows:
        out.append({
            "tweet_id": r["tweet_id"], "date": r["date"],
            # a low/medium-confidence read is where a human actually adds value
            "priority": "CHECK" if r.get("confidence") in ("low", "medium") else "",
            "my_image_type": r.get("image_type", ""),
            "my_pages": r.get("pages_shown", ""),
            "my_text": r.get("transcribed_text", ""),
            "my_confidence": r.get("confidence", ""),
            "my_note": r.get("notes", ""),
            "verdict": "", "fix_image_type": "", "fix_pages": "", "fix_text": "",
            "reviewer_note": "",
            "image": "review/thumbs/%s.jpg" % r["tweet_id"],
            "url": "https://x.com/Un4v5s8bgsVk9Xp/status/%s" % r["tweet_id"],
        })

    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(out)

    n_check = sum(1 for r in out if r["priority"] == "CHECK")
    print("review_pending: %d awaiting a verdict (%d flagged CHECK) -> %s"
          % (len(out), n_check, os.path.relpath(OUT, D())))
    if out:
        print("  newest: %s  %s  %s"
              % (out[0]["date"], out[0]["my_image_type"],
                 out[0]["my_pages"] or out[0]["my_text"][:40]))
        print("  Fill in `verdict` (ok/fix/unsure) and paste rows into "
              "review_queue.csv, then re-run run_update.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
