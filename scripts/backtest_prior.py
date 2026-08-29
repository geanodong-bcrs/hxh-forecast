#!/usr/bin/env python3
"""Phase 1C steps 14, 15, 17, 18 — rolling-origin backtest of the Level 1 prior.

For each batch b in order, fit the prior on batches STRICTLY BEFORE b and score
the prediction against b's actual gap. This is what selects the recency
half-life; §6 explicitly refuses to let it be chosen by intuition.

Leakage (§19) is enforced structurally: the training slice is gaps[:i] and the
test point is gaps[i]. An assertion checks it rather than trusting the slice.

Metrics
  CRPS       discrete ranked probability score, sum_g (F(g) - 1[g>=y])^2.
             Lower is better. Rewards being both calibrated and sharp.
  log score  -ln p(y). Punishes assigning near-zero probability to what happened.
  coverage   does the central 50/80/90% interval contain y? Should hit 50/80/90.
  MAE        |median - y|, in issues. A point-forecast sanity check only.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_batch_prior import load_gaps, weights, build_prior

HALF_LIVES = [None, 12, 8, 5, 3, 2]
MIN_TRAIN = 5          # need a few observations before a forecast is meaningful
MAX_GAP = 260


def crps(pmf, y):
    F = np.cumsum(pmf)
    step = (np.arange(len(pmf)) >= y).astype(float)
    return float(((F - step) ** 2).sum())


def interval(pmf, lo, hi):
    F = np.cumsum(pmf)
    return int(np.searchsorted(F, lo)), int(np.searchsorted(F, hi))


def main():
    gaps = [g for _, g in load_gaps()]
    n = len(gaps)
    print("observations: %d  -> %d rolling-origin test points (train >= %d)"
          % (n, n - MIN_TRAIN, MIN_TRAIN))

    results = {}
    per_point = {}
    for hl in HALF_LIVES:
        cr, ls, ae, cov = [], [], [], {50: 0, 80: 0, 90: 0}
        detail = []
        for i in range(MIN_TRAIN, n):
            train, y = gaps[:i], gaps[i]
            assert len(train) == i and train == gaps[:i], "leakage: training slice wrong"
            w = weights(len(train), hl)
            pmf, _ = build_prior([(0, g) for g in train], w, MAX_GAP)
            pmf = pmf / pmf.sum()

            cr.append(crps(pmf, y))
            p = max(float(pmf[y]) if y < len(pmf) else 0.0, 1e-12)
            ls.append(-np.log(p))
            med = int(np.searchsorted(np.cumsum(pmf), 0.5))
            ae.append(abs(med - y))
            for lvl, (lo, hi) in ((50, (.25, .75)), (80, (.10, .90)), (90, (.05, .95))):
                a, b = interval(pmf, lo, hi)
                cov[lvl] += int(a <= y <= b)
            detail.append((i, y, med))
        k = len(cr)
        results[hl] = {"CRPS": np.mean(cr), "logscore": np.mean(ls), "MAE": np.mean(ae),
                       "cov50": 100.0 * cov[50] / k, "cov80": 100.0 * cov[80] / k,
                       "cov90": 100.0 * cov[90] / k}
        per_point[hl] = detail

    print("\n%-10s %8s %10s %8s %8s %8s %8s"
          % ("half-life", "CRPS", "logscore", "MAE", "cov50", "cov80", "cov90"))
    for hl in HALF_LIVES:
        r = results[hl]
        print("%-10s %8.2f %10.2f %8.1f %7.0f%% %7.0f%% %7.0f%%"
              % (hl if hl else "none", r["CRPS"], r["logscore"], r["MAE"],
                 r["cov50"], r["cov80"], r["cov90"]))

    best_crps = min(HALF_LIVES, key=lambda h: results[h]["CRPS"])
    best_ls = min(HALF_LIVES, key=lambda h: results[h]["logscore"])
    print("\nbest by CRPS:      half-life = %s" % (best_crps if best_crps else "none"))
    print("best by log score: half-life = %s" % (best_ls if best_ls else "none"))

    print("\ncalibration target is 50 / 80 / 90. Systematic over-coverage means the")
    print("prior is too wide (under-confident); under-coverage means too narrow.")

    print("\n=== per-test-point, best-CRPS setting ===")
    print("%-6s %8s %8s %8s" % ("i", "actual", "median", "error"))
    for i, y, med in per_point[best_crps]:
        print("%-6d %8d %8d %+8d" % (i, y, med, med - y))


if __name__ == "__main__":
    main()
