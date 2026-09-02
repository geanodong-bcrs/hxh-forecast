#!/usr/bin/env python3
"""Phase 1B step 12 — Level 2: production evidence (Agents.md §13)

The target is W_b, the publication date of a batch's FIRST chapter. Every
production event on ANY chapter of that batch is a data point for it, with the
lag measured to W_b rather than to the event's own chapter.

    ch.396 manuscript_complete 2022-10-18, batch 47 started 2022-10-24  ->  +6
    ch.398 retake              2022-11-08, batch 47 started 2022-10-24  ->  -15

Negative lags are not errors. They are the publisher starting a run while later
chapters are still in production — the willingness to take that risk is exactly
what varies between batches, and it is what the forecast has to capture.

Method: ANALOG forecasting. Production data covers three batch starts, which is
far too few to fit a likelihood but enough to ask "if this batch behaves like
batch 47, when does it start?" for each analog in turn. Each analog produces its
own estimate; the predictive distribution is the recency-weighted mixture.

Conditioning: the next batch demonstrably has NOT started yet, so the
distribution is truncated below the first eligible issue. That is a real
observation and it does a lot of work.
"""
import csv
import json
import os
import sys
from collections import defaultdict
from datetime import date, timedelta

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
D = lambda *p: os.path.join(HERE, "..", *p)

sys.path.insert(0, HERE)
import snapshot

HALF_LIVES = [None]               # recency decay off (docs/backtest.md)
QS = [0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95]


def load(asof=None):
    """`asof` restricts evidence to what existed on that date (the replay path).

    Chapters are filtered by publication date and events by event date. The
    Announcements are filtered by the date they became public.  A 10-chapter
    extent comes from the batch convention, not from an announcement, so this
    cannot make a replayed target slide merely because a later schedule is now
    in the annotations file.  Rows without a verified public date remain a
    live-only convenience and are excluded from historical replay.

    Caveat, deliberately not engineered around: an event's date is when it
    happened, not when we knew it. Some events come from image transcriptions
    that were human-confirmed later, and some tweets were only discovered via
    Wayback. A replay is therefore very slightly better informed than the live
    run would have been. See docs/prediction_history.md.
    """
    ch = list(csv.DictReader(open(D("data", "processed", "chapters.csv"), encoding="utf-8")))
    ann = list(csv.DictReader(open(D("data", "annotations", "announcements.csv"), encoding="utf-8")))
    ev = list(csv.DictReader(open(D("data", "processed", "production_events.csv"), encoding="utf-8")))
    if asof:
        ch = [r for r in ch if r["publication_date_jp"]
              and date.fromisoformat(r["publication_date_jp"]) <= asof]
        ev = [r for r in ev if r.get("event_date")
              and date.fromisoformat(r["event_date"]) <= asof]
        ann = [r for r in ann if r.get("announcement_date")
               and date.fromisoformat(r["announcement_date"]) <= asof]

    batch, pos, start = {}, {}, {}
    for r in ch:
        if r["modeling_era"] != "1":
            continue
        c, b = int(r["chapter"]), int(r["batch_id"])
        batch[c], pos[c] = b, int(r["position_in_batch"])
        if r["is_batch_start"] == "1":
            start[b] = date.fromisoformat(r["publication_date_jp"])

    # The running batch runs to ten chapters (§3), whether or not they have been
    # published yet.
    #
    # This used to walk announcements.csv forward from the last published
    # chapter, which only reaches chapter 420 while that file happens to list
    # every unpublished chapter of the batch contiguously. Replayed to
    # 2026-06-29 — chapters published to 411, the file naming only 419 and 420 —
    # the walk stopped at 411 and the model forecast ch 412 instead of ch 421.
    # The whole replayed history was a SLIDING TARGET: 412, 413, ... 421. That is
    # why the forecast appeared to widen as evidence accumulated; it was moving
    # nine chapters further out, not losing confidence.
    #
    # The batch's extent is the convention, anchored on its observed start.
    # Announcements can extend it beyond ten but never define it.
    cur = max(start)
    first_of_cur = min(c for c in batch if batch[c] == cur)
    last = max(c for c in batch if batch[c] == cur)
    # Announcements may extend the batch past ten (batch 43 ran to eleven), but
    # only if they are plainly about THIS batch. Without the window an unrelated
    # entry drags the running batch out to it: replayed to 2024-09-30 the file's
    # ch 419/420 rows stretched batch 47 from 391-400 to 391-420, and the model
    # reported "W_48 — publication of ch 421".
    in_batch = [int(r["chapter"]) for r in ann
                if first_of_cur <= int(r["chapter"]) <= first_of_cur + 14]
    end_of_cur = max([last, first_of_cur + 9] + in_batch)
    for c in range(last + 1, end_of_cur + 1):
        batch[c], pos[c] = cur, c - first_of_cur + 1
    last = end_of_cur

    # The batch being forecast has no rows in chapters.csv yet — its chapters are
    # only visible through production events — so give it membership explicitly.
    nxt = cur + 1
    for i in range(10):
        c = last + 1 + i
        batch[c], pos[c] = nxt, i + 1
    return ev, batch, pos, start, cur, last


