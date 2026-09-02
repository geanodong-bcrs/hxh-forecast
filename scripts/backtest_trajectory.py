#!/usr/bin/env python3
"""Score the whole forecast TRAJECTORY of a resolved batch, not one cutoff.

`backtest_prior.py` scores the Level-1 prior once per batch.
`backtest_level2_coordinates.py` scores the full posterior once per batch, at
the last production event before the start.  Neither can see the defect the
history chart shows, because that defect is a property of the *sequence* of
forecasts:

  1. the first forecast of a hiatus is far too early ("not conservative enough")
  2. the forecast then recedes about one day per day until the batch starts
  3. production events barely move it

So this replays the real `build_posterior.main` across the whole gap preceding
a resolved batch start and reports:

  med@start   the median at the first forecast of the hiatus, in days after the
              preceding batch ends.  The outcome is printed beside it.
  drift       d(median date)/d(forecast date), fitted over the trajectory.
              1.0 is "recedes one day per day"; 0.0 is "stable".
  early%      share of the trajectory whose median is before the outcome
  |err| med   mean absolute error of the median, in days
  CRPS        mean over the trajectory, in issues
  ev+/ev-     mean median movement PER DAY ELAPSED at forecast dates that follow
              a NEW production event, and at those that do not.  Negative =
              earlier; 1.0 = recedes exactly as fast as the calendar advances.
              The stated goal is that evidence moves the date earlier and
              silence leaves it roughly where it was.

Every point in one trajectory shares one outcome, so these are display-quality
diagnostics over 2 resolved targets, not 100 independent tests.  They are still
the right instrument: the complaint is about trajectory shape, and every
setting is scored on exactly the same points.

    python3 scripts/backtest_trajectory.py                # all settings
    python3 scripts/backtest_trajectory.py --step 21      # coarser sampling
"""
import csv
import os
import sys
from datetime import date, timedelta

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
D = lambda *p: os.path.join(HERE, "..", *p)
sys.path.insert(0, HERE)
import build_posterior as bp

# name -> the module-level switches it sets
SETTINGS = {
    "V8 live (all-pairs)": dict(LEVEL2_MODE="all_pairs",
                                PARAMETRIC_LEVEL1=True,  SEPARATE_ZERO_GAP_MODE=False,
                                WEIGHT_ANALOGS_BY_SURVIVAL=False),
    "L1 fix, all-pairs":   dict(LEVEL2_MODE="all_pairs",
                                PARAMETRIC_LEVEL1=False, SEPARATE_ZERO_GAP_MODE=True,
                                WEIGHT_ANALOGS_BY_SURVIVAL=False),
    "L1 fix + survival wt": dict(LEVEL2_MODE="all_pairs",
                                PARAMETRIC_LEVEL1=False, SEPARATE_ZERO_GAP_MODE=True,
                                WEIGHT_ANALOGS_BY_SURVIVAL=True),
    "V10 ordered feas":    dict(LEVEL2_MODE="feasibility",
                                PARAMETRIC_LEVEL1=False, SEPARATE_ZERO_GAP_MODE=True,
                                WEIGHT_ANALOGS_BY_SURVIVAL=False),
    "V11 readiness mix":   dict(LEVEL2_MODE="readiness_mixture",
                                PARAMETRIC_LEVEL1=False, SEPARATE_ZERO_GAP_MODE=True,
                                WEIGHT_ANALOGS_BY_SURVIVAL=False),
    "V10 feas, old L1":    dict(LEVEL2_MODE="feasibility",
                                PARAMETRIC_LEVEL1=True,  SEPARATE_ZERO_GAP_MODE=False,
                                WEIGHT_ANALOGS_BY_SURVIVAL=False),
    "L1 fix, no Level 2":  dict(LEVEL2_MODE="none",
                                PARAMETRIC_LEVEL1=False, SEPARATE_ZERO_GAP_MODE=True,
                                WEIGHT_ANALOGS_BY_SURVIVAL=False),
}


