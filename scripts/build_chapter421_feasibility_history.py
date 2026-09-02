#!/usr/bin/env python3
"""Direct-target V11 two-sided ordered-readiness history for chapter 421."""
import csv
import os
import sys
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
D = lambda *p: os.path.join(HERE, "..", *p)
sys.path.insert(0, HERE)

import build_posterior  # noqa: E402
from build_chapter421_pairs_history import latest_live_date  # noqa: E402
from replay_forecast import sample_dates  # noqa: E402


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
        build_posterior.LEVEL2_MODE = "readiness_mixture"
        build_posterior.main(asof=asof, quiet=True,
                             rid=asof.strftime("%Y%m%dT205503Z"))
    finally:
        build_posterior.snapshot.write, build_posterior.LEVEL2_MODE = old_write, old_mode
    return captured


def main():
    start, end = date(2026, 6, 29), latest_live_date()
    dates = [d for d in sample_dates(start, end) if d < end] + [end]
    path = D("data", "working", "chapter421_feasibility_history.csv")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        out = csv.DictWriter(
            fh,
            fieldnames=[
                "asof", "median", "i80_lo", "i80_hi", "readiness", "attained",
                "floor_47", "floor_48", "floor_49",
            ],
            lineterminator="\n",
        )
        out.writeheader()
        for asof in dates:
            p = payload_at(asof)
            if "publication of ch 421" not in p.get("target", ""):
                continue
            floor = p.get("truncation_floor", "")
            pmf = [(d, float(v)) for d, v in p.get("level2_likelihood_pmf", []) if d >= floor]
            if pmf and sum(v for _, v in pmf) > 0:
                feasibility = p.get("feasibility", {})
                analogs = feasibility.get("analogs", {})

                def feasible_from(batch):
                    analog = analogs.get(batch, analogs.get(str(batch), {}))
                    return analog.get("feasible_from", "")

                out.writerow({
                    "asof": asof.isoformat(), "median": q(pmf, .5),
                    "i80_lo": q(pmf, .1), "i80_hi": q(pmf, .9),
                    "readiness": feasibility.get("level", ""),
                    "attained": feasibility.get("attained", ""),
                    "floor_47": feasible_from(47),
                    "floor_48": feasible_from(48),
                    "floor_49": feasible_from(49),
                })
    print("working: %s" % os.path.relpath(path, D()))


if __name__ == "__main__":
    main()
