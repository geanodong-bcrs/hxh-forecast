#!/usr/bin/env python3
"""Transcribe new image posts (Agents.md §8) — the last hand-run link in the chain.

~60% of Togashi's posts are image-only, and the highest-volume evidence in the
corpus (the page log, 218 observations) exists *only* as photographs. Until now
a human read them. That is fine at the pace of a research session and useless at
the pace of a poller, so this calls the `claude` CLI headless and writes what it
reads as a PROPOSED annotation.

What this does NOT do is promote its own reading. §8 is explicit that an event
read from an image is "an interpretation of a photograph, not a text quote", and
must carry its confirmation status alongside. So:

  image_annotations.csv            MODEL owns  <- this script appends here
  review_queue.csv                 HUMAN owns  <- never touched, by anything
  image_annotations.confirmed.csv  the join, by merge_review.py

A row written here is `proposed` and stays `proposed` until a human says
otherwise. The forecast built on it is labelled `provisional` in the snapshot,
and a later confirmation produces a second, revised snapshot rather than
retroactively editing the first (§16).

Appends only. An existing row for a tweet is never rewritten — re-reading an
image the reviewer has already ruled on would quietly relitigate their verdict.
"""
import argparse
import csv
import glob
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
D = lambda *p: os.path.join(HERE, "..", *p)
ANN = D("data", "annotations", "image_annotations.csv")
MEDIA = D("data", "raw", "tweet_media")
TWEETS = D("data", "processed", "tweets.csv")

COLS = ["tweet_id", "date", "image_type", "pages_shown", "transcribed_text",
        "chapters", "stage_raw", "annotator", "method", "confidence",
        "annotated_at", "status", "notes", "sheet"]

PROMPT = """\
You are transcribing a photograph posted by the manga artist Yoshihiro Togashi,
who documents Hunter x Hunter manuscript production on X. Report only what is
visibly in the image. Do not infer, complete, or guess at partially visible text.

Classify the image as exactly one `image_type`:

  page_log        a manuscript page (or pages) with a handwritten page number,
                  typically circled or in a corner. This is the most common type.
  milestone_text  handwritten or typed text stating a production milestone,
                  e.g. "No.426 ペン入れ 開始!" or "No.415 原稿完成"
  artwork         finished or in-progress art with no page number and no
                  milestone text: covers, colour pieces, commissioned drawings
  unclear         too blurred, cropped or dark to classify
  other           none of the above

Return ONE JSON object and nothing else. No markdown fence, no commentary.

{
  "image_type": "page_log|milestone_text|artwork|unclear|other",
  "pages_shown": "comma-separated page numbers visible, or \\"\\" if none",
  "transcribed_text": "VERBATIM Japanese text visible in the image, or \\"\\"",
  "chapters": "comma-separated chapter numbers stated IN THE IMAGE, or \\"\\"",
  "stage_raw": "the production-stage phrase as written, e.g. 台詞入れ完了, or \\"\\"",
  "confidence": "high|medium|low",
  "notes": "one short English clause on anything ambiguous, or \\"\\""
}

Rules that matter:
- transcribed_text is VERBATIM. Preserve the original Japanese exactly, including
  「」 and !. Never translate it, never normalise it, never tidy it.
- A chapter number goes in `chapters` only if it is written in the image. Do not
  infer one from page numbers or from context.
- Togashi mistypes his own chapter numbers. Transcribe what is written; put the
  discrepancy in `notes`.
- `confidence` is about legibility, not plausibility. Use low when you are
  reading through blur, and say so in notes.
"""


def norm_pages(v):
    """-> the corpus convention: space-separated integers.

    attribute_chapters.py does `pages_shown.split()` then `int(x)`, so a model
    that answers "6, 7" instead of "6 7" crashes the page log. Pull the integers
    out and re-join rather than trusting the model to match a format.
    """
    return " ".join(re.findall(r"\d+", str(v or "")))


def norm_text(v):
    """Verbatim Japanese, flattened to one CSV line with a space.

    §8 requires the verbatim Japanese an event was derived from, so this must not
    inject characters the image did not contain. An earlier version joined lines
    with " / " to match one corpus sample; extract_events.py then strips the
    chapter reference off the front and what survived into source_text_ja was
    "/ 背景指定書 / 完成" — a slash Togashi never wrote. A space collapses the
    line break without adding anything.
    """
    t = str(v or "").strip()
    return re.sub(r"\s*\n+\s*", " ", t)


def existing():
    if not os.path.exists(ANN):
        return {}
    with open(ANN, encoding="utf-8-sig") as fh:
        return {r["tweet_id"]: r for r in csv.DictReader(fh)}


def images_for(tid):
    return sorted(glob.glob(os.path.join(MEDIA, "%s_*" % tid)))


