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

Also applies the §3 within-batch schedule to derive the ten-chapter forecast.
The two non-consecutive intervals since 2007 occurred in the same run, so they
are represented as one shared disrupted-batch regime rather than nine
independent chapter-level skip trials.
"""
import csv
import json
import os
import sys
from datetime import date, timedelta
from math import erf, erfc, sqrt

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_batch_prior import (load_gaps, load_calendar, project_calendar,
                               weights, build_prior, build_shifted_lognormal_prior, D)
from build_level2 import load as load_l2, events_with_lag
from build_readiness import (states as readiness_states, batch_scope as name_scope,
                             coordinate_events)
import build_feasibility
import snapshot

HALF_LIFE = None       # backtest-selected: no recency decay (docs/backtest.md)
# Fifteen completed modeling-era batches supply fourteen regular schedules and
# one disrupted schedule.  The disrupted run had one extra issue before its
# sixth chapter and another before its ninth.  This empirical batch-level
# mixture preserves the observed correlation between those delays.
P_DISRUPTED_BATCH = 1.0 / 15.0
DISRUPTED_EXTRA_AFTER_STEPS = (5, 8)
QS = [0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95]
# V5 all-pairs settings.  The coordinate backtest imports this module and
# changes these explicitly for each leakage-free candidate setting.
COORD_BANDWIDTH = 1.0       # chapters
COORD_RANGE = (-20.0, 35.0)
PAIR_SIGMA_FLOOR = 21.0     # days
USE_ALL_PAIRS = True        # backtest may set False for the Level-1 baseline
# The direct two-gap prior is used for the batch after next while its
# predecessor has not yet begun.  Its support must cover the largest observed
# adjacent-pair sum (268 issues), rather than the one-gap maximum (184).
TWO_GAP_MAX = 280
TWO_GAP_BANDWIDTH = 60.0
SEPARATE_ZERO_GAP_MODE = True   # point mass at gap 0 + KDE on g >= 1
# V9: the V8 shifted-lognormal Level 1 is OFF.  Fitting log(G + 0.5) to a sample
# containing three zeros drove mu down and sigma up (mu 3.20, sigma 1.76), which
# put the day-one median at 15-23 issues against an empirical median near 50 and
# gave the prior a FALLING hazard.  A falling hazard is exactly what makes a
# forecast recede faster than one day per day once it is conditioned on continued
# non-publication: d(median)/d(elapsed) = h(elapsed)/h(median) > 1.
# `backtest_conditional_prior.py` scores that conditional family leakage-free and
# measures 1.56 issues of recession per issue waited for the lognormal against
# 0.61 for the mixture, with a worse CRPS (29.44 vs 24.27).  See docs/backtest.md.
PARAMETRIC_LEVEL1 = False
FREEZE_ANALOG_FADE_UNTIL_RECORD = True
# How the per-analog components are combined.  Both are off = the V8 form:
# average peak-height-1 curves with equal weight.  See `all_pairs_likelihood`.
NORMALISE_ANALOG_COMPONENTS = False
# Which Level 2 to run.  "all_pairs" is the V5-V8 coordinate date-translation;
# "readiness_mixture" is V11's two-sided ordered-readiness likelihood.
# "feasibility" retains V10's one-sided floor for comparison/replay.
LEVEL2_MODE = "readiness_mixture"
FEASIBILITY_SIGMA = 30.0    # days of softness on the one-sided ramp
READINESS_MIXTURE_SIGMA = 120.0  # broad by design: only three resolved analogs
# V9: reweight analogs by their own survival under continued non-publication.
# An analog whose implied start has already passed is not merely uninformative
# about *when* the batch starts; it is evidence that this batch is not being
# scheduled like that one.  Averaging with equal weight throws that away.
WEIGHT_ANALOGS_BY_SURVIVAL = True


def within_batch_offsets(k):
    """PMF over elapsed issues after ``k`` steps under one shared regime."""
    extras = sum(k >= step for step in DISRUPTED_EXTRA_AFTER_STEPS)
    out = np.zeros(k + extras + 1)
    out[k] += 1.0 - P_DISRUPTED_BATCH
    out[k + extras] += P_DISRUPTED_BATCH
    return out


def two_gap_prior(gaps, elapsed_first_gap):
    """Prior for H = G_1 + G_2, conditional on the first gap's non-start.

    `gaps` is chronological.  Adjacent pairs are deliberately retained as
    pairs rather than produced by convolving two independent one-gap draws:
    the data itself is the relevant two-batch process.  When the predecessor
    has already failed to start for `elapsed_first_gap` issues, only historical
    pairs with a first gap at least that long are comparable.

    With no comparable historical first gap left, preserve the physical lower
    bound H >= elapsed_first_gap and fall back to the broad unconditional H
    prior.  This is an explicit extrapolation, recorded in the snapshot.
    """
    raw = np.array([g for _, g in gaps], float)
    if len(raw) < 2:
        return np.ones(TWO_GAP_MAX + 1) / (TWO_GAP_MAX + 1), {
            "conditioning": "insufficient historical pairs", "n_pairs": 0,
        }
    first, second = raw[:-1], raw[1:]
    h = first + second
    # Each overlapping two-gap trajectory is one observation.  In particular,
    # the one observed (0, 0) trajectory is counted once, not split again by
    # the zero-gap clustering rule used for the one-gap prior.
    pair_w = weights(len(h), HALF_LIFE)
    keep = first >= elapsed_first_gap
    fallback = not bool(np.any(keep))
    if fallback:
        use_h, use_w = h, pair_w
    else:
        use_h, use_w = h[keep], pair_w[keep]

    if not SEPARATE_ZERO_GAP_MODE:
        # V7 experiment: H=0 is smoothed with every other H observation rather
        # than remaining a separate two-run-continuation point mass.
        grid = np.arange(0, TWO_GAP_MAX + 1, dtype=float)
        pmf = np.zeros(len(grid), float)
        for hi, wi in zip(use_h, use_w):
            pmf += wi * np.exp(-0.5 * ((grid - hi) / TWO_GAP_BANDWIDTH) ** 2)
        pmf /= pmf.sum()
    else:
        pmf = np.zeros(TWO_GAP_MAX + 1, float)
        zero_w = float(use_w[use_h == 0].sum())
        pmf[0] = zero_w / float(use_w.sum())
        positive = use_h > 0
        if np.any(positive):
            grid = np.arange(1, TWO_GAP_MAX + 1, dtype=float)
            dens = np.zeros(len(grid), float)
            for hi, wi in zip(use_h[positive], use_w[positive]):
                dens += wi * np.exp(-0.5 * ((grid - hi) / TWO_GAP_BANDWIDTH) ** 2)
            dens /= dens.sum()
            pmf[1:] = (1 - pmf[0]) * dens
        else:
            pmf[0] = 1.0

    # Kernel smoothing has support everywhere.  Reapply the factual lower bound
    # after smoothing: H >= G1 >= elapsed_first_gap.  Without this, a selected
    # long-first-gap pair could still leak a little density onto an impossible
    # early following-batch date.
    pmf[:min(elapsed_first_gap, len(pmf))] = 0.0
    if pmf.sum() > 0:
        pmf /= pmf.sum()
    return pmf, {
        "conditioning": "fallback: H truncated at elapsed first gap" if fallback
                        else "historical pairs with G1 >= elapsed first gap",
        "elapsed_first_gap": int(elapsed_first_gap),
        "n_pairs": int(len(h)), "n_eligible_pairs": int(keep.sum()),
        "observed_h": [int(x) for x in h], "max_gap": TWO_GAP_MAX,
        "bandwidth": TWO_GAP_BANDWIDTH,
        "separate_zero_mode": SEPARATE_ZERO_GAP_MODE,
    }


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

    announcement_rows = list(csv.DictReader(
        open(D("data", "annotations", "announcements.csv"), encoding="utf-8")))
    # A scheduled date can extend a batch only once the announcement itself was
    # public.  In a replay, an undated annotation is not admissible evidence.
    if asof:
        announcement_rows = [r for r in announcement_rows
                             if r.get("announcement_date")
                             and date.fromisoformat(r["announcement_date"]) <= asof]
    ann = {int(r["chapter"]): date.fromisoformat(r["publication_date"])
           for r in announcement_rows}

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
    # The batch's continued non-publication is a public fact at *every* forecast
    # timestamp.  Earlier V4/V5 revisions applied this floor only when a tweet
    # arrived; that left probability on dates already past, then discarded many
    # months of it in one artificial jump at the next tweet.  The production
    # likelihood remains event-derived, but the support must always begin after
    # the latest issue known not to contain this batch.
    latest_event = max((date.fromisoformat(r["event_date"]) for r in ev
                        if r.get("event_date")), default=today)
    floor_seq = max(end_seq + 1, last_obs + 1)
    elapsed_gap = floor_seq - end_seq - 1
    record_hiatus = elapsed_gap > max(g for _, g in gaps)
    # V8 keeps the analog-fade likelihood fixed between public production
    # events. The current issue floor still removes impossible start dates, but
    # an overdue analog is not continuously neutralised until a record hiatus.
    last_issue_at_event = max((c["seq"] for c in cal if not c["projected"]
                               and c["on_sale"] <= latest_event), default=end_seq)
    fade_floor_seq = floor_seq if (record_hiatus or not FREEZE_ANALOG_FADE_UNTIL_RECORD) \
        else max(end_seq + 1, last_issue_at_event + 1)

    w = weights(len(gaps), HALF_LIFE) * np.array(cluster_w)
    max_gap = 200
    if PARAMETRIC_LEVEL1:
        pmf_gap, prior_parameters = build_shifted_lognormal_prior(gaps, w, max_gap)
        pi0 = prior_parameters["raw_zero_frequency"]
    else:
        pmf_gap, pi0 = build_prior(gaps, w, max_gap,
                                   separate_zero=SEPARATE_ZERO_GAP_MODE)
        prior_parameters = {"family": "kernel", "separate_zero_mode": SEPARATE_ZERO_GAP_MODE}

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

    # ---------- V5: all-pairs coordinate likelihood ----------
    # Every usable production event is a point (C, t).  For each resolved
    # historical batch start h, pair that start with every event public before
    # it.  A current event votes through historical pairs with a similar
    # coordinate distance to the target publication coordinate.  This admits
    # evidence from preceding *and following* chapters without declaring those
    # events independent publication decisions.
    coords = coordinate_events(ev, asof=asof)
    first_by_batch = {b: min(c for c, bb in batch.items() if bb == b)
                      for b in start}
    current_pairs = [e for e in coords
                     if COORD_RANGE[0] <= first_ch - e["coordinate"] <= COORD_RANGE[1]]
    historical_pairs = {}
    for h in analogs:
        target_c = first_by_batch[h]
        outcome = start[h]
        historical_pairs[h] = [{"delta_c": target_c - e["coordinate"],
                                "lag": (outcome - e["date"]).days,
                                "event_id": e["event_id"]}
                               for e in coords
                               if e["date"] <= outcome and
                               COORD_RANGE[0] <= target_c - e["coordinate"] <= COORD_RANGE[1]]

    def all_pairs_likelihood():
        by_h, detail, comp_weight = [], {}, []
        # Continued non-publication makes an analogue which predicted a much
        # earlier start progressively less relevant.  This is distinct from a
        # production tweet: it evolves with the factual no-start floor, rather
        # than being applied in one lump at the next tweet.
        fade_floor_ord = by_seq[fade_floor_seq]["on_sale"].toordinal()
        x = np.array([d.toordinal() for _, d, _ in cand], float)
        for h in analogs:
            templates = historical_pairs.get(h) or []
            # Each current event is given equal total influence; within it every
            # compatible historical coordinate pair is used with kernel weight.
            per_current = []
            n_pairs = 0
            for e in current_pairs:
                dc = first_ch - e["coordinate"]
                ws, centres = [], []
                for q_ in templates:
                    w_ = np.exp(-0.5 * ((dc - q_["delta_c"]) / COORD_BANDWIDTH) ** 2)
                    if w_ < 1e-4:
                        continue
                    ws.append(w_)
                    centres.append(e["date"].toordinal() + q_["lag"])
                if ws:
                    per_current.append((np.array(ws), np.array(centres, float)))
                    n_pairs += len(ws)
            if not per_current:
                continue
            all_centres = np.concatenate([z for _, z in per_current])
            centre = float(np.median(all_centres))
            sigma_pair = max(1.4826 * float(np.median(np.abs(all_centres - centre))),
                             PAIR_SIGMA_FLOOR)
            mix = np.zeros(len(cand), float)
            survive = []
            for ws, centres in per_current:
                ws = ws / ws.sum()
                mix += np.sum(ws[:, None] * np.exp(-0.5 * ((x[None, :] - centres[:, None]) /
                                                           sigma_pair) ** 2), axis=0)
                survive.append(float(np.sum(ws * 0.5 * np.vectorize(erfc)(
                    (fade_floor_ord - centres) / (sigma_pair * sqrt(2.0))))))
            mix /= len(per_current)
            raw_survival = float(np.mean(survive))
            alpha = raw_survival / (raw_survival + 0.05)  # stale -> neutral
            if NORMALISE_ANALOG_COMPONENTS:
                # V9.  Each analog is one hypothesis about how this batch is
                # being scheduled, and the analogs are averaged.  That average
                # is only a mixture over hypotheses if every component is a
                # normalised density.  Up to V8 the components were averaged
                # after being scaled to peak height 1, so a component's weight
                # was proportional to its own spread: batch 47 (sigma 53 d) and
                # batch 48 (sigma 250 d) entered the average with total masses
                # in a 1:4.7 ratio purely because one analog was vaguer than the
                # other.  Normalising first makes "vaguer" mean "flatter", which
                # is what it should mean.
                total = float(mix.sum())
                dens = mix / total if total > 0 else np.full(len(cand), 1.0 / len(cand))
                flat = np.full(len(cand), 1.0 / len(cand))
                by_h.append(alpha * dens + (1 - alpha) * flat)
            else:
                by_h.append(alpha * mix + (1 - alpha))
            comp_weight.append(max(raw_survival, 1e-6)
                               if WEIGHT_ANALOGS_BY_SURVIVAL else 1.0)
            detail[h] = {"historical_pairs": len(templates),
                         "current_events_matched": len(per_current),
                         "weighted_pair_matches": n_pairs,
                         "centre": date.fromordinal(int(centre)).isoformat(),
                         "sigma_days": round(sigma_pair, 2),
                         "fade_alpha": round(alpha, 4),
                         "survival_under_no_start": round(raw_survival, 4)}
        if not by_h:
            return np.ones(len(cand), float), detail
        cw_ = np.array(comp_weight, float)
        cw_ /= cw_.sum()
        for h, wt in zip(detail, cw_):
            detail[h]["component_weight"] = round(float(wt), 4)
        out = np.sum(cw_[:, None] * np.array(by_h), axis=0)
        out /= out.max() if out.max() > 0 else 1
        return out, detail

    if LEVEL2_MODE == "all_pairs":
        all_pairs_lik, all_pairs_detail = all_pairs_likelihood()
    else:
        # V10 does not consume the expensive V5--V8 date-translation model.
        # Research replays select ``all_pairs`` explicitly when they need it.
        all_pairs_lik, all_pairs_detail = np.ones(len(cand), float), {}
    lik = all_pairs_lik if USE_ALL_PAIRS else np.ones(len(cand), float)

    # ---------- V10/V11: ordered batch readiness ----------
    analog_chapters = {h: sorted(c for c, b in batch.items() if b == h)[:10]
                       for h in analogs}
    feas_floors, feasibility = build_feasibility.floor_components(
        ev, target_chapters, analog_chapters, {h: start[h] for h in analogs}, today)
    readiness_centres, _readiness_sigma, readiness_mixture = build_feasibility.components(
        ev, target_chapters, analog_chapters, {h: start[h] for h in analogs}, today)
    if LEVEL2_MODE == "none":
        lik = np.ones(len(cand), float)
    elif LEVEL2_MODE == "feasibility":
        if feas_floors:
            xs = np.array([d.toordinal() for _, d, _ in cand], float)
            # One analog is one component (the correlation rule): average the
            # per-analog ramps rather than multiplying them, so three analogs
            # cannot compound into a hard wall.
            ramps = [0.5 * (1.0 + np.vectorize(erf)((xs - f) /
                                                    (FEASIBILITY_SIGMA * sqrt(2.0))))
                     for f in feas_floors.values()]
            lik = np.mean(ramps, axis=0)
            lik = np.maximum(lik, 1e-9)
            lik /= lik.max()
        else:
            lik = np.ones(len(cand), float)
        feasibility["applied"] = bool(feas_floors)
    elif LEVEL2_MODE == "readiness_mixture":
        if readiness_centres:
            xs = np.array([d.toordinal() for _, d, _ in cand], float)
            kernels = [np.exp(-0.5 * ((xs - centre) /
                                      READINESS_MIXTURE_SIGMA) ** 2)
                       for centre in readiness_centres.values()]
            # One component per resolved historical batch. Averaging preserves
            # the independent evidence count; multiplying would falsely turn
            # three analogs into a narrow consensus estimate.
            lik = np.mean(kernels, axis=0)
            lik = np.maximum(lik, 1e-12)
            lik /= lik.max()
        else:
            lik = np.ones(len(cand), float)
        readiness_mixture["applied"] = bool(readiness_centres)
        readiness_mixture["kernel"] = "Gaussian"
        readiness_mixture["component_sigma_days"] = READINESS_MIXTURE_SIGMA
        readiness_mixture["centres"] = {
            str(h): date.fromordinal(int(v)).isoformat()
            for h, v in readiness_centres.items()
        }

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
        """PMF over elapsed issues after ``k`` steps under a shared regime.

        A batch is drawn once as regular or disrupted.  It is not redrawn at
        every chapter transition, because both observed delays belong to the
        same historical run.
        """
        return within_batch_offsets(k)

    def shift(pmf_in, grid_len, k):
        """Advance a distribution over candidate slots by k within-batch steps."""
        out = np.zeros(grid_len)
        for j, pw in enumerate(offsets(k)):
            if pw <= 0 or j >= grid_len:
                continue
            out[j:] += pw * pmf_in[:grid_len - j]
        return out

    # ---------- the batch AFTER this one ----------
    # V8 restores the V6-style conditional convolution. Its only gap input is
    # the parametric Level-1 prior; no following-batch tweet is reused here.
    seqs = [c[0] for c in cand]
    grid2 = [(s_, by_seq[s_]["on_sale"])
             for s_ in range(seqs[-1] + 1, seqs[-1] + max_gap + 2)
             if s_ in by_seq]
    all_seq = seqs + [s_ for s_, _ in grid2]
    all_date = [c[1] for c in cand] + [d for _, d in grid2]
    cand2 = [[s_, d, 0.0] for s_, d in zip(all_seq, all_date)]
    end_this = shift(post, len(cand), 9)
    post2 = np.zeros(len(cand2))
    for i, pe in enumerate(end_this):
        if pe <= 0:
            continue
        for g, pg in enumerate(pmf_gap):
            j = i + g + 1
            if j < len(post2):
                post2[j] += pe * pg
    if post2.sum() > 0:
        post2 /= post2.sum()

    def q2(pmf, qq):
        c = np.cumsum(pmf)
        return cand2[min(int(np.searchsorted(c, qq)), len(cand2) - 1)]

    conditional_scenarios = []

    second_ch = first_ch + 10
    rows_out2 = []
    for k in range(10):
        pmf = shift(post2, len(cand2), k)
        pmf = pmf / pmf.sum()
        rows_out2.append({"chapter": second_ch + k,
                          "median": q2(pmf, .50)[1].isoformat(),
                          "i50": [q2(pmf, .25)[1].isoformat(), q2(pmf, .75)[1].isoformat()],
                          "i80": [q2(pmf, .10)[1].isoformat(), q2(pmf, .90)[1].isoformat()]})
    say("\n=== following batch (ch %d-%d), parametric gap convolution ==="
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

    say("\nWithin-batch spacing uses one shared regime: 14/15 completed batches")
    say("are regular; the one disrupted batch supplies both observed delays.")
    say("These chapters are conditional marginals, NOT independent forecasts.")

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
        "level2_design": ("ordered_readiness_two_sided_mixture_v11" if LEVEL2_MODE == "readiness_mixture"
                          else "ordered_readiness_feasibility_floor_v10" if LEVEL2_MODE == "feasibility"
                          else "all_pairs_coordinate_likelihood_v9_mixture_level1"),
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
                                "manuscript_complete": .90},
            "note": "Retouch is excluded. Direct progress is retained separately from the order-inferred readiness floor used by B(t).",
        },
        "analog_detail": {str(h): analog_detail[h] for h in analog_detail},
        "preceding_batch_context": {"weight": CONTEXT_WEIGHT,
                                      "analogs": {str(h): context_detail[h] for h in context_detail},
                                      "implied_by_analog": {str(h): date.fromordinal(int(v)).isoformat()
                                                             for h, v in context_implied.items()},
                                      "fading_analogs": context_fading},
        "all_pairs_coordinate_likelihood": {
            "coordinate": "C = chapter - 1 + within-chapter progress",
            "delta_c": "target publication coordinate minus event coordinate",
            "coordinate_bandwidth_chapters": COORD_BANDWIDTH,
            "coordinate_range": list(COORD_RANGE),
            "component_sigma_floor_days": PAIR_SIGMA_FLOOR,
            "current_event_count": len(current_pairs),
            "historical_component_detail": {str(h): all_pairs_detail[h]
                                              for h in all_pairs_detail},
            "note": "All coordinate pairs inform each historical batch component; components, not pairs, are averaged.",
        },
        "exhausted_analogs": exhausted,
        "implied_by_analog": {str(h): date.fromordinal(int(v)).isoformat()
                              for h, v in implied.items()},
        "truncation_floor": by_seq[floor_seq]["on_sale"].isoformat(),
        "analog_fade_floor": by_seq[fade_floor_seq]["on_sale"].isoformat(),
        "conditioning_through": by_seq[floor_seq]["on_sale"].isoformat(),
        "last_production_event": latest_event.isoformat(),
        "level1_prior": prior_parameters,
        "level2_mode": LEVEL2_MODE,
        "feasibility": feasibility,
        "readiness_mixture": readiness_mixture,
        "no_start_update": "The posterior support is conditioned through each issue publicly known not to contain the batch. The analog-fade likelihood is held at the latest production-event issue until a record hiatus.",
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
        "posterior_pmf_issue_seq": [[c[0], round(float(pv), 8)]
                                     for c, pv in zip(cand, post) if pv > 1e-7],
        "prior_pmf": [[c[1].isoformat(), round(float(pv), 8)]
                      for c, pv in zip(cand, prior) if pv > 1e-7],
        # Retained for research diagnostics.  This is the all-pairs Level-2
        # likelihood before multiplication by Level 1; like any likelihood it
        # is only identified up to a positive scale.
        "all_pairs_likelihood_pmf": [[c[1].isoformat(), round(float(pv), 8)]
                                      for c, pv in zip(cand, all_pairs_lik) if pv > 1e-7],
        "level2_likelihood_pmf": [[c[1].isoformat(), round(float(pv), 8)]
                                   for c, pv in zip(cand, lik) if pv > 1e-7],
        "ten_chapter_forecast": rows_out,
        "within_batch_schedule": {
            "model": "shared_regular_or_disrupted_batch_regime",
            "regular_probability": round(1.0 - P_DISRUPTED_BATCH, 6),
            "disrupted_probability": round(P_DISRUPTED_BATCH, 6),
            "disrupted_extra_issue_before_positions": [6, 9],
            "evidence": "Fourteen of fifteen completed modeling-era batches were consecutive; both exceptional intervals occurred in the same remaining batch.",
        },
        "next_batch": {
            "batch": next_batch + 1,
            "first_chapter": second_ch,
            "target": "W_%d — publication of ch %d" % (next_batch + 1, second_ch),
            "mode": "forecast",
            "median": q2(post2, .50)[1].isoformat(),
            "intervals": {str(l): [q2(post2, lo)[1].isoformat(),
                                   q2(post2, hi)[1].isoformat()]
                          for l, lo, hi in ((50, .25, .75), (80, .10, .90),
                                            (90, .05, .95))},
            "pmf": [[c[1].isoformat(), round(float(pv), 8)]
                    for c, pv in zip(cand2, post2) if pv > 1e-7],
            "ten_chapter_forecast": rows_out2,
            "evidence": "The Level 1 gap prior convolved with the direct "
                        "predecessor posterior. Following-batch production events "
                        "are not reused here.",
            "level1_gap_prior": prior_parameters,
            "conditional_scenarios": conditional_scenarios,
        },
        "correlation_note": "Each historical batch contributes ONE feasibility ramp. "
                            "The ordered chapter states summarise correlated tweets; "
                            "treating chapters or events as independent would badly "
                            "over-sharpen the posterior. Direct observations and "
                            "order-inferred floors remain separately recorded.",
    }, summary={"median": med[1].isoformat(), "i50": intervals["50"],
                "i80": intervals["80"], "i90": intervals["90"]},
       rid=rid, extra={"provenance": "replay", "replay_asof": asof.isoformat()}
       if asof else None)
    say("\nsnapshot -> %s" % os.path.relpath(path, D()))


if __name__ == "__main__":
    main()
