#!/usr/bin/env python3
"""Direct-target all-pairs likelihood history for chapter 421.

Chapter 421 becomes the model's direct target when batch 49 begins publishing.
Before that date the all-pairs likelihood belongs to the preceding batch, so it
is intentionally outside this diagnostic's scope.
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

import build_posterior  # noqa: E402
from replay_forecast import sample_dates  # noqa: E402


def latest_live_date():
    dates = []
    for path in glob.glob(D("data", "forecasts", "*_posterior.json")):
        with open(path, encoding="utf-8") as fh:
            snap = json.load(fh)
        if snap.get("provenance") != "replay" and snap.get("forecast_timestamp"):
            dates.append(date.fromisoformat(snap["forecast_timestamp"]))
    return max(dates)


def q(pmf, level):
    total, acc = sum(p for _, p in pmf), 0.0
    for d, p in pmf:
        acc += p / total
        if acc >= level:
            return d
    return pmf[-1][0]


def payload_at(asof):
    captured = {}
    def capture(_kind, _batch, payload, **_kwargs):
        captured.update(payload)
        return "in-memory diagnostic"
    old_write, old_mode = build_posterior.snapshot.write, build_posterior.LEVEL2_MODE
    try:
        build_posterior.snapshot.write = capture
        # Preserve the all-pairs calculation, but do not let the live V9
        # feasibility mode alter the diagnostic's captured likelihood.
        build_posterior.LEVEL2_MODE = "none"
        build_posterior.main(asof=asof, quiet=True,
                             rid=asof.strftime("%Y%m%dT205502Z"))
    finally:
        build_posterior.snapshot.write, build_posterior.LEVEL2_MODE = old_write, old_mode
    return captured


def main():
    start, end = date(2026, 6, 29), latest_live_date()
    dates = [d for d in sample_dates(start, end) if d < end] + [end]
    path = D("data", "working", "chapter421_pairs_history.csv")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        out = csv.DictWriter(fh, fieldnames=["asof", "median", "i80_lo", "i80_hi"])
        out.writeheader()
        for asof in dates:
            p = payload_at(asof)
            if "publication of ch 421" not in p.get("target", ""):
                continue
            floor = p.get("truncation_floor", "")
            pmf = [(d, float(v)) for d, v in p.get("all_pairs_likelihood_pmf", []) if d >= floor]
            if pmf and sum(v for _, v in pmf) > 0:
                out.writerow({"asof": asof.isoformat(), "median": q(pmf, .5),
                              "i80_lo": q(pmf, .1), "i80_hi": q(pmf, .9)})
    print("working: %s" % os.path.relpath(path, D()))


if __name__ == "__main__":
    main()
