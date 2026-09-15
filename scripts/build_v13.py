#!/usr/bin/env python3
"""V13: slowest-observed production countdown.

For a fixed 0--10 ordered-readiness grid, each half-chapter transition receives
the longest observed duration among batches 47--49.  The remaining budget is
the sum of the still-unfinished transitions plus the longest observed delay
from the last reported readiness state to publication.

At every new readiness observation a candidate deadline is formed.  The live
deadline is the earliest candidate seen so far, so progress can improve it or
leave it unchanged but can never move it later.  Silence does not reset the
clock.  This is a slowest-*observed* envelope, not a claim about a physical
maximum.
"""
from datetime import timedelta
from math import sqrt

import numpy as np

from build_readiness import ordered_trace

GRID_STEP = 0.5
GRID_MAX = 10.0
TAIL_SIGMA_DAYS = 120.0
LEFT_CENSOR_LEVEL = 1.0


def crossing(path, level):
    """First date at/above level, or None when absent/left-censored."""
    if not path or path[-1][1] + 1e-9 < level:
        return None
    if path[0][1] > LEFT_CENSOR_LEVEL and level <= path[0][1] + 1e-9:
        return None
    return next(d for d, value in path if value + 1e-9 >= level)


def transition_envelope(analog_paths, analog_starts):
    """Longest observed duration for each common half-chapter transition."""
    segments, observed = [], []
    n = int(round(GRID_MAX / GRID_STEP))
    for i in range(n):
        lo, hi = i * GRID_STEP, (i + 1) * GRID_STEP
        values = []
        for batch, path in analog_paths.items():
            d0, d1 = crossing(path, lo), crossing(path, hi)
            if d0 is not None and d1 is not None:
                values.append({"batch": batch, "days": (d1 - d0).days})
        if values:
            longest = max(v["days"] for v in values)
            observed.append(longest)
        else:
            longest = None
        segments.append({"from": lo, "to": hi, "days": longest,
                         "observations": values})

    fallback = max(observed) if observed else 0
    for row in segments:
        if row["days"] is None:
            row["days"] = fallback
            row["fallback"] = True

    schedule = []
    for batch, path in analog_paths.items():
        if path and batch in analog_starts:
            schedule.append({"batch": batch,
                             "days": (analog_starts[batch] - path[-1][0]).days})
    schedule_days = max((x["days"] for x in schedule), default=0)
    return segments, schedule_days, schedule


def remaining_budget(level, segments, schedule_days):
    """Unspent slowest-observed days after a readiness observation."""
    return schedule_days + sum(row["days"] for row in segments
                               if row["to"] > level + 1e-9)


def build(events, target_chapters, analog_chapters, analog_starts, asof):
    analog_paths = {
        h: [(d, b) for d, b, _ in ordered_trace(events, chapters, analog_starts[h])]
        for h, chapters in analog_chapters.items() if h in analog_starts
    }
    segments, schedule_days, schedule_obs = transition_envelope(
        analog_paths, analog_starts)
    target_path = [(d, b) for d, b, _ in ordered_trace(events, target_chapters, asof)]
    candidates, deadline = [], None
    for attained, level in target_path:
        budget = remaining_budget(level, segments, schedule_days)
        candidate = attained + timedelta(days=budget)
        deadline = candidate if deadline is None else min(deadline, candidate)
        candidates.append({"attained": attained.isoformat(), "level": round(level, 4),
                           "remaining_budget_days": budget,
                           "candidate_deadline": candidate.isoformat(),
                           "running_deadline": deadline.isoformat()})
    return deadline, {
        "level": round(target_path[-1][1], 4) if target_path else 0.0,
        "grid_step": GRID_STEP,
        "transition_segments": segments,
        "schedule_delay_days": schedule_days,
        "schedule_observations": schedule_obs,
        "deadline_history": candidates,
        "deadline": deadline.isoformat() if deadline else None,
        "tail_sigma_days": TAIL_SIGMA_DAYS,
        "interpretation": "slowest observed envelope; not a maximum possible wait",
    }


def distribution(candidate_dates, deadline, sigma=TAIL_SIGMA_DAYS):
    """Broad forecast centred on the active conservative deadline.

    V13 deliberately does not multiply this by the ordinary gap prior: doing
    that made the supposedly pessimistic forecast inherit the prior's much
    earlier median. Historical hiatus information enters through the separate
    longest-observed hiatus deadline selected by the caller.
    """
    if deadline is None:
        return np.ones(len(candidate_dates), float)
    z = np.array([(d - deadline).days for d in candidate_dates], float) / sigma
    out = np.exp(-0.5 * z ** 2)
    out = np.maximum(out, 1e-12)
    return out / out.sum()