def events_with_lag(ev, batch, pos, start):
    """Every chapter-scoped event, tagged with its batch and lag to W_b."""
    out = []
    for r in ev:
        if r["event_class"] != "chapter_stage" or r["confidence"] == "low":
            continue
        if not str(r["chapter"]).strip() or not r["stage"]:
            continue
        c = int(float(r["chapter"]))
        if c not in batch:
            continue
        b = batch[c]
        d = date.fromisoformat(r["event_date"])
        rec = {"chapter": c, "batch": b, "pos": pos[c], "stage": r["stage"],
               "status": r["status"], "date": d}
        if b in start:
            rec["lag"] = (start[b] - d).days
        out.append(rec)
    return out


def main():
    ev, batch, pos, start, cur_batch, last_ch = load()
    rows = events_with_lag(ev, batch, pos, start)

    # historical lags, keyed by (position, stage) — the analog lookup
    # analogs are every batch whose start date is known, which now includes the
    # batch that is currently running — it started, so it is history for this purpose
    hist = defaultdict(dict)
    for r in rows:
        if "lag" not in r:
            continue
        k = (r["pos"], r["stage"])
        # earliest event of that stage at that position, matching the current side
        if r["batch"] not in hist[k] or r["date"] < hist[k][r["batch"]]["date"]:
            hist[k][r["batch"]] = r

    analogs = sorted({r["batch"] for r in rows if "lag" in r})
    print("analog batches: %s" % analogs)

    # current batch = the one after cur_batch
    next_batch = cur_batch + 1
    first_ch = last_ch + 1
    nxt = [r for r in rows if first_ch <= r["chapter"] <= first_ch + 9]
    seen = {}
    for r in nxt:
        k = (r["pos"], r["stage"])
        if k not in seen or r["date"] < seen[k]["date"]:
            seen[k] = r
    print("batch %d = ch %d-%d, with %d distinct (position, stage) observations"
          % (next_batch, first_ch, first_ch + 9, len(seen)))

    # earliest possible start: the issue after the running batch's last chapter
    ann = {int(r["chapter"]): date.fromisoformat(r["publication_date"])
           for r in csv.DictReader(open(D("data", "annotations", "announcements.csv"),
                                        encoding="utf-8"))}
    floor = max(ann.values()) + timedelta(days=7)
    print("earliest eligible start (batch %d ends %s): %s"
          % (cur_batch, max(ann.values()), floor))

    # ---- per-analog estimates ----
    print("\n=== analog estimates for W_%d ===" % next_batch)
    per_analog = {}
    for h in analogs:
        ests = []
        for (p, stg), obs in sorted(seen.items()):
            m = hist.get((p, stg), {}).get(h)
            if not m:
                continue
            ests.append((obs["date"] + timedelta(days=m["lag"]), p, stg, m["lag"]))
        if not ests:
            continue
        ds = sorted(e[0] for e in ests)
        med = ds[len(ds) // 2]
        alive = [d for d in ds if d >= floor]
        per_analog[h] = {"n": len(ds), "median": med,
                         "min": ds[0], "max": ds[-1],
                         "n_falsified": len(ds) - len(alive)}
        print("  batch %d: n=%2d  median %s   range %s .. %s   (%d estimates already "
              "falsified by the batch not having started)"
              % (h, len(ds), med, ds[0], ds[-1], len(ds) - len(alive)))

    # ---- mixture over analogs, truncated at the floor ----
    print("\n=== predictive distribution for W_%d (truncated at %s) ===" % (next_batch, floor))
    print("%-10s %8s %12s %12s %12s %12s" % ("half-life", "n", "p10", "p50", "p90", "p95"))
    out = {}
    for hl in HALF_LIVES:
        samples, weights = [], []
        for i, h in enumerate(analogs):
            w = 1.0 if hl is None else 0.5 ** ((len(analogs) - 1 - i) / float(hl))
            for (p, stg), obs in sorted(seen.items()):
                m = hist.get((p, stg), {}).get(h)
                if not m:
                    continue
                est = obs["date"] + timedelta(days=m["lag"])
                if est < floor:          # falsified: the batch has not started
                    continue
                samples.append(est)
                weights.append(w)
        if not samples:
            continue
        order = np.argsort([d.toordinal() for d in samples])
        s = np.array([samples[i].toordinal() for i in order], float)
        w = np.array([weights[i] for i in order], float)
        cw = np.cumsum(w) / w.sum()
        q = {qq: date.fromordinal(int(s[np.searchsorted(cw, qq)])) for qq in QS}
        out[str(hl)] = {"n_samples": len(samples),
                        "quantiles": {str(k): v.isoformat() for k, v in q.items()}}
        print("%-10s %8d %12s %12s %12s %12s"
              % (hl if hl else "none", len(samples), q[0.10], q[0.50], q[0.90], q[0.95]))

    path = snapshot.write("level2_analog", next_batch, {
        "forecast_timestamp": date.today().isoformat(),
        "target": "W_%d — publication date of ch %d, first chapter of batch %d"
                  % (next_batch, first_ch, next_batch),
        "level": "2 — production evidence, analog method",
        "analog_batches": analogs,
        "n_observations_current_batch": len(seen),
        "truncation_floor": floor.isoformat(),
        "per_analog": {str(k): {kk: (vv.isoformat() if isinstance(vv, date) else vv)
                                for kk, vv in v.items()} for k, v in per_analog.items()},
        "predictive": out,
        "caveat": "Three analogs. Each analog is one historical batch's behaviour "
                  "replayed onto current production dates; the spread WITHIN an "
                  "analog is measurement noise, the spread BETWEEN analogs is the "
                  "real uncertainty and it is not reducible with n=3.",
    })
    print("\nsnapshot -> %s" % os.path.relpath(path, D()))


if __name__ == "__main__":
    main()
