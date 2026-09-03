#!/usr/bin/env python3
"""What changed between the last two forecasts, and is it worth saying out loud?

Feeds the reply card. Two questions a reader of Togashi's replies actually cares
about, in the order they care about them:

  1. did the expected date move, and which way
  2. did the chance of the nearest candidate issue change

A run that changes neither is not news. `newsworthy()` is what stops the bot
replying "the forecast is exactly the same" under a production post, which is
worse than saying nothing.

A delta is only meaningful with the MODEL and the TARGET held fixed. A median
that moved because the model was revised is not news about Togashi, and posting
it under his tweet would misattribute our own edit to his work. See
`pick_pair()`.
"""
import csv
import glob
import json
import os
from datetime import date

HERE = os.path.dirname(os.path.abspath(__file__))
D = lambda *p: os.path.join(HERE, "..", *p)

MIN_DAYS = 7          # a shift smaller than one issue is not a story
MIN_PP = 2.0          # percentage points


def posteriors():
    """Every timestamped LIVE posterior snapshot, oldest first.

    Replays are excluded. They are re-runs at past dates emitted in bulk
    whenever a candidate Level 2 is scored, so they are not part of the record
    of what the model said as evidence arrived — and one written with a run_id
    at or after the newest live snapshot would silently become the baseline.
    """
    out = []
    for f in sorted(glob.glob(D("data", "forecasts", "*_posterior.json"))):
        if "T" not in os.path.basename(f).split("_")[0]:
            continue                      # pre-automation, date-only names
        with open(f, encoding="utf-8") as fh:
            snap = json.load(fh)
        if snap.get("provenance") == "replay":
            continue
        if not snap.get("median") or not (snap.get("intervals") or {}).get("80"):
            continue                      # incomplete snapshot, nothing to diff
        out.append((f, snap))
    return out


def _design(snap):
    return snap.get("level2_design") or "legacy_v1"


def pick_pair(snaps=None):
    """Newest snapshot, and the newest baseline it can honestly be diffed with.

    Returns ``(cur, prev, reason)``; ``prev`` is None when no such baseline
    exists and ``reason`` says why.

    Walking back STOPS at the first snapshot whose model design or target batch
    differs, rather than skipping over it: if either changed anywhere between
    the two snapshots, the difference is contaminated by that change and is not
    a measurement of new evidence.

    This is not hypothetical. The V10 -> V11 revision on 2026-09-02 moved the
    ch. 421 median from 2028-03-21 to 2026-11-09 — 498 days. With the bot armed
    and a production post landing in that window, it would have told Togashi's
    readers that his post moved the forecast sixteen months. The batch guard is
    the same argument at the roll-over: the first forecast of batch 51 is a new
    target, not a shift in batch 50.
    """
    snaps = posteriors() if snaps is None else snaps
    if not snaps:
        return None, None, "no snapshots"
    cur = snaps[-1][1]
    if len(snaps) == 1:
        return cur, None, "only one live snapshot"
    for _, prev in reversed(snaps[:-1]):
        if _design(prev) != _design(cur):
            return cur, None, ("model changed to %s after %s; no baseline on "
                               "this model yet" % (_design(cur), prev["run_id"]))
        if prev.get("batch") != cur.get("batch"):
            return cur, None, ("target moved to batch %s after %s; nothing to "
                               "compare" % (cur.get("batch"), prev["run_id"]))
        return cur, prev, "ok"
    return cur, None, "no comparable baseline"


def pmf_at(snap, iso):
    for d, p in snap.get("posterior_pmf") or []:
        if d == iso:
            return p
    return 0.0


def compute(cur=None, prev=None):
    """Delta between two snapshots. Defaults to the newest pair."""
    if cur is None:
        cur, prev, _reason = pick_pair()
        if prev is None:
            return None

    new_med = date.fromisoformat(cur["median"])
    old_med = date.fromisoformat(prev["median"])
    shift = (new_med - old_med).days          # negative = moved earlier

    # the single issue carrying most mass — the number people quote
    pmf = cur.get("posterior_pmf") or []
    spike_iso, spike_p = (max(pmf, key=lambda x: x[1]) if pmf else (None, 0.0))
    spike_prev = pmf_at(prev, spike_iso) if spike_iso else 0.0
    pp = (spike_p - spike_prev) * 100

    first_ch = int(cur["target"].split("ch ")[-1])
    return {
        "chapter": first_ch,
        "batch": cur.get("batch"),
        "design": _design(cur),
        "run_id": cur["run_id"],
        "prev_run_id": prev["run_id"],
        "trigger": cur.get("trigger", ""),
        "trigger_detail": cur.get("trigger_detail", ""),
        "median": cur["median"],
        "prev_median": prev["median"],
        "shift_days": shift,
        "spike_date": spike_iso,
        "spike_p": spike_p,
        "spike_prev_p": spike_prev,
        "spike_pp": pp,
        "i80": cur["intervals"]["80"],
        "prev_i80": prev["intervals"]["80"],
        "pmf": pmf,
        "prev_pmf": prev.get("posterior_pmf") or [],
        "evidence_asof": cur.get("evidence_asof", ""),
    }


def newsworthy(d):
    """Is there a story? Returns (bool, headline_kind)."""
    if not d:
        return False, None
    if abs(d["shift_days"]) >= MIN_DAYS:
        return True, "date"
    if abs(d["spike_pp"]) >= MIN_PP:
        return True, "probability"
    return False, None


def headline(d):
    """One line, the way a person would say it."""
    kind = newsworthy(d)[1]
    if kind == "date":
        n = abs(d["shift_days"])
        way = "earlier" if d["shift_days"] < 0 else "later"
        return "%d day%s %s" % (n, "" if n == 1 else "s", way)
    if kind == "probability":
        return "%+.1f points" % d["spike_pp"]
    return "no change"


def main():
    d = compute()
    if not d:
        _cur, _prev, reason = pick_pair()
        print("no comparable baseline: %s" % reason)
        return 1
    ok, kind = newsworthy(d)
    print("chapter %d   %s -> %s  (%+d days)"
          % (d["chapter"], d["prev_median"], d["median"], d["shift_days"]))
    print("P(%s)  %.1f%% -> %.1f%%  (%+.1f pp)"
          % (d["spike_date"], d["spike_prev_p"] * 100, d["spike_p"] * 100, d["spike_pp"]))
    print("model %s, batch %s   %s -> %s"
          % (d["design"], d["batch"], d["prev_run_id"], d["run_id"]))
    print("newsworthy: %s%s" % (ok, ("  (%s: %s)" % (kind, headline(d))) if ok else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
