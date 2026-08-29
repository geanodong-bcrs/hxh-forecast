#!/usr/bin/env python3
"""Phase 1B step 13 — posterior and the ten-chapter forecast (Agents.md §13-§15)

    P(W_b | H, production evidence)  ∝  L(W_b | production) · P(W_b | H)

Level 1 supplies the prior over candidate WSJ issues. Level 2 supplies the
likelihood, built from analog batches.

THE CORRELATION RULE (§11). The current batch has 27 observed (position, stage)
events. They are not 27 independent observations — they are one production
process seen 27 times, and multiplying them would produce a posterior sharper
than the evidence by a wide margin. So each ANALOG contributes a single
likelihood factor, summarising how well that analog's timing fits all observed
events at once. Evidence strength scales with the number of analogs (3), not
with the number of events.

Also applies the §3 within-batch schedule to derive the ten-chapter forecast:
143 of 145 within-batch intervals since 2007 are exactly one issue, so a chapter
follows its predecessor by one issue with p=0.986 and by two with p=0.014.
"""
import csv
import json
import os
import sys
from datetime import date, timedelta

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_batch_prior import (load_gaps, load_calendar, project_calendar,
                               weights, build_prior, D)
from build_level2 import load as load_l2, events_with_lag
import snapshot

HALF_LIFE = None       # backtest-selected: no recency decay (docs/backtest.md)
P_SKIP = 1 - 143 / 145.0
QS = [0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95]


