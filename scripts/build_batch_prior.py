#!/usr/bin/env python3
"""Phase 1B step 9 — the historical batch-start prior (Agents.md §6)

    P(W_b | historical publication data)

LEVEL 1 ONLY. This file must never read the tweet corpus, the event table or the
page log: §6 requires the prior be built from publication history alone, or the
Level-2 update is not an update at all. The only inputs are chapters.csv and
wsj_issues.csv.

Shape of the prior, per the settled decisions in §3 and §6:
  - modeling era 2007+ (16 batch observations)
  - a MIXTURE: either the next batch follows immediately (gap 0) or after a long
    wait. Fitting one smooth distribution over {0,0,0,9,...,184} would describe
    neither mode.
  - recency weighting, exponential decay with the half-life measured in BATCHES
    (not years — the hiatuses are too uneven for calendar decay to be meaningful)
  - the half-life is a hyperparameter, reported across a grid for Phase 1C to
    select by out-of-sample calibration. Nothing here picks a winner.
"""
import csv
import json
import os
import sys
from datetime import date, timedelta

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
D = lambda *p: os.path.join(HERE, "..", *p)
SNAP = D("data", "forecasts")

sys.path.insert(0, HERE)
import snapshot

# Both selected by rolling-origin backtest (docs/backtest.md), not by judgement.
# Recency weighting is retained in the code but switched OFF: no decay scored
# best on CRPS and log score at every bandwidth tested. Re-enable by setting
# HALF_LIFE to a number if a future backtest says otherwise.
HALF_LIFE = None                  # no recency decay
BANDWIDTH = 60.0                  # issues; the old value of 8 was the worst in the grid
HALF_LIVES = [HALF_LIFE]          # grid kept for the backtest script
QUANTILES = [0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95]