def candidates(include_text_posts=False):
    """Togashi posts with a local image and no annotation row yet.

    Scope note. The existing 299 annotations are exactly the IMAGE-ONLY posts;
    every image post carrying text was deliberately skipped, on the reasoning
    that the text already says what the picture shows. 173 such posts exist.

    That is not strictly safe — §8 rule 1 gives an explicit counterexample, a
    post reading 「No.426 ペン入れ 開始!」 that *also* shows manuscript page 1, so
    the page-log observation in a text post is being lost. But re-reading 173
    historical images is a backfill decision with a real cost attached, not
    something a poller should start doing on its own. Default scope therefore
    matches the corpus; `--include-text-posts` opts into the backfill.
    """
    have = existing()
    out = []
    with open(TWEETS, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["is_togashi"] != "1" or r["tweet_id"] in have:
                continue
            if r["has_text"] == "1" and not include_text_posts:
                continue
            imgs = images_for(r["tweet_id"])
            if imgs:
                out.append((r["tweet_id"],
                            (r["created_at_utc"] or r["id_created_at_utc"])[:10],
                            imgs))
    return sorted(out, key=lambda t: t[1])


def ask_claude(images, timeout=180):
    """One headless claude call per post. Returns a dict, or None on failure."""
    cmd = ["claude", "-p", PROMPT + "\n\nImages:\n"
           + "\n".join(os.path.abspath(p) for p in images)]
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, "claude timed out after %ds" % timeout
    if p.returncode != 0:
        return None, "claude exit %d: %s" % (p.returncode, (p.stderr or "")[:200])

    raw = (p.stdout or "").strip()
    m = re.search(r"\{.*\}", raw, re.S)          # tolerate stray prose or a fence
    if not m:
        return None, "no JSON in output: %s" % raw[:200]
    try:
        return json.loads(m.group(0)), None
    except json.JSONDecodeError as exc:
        return None, "bad JSON (%s): %s" % (exc, m.group(0)[:200])


def append(rows):
    new = not os.path.exists(ANN)
    with open(ANN, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        if new:
            w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0,
                    help="transcribe at most N posts (0 = no limit)")
    ap.add_argument("--dry-run", action="store_true",
                    help="list what would be transcribed and exit")
    ap.add_argument("--tweet", action="append", default=[],
                    help="transcribe these tweet ids only, even if already annotated")
    ap.add_argument("--include-text-posts", action="store_true",
                    help="also transcribe image posts that carry text (see candidates(); "
                         "173 such posts are unannotated — this is the backfill, not "
                         "the routine path)")
    args = ap.parse_args()

    todo = candidates(include_text_posts=args.include_text_posts)
    if args.tweet:
        todo = [(t, "", images_for(t)) for t in args.tweet]
        with open(TWEETS, encoding="utf-8") as fh:
            dates = {r["tweet_id"]: (r["created_at_utc"] or r["id_created_at_utc"])[:10]
                     for r in csv.DictReader(fh)}
        todo = [(t, dates.get(t, ""), i) for t, _, i in todo if i]
    if args.limit:
        todo = todo[:args.limit]

    if not todo:
        print("vision_pass: nothing to transcribe")
        return 0

    print("vision_pass: %d post(s) to transcribe" % len(todo))
    if args.dry_run:
        for tid, d, imgs in todo:
            print("  %s  %s  %d image(s)" % (d, tid, len(imgs)))
        return 0

    now = datetime.now(timezone.utc).isoformat()
    rows, failed = [], []
    for i, (tid, d, imgs) in enumerate(todo, 1):
        print("  [%d/%d] %s %s (%d img)" % (i, len(todo), d, tid, len(imgs)), end=" ")
        sys.stdout.flush()
        got, err = ask_claude(imgs)
        if got is None:
            print("FAILED: %s" % err)
            failed.append((tid, err))
            continue
        row = {
            "tweet_id": tid, "date": d,
            "image_type": str(got.get("image_type", "unclear")).strip(),
            "pages_shown": norm_pages(got.get("pages_shown")),
            "transcribed_text": norm_text(got.get("transcribed_text")),
            "chapters": norm_pages(got.get("chapters")),
            "stage_raw": norm_text(got.get("stage_raw")),
            "annotator": "claude", "method": "vision_model_auto",
            "confidence": str(got.get("confidence", "low")).strip(),
            "annotated_at": now, "status": "proposed",
            "notes": str(got.get("notes", "") or "").strip(),
            "sheet": "",
        }
        rows.append(row)
        print("-> %s %s" % (row["image_type"],
                            row["pages_shown"] or row["transcribed_text"][:30] or ""))

    if rows:
        append(rows)
        print("\nappended %d proposed annotation(s) to %s"
              % (len(rows), os.path.relpath(ANN, D())))
    if failed:
        print("\n%d post(s) could not be transcribed and were left unannotated:" % len(failed))
        for tid, err in failed:
            print("  %s  %s" % (tid, err))
        print("They stay in the queue and will be retried on the next run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
