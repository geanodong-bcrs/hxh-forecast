#!/usr/bin/env python3
"""Append-only forecast snapshots (Agents.md §16, §28).

§16 says historical forecast snapshots must never be overwritten. Until now the
filename carried only a date, so two runs on the same day silently replaced each
other — survivable while a human ran the scripts once a day, fatal once a poller
runs eight times. Snapshots are therefore keyed by a UTC *timestamp*, and
`write` refuses outright if the path already exists rather than trusting the
convention to hold.

One run of the pipeline emits several artifacts (level 1 prior, level 2 analog,
posterior). They share a `run_id` so they can be joined back together, and the
orchestrator passes it in through the environment; a script run by hand gets a
fresh one and `trigger=manual`, so every script stays independently runnable.

§28 wants a model result reproducible from a specific data version. Every
snapshot therefore carries the sha256 of each input CSV it was built from.
"""
import csv
import hashlib
import json
import os
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
D = lambda *p: os.path.join(HERE, "..", *p)
SNAP = D("data", "forecasts")
INDEX = os.path.join(SNAP, "index.csv")

# The inputs a forecast is a function of. Digested into every snapshot so a
# result can be tied to the exact data version that produced it.
INPUTS = [
    ("chapters", "data/processed/chapters.csv"),
    ("wsj_issues", "data/processed/wsj_issues.csv"),
    ("production_events", "data/processed/production_events.csv"),
    ("production_intervals", "data/processed/production_intervals.csv"),
    ("tweets", "data/processed/tweets.csv"),
    ("image_annotations_confirmed", "data/annotations/image_annotations.confirmed.csv"),
    ("announcements", "data/annotations/announcements.csv"),
]

INDEX_COLS = ["run_id", "written_utc", "trigger", "trigger_detail", "kind", "batch",
              "annotation_status", "evidence_asof", "median",
              "i50_lo", "i50_hi", "i80_lo", "i80_hi", "i90_lo", "i90_hi", "path"]


def _now():
    return datetime.now(timezone.utc)


def run_id():
    """Stable within one pipeline run; fresh for a hand-run script."""
    rid = os.environ.get("TOGASHI_RUN_ID")
    return rid if rid else _now().strftime("%Y%m%dT%H%M%SZ")


def trigger():
    return os.environ.get("TOGASHI_TRIGGER", "manual")


def trigger_detail():
    return os.environ.get("TOGASHI_TRIGGER_DETAIL", "")


def sha256(path):
    if not os.path.exists(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def input_digests():
    return {name: sha256(D(*rel.split("/"))) for name, rel in INPUTS}


def evidence_asof():
    """Newest post creation time in the corpus — the §19 'known at' bound.

    Deliberately `created_at`, not ingestion time: that is when the evidence
    became public, which is the timestamp a backtest is allowed to condition on.
    """
    path = D("data", "processed", "tweets.csv")
    if not os.path.exists(path):
        return ""
    newest = ""
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            t = r.get("created_at_utc") or r.get("id_created_at_utc") or ""
            if t > newest:
                newest = t
    return newest


def annotation_status():
    """`provisional` while any image reading in play is still unconfirmed.

    An auto-transcribed image is a model's interpretation of a photograph
    (§8), and a snapshot built on one is not the same object as a snapshot
    built on human-confirmed readings. The distinction is recorded rather
    than smoothed over, so the revised snapshot can be compared against the
    provisional one it replaced.
    """
    path = D("data", "annotations", "image_annotations.confirmed.csv")
    if not os.path.exists(path):
        return "unknown"
    pending = 0
    total = 0
    with open(path, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            total += 1
            if (r.get("status") or "") != "confirmed":
                pending += 1
    if not total:
        return "unknown"
    return "confirmed" if pending == 0 else "provisional:%d_unconfirmed" % pending


def write(kind, batch, payload, summary=None, rid=None, extra=None):
    """Write one snapshot. Never overwrites; appends a row to index.csv.

    kind     'prior_level1' | 'level2_analog' | 'posterior'
    batch    the batch being forecast, from the data — never hardcoded
    summary  optional dict of median / i50 / i80 / i90 for the index
    rid      override the run_id. Only the replay harness passes this, so that a
             reconstructed forecast is keyed by the date it is a forecast *for*
             rather than by the wall clock at which it was computed.
    extra    extra provenance merged into the snapshot's meta block (not the
             index). `provenance: replay` rides here.
    """
    rid = rid or run_id()
    os.makedirs(SNAP, exist_ok=True)
    path = os.path.join(SNAP, "%s_batch%d_%s.json" % (rid, batch, kind))

    if os.path.exists(path):
        raise SystemExit(
            "refusing to overwrite an existing snapshot (Agents.md §16):\n  %s\n"
            "Snapshots are append-only. If this is a re-run, let it take a new "
            "run_id rather than replacing the record of what was forecast."
            % os.path.relpath(path, D()))

    meta = {
        "run_id": rid,
        "written_utc": _now().isoformat(),
        "trigger": trigger(),
        "trigger_detail": trigger_detail(),
        "annotation_status": annotation_status(),
        "evidence_asof": evidence_asof(),
        "batch": batch,
        "input_sha256": input_digests(),
    }
    meta.update(extra or {})
    # payload wins on key collisions: the model script is the authority on its
    # own fields, this only supplies provenance.
    out = dict(meta)
    out.update(payload)

    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, ensure_ascii=False)

    s = summary or {}
    row = {
        "run_id": rid, "written_utc": meta["written_utc"], "trigger": meta["trigger"],
        "trigger_detail": meta["trigger_detail"], "kind": kind, "batch": batch,
        "annotation_status": meta["annotation_status"],
        "evidence_asof": meta["evidence_asof"],
        "median": s.get("median", ""),
        "i50_lo": s.get("i50", ["", ""])[0], "i50_hi": s.get("i50", ["", ""])[1],
        "i80_lo": s.get("i80", ["", ""])[0], "i80_hi": s.get("i80", ["", ""])[1],
        "i90_lo": s.get("i90", ["", ""])[0], "i90_hi": s.get("i90", ["", ""])[1],
        "path": os.path.relpath(path, D()),
    }
    new = not os.path.exists(INDEX)
    with open(INDEX, "a", newline="", encoding="utf-8") as fh:
        # The historical index uses CRLF, but emitted rows should not acquire a
        # trailing carriage return in a Unix worktree.
        w = csv.DictWriter(fh, fieldnames=INDEX_COLS, lineterminator="\n")
        if new:
            w.writeheader()
        w.writerow(row)

    return path
