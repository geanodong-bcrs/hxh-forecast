#!/usr/bin/env python3
"""Does the taxonomy actually explain the corpus?

Applies data/taxonomy/production_events.yaml to every chapter-scoped phrase in
the text posts and image transcriptions, and reports what it fails to classify.
Unmatched phrases are the taxonomy's gaps - the point is to surface them, not to
report a flattering number.
"""
import csv
import os
import re
from collections import Counter

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
TAX = os.path.join(HERE, "..", "data", "taxonomy", "production_events.yaml")
TW = os.path.join(HERE, "..", "data", "processed", "tweets.csv")
ANN = os.path.join(HERE, "..", "data", "annotations", "image_annotations.confirmed.csv")

CH = re.compile(r"(?:No|NO|Mo)\.?\s*(\d{3})")


def load_taxonomy():
    t = yaml.safe_load(open(TAX, encoding="utf-8"))
    # longest-first, so 人物ペン入れ beats ペン入れ and 背景指定書 beats 背景
    stages = [(p, s["id"]) for s in t["stages"] for p in s["patterns"]]
    stages.sort(key=lambda x: -len(x[0]))
    statuses = [(p, s["id"]) for s in t["statuses"] for p in s["patterns"]]
    statuses.sort(key=lambda x: -len(x[0]))
    return t, stages, statuses


def classify(phrase, stages, statuses, bare_scope):
    stage = next((sid for pat, sid in stages if pat in phrase), None)
    status = next((sid for pat, sid in statuses if pat in phrase), None)
    # a status with no stage is scoped to the whole chapter (see taxonomy)
    if status and not stage:
        stage = bare_scope.get(status)
    return stage, status


def sources():
    out = []
    with open(TW, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["is_togashi"] == "1" and r["has_text"] == "1":
                out.append((r["id_created_at_utc"][:10], r["text_body"], "text"))
    with open(ANN, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["transcribed_text"].strip():
                out.append((r["date"], r["transcribed_text"], "image"))
    return out


def main():
    tax, stages, statuses = load_taxonomy()
    guards = tax["guards"]["chapter_number"]
    bare_scope = tax.get("bare_status_scope", {})

    matched, partial, unmatched = [], [], []
    stage_counts, status_counts, oor = Counter(), Counter(), []

    for date, text, kind in sources():
        text = str(text)
        # split into per-chapter segments: everything from one No.NNN to the next
        marks = [(m.start(), int(m.group(1))) for m in CH.finditer(text)]
        for i, (pos, ch) in enumerate(marks):
            end = marks[i + 1][0] if i + 1 < len(marks) else len(text)
            seg = text[pos:end]
            phrase = re.sub(r"^(?:No|NO|Mo)\.?\s*\d{3}[\s、,．.…]*", "", seg).strip()
            phrase = phrase.split("\n")[0][:30].strip("。 　")
            if not (guards["min"] <= ch <= guards["max"]):
                oor.append((date, ch, phrase))
            if not phrase:
                continue
            stage, status = classify(phrase, stages, statuses, bare_scope)
            rec = (date, ch, phrase, stage, status, kind)
            if stage and status:
                matched.append(rec); stage_counts[stage] += 1; status_counts[status] += 1
            elif stage or status:
                partial.append(rec)
                if stage: stage_counts[stage] += 1
                if status: status_counts[status] += 1
            else:
                unmatched.append(rec)

    total = len(matched) + len(partial) + len(unmatched)
    print("chapter-scoped phrases: %d" % total)
    print("  stage + status   %4d  (%.0f%%)" % (len(matched), 100.0 * len(matched) / total))
    print("  partial          %4d  (%.0f%%)" % (len(partial), 100.0 * len(partial) / total))
    print("  unmatched        %4d  (%.0f%%)" % (len(unmatched), 100.0 * len(unmatched) / total))

    print("\nstages:  " + ", ".join("%s=%d" % kv for kv in stage_counts.most_common()))
    print("statuses:" + ", ".join(" %s=%d" % kv for kv in status_counts.most_common()))

    if oor:
        print("\nchapter numbers outside [%d,%d] (flagged, not dropped): %d"
              % (guards["min"], guards["max"], len(oor)))
        for d, c, p in oor[:6]:
            print("  %s  No.%d  %s" % (d, c, p[:40]))

    if partial:
        print("\npartial matches (stage or status missing) — %d:" % len(partial))
        for d, c, p, st, su, k in partial[:12]:
            print("  %s ch%s  stage=%-20s status=%-14s %s" % (d, c, st, su, p[:34]))

    if unmatched:
        print("\nUNMATCHED — the taxonomy's gaps (%d):" % len(unmatched))
        for d, c, p, _, _, k in unmatched[:20]:
            print("  %s ch%s  %s" % (d, c, p[:46]))


if __name__ == "__main__":
    main()
