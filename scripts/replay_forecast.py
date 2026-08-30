#!/usr/bin/env python3
"""Reconstruct the forecast at past dates, so the history charts have an axis.

The model has only existed since 2026-08-27, but the interesting stretch is the
whole of batch 49 — the run that produced the production evidence Level 2 is
built from. This replays `build_posterior.main` with the evidence filtered to
each past date, writing one snapshot per date, marked `provenance: replay`.

WHAT IS FILTERED (build_level2.load, build_batch_prior.load_gaps/load_calendar):

    chapters.csv          published on or before the replay date
    production_events.csv event_date on or before the replay date
    wsj_issues.csv        on sale on or before the replay date

WHAT IS NOT, and why:

    announcements.csv     it carries "batch 49 runs 411-420", which follows from
                          the 10-chapter convention (§3) and was as true in June
                          as it is now. Structure, not evidence.

    the model itself      hyperparameters were selected by a backtest over
                          historical batch gaps, not over this batch's outcome,
                          so replaying August's code onto July is not circular.
                          It is still August's code.

    know-date vs event-date  an event enters the replay on the day it happened,
                          not the day we learned of it. Some events come from
                          image transcriptions confirmed later, and some tweets
                          were only found via Wayback. A replay is therefore
                          slightly better informed than the live run would have
                          been. Recorded rather than engineered around.

Sample points are issue on-sale dates and production-event dates: those are the
days something could have moved the forecast, and they are what produce the
steps in the history charts.

    python3 scripts/replay_forecast.py            # replay, skipping what exists
    python3 scripts/replay_forecast.py --dry-run  # list the dates, write nothing

Use `--revision-v2`, `--revision-v3`, or `--revision-v4` to reconstruct an
append-only series for a later model revision.
"""
import csv
import glob
import json
import os
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
D = lambda *p: os.path.join(HERE, "..", *p)
sys.path.insert(0, HERE)

import build_posterior

def target_chapter():
    """The chapter the live forecast is for — the batch the replay is about."""
    best, ch = "", None
    for p in glob.glob(D("data", "forecasts", "*_posterior.json")):
        with open(p, encoding="utf-8") as fh:
            d = json.load(fh)
        if d.get("provenance") == "replay" or not d.get("run_id"):
            continue
        if d["run_id"] > best:
            best, ch = d["run_id"], int(d["target"].split("ch ")[-1])
    return ch


def first_event(chapter):
    """The earliest production event reported for a chapter.

    The replay starts here rather than at the batch's own start: the forecast
    for a chapter is worth showing from the moment there is any evidence about
    it at all. Before the batch containing it becomes the *next* one, the model
    still speaks about it through the following-batch branch (Level 1 only), so
    the series is continuous — it just starts much wider.
    """
    out = None
    with open(D("data", "processed", "production_events.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["event_class"] != "chapter_stage" or not r["chapter"]:
                continue
            try:
                c = int(float(r["chapter"]))
            except ValueError:
                continue
            if c != chapter or not r.get("event_date"):
                continue
            d = date.fromisoformat(r["event_date"])
            out = d if out is None or d < out else out
    return out


def live_from():
    """First date carrying a real (non-replay) posterior snapshot."""
    ds = []
    for p in glob.glob(D("data", "forecasts", "*_posterior.json")):
        try:
            with open(p, encoding="utf-8") as fh:
                d = json.load(fh)
        except Exception:
            continue
        if d.get("provenance") == "replay":
            continue
        ts = d.get("forecast_timestamp") or ""
        if ts:
            ds.append(date.fromisoformat(ts))
    return min(ds) if ds else date.today()


def sample_dates(lo, hi):
    out = set()
    with open(D("data", "processed", "wsj_issues.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            d = date.fromisoformat(r["on_sale_date"])
            if lo <= d <= hi:
                out.add(d)
    with open(D("data", "processed", "production_events.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if not r.get("event_date"):
                continue
            d = date.fromisoformat(r["event_date"])
            if lo <= d <= hi:
                out.add(d)
    return sorted(out)


def main():
    dry = "--dry-run" in sys.argv
    revision_v2 = "--revision-v2" in sys.argv
    revision_v3 = "--revision-v3" in sys.argv
    revision_v4 = "--revision-v4" in sys.argv
    hi = live_from()
    ch = target_chapter()
    start = first_event(ch) or date(2026, 6, 29)
    print("target ch %s; first reported production event %s" % (ch, start))
    dates = [d for d in sample_dates(start, hi) if d < hi]
    print("replaying %d dates, %s .. %s (live record starts %s)"
          % (len(dates), dates[0] if dates else "-", dates[-1] if dates else "-", hi))
    if dry:
        for d in dates:
            print("  %s" % d)
        return

    made = 0
    for d in dates:
        # Keep reconstructed v2 forecasts alongside, rather than overwriting,
        # the original v1 replay.  Noon UTC makes the run id parse as a normal
        # timestamp in the site history while staying distinct from v1 midnight.
        rid = (d.strftime("%Y%m%dT210000Z") if revision_v4 else
               d.strftime("%Y%m%dT180000Z") if revision_v3 else
               d.strftime("%Y%m%dT120000Z") if revision_v2 else
               d.strftime("%Y%m%dT000000Z"))
        # the batch being forecast changes across a two-year replay, so the
        # filename cannot be assumed
        found = glob.glob(D("data", "forecasts", "%s_batch*_posterior.json" % rid))
        if found:
            continue
        try:
            build_posterior.main(asof=d, quiet=True, rid=rid)
        except Exception as e:                      # noqa: BLE001
            print("  %s  SKIPPED — %s: %s" % (d, type(e).__name__, e))
            continue
        path = glob.glob(D("data", "forecasts", "%s_batch*_posterior.json" % rid))[0]
        with open(path, encoding="utf-8") as fh:
            snap = json.load(fh)
        print("  %s  %-28s median %s   80%% hi %s"
              % (d, snap["target"], snap["median"], snap["intervals"]["80"][1]))
        made += 1
    print("wrote %d replay snapshots" % made)


if __name__ == "__main__":
    main()