def load_gaps(with_cluster_weights=False):
    """(batch_id, gap_in_issues) for the modeling era, in order.

    with_cluster_weights also returns a per-observation weight that de-duplicates
    the split-run zeros. Batches 40 and 41 are both zero-gap continuations of the
    SAME run (ch 311-340, which our 10-chapter rule chopped into three), so
    counting them as two independent "the next batch began immediately" events
    overstates that mode. Each run's zeros share one observation's worth of
    weight. This is a statement about what the data is, not a tuning knob.
    """
    rows, runs = [], []
    with open(D("data", "processed", "chapters.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["modeling_era"] == "1" and r["is_batch_start"] == "1" \
                    and r["issues_gap_before_batch"] != "":
                g = int(float(r["issues_gap_before_batch"]))
                rows.append((int(r["batch_id"]), g))
                runs.append((int(r["run_id"]), g))
    order = sorted(range(len(rows)), key=lambda i: rows[i][0])
    rows = [rows[i] for i in order]
    runs = [runs[i] for i in order]
    if not with_cluster_weights:
        return rows
    from collections import Counter
    zeros_per_run = Counter(rid for rid, g in runs if g == 0)
    cw = [1.0 / zeros_per_run[rid] if g == 0 else 1.0 for rid, g in runs]
    return rows, cw


def load_calendar():
    cal = []
    with open(D("data", "processed", "wsj_issues.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            cal.append({"seq": int(r["seq"]), "label": r["issue_label"],
                        "year": int(r["issue_year"]),
                        "on_sale": date.fromisoformat(r["on_sale_date"]),
                        "projected": False})
    return cal


def project_calendar(cal, n_future):
    """Extend the issue calendar by replaying last year's gap structure.

    WSJ is weekly but not uniformly so — combined issues at New Year, Golden Week
    and midsummer insert 14-day gaps. Repeating the preceding 12 months of gaps
    preserves that structure far better than assuming 7 days forever, which would
    drift about three weeks per year.
    """
    gaps = [(cal[i]["on_sale"] - cal[i - 1]["on_sale"]).days for i in range(1, len(cal))]
    # The cycle must be one YEAR of issues, not an arbitrary 52. A WSJ year is
    # ~49 issues (combined issues absorb weeks), so slicing 52 starts the replay
    # about fourteen months back and lands New-Year/summer double gaps in the
    # wrong place — it put a 14-day gap immediately after 2026-09-07.
    year = sum(1 for c in cal if (cal[-1]["on_sale"] - c["on_sale"]).days < 365)
    last_year = [g for g in gaps[-year:] if 0 < g <= 21] or [7]
    out, cur, seq, i = [], cal[-1]["on_sale"], cal[-1]["seq"], 0
    while len(out) < n_future:
        cur = cur + timedelta(days=last_year[i % len(last_year)])
        seq += 1
        i += 1
        out.append({"seq": seq, "label": "", "year": cur.year,
                    "on_sale": cur, "projected": True})
    return cal + out


def weights(n, half_life):
    """Most recent observation has weight 1."""
    if half_life is None:
        return np.ones(n)
    age = np.arange(n - 1, -1, -1, dtype=float)
    return 0.5 ** (age / half_life)


def ess(w):
    return float(w.sum() ** 2 / (w ** 2).sum())


def build_prior(gaps, w, max_gap):
    """Mixture over gap in issues: point mass at 0 + weighted empirical on g>0.

    The positive component is smoothed with a small discrete kernel so the prior
    does not assign literally zero probability to gaps that merely happen to be
    absent from thirteen observations.
    """
    g = np.array([x[1] for x in gaps], float)
    pi0 = float(w[g == 0].sum() / w.sum())

    pos_g, pos_w = g[g > 0], w[g > 0]
    grid = np.arange(1, max_gap + 1)
    dens = np.zeros(len(grid), float)
    bw = BANDWIDTH
    for gi, wi in zip(pos_g, pos_w):
        dens += wi * np.exp(-0.5 * ((grid - gi) / bw) ** 2)
    dens /= dens.sum()

    pmf = np.zeros(max_gap + 1, float)
    pmf[0] = pi0
    pmf[1:] = (1 - pi0) * dens
    return pmf, pi0


def quantile_from_pmf(pmf, q):
    c = np.cumsum(pmf)
    return int(np.searchsorted(c, q))


def current_batch():
    """(batch_id, last chapter, n announced-but-unpublished) for the running batch.

    Announcements are Level 0 scheduling information (§12), not production
    evidence, so consulting them here does not breach the Level 1 purity rule at
    the top of this file — it is the same class of fact as a published date, just
    one that has not happened yet. This replaces a hardcoded "batch 49 ends two
    issues after the last observed one", which was true only for August 2026.
    """
    cur, last = None, None
    with open(D("data", "processed", "chapters.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["modeling_era"] != "1":
                continue
            b, c = int(r["batch_id"]), int(r["chapter"])
            if cur is None or b > cur or (b == cur and c > last):
                if cur is None or b > cur:
                    cur, last = b, c
                else:
                    last = c

    ann_path = D("data", "annotations", "announcements.csv")
    extra = 0
    if os.path.exists(ann_path):
        with open(ann_path, encoding="utf-8") as fh:
            announced = sorted(int(r["chapter"]) for r in csv.DictReader(fh))
        # only those that continue the running batch contiguously
        for c in announced:
            if c == last + 1:
                last += 1
                extra += 1
    return cur, last, extra


def main():
    gaps, cluster_w = load_gaps(with_cluster_weights=True)
    cal = project_calendar(load_calendar(), 400)
    seq_by_date = {c["seq"]: c for c in cal}

    cur_batch, last_ch, n_announced = current_batch()
    next_batch = cur_batch + 1
    # The running batch ends with its last announced chapter; each announced-but-
    # unpublished chapter occupies one issue slot after the last observed issue.
    last_observed = max(c["seq"] for c in cal if not c["projected"])
    batch_end_seq = last_observed + n_announced
    end = seq_by_date[batch_end_seq]

    print("batch-start gaps, modeling era (n=%d):" % len(gaps))
    print("  " + ", ".join(str(g) for _, g in gaps))
    print("\nbatch %d ends with ch %d at issue seq %d, on sale %s (%d announced ahead)"
          % (cur_batch, last_ch, batch_end_seq, end["on_sale"], n_announced))

    raw = np.array([g for _, g in gaps], float)
    print("\nraw empirical quantiles (unweighted, for reference): "
          + ", ".join("p%d=%d" % (int(q*100), np.percentile(raw, q*100))
                      for q in (0.10, 0.25, 0.50, 0.75, 0.90)))

    max_gap = 260
    results = {}
    print("\n%-10s %6s %8s %8s %8s %8s %8s"
          % ("half-life", "ESS", "P(gap=0)", "p10", "median", "p90", "p95"))
    for hl in HALF_LIVES:
        w = weights(len(gaps), hl) * np.array(cluster_w)
        pmf, pi0 = build_prior(gaps, w, max_gap)
        qs = {q: quantile_from_pmf(pmf, q) for q in QUANTILES}
        results[str(hl)] = {"ess": ess(w), "p_gap_zero": pi0,
                            "quantiles_issues": {str(k): v for k, v in qs.items()},
                            "pmf": pmf.tolist()}
        print("%-10s %6.1f %8.2f %8d %8d %8d %8d"
              % (hl if hl else "none", ess(w), pi0, qs[0.10], qs[0.50], qs[0.90], qs[0.95]))

    # ---- predictive dates, per half-life ----
    print("\n=== next batch start (ch %d), as calendar dates ===" % (last_ch + 1))
    for hl in HALF_LIVES:
        r = results[str(hl)]
        row = []
        for q in (0.10, 0.25, 0.50, 0.75, 0.90):
            g = r["quantiles_issues"][str(q)]
            # gap counts issues SKIPPED, so the batch starts one issue later:
            # gap 0 means the very next issue, not the same one.
            s = seq_by_date.get(batch_end_seq + g + 1)
            row.append("%s=%s" % (int(q * 100), s["on_sale"] if s else "?"))
        print("  half-life %-4s  %s" % (hl if hl else "none", "  ".join(row)))

    # ---- snapshot: append-only, never overwritten (§16) ----
    path = snapshot.write("prior_level1", next_batch, {
        "forecast_timestamp": date.today().isoformat(),
        "target": "start of batch %d (ch %d-%d)"
                  % (next_batch, last_ch + 1, last_ch + 10),
        "level": "1 — historical publication data only, no production evidence",
        "n_observations": len(gaps),
        "gaps_issues": [g for _, g in gaps],
        "batch_end_seq": batch_end_seq,
        "batch_end_on_sale": end["on_sale"].isoformat(),
        "batch_end_projected": end["projected"],
        "n_announced_ahead": n_announced,
        "half_life_grid": [str(h) for h in HALF_LIVES],
        "results": {k: {kk: vv for kk, vv in v.items() if kk != "pmf"}
                    for k, v in results.items()},
        "note": "Half-life is NOT selected here. Phase 1C picks it by "
                "out-of-sample calibration.",
    })
    print("\nsnapshot -> %s" % os.path.relpath(path, D()))


if __name__ == "__main__":
    main()
