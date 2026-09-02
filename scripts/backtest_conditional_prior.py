#!/usr/bin/env python3
"""Rolling-origin backtest of the Level 1 prior AS IT IS DISPLAYED.

`backtest_prior.py` scores the unconditional prior P(G) once per batch, at the
moment the previous batch ends.  That is not what the site shows.  The site
shows, every day of a hiatus, the *conditional* forecast

    P(G | G >= a),   a = eligible issues already known not to carry the batch,

and the complaint the model has to answer — "the first prediction is not
conservative enough and then it slides later every week" — is a statement about
that family of conditional forecasts, not about P(G) at a = 0.

So this scores the whole trajectory.  For each batch i, fit on gaps[:i] (an
assertion enforces the slice, as in backtest_prior.py) and score
P(G | G >= a) against gaps[i] for every a on a grid up to gaps[i].  Reported:

  CRPS, log score      proper scores, averaged over the trajectory
  cov50/80/90          interval coverage over the trajectory
  drift                d(median)/da, fitted over the trajectory.  1.0 means the
                       predicted date recedes one day for every day waited;
                       0.0 means waiting does not move it.
  early                fraction of trajectory points whose median is EARLIER
                       than the outcome — the "not conservative enough" defect
  med@0                the first (a = 0) median, in issues.  The headline number
                       a reader sees on day one of a hiatus.

Trajectory points share one outcome, so they are not independent test cases;
CRPS and log score here are trajectory-average display scores, not n-fold
evidence.  The ranking across settings is still meaningful because every
setting is scored on exactly the same points.
"""
import os
import sys
from math import erf, sqrt

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_batch_prior import (load_gaps, weights, build_prior,
                               build_shifted_lognormal_prior)

MIN_TRAIN = 5
MAX_GAP = 400
A_STEP = 5            # trajectory sampled every 5 issues of waiting


def conditional(pmf, a):
    p = np.array(pmf, float).copy()
    p[:a] = 0.0
    s = p.sum()
    return p / s if s > 0 else None


def crps(pmf, y):
    F = np.cumsum(pmf)
    return float(((F - (np.arange(len(pmf)) >= y).astype(float)) ** 2).sum())


def quant(pmf, q):
    return int(np.searchsorted(np.cumsum(pmf), q))


def build(family, train, w):
    gaps = [(0, g) for g in train]
    if family == "lognormal":
        pmf, _ = build_shifted_lognormal_prior(gaps, w, MAX_GAP)
    elif family == "kde-smooth":
        pmf, _ = build_prior(gaps, w, MAX_GAP, separate_zero=False)
    elif family in ("gamma", "weibull"):
        pmf = build_hazard_prior(family, train, w)
    else:
        pmf, _ = build_prior(gaps, w, MAX_GAP, separate_zero=True)
    return pmf / pmf.sum()


def build_hazard_prior(family, train, w):
    """Two-parameter light-tailed fit on the positive gaps, plus the zero mass.

    Included because the defect under test is a hazard-shape defect: a prior
    whose hazard falls with elapsed time must drift faster than one day per day
    once it is conditioned on continued non-publication.  Gamma with shape > 1
    and Weibull with shape > 1 both have rising hazard, so they are the natural
    families to test against the kernel estimates.
    """
    from math import lgamma
    g = np.array(train, float)
    w = np.asarray(w, float) * np.ones(len(g))
    pos, wp = g[g > 0], w[g > 0]
    pi0 = float(w[g == 0].sum() / w.sum())
    grid = np.arange(MAX_GAP + 1, dtype=float)
    m = float(np.sum(wp * pos) / np.sum(wp))
    v = float(np.sum(wp * (pos - m) ** 2) / np.sum(wp))
    if family == "gamma":
        k, th = max(m * m / v, 0.05), v / m
        dens = np.exp((k - 1) * np.log(np.maximum(grid, 1e-9)) - grid / th
                      - lgamma(k) - k * np.log(th))
        dens[0] = 0.0
    else:
        # shape from the coefficient of variation, scale from the mean
        cv = sqrt(v) / m
        k = cv ** -1.086                      # Justus et al. approximation
        lam = m / np.exp(lgamma(1 + 1 / k))
        S = np.exp(-(np.maximum(grid, 0.0) / lam) ** k)
        dens = np.zeros(MAX_GAP + 1)
        dens[1:] = S[:-1] - S[1:]
    dens = np.maximum(dens, 0.0)
    dens[1:] /= dens[1:].sum()
    pmf = np.zeros(MAX_GAP + 1)
    pmf[0] = pi0
    pmf[1:] = (1 - pi0) * dens[1:]
    return pmf


