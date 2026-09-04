#!/usr/bin/env python3
"""Level 2 as batch FEASIBILITY, indexed by a monotone readiness state.

The all-pairs coordinate likelihood (V5-V8) translates each production event
into an implied start date by adding a historical event-to-start lag.  That
construction has two properties the history chart keeps exposing:

  * a report arriving later than the analog expected pushes the forecast LATER,
    so a production event — physically always progress — usually reads as bad
    news;
  * the implied dates move whenever the event cloud moves, which is often.

This module implements the alternative the project's own findings point at
(README, "Production is not the bottleneck"; docs/model.md, "Level 2 should
treat production state as evidence about batch feasibility"): summarise the
batch by ONE monotone state and ask history how long batches took to start from
that state.

    B(t) = sum over the batch's ten ordered chapter-readiness coordinates.

B is non-decreasing in t by construction, so at equal calendar time more
production always implies an earlier forecast — the monotonicity the analog
date-translation could not offer.

Measured at the three resolved tweet-era starts on the ordered 0--10 scale:

    batch 47   B =  9.1 at start
    batch 48   B =  9.5 at start
    batch 49   B = 10.0 at start

The remaining time at comparable thresholds is the editorial decision the
model cannot see.

For each analog h this module builds the empirical remaining-time curve

    R_h(b) = start[h] - (first date at which B_h reached b)

using only events public before start[h].  At forecast time the current batch's
level b = B(t) was first attained on a known date, so

    implied_start(h) = attained_date(b) + R_h(b).

One analog is one component, per the correlation rule: ten chapters at one
readiness level are one production process, not ten observations.
"""
from datetime import date, timedelta

import numpy as np

from build_readiness import ordered_trace

SIGMA_FLOOR = 30.0       # days; three analogs cannot support a sharper claim


def trace(ev, chapters, upto):
    """[(date, B)] at every date B increased, up to and including `upto`.

    B is the 0--10 sum of ordered, retouch-free chapter readiness returned by
    :func:`build_readiness.ordered_trace`.
    """
    return [(d, value) for d, value, _ in ordered_trace(ev, chapters, upto)]


def level(ev, chapters, asof):
    """B(t): summed ordered readiness across a batch's ten chapters."""
    path = trace(ev, chapters, asof)
    return path[-1][1] if path else 0.0


def attained_date(path, b):
    """First traced date at which the level reached `b`."""
    for d, v in path:
        if v >= b - 1e-9:
            return d
    return path[-1][0] if path else None


# A run whose FIRST public report already places it above this level was not
# observed from the beginning, so the date it crossed any lower level is
# unknown. Batch 47 opens at B=3.00 because Togashi's account did not exist
# earlier; batches 48 and 49 open at 0.05 and 0.03, which is genuinely the
# start. One chapter-equivalent separates the two cases cleanly.
OBSERVED_FROM_START = 1.0


def remaining(path, outcome, b):
    """R(b): days from first reaching level `b` to the batch actually starting.

    Returns None when the analog cannot speak to this level, in either
    direction:

    * `b` above anything it reached before starting -- not extrapolated;
    * `b` at or below its first observed reading, when that reading is itself
      well above zero -- LEFT-CENSORED. `attained_date` would otherwise hand
      back the day the first post was made, which is when the archive begins,
      not when the run reached that level. That silently turned "we have no
      idea" into "152 days" for batch 47 at B=1.5.
    """
    if not path or b > path[-1][1] + 1e-9:
        return None
    if path[0][1] > OBSERVED_FROM_START and b <= path[0][1] + 1e-9:
        return None
    d = attained_date(path, b)
    return None if d is None else (outcome - d).days


