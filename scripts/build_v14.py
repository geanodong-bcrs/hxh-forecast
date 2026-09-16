#!/usr/bin/env python3
"""V14: per-analog production countdowns, averaged.  NOT ADOPTED.

Built to remove the two defects `docs/v13_review.md` found in V13, measured
against them on the 21-day trajectory diagnostic, and rejected: it is worse than
V13, worse than V12, and worse than running no Level 2 at all.  Production
reporting only begins with batch 47, so under leave-one-out there are 0--1 usable
analogs -- see ``REQUIRE_UNCENSORED_ANALOGS`` below and the "Per-analog
countdowns (V14, not adopted)" section of `docs/model.md` for the scores.

Retained as a selectable comparison mode, and every live snapshot records the
`analog_countdown` block, so what V14 would have said is on the record at each
forecast date without being published.  The construction below is what the
project would want if production reporting were ever complete enough to
support it.

Each resolved analog batch supplies one *observed* wait from a readiness level
to that batch's publication, on the same ordered 0--10 grid as the target:

    r_b(x) = publication_b - date_b(x)

Both ends of ``r_b`` come from the same batch, so the quantity is never a sum
across batches and cannot exceed that batch's own production run.  It also
already contains the post-production scheduling delay, so V13's separate
additive floor is gone: at x = 10.0, ``r_b`` *is* the completion-to-publication
wait, and it decays as readiness rises instead of standing as a constant.

Each analog then contributes one Gaussian component centred on
``attained + r_b(level)``, and the components are AVERAGED, not multiplied
(Agents.md 11).  Three analogs are three views of one correlated process, so the
spread between them is the forecast's width.  V13 instead collapsed them with
``max`` and declared a 120-day width around the slowest one, which put roughly
half the forecast mass beyond a date it described as the slowest observed.

Monotonicity is checked one step rather than over the whole history: the
candidate implied by the newest readiness state is compared with the candidate
implied by the immediately preceding state, and the earlier of the two is kept
per analog.  V13 took a minimum over every candidate it had ever formed, which
stayed well behaved only because its summed envelope was inflated; on a
like-for-like envelope that minimum locks onto pre-stall estimates which the
run's own subsequent silence has already refuted.  A previous candidate that the
publication floor has passed is refuted and does not bind.

The forecast is therefore no longer a "worst case".  ``slowest_observed_date``
is still reported, as the latest of the three components, but it is a marker
rather than the centre of the distribution.
"""
from datetime import timedelta

import numpy as np

from build_readiness import ordered_trace
# Path geometry, shared rather than duplicated. build_v13 is frozen for replay
# (docs/model.md), so importing from it is stable.
from build_v13 import crossing, LEFT_CENSOR_LEVEL  # noqa: F401  (re-exported)

GRID_STEP = 0.5
GRID_MAX = 10.0
# The same broad component width V11/V12 used (READINESS_MIXTURE_SIGMA): three
# resolved analogs do not support a fitted value, and the between-component
# spread now carries most of the uncertainty anyway.
COMPONENT_SIGMA_DAYS = 120.0
# Only analogs whose run was reported from the start supply a countdown.
#
# B(t) is *reported* readiness, and the reporting regimes are not comparable.
# Batch 47's reported trajectory spans 146 days, from B=3.00 to B=9.10, against
# 722 and 626 days for batches 48 and 49: its reporting is left-censored and
# compressed into the final months before publication.  So r_47(x) is small at
# every level -- 126 days at B=4.0, where batch 49 took 659 -- because "B=4.0
# reported" does not describe the same production state across the three runs.
# V13's ``max`` discarded that analog implicitly; averaging gives it equal
# weight, and the 21-day trajectory diagnostic then degrades sharply (MAE 266
# and 246 days against V13's 92 and 34).  Requiring an uncensored path is the
# stated reason to exclude it rather than relying on ``max`` to do so silently.
REQUIRE_UNCENSORED_ANALOGS = True


def analog_remaining(analog_paths, analog_starts, level, require_uncensored=None):
    """Observed days from ``level`` to publication, per analog batch.

    A batch contributes only when its own path demonstrably reached ``level``.
    ``crossing`` returns None both when the path never got there and when the
    path is left-censored at or above it, so a batch whose reporting began
    mid-production is not credited with instant early progress.  When
    ``require_uncensored`` such a batch is excluded outright: see
    ``REQUIRE_UNCENSORED_ANALOGS`` for why a censored path's countdown is not
    comparable.
    """
    if require_uncensored is None:
        require_uncensored = REQUIRE_UNCENSORED_ANALOGS
    out = {}
    for batch, path in analog_paths.items():
        if batch not in analog_starts or not path:
            continue
        if require_uncensored and path[0][1] > LEFT_CENSOR_LEVEL:
            continue
        reached = crossing(path, level)
        if reached is None:
            continue
        out[batch] = (analog_starts[batch] - reached).days
    return out


