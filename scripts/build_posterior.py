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
from math import erfc, sqrt

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_batch_prior import (load_gaps, load_calendar, project_calendar,
                               weights, build_prior, D)
from build_level2 import load as load_l2, events_with_lag
from build_readiness import states as readiness_states, batch_scope as name_scope
import snapshot

HALF_LIFE = None       # backtest-selected: no recency decay (docs/backtest.md)
P_SKIP = 1 - 143 / 145.0
QS = [0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95]


def quarter_ends(start, n=10):
    """The next n calendar quarter-ends on or after `start`."""
    out, y, q = [], start.year, (start.month - 1) // 3
    while len(out) < n:
        m = q * 3 + 3
        d = date(y + 1, 1, 1) - timedelta(days=1) if m == 12 \
            else date(y, m + 1, 1) - timedelta(days=1)
        if d >= start:
            out.append(d)
        q += 1
        if q > 3:
            y, q = y + 1, 0
    return out


def main(asof=None, quiet=False, rid=None):
    """asof=None is the live run. A date replays the model on the evidence that
    existed then — see build_level2.load for what that does and does not filter.
    """
    say = (lambda *a, **k: None) if quiet else print
    today = asof or date.today()

    # ---------- Level 1: prior over candidate issues ----------
    gaps, cluster_w = load_gaps(with_cluster_weights=True, asof=asof)
    cal = project_calendar(load_calendar(asof=asof), 900)
    by_seq = {c["seq"]: c for c in cal}
    last_obs = max(c["seq"] for c in cal if not c["projected"])

    ann = {int(r["chapter"]): date.fromisoformat(r["publication_date"])
           for r in csv.DictReader(open(D("data", "annotations", "announcements.csv"),
                                        encoding="utf-8"))}

    # ---------- Level 2: analog likelihood ----------
    ev, batch, pos, start, cur_batch, last_ch = load_l2(asof=asof)
    rows = events_with_lag(ev, batch, pos, start)

    # Where the running batch ends, and so the earliest issue the next one could
    # begin on. Derived from the batch itself: its observed start plus the
    # ten-chapter convention (§3), extended if the schedule file names something
    # later inside it.
    #
    # Two earlier versions of this were wrong under replay. `last_obs + len(ann)`
    # inferred the end from the ROW COUNT of announcements.csv — right only while
    # that file holds exactly the unpublished tail. Anchoring on max(ann) instead
    # fixed that but still assumed the file describes whichever batch is running,
    # which is false at any date before batch 49 existed.
    by_date = {c["on_sale"]: c["seq"] for c in cal}
    cur_start_seq = by_date.get(start[cur_batch])
    if cur_start_seq is None:
        cur_start_seq = min((c["seq"] for c in cal if c["on_sale"] >= start[cur_batch]),
                            default=last_obs)
    end_seq = cur_start_seq + 9
    for c, d in ann.items():
        if last_ch - 9 <= c <= last_ch and d in by_date:
            end_seq = max(end_seq, by_date[d])
    # Non-publication is conditioned on only when new public evidence arrives.
    # Re-running on an otherwise uneventful day must not mechanically slide the
    # forecast one issue later.  At a tweet/publication update, issues already
    # past by that date are ruled out in the usual way.
    latest_event = max((date.fromisoformat(r["event_date"]) for r in ev
                        if r.get("event_date")), default=today)
    evidence_seq = max((c["seq"] for c in cal if c["on_sale"] <= latest_event),
                       default=end_seq)
    floor_seq = max(end_seq + 1, evidence_seq + 1)

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

    analogs = sorted({r["batch"] for r in rows if "lag" in r})

    first_ch = last_ch + 1
    target_chapters = list(range(first_ch, first_ch + 10))
    preceding_chapters = list(range(first_ch - 10, first_ch))
    following_chapters = list(range(first_ch + 10, first_ch + 20))
    current_state = readiness_states(ev, target_chapters, asof=asof)
    preceding_state = readiness_states(ev, preceding_chapters, asof=asof)
    following_state = readiness_states(ev, following_chapters, asof=asof)
    names = name_scope(ev, asof=asof)

    # Level 2 no longer matches only an exact (position, stage).  Each chapter
    # contributes its furthest observed progress coordinate, which can be a page
    # log or a stage/status interval.  Historic comparison is restricted to the
    # evidence public before that analog batch started.
    by_batch_pos = {}
    for c, b in batch.items():
        if c in pos:
            by_batch_pos[(b, pos[c])] = c

    def readiness_analogs(now_state, now_first, source_to_outcome):
        """One correlated likelihood component per historical source batch."""
        implied, sigma, detail = {}, {}, {}
        for h, outcome in source_to_outcome.items():
            h_chapters = [by_batch_pos.get((h, p)) for p in range(1, 11)]
            h_chapters = [c for c in h_chapters if c is not None]
            historical_state = readiness_states(ev, h_chapters, asof=outcome)
            estimates, compatibility = [], []
            for p in range(1, 11):
                now = now_state.get(now_first + p - 1)
                old = historical_state.get(by_batch_pos.get((h, p)))
                if not now or not old or now["p_hat"] is None or old["p_hat"] is None:
                    continue
                if not now["attained_date"] or not old["attained_date"]:
                    continue
                diff = abs(now["p_hat"] - old["p_hat"])
                if diff > 0.35:
                    continue
                estimates.append((date.fromisoformat(now["attained_date"]) +
                                  (outcome - date.fromisoformat(old["attained_date"]))).toordinal())
                compatibility.append(np.exp(-0.5 * (diff / 0.15) ** 2))
            if len(estimates) < 3:
                continue
            a = np.array(estimates, float)
            implied[h] = float(np.median(a))
            sigma[h] = max(float(1.4826 * np.median(np.abs(a - np.median(a)))), 14.0)
            detail[h] = {"n_positions": len(estimates),
                         "mean_progress_compatibility": round(float(np.mean(compatibility)), 4),
                         "historical_outcome": outcome.isoformat()}
        return implied, sigma, detail

    implied, sigma, analog_detail = readiness_analogs(current_state, first_ch,
                                                       {h: start[h] for h in analogs})
    # Preceding-batch context: historical source batch h is paired with the
    # observed start of h+1.  It is a weaker feasibility/context signal, never
    # a substitute for readiness in the target batch itself.
    context_sources = {h: start[h + 1] for h in analogs if h + 1 in start}
    context_implied, context_sigma, context_detail = readiness_analogs(
        preceding_state, first_ch - 10, context_sources)

    def analog_likelihood(implied, sigma):
        if not implied:
            return np.ones(len(cand), float), []
        out, fading = np.zeros(len(cand), float), []
        for i, (_, d, _) in enumerate(cand):
            terms = []
            for h in implied:
                z = (by_seq[floor_seq]["on_sale"].toordinal() - implied[h]) / sigma[h]
                survive = 0.5 * erfc(z / sqrt(2.0))
                # Smoothly hand a stale analog back to a flat (neutral)
                # likelihood.  5% is a scale, not a discontinuous switch.
                alpha = survive / (survive + 0.05)
                if alpha < .1:
                    fading.append(h)
                gaussian = np.exp(-0.5 * ((d.toordinal() - implied[h]) / sigma[h]) ** 2)
                terms.append(alpha * gaussian + (1 - alpha))
            out[i] = float(np.mean(terms))
        out /= out.max() if out.max() > 0 else 1
        return out, sorted(set(fading))

    direct_lik, exhausted = analog_likelihood(implied, sigma)
    context_lik, context_fading = analog_likelihood(context_implied, context_sigma)
    CONTEXT_WEIGHT = 0.10
    lik = np.maximum(direct_lik, 1e-12) ** (1 - CONTEXT_WEIGHT) \
        * np.maximum(context_lik, 1e-12) ** CONTEXT_WEIGHT

    '''
    Legacy exact-stage implementation retained below in git history; the
    readiness-coordinate analogue calculation above is the live Level 2.
    '''
    """
    for h in analogs:
        h_chapters = [by_batch_pos.get((h, p)) for p in range(1, 11)]
        h_chapters = [c for c in h_chapters if c is not None]
        historical_state = readiness_states(ev, h_chapters, asof=start[h])
        estimates, compatibility = [], []
        for p in range(1, 11):
            now = current_state.get(first_ch + p - 1)
            old = historical_state.get(by_batch_pos.get((h, p)))
            if not now or not old or now["p_hat"] is None or old["p_hat"] is None:
                continue
            if not now["attained_date"] or not old["attained_date"]:
                continue
            # A close progress match should matter more, but no individual event
            # is allowed to become an independent likelihood factor.
            diff = abs(now["p_hat"] - old["p_hat"])
            if diff > 0.35:
                continue
            estimates.append((date.fromisoformat(now["attained_date"]) +
                              (start[h] - date.fromisoformat(old["attained_date"]))).toordinal())
            compatibility.append(np.exp(-0.5 * (diff / 0.15) ** 2))
        if len(estimates) < 3:
            continue
        a = np.array(estimates, float)
        implied[h] = float(np.median(a))
        # The internal spread describes disagreement within one correlated
        # production process; do not shrink it by sqrt(n).
        sigma[h] = max(float(1.4826 * np.median(np.abs(a - np.median(a)))), 14.0)
        analog_detail[h] = {"n_positions": len(estimates),
                            "mean_progress_compatibility": round(float(np.mean(compatibility)), 4),
                            "historical_start": start[h].isoformat()}

    aw = {h: (1.0 if HALF_LIFE is None
              else 0.5 ** ((len(analogs) - 1 - i) / float(HALF_LIFE)))
          for i, h in enumerate(analogs)}
    tot = sum(aw[h] for h in implied)

    # No usable comparable state is an honest Level-1-only forecast.
    if tot <= 0:
        lik = np.ones(len(cand), float)
    else:
        lik = np.zeros(len(cand), float)
    exhausted = []
    analog_grid = enumerate(cand) if tot > 0 else []
    for i, (s, d, _) in analog_grid:
        x = d.toordinal()
        terms = []
        for h in implied:
            # If the analog placed the start so far before the observed
            # non-start floor that its surviving Normal tail is <5%, it has been
            # falsified as a timing analog.  A stale "should have happened"
            # prediction must be neutral, not a spurious "next issue" spike.
            z = (by_seq[floor_seq]["on_sale"].toordinal() - implied[h]) / sigma[h]
            survive = 0.5 * erfc(z / sqrt(2.0))
            if survive < 0.05:
                if h not in exhausted:
                    exhausted.append(h)
                component = 1.0
            else:
                component = np.exp(-0.5 * ((x - implied[h]) / sigma[h]) ** 2)
            terms.append((aw[h] / tot) * component)
        lik[i] = sum(terms)
    """

    # ---------- posterior ----------
    # A likelihood is only defined up to a constant, and this one is a sum of
    # Gaussians: when every analog implies a date far outside the candidate grid
    # each term underflows to exactly 0.0 and the posterior becomes 0/0. Rescaling
    # by the peak is free — it cancels in the normalisation — and keeps the ratios
    # that matter representable. Found by replaying to 2025-06-02, where the
    # analogs implied a start the truncation had already ruled out.
    if lik.max() > 0:
        lik = lik / lik.max()
    post = prior * lik
    for i, (s, _, _) in enumerate(cand):
        if s < floor_seq:                    # the batch has not started
            post[i] = 0.0
    if post.sum() <= 0:
        # Nothing survived: the production evidence and the "it has not started
        # yet" truncation are in flat contradiction. Level 1 alone is the honest
        # answer, not a crash and not a silently renormalised nan.
        say("  likelihood vanishes under truncation — falling back to Level 1")
        post = prior.copy()
        for i, (s, _, _) in enumerate(cand):
            if s < floor_seq:
                post[i] = 0.0
    # Beyond every observed historical gap we deliberately enter a separate
    # record-hiatus regime: modest mass on the next issue, with the remaining
    # tail inherited from history.  This is the one circumstance where the
    # human "maybe next week" instinct is represented explicitly.
    elapsed_gap = floor_seq - end_seq - 1
    record_hiatus = elapsed_gap > max(g for _, g in gaps)
    if record_hiatus:
        tail = prior.copy()
        for i, (s, _, _) in enumerate(cand):
            if s < floor_seq:
                tail[i] = 0.0
        tail /= tail.sum()
        post = 0.80 * tail
        floor_i = next(i for i, (s, _, _) in enumerate(cand) if s == floor_seq)
        post[floor_i] += 0.20
    post /= post.sum()

    def q(pmf, qq):
        c = np.cumsum(pmf)
        return cand[int(np.searchsorted(c, qq))]

    say("analogs: %s   half-life %s batches" % (analogs, HALF_LIFE))
    say("implied start per analog:")
    for h in sorted(implied):
        say("  batch %d -> %s  (sigma %.0f d, weight %.2f)"
              % (h, date.fromordinal(int(implied[h])), sigma[h],
                 1.0 / max(len(implied), 1)))
    say("\nbatch %d ends %s; earliest eligible start %s"
          % (cur_batch, by_seq[end_seq]["on_sale"], by_seq[floor_seq]["on_sale"]))

    say("\n%-10s %12s %12s %12s %12s %12s"
          % ("", "p10", "p25", "p50", "p75", "p90"))
    for name, pmf in (("prior", prior), ("posterior", post)):
        say("%-10s %12s %12s %12s %12s %12s"
              % (name, q(pmf, .10)[1], q(pmf, .25)[1], q(pmf, .50)[1],
                 q(pmf, .75)[1], q(pmf, .90)[1]))

    med = q(post, .50)
    say("\n=== W_50: publication of ch %d (§14 intervals) ===" % first_ch)
    say("  median            %s  (WSJ issue seq %d)" % (med[1], med[0]))
    for lvl, lo, hi in ((50, .25, .75), (80, .10, .90), (90, .05, .95)):
        say("  %d%% interval      %s .. %s" % (lvl, q(post, lo)[1], q(post, hi)[1]))

    say("\n  P(started by ...)")
    cum = np.cumsum(post)
    p_by = {}
    for target in quarter_ends(today):
        p = float(cum[max(i for i, c in enumerate(cand) if c[1] <= target)]) \
            if any(c[1] <= target for c in cand) else 0.0
        p_by[target.isoformat()] = round(p, 4)
        say("    by %s   %5.1f%%" % (target, 100 * p))

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
    say("\n=== following batch (ch %d-%d), Level 1 gap only ==="
          % (second_ch, second_ch + 9))
    say("  median %s   80%% %s .. %s"
          % (q2(post2, .50)[1], q2(post2, .10)[1], q2(post2, .90)[1]))

    # ---------- §15 conditional ten-chapter forecast ----------
    say("\n=== conditional ten-chapter forecast (ch %d-%d) ==="
          % (first_ch, first_ch + 9))
    say("%-9s %12s %-26s %-26s" % ("chapter", "median", "50% interval", "80% interval"))
    rows_out = []
    for k in range(10):
        pmf = shift(post, len(cand), k)
        pmf /= pmf.sum()
        r = {"chapter": first_ch + k, "median": q(pmf, .50)[1].isoformat(),
             "i50": [q(pmf, .25)[1].isoformat(), q(pmf, .75)[1].isoformat()],
             "i80": [q(pmf, .10)[1].isoformat(), q(pmf, .90)[1].isoformat()]}
        rows_out.append(r)
        say("%-9d %12s %-26s %-26s"
              % (r["chapter"], r["median"], " .. ".join(r["i50"]), " .. ".join(r["i80"])))

    say("\nWithin-batch spacing is near-deterministic (143/145 intervals are one")
    say("issue), so these intervals are almost entirely inherited from W_50.")
    say("They are NOT independent forecasts.")

    next_batch = cur_batch + 1
    intervals = {str(l): [q(post, lo)[1].isoformat(), q(post, hi)[1].isoformat()]
                 for l, lo, hi in ((50, .25, .75), (80, .10, .90), (90, .05, .95))}

    # P(chapter published by ...) for every chapter in the 20-chapter horizon.
    # `p_started_by` above is about the batch START; it answers for ch 421 only
    # while 421 is that start. Across a two-year replay 421 sits in the current
    # batch, then the next one, then is the start — so the history charts need
    # the question asked per chapter.
    horizons = quarter_ends(today, 16)
    p_ch = {}
    for k in range(10):
        for ch_no, pmf_in, grid in ((first_ch + k, post, cand),
                                    (second_ch + k, post2, cand2)):
            pm = shift(pmf_in, len(grid), k)
            tot = pm.sum()
            if tot <= 0:
                continue
            cumk = np.cumsum(pm / tot)
            row = {}
            for t in horizons:
                idx = [i for i, c in enumerate(grid) if c[1] <= t]
                row[t.isoformat()] = round(float(cumk[max(idx)]), 4) if idx else 0.0
            p_ch[str(ch_no)] = row

    path = snapshot.write("posterior", next_batch, {
        "forecast_timestamp": today.isoformat(),
        "target": "W_%d — publication of ch %d" % (next_batch, first_ch),
        "level": "1+2 combined posterior",
        "half_life_batches": HALF_LIFE,
        "analogs": analogs,
        "level2_design": "readiness_coordinate_context_record_hiatus_v4",
        "n_chapters_with_current_readiness": sum(r["p_hat"] is not None
                                                  for r in current_state.values()),
        "readiness_target_batch": [current_state[c] for c in target_chapters],
        "readiness_preceding_batch": [preceding_state[c] for c in preceding_chapters],
        "readiness_following_batch": [following_state[c] for c in following_chapters],
        "batch_scope_name_events": names,
        "progress_coordinate": {
            "page_log": "0.01 per observed manuscript page, capped at 0.19",
            "stage_endpoints": {"panel_layout": .30, "character_inking": .50,
                                "bg_spec": .60, "bg_work": .70, "dialogue": .80,
                                "manuscript_complete": .90, "retouch": .99},
            "note": "Status flags are retained separately; the coordinate is furthest observed progress, not a claim of irreversible sequential work.",
        },
        "analog_detail": {str(h): analog_detail[h] for h in analog_detail},
        "preceding_batch_context": {"weight": CONTEXT_WEIGHT,
                                      "analogs": {str(h): context_detail[h] for h in context_detail},
                                      "implied_by_analog": {str(h): date.fromordinal(int(v)).isoformat()
                                                             for h, v in context_implied.items()},
                                      "fading_analogs": context_fading},
        "exhausted_analogs": exhausted,
        "implied_by_analog": {str(h): date.fromordinal(int(v)).isoformat()
                              for h, v in implied.items()},
        "truncation_floor": by_seq[floor_seq]["on_sale"].isoformat(),
        # Calendar time after this date is intentionally not another no-start
        # observation.  A silent interval should leave the forecast unchanged.
        "conditioning_through": latest_event.isoformat(),
        "record_hiatus": record_hiatus,
        "median": med[1].isoformat(),
        "intervals": intervals,
        "p_started_by": p_by,
        "p_by_chapter": p_ch,
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
        "correlation_note": "Each analog contributes ONE likelihood factor. "
                            "The per-chapter readiness states summarise correlated "
                            "tweets; treating every event as independent would badly "
                            "over-sharpen the posterior. Same-batch readiness has "
                            "weight 0.75; preceding-batch production context has "
                            "weight 0.25. Stale analogs fade smoothly to neutral.",
    }, summary={"median": med[1].isoformat(), "i50": intervals["50"],
                "i80": intervals["80"], "i90": intervals["90"]},
       rid=rid, extra={"provenance": "replay", "replay_asof": asof.isoformat()}
       if asof else None)
    say("\nsnapshot -> %s" % os.path.relpath(path, D()))


if __name__ == "__main__":
    main()