def floor_components(ev, target_chapters, analog_chapters, analog_starts, asof):
    """One-sided feasibility floors: the earliest each analog still allows.

    `components` centres a bump on an implied date, which lets three analogs
    assert a start date they cannot support.  This instead returns a LOWER
    bound per analog and lets the historical gap prior say everything above it:

        remaining_h = max(0, R_h(b) - days already spent at level b)
        floor_h     = asof + remaining_h

    At equal calendar time a higher readiness level b gives a smaller R_h(b)
    and so an earlier floor: the term is monotone in production state, which is
    what "a production event can only move the date earlier" has to mean once
    the calendar is held fixed.  During silence b does not change and the floor
    can only advance until the analog's remaining time is spent, after which it
    is inert - production has stopped constraining anything, which for these
    batches is the true state of affairs well before the batch starts.
    """
    ordered_now = ordered_trace(ev, target_chapters, asof)
    now_path = [(d, value) for d, value, _ in ordered_now]
    if not now_path:
        return {}, {"level": 0.0, "reason": "no production reported"}
    b_now = now_path[-1][1]
    at = attained_date(now_path, b_now)
    spent = (asof - at).days if at else 0
    floors, detail_h = {}, {}
    for h, chs in analog_chapters.items():
        outcome = analog_starts.get(h)
        if outcome is None:
            continue
        r = remaining(trace(ev, chs, outcome), outcome, b_now)
        if r is None:
            detail_h[h] = {"usable": False,
                           "reason": "analog never reached B=%.3f before starting" % b_now}
            continue
        left = max(0, r - spent)
        floors[h] = (asof + timedelta(days=left)).toordinal()
        detail_h[h] = {"usable": True, "remaining_days_at_this_level": r,
                       "days_already_spent": spent, "still_required": left,
                       "feasible_from": (asof + timedelta(days=left)).isoformat()}
    latest_detail = ordered_now[-1][2]
    chapter_states = [{"chapter": chapter,
                       "direct": round(latest_detail["direct"][chapter], 4),
                       "inferred_floor": round(latest_detail["inferred_floor"][chapter], 4),
                       "ordered": round(latest_detail["ordered"][chapter], 4)}
                      for chapter in sorted(target_chapters)]
    return floors, {"level": round(b_now, 4),
                    "scale": "summed chapter-equivalents, 0 to %d" % len(target_chapters),
                    "attained": at.isoformat() if at else None,
                    "days_at_level": spent, "analogs": detail_h,
                    "chapter_states": chapter_states,
                    "binding": bool(floors) and max(floors.values()) > asof.toordinal()}


def components(ev, target_chapters, analog_chapters, analog_starts, asof):
    """(implied, sigma, detail) — one Gaussian component per analog batch.

    `analog_chapters[h]` is that batch's own ten chapters; `analog_starts[h]`
    the date it began.  Each analog is traced only on evidence public before it
    started, so this is a leakage-free comparison.
    """
    now_path = trace(ev, target_chapters, asof)
    if not now_path:
        return {}, {}, {"level": 0.0, "reason": "no production reported"}
    b_now = now_path[-1][1]
    at = attained_date(now_path, b_now)
    implied, detail_h = {}, {}
    for h, chs in analog_chapters.items():
        outcome = analog_starts.get(h)
        if outcome is None:
            continue
        path = trace(ev, chs, outcome)
        r = remaining(path, outcome, b_now)
        if r is None:
            detail_h[h] = {"usable": False,
                           "reason": "analog never reached B=%.3f before starting" % b_now,
                           "max_level": round(path[-1][1], 3) if path else 0.0}
            continue
        implied[h] = (at + timedelta(days=r)).toordinal()
        detail_h[h] = {"usable": True, "remaining_days_at_this_level": r,
                       "analog_start": outcome.isoformat(),
                       "implied_start": (at + timedelta(days=r)).isoformat()}

    if not implied:
        return {}, {}, {"level": round(b_now, 4),
                        "attained": at.isoformat() if at else None,
                        "analogs": detail_h,
                        "reason": "no analog reached this readiness level pre-start"}

    # The spread ACROSS analogs is the honest scale: it is the disagreement
    # between the only comparable runs about how long "this ready" lasts.  A
    # single usable analog cannot supply a spread, so it falls back to the floor.
    vals = np.array(list(implied.values()), float)
    spread = max(float(1.4826 * np.median(np.abs(vals - np.median(vals)))), SIGMA_FLOOR)
    sigma = {h: spread for h in implied}
    return implied, sigma, {"level": round(b_now, 4),
                            "attained": at.isoformat() if at else None,
                            "sigma_days": round(spread, 1),
                            "analogs": detail_h}