def candidates(analog_paths, analog_starts, attained, level,
               require_uncensored=None):
    """One implied publication date per analog, from one readiness observation."""
    return {batch: attained + timedelta(days=days) for batch, days
            in analog_remaining(analog_paths, analog_starts, level,
                                require_uncensored).items()}


def build(events, target_chapters, analog_chapters, analog_starts, asof,
          floor=None, require_uncensored=None):
    """Return ``(components, detail)``: one implied date per analog batch.

    ``floor`` is the earliest issue the batch could still start on.  A candidate
    from the preceding readiness state that already sits before it has been
    refuted by continued non-publication and is not allowed to bind.
    """
    analog_paths = {
        h: [(d, b) for d, b, _ in ordered_trace(events, chapters, analog_starts[h])]
        for h, chapters in analog_chapters.items() if h in analog_starts
    }
    target_path = [(d, b) for d, b, _ in ordered_trace(events, target_chapters, asof)]
    if not target_path:
        return {}, {"level": 0.0, "grid_step": GRID_STEP,
                    "component_sigma_days": COMPONENT_SIGMA_DAYS,
                    "components": {}, "analog_remaining_days": {},
                    "slowest_observed_date": None,
                    "one_step_monotonicity": {"applied": False},
                    "interpretation": "no target readiness observations yet"}

    attained, level = target_path[-1]
    current = candidates(analog_paths, analog_starts, attained, level,
                         require_uncensored)

    previous, previous_state = {}, None
    if len(target_path) > 1:
        prev_attained, prev_level = target_path[-2]
        previous = candidates(analog_paths, analog_starts, prev_attained,
                              prev_level, require_uncensored)
        previous_state = {"attained": prev_attained.isoformat(),
                          "level": round(prev_level, 4)}

    components, bound, refuted = {}, [], []
    for batch, implied in current.items():
        earlier = previous.get(batch)
        if earlier is not None and floor is not None and earlier < floor:
            refuted.append(batch)
            earlier = None
        if earlier is not None and earlier < implied:
            bound.append(batch)
            implied = earlier
        components[batch] = implied

    slowest = max(components.values()) if components else None
    return components, {
        "level": round(level, 4),
        "attained": attained.isoformat(),
        "grid_step": GRID_STEP,
        "component_sigma_days": COMPONENT_SIGMA_DAYS,
        "analog_remaining_days": {str(b): d for b, d in
                                  analog_remaining(analog_paths, analog_starts,
                                                   level,
                                                   require_uncensored).items()},
        "components": {str(b): d.isoformat() for b, d in components.items()},
        "slowest_observed_date": slowest.isoformat() if slowest else None,
        "one_step_monotonicity": {
            "rule": "per-analog earlier of newest and preceding readiness state",
            "applied": bool(bound),
            "bound_for_batches": sorted(bound),
            "refuted_by_floor": sorted(refuted),
            "previous_readiness": previous_state,
        },
        "combination": "one component per analog, averaged (Agents.md 11)",
        "require_uncensored_analogs": (REQUIRE_UNCENSORED_ANALOGS
                                       if require_uncensored is None
                                       else require_uncensored),
        "interpretation": ("per-analog observed waits from the current readiness "
                           "level to that analog's publication; the spread "
                           "between analogs is the width, and the slowest "
                           "component is a marker, not the centre"),
    }


def distribution(candidate_dates, components, sigma=COMPONENT_SIGMA_DAYS):
    """Average one Gaussian per analog; never multiply them.

    Multiplying three views of one correlated production process would produce a
    consensus far sharper than three observations support.  Averaging keeps the
    evidence count at the number of analogs, which is the same rule the V5--V8
    all-pairs likelihood and V11/V12's readiness mixture both follow.
    """
    if not components:
        return np.ones(len(candidate_dates), float)
    x = np.array([d.toordinal() for d in candidate_dates], float)
    kernels = [np.exp(-0.5 * ((x - c.toordinal()) / sigma) ** 2)
               for c in components.values()]
    out = np.mean(kernels, axis=0)
    out = np.maximum(out, 1e-12)
    return out / out.sum()
