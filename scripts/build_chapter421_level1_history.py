#!/usr/bin/env python3
"""Replay the selected baseline for chapter 421, with Level 2 disabled.

The output is a derived working table, not an append-only forecast snapshot:
it is a diagnostic reconstruction used by research-methods.html.  Replacing
snapshot.write in memory keeps the actual forecast record untouched.
"""
import csv
import os
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
D = lambda *p: os.path.join(HERE, "..", *p)
sys.path.insert(0, HERE)

import build_posterior  # noqa: E402
from replay_forecast import first_event, live_from, sample_dates  # noqa: E402


def quantile(row, key):
    return (row.get(key) or [None, None])


def row_for_chapter(payload, chapter=421):
    for source in (payload.get("ten_chapter_forecast") or [],
                   (payload.get("next_batch") or {}).get("ten_chapter_forecast") or []):
        for row in source:
            if row.get("chapter") == chapter:
                return row
    return None


def replay(asof):
    captured = {}

    def capture(_kind, _batch, payload, **_kwargs):
        captured.update(payload)
        return "in-memory diagnostic"

    original_write = build_posterior.snapshot.write
    original_mode = build_posterior.LEVEL2_MODE
    try:
        build_posterior.snapshot.write = capture
        build_posterior.LEVEL2_MODE = "none"
        build_posterior.main(asof=asof, quiet=True,
                             rid=asof.strftime("%Y%m%dT205501Z"))
    finally:
        build_posterior.snapshot.write = original_write
        build_posterior.LEVEL2_MODE = original_mode
    return captured


def main():
    target = 421
    start = first_event(target)
    end = live_from()
    dates = [d for d in sample_dates(start, end) if d < end] + [end]
    path = D("data", "working", "chapter421_level1_history.csv")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        out = csv.DictWriter(fh, fieldnames=["asof", "median", "i50_lo", "i50_hi",
                                              "i80_lo", "i80_hi", "source"])
        out.writeheader()
        for asof in dates:
            payload = replay(asof)
            row = row_for_chapter(payload, target)
            if not row:
                continue
            i50, i80 = quantile(row, "i50"), quantile(row, "i80")
            source = "direct" if target == int(payload["target"].split("ch ")[-1]) else "following"
            out.writerow({"asof": asof.isoformat(), "median": row["median"],
                          "i50_lo": i50[0], "i50_hi": i50[1],
                          "i80_lo": i80[0], "i80_hi": i80[1], "source": source})
    print("working: %s" % os.path.relpath(path, D()))


if __name__ == "__main__":
    main()