def evaluate(family, bw, hl, cluster):
    import build_batch_prior as bbp
    old_bw = bbp.BANDWIDTH
    bbp.BANDWIDTH = bw
    try:
        rows, cw = load_gaps(with_cluster_weights=True)
        gaps = [g for _, g in rows]
        n = len(gaps)
        cr, ls, cov = [], [], {50: 0, 80: 0, 90: 0}
        npts, early, med0, slopes, slopes10 = 0, 0, [], [], []
        for i in range(MIN_TRAIN, n):
            train, y = gaps[:i], gaps[i]
            assert train == gaps[:i], "leakage: training slice wrong"
            w = weights(i, hl) * (np.array(cw[:i]) if cluster else 1.0)
            pmf = build(family, train, w)
            aa, mm = [], []
            for a in range(0, y + 1, A_STEP):
                c = conditional(pmf, a)
                if c is None:
                    continue
                cr.append(crps(c, y))
                ls.append(-np.log(max(float(c[y]) if y < len(c) else 0.0, 1e-12)))
                m = quant(c, 0.5)
                aa.append(a)
                mm.append(m)
                npts += 1
                early += int(m < y)
                if a == 0:
                    med0.append(m)
                for lvl, (lo, hi) in ((50, (.25, .75)), (80, (.10, .90)), (90, (.05, .95))):
                    cov[lvl] += int(quant(c, lo) <= y <= quant(c, hi))
            if len(aa) >= 3:
                slopes.append(float(np.polyfit(aa, mm, 1)[0]))
            # The mixture prior loses its whole zero mode at a = 1, which shows
            # up as one step, not as a slope.  Measuring the slope again from
            # a >= 10 separates "the day-one headline moved" from "the forecast
            # recedes for every week waited", which is the defect under test.
            tail = [(a, m) for a, m in zip(aa, mm) if a >= 10]
            if len(tail) >= 3:
                slopes10.append(float(np.polyfit([a for a, _ in tail],
                                                 [m for _, m in tail], 1)[0]))
        return {"family": family, "bw": bw, "hl": hl, "cluster": cluster,
                "CRPS": float(np.mean(cr)), "log": float(np.mean(ls)),
                "cov50": 100.0 * cov[50] / npts, "cov80": 100.0 * cov[80] / npts,
                "cov90": 100.0 * cov[90] / npts,
                "drift": float(np.mean(slopes)),
                "drift10": float(np.mean(slopes10)) if slopes10 else float("nan"),
                "early": 100.0 * early / npts,
                "med0": float(np.mean(med0)), "n": npts}
    finally:
        bbp.BANDWIDTH = old_bw


def main():
    rows, _ = load_gaps(with_cluster_weights=True)
    gaps = [g for _, g in rows]
    print("%d gaps; %d rolling-origin batches; trajectory sampled every %d issues"
          % (len(gaps), len(gaps) - MIN_TRAIN, A_STEP))
    print("outcomes scored: %s\n" % gaps[MIN_TRAIN:])

    out = [evaluate("lognormal", 60.0, None, True)]
    for bw in (30.0, 40.0, 60.0, 80.0):
        for hl in (None, 8, 5):
            out.append(evaluate("mixture", bw, hl, True))
            out.append(evaluate("kde-smooth", bw, hl, True))
    for hl in (None, 8, 5):
        out.append(evaluate("gamma", 0.0, hl, True))
        out.append(evaluate("weibull", 0.0, hl, True))
    out.append(evaluate("mixture", 60.0, None, False))

    hdr = "%-11s %5s %5s  %7s %6s  %5s %5s %5s  %6s %7s %6s %6s"
    print(hdr % ("family", "bw", "hl", "CRPS", "log", "c50", "c80", "c90",
                 "drift", "drift10", "early%", "med@0"))
    for r in sorted(out, key=lambda r: r["CRPS"]):
        print("%-11s %5.0f %5s  %7.2f %6.2f  %4.0f%% %4.0f%% %4.0f%%  %6.2f %7.2f %5.0f%% %6.0f"
              % (r["family"], r["bw"], r["hl"] if r["hl"] else "-", r["CRPS"], r["log"],
                 r["cov50"], r["cov80"], r["cov90"], r["drift"], r["drift10"],
                 r["early"], r["med0"]))
    print("\ndrift = d(median gap)/d(issues waited).  1.0 is the runaway the site shows.")
    print("early%% = share of displayed forecasts whose median is before the outcome.")


if __name__ == "__main__":
    main()