def batch_starts():
    out = {}
    with open(D("data", "processed", "chapters.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r.get("modeling_era") == "1" and r.get("is_batch_start") == "1":
                out[int(r["batch_id"])] = date.fromisoformat(r["publication_date_jp"])
    return out


def event_dates():
    out = set()
    with open(D("data", "processed", "production_events.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r.get("event_date"):
                out.add(date.fromisoformat(r["event_date"]))
    return out


def issue_seq():
    out = {}
    with open(D("data", "processed", "wsj_issues.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            out[date.fromisoformat(r["on_sale_date"])] = int(r["seq"])
    return out


def run(asof):
    old = {k: getattr(bp, k) for k in ("snapshot",)}
    captured = {}
    real_write = bp.snapshot.write
    try:
        def _capture(_kind, _batch, payload, **_kw):
            captured.setdefault("p", payload)
            return "memory"
        bp.snapshot.write = _capture
        bp.main(asof=asof, quiet=True, rid="BACKTEST")
    finally:
        bp.snapshot.write = real_write
        for k, v in old.items():
            setattr(bp, k, v)
    return captured.get("p")


def trajectory(target, starts, evd, step):
    """Forecast dates across the gap that precedes `target`'s start."""
    lo, hi = starts[target - 1] + timedelta(days=70), starts[target]
    days, d = [], lo
    while d < hi:
        days.append(d)
        d += timedelta(days=step)
    days += sorted(x for x in evd if lo <= x < hi)
    return sorted(set(days))


def score(name, cfg, cases, evd, seqs, step):
    saved = {k: getattr(bp, k) for k in cfg}
    for k, v in cfg.items():
        setattr(bp, k, v)
    rows = []
    try:
        for target, outcome in cases:
            days = trajectory(target, STARTS, evd, step)
            meds, crps, ok = [], [], []
            for d in days:
                post = run(d)
                if not post or not post.get("median"):
                    continue
                m = date.fromisoformat(post["median"])
                pmf = post.get("posterior_pmf_issue_seq") or []
                x = np.array([int(s) for s, _ in pmf], float)
                p = np.array([float(v) for _, v in pmf], float)
                p /= p.sum()
                cdf = np.cumsum(p)
                crps.append(float(np.sum((cdf - (x >= seqs[outcome]).astype(float)) ** 2)))
                meds.append((d, m))
                ok.append(d)
            if len(meds) < 3:
                continue
            xs = np.array([d.toordinal() for d, _ in meds], float)
            ys = np.array([m.toordinal() for _, m in meds], float)
            drift = float(np.polyfit(xs, ys, 1)[0])
            early = 100.0 * float(np.mean(ys < outcome.toordinal()))
            err = float(np.mean(np.abs(ys - outcome.toordinal())))
            # Movement per day elapsed, so a 1-day event step and a 28-day
            # quiet step are comparable.  Negative means the forecast moved
            # EARLIER, which is what a production report is supposed to do.
            dm = np.diff(ys) / np.maximum(np.diff(xs), 1.0)
            after_event = np.array([meds[i + 1][0] in evd for i in range(len(meds) - 1)])
            ev_plus = float(np.mean(dm[after_event])) if after_event.any() else float("nan")
            ev_minus = float(np.mean(dm[~after_event])) if (~after_event).any() else float("nan")
            rows.append({"target": target, "outcome": outcome,
                         "med0": meds[0][1], "at": meds[0][0],
                         "drift": drift, "early": early, "err": err,
                         "crps": float(np.mean(crps)),
                         "ev": ev_plus, "sil": ev_minus, "n": len(meds)})
    finally:
        for k, v in saved.items():
            setattr(bp, k, v)
    return rows


STARTS = batch_starts()


def main():
    step = 14
    if "--step" in sys.argv:
        step = int(sys.argv[sys.argv.index("--step") + 1])
    evd, seqs = event_dates(), issue_seq()
    cases = [(48, STARTS[48]), (49, STARTS[49])]
    print("resolved targets: %s" % ", ".join(
        "batch %d started %s (gap after batch %d)" % (t, o, t - 1) for t, o in cases))
    print("trajectory sampled every %d days plus every production-event date\n" % step)

    hdr = "%-22s %-6s %-11s %-11s %6s %6s %7s %7s %7s %7s"
    print(hdr % ("setting", "batch", "outcome", "first med", "drift", "early%",
                 "|err|d", "CRPS", "d/event", "d/quiet"))
    selected = None
    if "--setting" in sys.argv:
        selected = sys.argv[sys.argv.index("--setting") + 1]
    for name, cfg in SETTINGS.items():
        if selected and name != selected:
            continue
        for r in score(name, cfg, cases, evd, seqs, step):
            print("%-22s %-6d %-11s %-11s %6.2f %5.0f%% %7.0f %7.2f %7.1f %7.1f"
                  % (name, r["target"], r["outcome"], r["med0"], r["drift"],
                     r["early"], r["err"], r["crps"], r["ev"], r["sil"]))
        print()


if __name__ == "__main__":
    main()