def main():
    # ---------- Level 1: prior over candidate issues ----------
    gaps, cluster_w = load_gaps(with_cluster_weights=True)
    cal = project_calendar(load_calendar(), 900)
    by_seq = {c["seq"]: c for c in cal}
    last_obs = max(c["seq"] for c in cal if not c["projected"])

    ann = {int(r["chapter"]): date.fromisoformat(r["publication_date"])
           for r in csv.DictReader(open(D("data", "annotations", "announcements.csv"),
                                        encoding="utf-8"))}
    # batch 49 ends with the last announced chapter; batch 50 can start no earlier
    # than the following issue
    end_seq = last_obs + len(ann)
    floor_seq = end_seq + 1

    w = weights(len(gaps), HALF_LIFE) * np.array(cluster_w)
    max_gap = 200
    pmf_gap, pi0 = build_prior(gaps, w, max_gap)

    cand = []          # (seq, date, prior)
    for g in range(0, max_gap + 1):
        s = end_seq + g + 1
        if s in by_seq:
            cand.append([s, by_seq[s]["on_sale"], pmf_gap[g]])
    prior = np.array([c[2] for c in cand], float)
    prior /= prior.sum()

    # ---------- Level 2: analog likelihood ----------
    ev, batch, pos, start, cur_batch, last_ch = load_l2()
    rows = events_with_lag(ev, batch, pos, start)

    hist = {}
    for r in rows:
        if "lag" not in r:
            continue
        k = (r["pos"], r["stage"])
        hist.setdefault(k, {})
        if r["batch"] not in hist[k] or r["date"] < hist[k][r["batch"]]["date"]:
            hist[k][r["batch"]] = r
    analogs = sorted({r["batch"] for r in rows if "lag" in r})

    first_ch = last_ch + 1
    seen = {}
    for r in rows:
        if first_ch <= r["chapter"] <= first_ch + 9:
            k = (r["pos"], r["stage"])
            if k not in seen or r["date"] < seen[k]["date"]:
                seen[k] = r

    # per-analog implied start dates, and the scale of their internal disagreement
    implied, sigma = {}, {}
    for h in analogs:
        ds = []
        for k, obs in seen.items():
            m = hist.get(k, {}).get(h)
            if m:
                ds.append((obs["date"] + timedelta(days=m["lag"])).toordinal())
        if len(ds) < 3:
            continue
        a = np.array(ds, float)
        implied[h] = float(np.median(a))
        # robust scale: MAD -> sd. This is how tightly the analog pins the date,
        # and it is deliberately NOT shrunk by sqrt(n) — the events are one process.
        sigma[h] = max(float(1.4826 * np.median(np.abs(a - np.median(a)))), 14.0)

    aw = {h: (1.0 if HALF_LIFE is None
              else 0.5 ** ((len(analogs) - 1 - i) / float(HALF_LIFE)))
          for i, h in enumerate(analogs)}
    tot = sum(aw[h] for h in implied)

    lik = np.zeros(len(cand), float)
    for i, (s, d, _) in enumerate(cand):
        x = d.toordinal()
        lik[i] = sum((aw[h] / tot) * np.exp(-0.5 * ((x - implied[h]) / sigma[h]) ** 2)
                     for h in implied)

    # ---------- posterior ----------
    post = prior * lik
    for i, (s, _, _) in enumerate(cand):
        if s < floor_seq:                    # the batch has not started
            post[i] = 0.0
    post /= post.sum()

    def q(pmf, qq):
        c = np.cumsum(pmf)
        return cand[int(np.searchsorted(c, qq))]

    print("analogs: %s   half-life %s batches" % (analogs, HALF_LIFE))
    print("implied start per analog:")
    for h in sorted(implied):
        print("  batch %d -> %s  (sigma %.0f d, weight %.2f)"
              % (h, date.fromordinal(int(implied[h])), sigma[h], aw[h] / tot))
    print("\nbatch %d ends %s; earliest eligible start %s"
          % (cur_batch, max(ann.values()), by_seq[floor_seq]["on_sale"]))

    print("\n%-10s %12s %12s %12s %12s %12s"
          % ("", "p10", "p25", "p50", "p75", "p90"))
    for name, pmf in (("prior", prior), ("posterior", post)):
        print("%-10s %12s %12s %12s %12s %12s"
              % (name, q(pmf, .10)[1], q(pmf, .25)[1], q(pmf, .50)[1],
                 q(pmf, .75)[1], q(pmf, .90)[1]))

    med = q(post, .50)
    print("\n=== W_50: publication of ch %d (§14 intervals) ===" % first_ch)
    print("  median            %s  (WSJ issue seq %d)" % (med[1], med[0]))
    for lvl, lo, hi in ((50, .25, .75), (80, .10, .90), (90, .05, .95)):
        print("  %d%% interval      %s .. %s" % (lvl, q(post, lo)[1], q(post, hi)[1]))

    print("\n  P(started by ...)")
    cum = np.cumsum(post)
    p_by = {}
    for target in (date(2026, 12, 31), date(2027, 3, 31), date(2027, 6, 30),
                   date(2027, 12, 31), date(2028, 12, 31)):
        p = float(cum[max(i for i, c in enumerate(cand) if c[1] <= target)]) \
            if any(c[1] <= target for c in cand) else 0.0
        p_by[target.isoformat()] = round(p, 4)
        print("    by %s   %5.1f%%" % (target, 100 * p))

    # ---------- helpers shared by both batches ----------
    def offsets(k):
        """PMF over issues elapsed after k within-batch steps (occasional skips)."""
        off = np.zeros(k + 6)
        off[0] = 1.0
        for _ in range(k):
            nxt = np.zeros_like(off)
            nxt[1:] += off[:-1] * (1 - P_SKIP)
            nxt[2:] += off[:-2] * P_SKIP
            off = nxt
        return off

    def shift(pmf_in, grid_len, k):
        """Advance a distribution over candidate slots by k within-batch steps."""
        out = np.zeros(grid_len)
        for j, pw in enumerate(offsets(k)):
            if pw <= 0 or j >= grid_len:
                continue
            out[j:] += pw * pmf_in[:grid_len - j]
        return out

    # ---------- the batch AFTER this one (§12 "what remains to be forecast") ----------
    # W_next2 = (this batch's last chapter) + one more inter-batch gap. The gap
    # prior is Level 1 only: production evidence exists for the first few chapters
    # of that batch, but every reported event is at character_inking, the earliest
    # pipeline stage, which says nothing about when the publisher will schedule it.
    # Presenting this as production-informed would be a lie about its provenance.
    seqs = [c[0] for c in cand]
    seq_index = {s_: i for i, s_ in enumerate(seqs)}
    grid2 = []
    for g in range(0, max_gap + 1):
        s_ = seqs[-1] + g + 1
        if s_ in by_seq:
            grid2.append((s_, by_seq[s_]["on_sale"]))
    # end-of-this-batch distribution, then one more gap on top
    end_this = shift(post, len(cand), 9)
    all_seq = seqs + [s_ for s_, _ in grid2]
    all_date = [c[1] for c in cand] + [d for _, d in grid2]
    post2 = np.zeros(len(all_seq))
    for i, pe in enumerate(end_this):
        if pe <= 0:
            continue
        for g in range(0, max_gap + 1):
            j = i + g + 1
            if j < len(post2):
                post2[j] += pe * pmf_gap[g]
    if post2.sum() > 0:
        post2 /= post2.sum()
    cand2 = [[s_, d, 0.0] for s_, d in zip(all_seq, all_date)]

    def q2(pmf, qq):
        c = np.cumsum(pmf)
        return cand2[min(int(np.searchsorted(c, qq)), len(cand2) - 1)]

    second_ch = first_ch + 10
    rows_out2 = []
    for k in range(10):
        pmf = shift(post2, len(cand2), k)
        pmf = pmf / pmf.sum()
        rows_out2.append({"chapter": second_ch + k,
                          "median": q2(pmf, .50)[1].isoformat(),
                          "i50": [q2(pmf, .25)[1].isoformat(), q2(pmf, .75)[1].isoformat()],
                          "i80": [q2(pmf, .10)[1].isoformat(), q2(pmf, .90)[1].isoformat()]})
    print("\n=== following batch (ch %d-%d), Level 1 gap only ==="
          % (second_ch, second_ch + 9))
    print("  median %s   80%% %s .. %s"
          % (q2(post2, .50)[1], q2(post2, .10)[1], q2(post2, .90)[1]))

    # ---------- §15 conditional ten-chapter forecast ----------
    print("\n=== conditional ten-chapter forecast (ch %d-%d) ==="
          % (first_ch, first_ch + 9))
    print("%-9s %12s %-26s %-26s" % ("chapter", "median", "50% interval", "80% interval"))
    rows_out = []
    for k in range(10):
        pmf = shift(post, len(cand), k)
        pmf /= pmf.sum()
        r = {"chapter": first_ch + k, "median": q(pmf, .50)[1].isoformat(),
             "i50": [q(pmf, .25)[1].isoformat(), q(pmf, .75)[1].isoformat()],
             "i80": [q(pmf, .10)[1].isoformat(), q(pmf, .90)[1].isoformat()]}
        rows_out.append(r)
        print("%-9d %12s %-26s %-26s"
              % (r["chapter"], r["median"], " .. ".join(r["i50"]), " .. ".join(r["i80"])))

    print("\nWithin-batch spacing is near-deterministic (143/145 intervals are one")
    print("issue), so these intervals are almost entirely inherited from W_50.")
    print("They are NOT independent forecasts.")

    next_batch = cur_batch + 1
    intervals = {str(l): [q(post, lo)[1].isoformat(), q(post, hi)[1].isoformat()]
                 for l, lo, hi in ((50, .25, .75), (80, .10, .90), (90, .05, .95))}

    path = snapshot.write("posterior", next_batch, {
        "forecast_timestamp": date.today().isoformat(),
        "target": "W_%d — publication of ch %d" % (next_batch, first_ch),
        "level": "1+2 combined posterior",
        "half_life_batches": HALF_LIFE,
        "analogs": analogs,
        "n_events_current_batch": len(seen),
        "implied_by_analog": {str(h): date.fromordinal(int(v)).isoformat()
                              for h, v in implied.items()},
        "truncation_floor": by_seq[floor_seq]["on_sale"].isoformat(),
        "median": med[1].isoformat(),
        "intervals": intervals,
        "p_started_by": p_by,
        # §17: "For every forecast timestamp, preserve the full probability
        # distribution over candidate next batch-start weeks." Quantiles alone
        # cannot reconstruct the shape — and the shape is the interesting part
        # here, because the posterior is a spike on the zero-gap issue sitting on
        # a long thin tail. Negligible mass is dropped to keep the file readable.
        "posterior_pmf": [[c[1].isoformat(), round(float(pv), 8)]
                          for c, pv in zip(cand, post) if pv > 1e-7],
        "prior_pmf": [[c[1].isoformat(), round(float(pv), 8)]
                      for c, pv in zip(cand, prior) if pv > 1e-7],
        "ten_chapter_forecast": rows_out,
        "next_batch": {
            "batch": next_batch + 1,
            "first_chapter": second_ch,
            "target": "W_%d — publication of ch %d" % (next_batch + 1, second_ch),
            "median": q2(post2, .50)[1].isoformat(),
            "intervals": {str(l): [q2(post2, lo)[1].isoformat(),
                                   q2(post2, hi)[1].isoformat()]
                          for l, lo, hi in ((50, .25, .75), (80, .10, .90),
                                            (90, .05, .95))},
            "pmf": [[c[1].isoformat(), round(float(pv), 8)]
                    for c, pv in zip(cand2, post2) if pv > 1e-7],
            "ten_chapter_forecast": rows_out2,
            "evidence": "Level 1 gap prior applied to the end of the current "
                        "batch. NOT production-informed: the only reported events "
                        "for these chapters are at character_inking, the earliest "
                        "pipeline stage, which does not constrain a start date.",
        },
        "correlation_note": "Each analog contributes ONE likelihood factor. The %d "
                            "observed production events are one correlated process "
                            "(§11); treating them as independent would badly "
                            "over-sharpen the posterior." % len(seen),
    }, summary={"median": med[1].isoformat(), "i50": intervals["50"],
                "i80": intervals["80"], "i90": intervals["90"]})
    print("\nsnapshot -> %s" % os.path.relpath(path, D()))


if __name__ == "__main__":
    main()
