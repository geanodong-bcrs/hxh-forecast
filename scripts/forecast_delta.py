#!/usr/bin/env python3
"""What changed between the last two forecasts, and is it worth saying out loud?

Feeds the reply card. Two questions a reader of Togashi's replies actually cares
about, in the order they care about them:

  1. did the expected date move, and which way
  2. did the chance of the nearest candidate issue change

A run that changes neither is not news. `newsworthy()` is what stops the bot
replying "the forecast is exactly the same" under a production post, which is
worse than saying nothing.
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
    """Every timestamped posterior snapshot, oldest first."""
    out = []
    for f in sorted(glob.glob(D("data", "forecasts", "*_posterior.json"))):
        if "T" not in os.path.basename(f).split("_")[0]:
            continue                      # pre-automation, date-only names
        with open(f, encoding="utf-8") as fh:
            out.append((f, json.load(fh)))
    return out


def pmf_at(snap, iso):
    for d, p in snap.get("posterior_pmf") or []:
        if d == iso:
            return p
    return 0.0


def compute(cur=None, prev=None):
    """Delta between two snapshots. Defaults to the newest pair."""
    snaps = posteriors()
    if len(snaps) < 2 and cur is None:
        return None
    if cur is None:
        (_, prev), (_, cur) = snaps[-2], snaps[-1]

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
        print("need at least two snapshots to compare")
        return 1
    ok, kind = newsworthy(d)
    print("chapter %d   %s -> %s  (%+d days)"
          % (d["chapter"], d["prev_median"], d["median"], d["shift_days"]))
    print("P(%s)  %.1f%% -> %.1f%%  (%+.1f pp)"
          % (d["spike_date"], d["spike_prev_p"] * 100, d["spike_p"] * 100, d["spike_pp"]))
    print("newsworthy: %s%s" % (ok, ("  (%s: %s)" % (kind, headline(d))) if ok else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
