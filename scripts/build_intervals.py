#!/usr/bin/env python3
"""Phase 1B step 10 — production-event -> publication intervals (Agents.md §9)

For every chapter-scoped event on a chapter that has actually published, record
the interval from the event to that chapter's on-sale date. Individual
observations are preserved; §9 forbids collapsing them to an average.

Output:
  data/processed/production_intervals.csv   one row per observation
plus a distribution report per stage, broken out BY BATCH — because the batches
do not share a regime and pooling them would manufacture a distribution that
describes none of them.
"""
import csv
import os
from collections import defaultdict
from datetime import date

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
D = lambda *p: os.path.join(HERE, "..", *p)
OUT = D("data", "processed", "production_intervals.csv")

STAGE_ORDER = ["name", "character_inking", "panel_layout", "bg_spec", "bg_work",
               "dialogue", "retouch", "manuscript_complete", "chapter_level"]


def skew(x):
    x = np.asarray(x, float)
    if len(x) < 3 or x.std() == 0:
        return float("nan")
    return float(((x - x.mean()) ** 3).mean() / x.std() ** 3)


def main():
    pub, batch, pos = {}, {}, {}
    with open(D("data", "processed", "chapters.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            c = int(r["chapter"])
            if r["publication_date_jp"]:
                pub[c] = date.fromisoformat(r["publication_date_jp"])
                batch[c] = int(r["batch_id"])
                pos[c] = int(r["position_in_batch"])

    rows = []
    with open(D("data", "processed", "production_events.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["event_class"] not in ("chapter_stage", "page_completed"):
                continue
            if r["confidence"] == "low" or not str(r["chapter"]).strip():
                continue
            c = int(float(r["chapter"]))
            if c not in pub:
                continue                      # not yet published: right-censored
            d = date.fromisoformat(r["event_date"])
            stage = r["stage"] or ("page_log" if r["event_class"] == "page_completed" else "")
            rows.append({
                "chapter": c, "batch_id": batch[c], "position_in_batch": pos[c],
                "stage": stage, "status": r["status"],
                "event_date": r["event_date"], "publication_date": pub[c].isoformat(),
                "lag_days": (pub[c] - d).days,
                "event_id": r["event_id"], "confidence": r["confidence"],
                "extraction_method": r["extraction_method"],
            })

    rows.sort(key=lambda r: (r["chapter"], r["event_date"]))
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print("observations: %d over %d published chapters"
          % (len(rows), len({r["chapter"] for r in rows})))
    print("negative lags (event AFTER publication): %d"
          % sum(1 for r in rows if r["lag_days"] < 0))

    # ---- per stage, first-occurrence only, split by batch ----
    print("\n=== lag to publication, days — first event of each stage per chapter ===")
    print("%-20s %-8s %4s %6s %6s %6s %6s %6s %7s"
          % ("stage", "batch", "n", "min", "p25", "med", "p75", "max", "skew"))
    by = defaultdict(list)
    firsts = {}
    for r in rows:
        k = (r["chapter"], r["stage"])
        if k not in firsts or r["event_date"] < firsts[k]["event_date"]:
            firsts[k] = r
    for r in firsts.values():
        by[(r["stage"], r["batch_id"])].append(r["lag_days"])

    for stage in STAGE_ORDER + ["page_log"]:
        batches = sorted(b for (s, b) in by if s == stage)
        if not batches:
            continue
        allv = []
        for b in batches:
            v = np.array(by[(stage, b)])
            allv += list(v)
            print("%-20s %-8s %4d %6d %6.0f %6.0f %6.0f %6d %7.2f"
                  % (stage, b, len(v), v.min(), np.percentile(v, 25),
                     np.median(v), np.percentile(v, 75), v.max(), skew(v)))
        if len(batches) > 1:
            v = np.array(allv)
            print("%-20s %-8s %4d %6d %6.0f %6.0f %6.0f %6d %7.2f  <- POOLED"
                  % ("", "ALL", len(v), v.min(), np.percentile(v, 25),
                     np.median(v), np.percentile(v, 75), v.max(), skew(v)))
        print()

    # ---- does lag depend on position within the batch? ----
    print("=== position-in-batch effect (manuscript_complete) ===")
    mc = [r for r in firsts.values() if r["stage"] == "manuscript_complete"]
    for b in sorted({r["batch_id"] for r in mc}):
        s = sorted((r["position_in_batch"], r["lag_days"]) for r in mc if r["batch_id"] == b)
        if len(s) > 2:
            p = np.array([x[0] for x in s], float)
            l = np.array([x[1] for x in s], float)
            print("  batch %-3s n=%2d  corr(position, lag) = %+.2f   lags %s"
                  % (b, len(s), np.corrcoef(p, l)[0, 1], [int(x) for x in l]))
    print("\nwrote %s" % OUT)


if __name__ == "__main__":
    main()
