#!/usr/bin/env python3
"""Leakage-free rolling-origin diagnostic for Level-2 all-pairs coordinates.

Each target is a real historical batch start.  The forecast cutoff is the last
usable production event before that start; ``build_posterior.main(asof=...)``
then sees only chapters, production events, and batch starts public by that
date.  Snapshot writing is intercepted in memory, so backtesting can never
pollute the append-only forecast record.

There are only two independent tweet-era targets with an earlier tweet-era
start available as a historical all-pairs component (batches 48 and 49).  This
is a rejection diagnostic, not a licence to finely optimise hyperparameters.
"""
import csv
import itertools
import os
import sys
from datetime import date

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_posterior as bp
from build_readiness import coordinate_events

D = lambda *p: os.path.join(HERE, "..", *p)


def starts_and_sequences():
    starts = {}
    with open(D("data", "processed", "chapters.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r.get("modeling_era") == "1" and r.get("is_batch_start") == "1":
                starts[int(r["batch_id"])] = date.fromisoformat(r["publication_date_jp"])
    seq = {}
    with open(D("data", "processed", "wsj_issues.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            seq[date.fromisoformat(r["on_sale_date"])] = int(r["seq"])
    return starts, seq


def cutoff_for(target, starts, events):
    """Last usable public production event after the preceding batch began."""
    lo, hi = starts[target - 1], starts[target]
    ds = [e["date"] for e in events if lo <= e["date"] < hi]
    if not ds:
        raise RuntimeError("no coordinate event before batch %d" % target)
    return max(ds)


def forecast_at(asof, bandwidth, coord_range, sigma_floor, use_all_pairs=True):
    """Run the live code but capture its would-be posterior in memory."""
    # V9 made the all-pairs likelihood one of several Level-2 modes.  Pin the
    # mode here, or both arms of this comparison would run the feasibility
    # Level 2 and score identically.
    old = (bp.COORD_BANDWIDTH, bp.COORD_RANGE, bp.PAIR_SIGMA_FLOOR,
           bp.USE_ALL_PAIRS, bp.LEVEL2_MODE, bp.PARAMETRIC_LEVEL1,
           bp.SEPARATE_ZERO_GAP_MODE, bp.snapshot.write)
    captured = {}
    try:
        bp.COORD_BANDWIDTH, bp.COORD_RANGE, bp.PAIR_SIGMA_FLOOR = bandwidth, coord_range, sigma_floor
        bp.USE_ALL_PAIRS = use_all_pairs
        bp.LEVEL2_MODE = "all_pairs"
        bp.PARAMETRIC_LEVEL1, bp.SEPARATE_ZERO_GAP_MODE = True, False
        def capture(_kind, _batch, payload, **_kwargs):
            captured.setdefault("posterior", payload)
            return "memory"
        bp.snapshot.write = capture
        bp.main(asof=asof, quiet=True, rid="BACKTEST")
    finally:
        (bp.COORD_BANDWIDTH, bp.COORD_RANGE, bp.PAIR_SIGMA_FLOOR,
         bp.USE_ALL_PAIRS, bp.LEVEL2_MODE, bp.PARAMETRIC_LEVEL1,
         bp.SEPARATE_ZERO_GAP_MODE, bp.snapshot.write) = old
    return captured["posterior"]


def score(post, outcome_seq):
    pmf = post.get("posterior_pmf_issue_seq") or []
    x = np.array([int(s) for s, _ in pmf])
    p = np.array([float(v) for _, v in pmf])
    p /= p.sum()
    hit = np.where(x == outcome_seq)[0]
    p_out = float(p[hit[0]]) if len(hit) else 1e-12
    cdf = np.cumsum(p)
    crps = float(np.sum((cdf - (x >= outcome_seq).astype(float)) ** 2))
    q = lambda a: int(x[min(np.searchsorted(cdf, a), len(x) - 1)])
    return {"log": -np.log(p_out), "crps": crps,
            "cov50": q(.25) <= outcome_seq <= q(.75),
            "cov80": q(.10) <= outcome_seq <= q(.90),
            "p_out": p_out, "median_seq": q(.50)}


def main():
    starts, seq = starts_and_sequences()
    raw = list(csv.DictReader(open(D("data", "processed", "production_events.csv"), encoding="utf-8")))
    events = coordinate_events(raw)
    targets = [48, 49]
    cases = [(h, cutoff_for(h, starts, events), seq[starts[h]]) for h in targets]
    print("targets (one latest pre-start cutoff each):")
    for h, cutoff, outcome in cases:
        print("  batch %d  cutoff %s  outcome issue seq %d" % (h, cutoff, outcome))

    grid = list(itertools.product((.5, 1.0, 2.0),
                                  ((-10.0, 25.0), (-20.0, 35.0)),
                                  (14.0, 21.0, 42.0)))
    baseline_rows = [score(forecast_at(cutoff, 1.0, (-20.0, 35.0), 21.0,
                                       use_all_pairs=False), outcome)
                     for _h, cutoff, outcome in cases]
    baseline = {"log": float(np.mean([r["log"] for r in baseline_rows])),
                "crps": float(np.mean([r["crps"] for r in baseline_rows])),
                "cov50": float(np.mean([r["cov50"] for r in baseline_rows])),
                "cov80": float(np.mean([r["cov80"] for r in baseline_rows])),
                "rows": baseline_rows}
    results = []
    for bw, rng, floor in grid:
        rows = []
        for h, cutoff, outcome in cases:
            rows.append(score(forecast_at(cutoff, bw, rng, floor), outcome))
        results.append({"bandwidth": bw, "range": rng, "floor": floor,
                        "log": float(np.mean([r["log"] for r in rows])),
                        "crps": float(np.mean([r["crps"] for r in rows])),
                        "cov50": float(np.mean([r["cov50"] for r in rows])),
                        "cov80": float(np.mean([r["cov80"] for r in rows])),
                        "rows": rows})
    results.sort(key=lambda r: (r["crps"], r["log"]))
    print("\nmean score over the two independent targets (lower is better):")
    print("  bandwidth  range       floor  CRPS    log     cov50 cov80")
    for r in results:
        print("  %8.1f  %5.0f..%-5.0f %5.0f  %6.2f  %6.2f   %4.0f%%  %4.0f%%"
              % (r["bandwidth"], r["range"][0], r["range"][1], r["floor"],
                 r["crps"], r["log"], 100 * r["cov50"], 100 * r["cov80"]))
    print("\n  Level-1 only (same historical cutoff):  CRPS %.2f  log %.2f  cov50 %.0f%%  cov80 %.0f%%"
          % (baseline["crps"], baseline["log"], 100 * baseline["cov50"],
             100 * baseline["cov80"]))
    print("  Per-target V5 / Level-1 details:")
    for (h, cutoff, outcome), v5, level1 in zip(cases, results[0]["rows"], baseline_rows):
        print("    batch %d (%s; outcome %d): V5 median %d, p(outcome) %.4g; "
              "Level-1 median %d, p(outcome) %.4g"
              % (h, cutoff, outcome, v5["median_seq"], v5["p_out"],
                 level1["median_seq"], level1["p_out"]))
    best = results[0]
    print("\nlowest CRPS: bandwidth %.1f, range %s, floor %.0f days"
          % (best["bandwidth"], best["range"], best["floor"]))
    print("Do not select it as a tuned setting: n=2 targets is only enough to reject gross failures.")


if __name__ == "__main__":
    main()
