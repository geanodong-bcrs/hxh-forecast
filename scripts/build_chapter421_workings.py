#!/usr/bin/env python3
"""Export auditable working tables for the chapter-421 forecast history.

The wide table is meant for reading: it records the parametric Level-1 inputs,
the predecessor forecast, and the chapter-421 result at each public-information
cutoff. The long table preserves the full output PMFs for checking the
convolution outside the site.
"""
import csv
import glob
import json
import os
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
D = lambda *p: os.path.join(HERE, "..", *p)
OUT = D("data", "working")
MODEL = "ordered_readiness_two_sided_mixture_v11"


def asof(snap):
    return snap.get("replay_asof") or snap.get("forecast_timestamp") or ""


def direct_target(snap, chapter):
    return ("publication of ch %d" % chapter) in (snap.get("target") or "")


def load_history():
    """One selected direct-two-gap snapshot per forecast date."""
    selected = {}
    for path in glob.glob(D("data", "forecasts", "*_posterior.json")):
        try:
            with open(path, encoding="utf-8") as fh:
                snap = json.load(fh)
        except (OSError, json.JSONDecodeError):
            continue
        if snap.get("level2_design") != MODEL:
            continue
        nb = snap.get("next_batch") or {}
        relevant = direct_target(snap, 421) or nb.get("first_chapter") == 421
        if not relevant:
            continue
        key = asof(snap)
        if key and (key not in selected or snap.get("run_id", "") > selected[key].get("run_id", "")):
            selected[key] = snap
    return [selected[k] for k in sorted(selected)]


def qfields(intervals, median):
    intervals = intervals or {}
    return {"p10": (intervals.get("80") or ["", ""])[0],
            "p25": (intervals.get("50") or ["", ""])[0],
            "p50": median or "",
            "p75": (intervals.get("50") or ["", ""])[1],
            "p90": (intervals.get("80") or ["", ""])[1]}


def build():
    os.makedirs(OUT, exist_ok=True)
    snaps = load_history()
    steps_path = os.path.join(OUT, "chapter421_forecast_steps.csv")
    pmf_path = os.path.join(OUT, "chapter421_forecast_pmf.csv")
    readme_path = os.path.join(OUT, "chapter421_forecast_workings.md")

    step_fields = [
        "as_of", "run_id", "source", "predecessor_batch", "predecessor_chapter",
        "predecessor_p10", "predecessor_p25", "predecessor_p50", "predecessor_p75", "predecessor_p90",
        "level1_family", "level1_mu", "level1_sigma", "analog_fade_floor",
        "chapter421_p10", "chapter421_p25", "chapter421_p50", "chapter421_p75", "chapter421_p90",
    ]
    pmf_fields = ["as_of", "run_id", "distribution", "publication_date", "probability"]
    with open(steps_path, "w", newline="", encoding="utf-8") as steps, \
         open(pmf_path, "w", newline="", encoding="utf-8") as pmf:
        sw = csv.DictWriter(steps, fieldnames=step_fields, lineterminator="\n")
        pw = csv.DictWriter(pmf, fieldnames=pmf_fields, lineterminator="\n")
        sw.writeheader()
        pw.writeheader()
        for snap in snaps:
            nb = snap.get("next_batch") or {}
            direct = direct_target(snap, 421)
            prior = snap.get("level1_prior") if direct else nb.get("level1_gap_prior")
            prior = prior or {}
            predecessor_q = qfields(snap.get("intervals"), snap.get("median"))
            chapter_q = qfields(snap.get("intervals"), snap.get("median")) if direct \
                else qfields(nb.get("intervals"), nb.get("median"))
            sw.writerow({
                "as_of": asof(snap), "run_id": snap.get("run_id", ""),
                "source": "direct next-batch forecast" if direct else "parametric gap convolution",
                "predecessor_batch": snap.get("batch", "") if not direct else "",
                "predecessor_chapter": (snap.get("target") or "").split("ch ")[-1] if not direct else "",
                **({"predecessor_" + k: v for k, v in predecessor_q.items()} if not direct else {}),
                "level1_family": prior.get("family", ""),
                "level1_mu": prior.get("mu", ""),
                "level1_sigma": prior.get("sigma", ""),
                "analog_fade_floor": snap.get("analog_fade_floor", ""),
                **{"chapter421_" + k: v for k, v in chapter_q.items()},
            })
            if not direct:
                for d, p in snap.get("posterior_pmf") or []:
                    pw.writerow({"as_of": asof(snap), "run_id": snap.get("run_id", ""),
                                 "distribution": "predecessor_batch_start", "publication_date": d,
                                 "probability": p})
                for d, p in nb.get("pmf") or []:
                    pw.writerow({"as_of": asof(snap), "run_id": snap.get("run_id", ""),
                                 "distribution": "chapter421_parametric_convolution", "publication_date": d,
                                 "probability": p})
            else:
                for d, p in snap.get("posterior_pmf") or []:
                    pw.writerow({"as_of": asof(snap), "run_id": snap.get("run_id", ""),
                                 "distribution": "chapter421_direct_next_batch", "publication_date": d,
                                 "probability": p})

    with open(readme_path, "w", encoding="utf-8") as fh:
        fh.write("# Chapter 421 forecast workings\n\n")
        fh.write("Generated by `scripts/build_chapter421_workings.py`. Do not edit by hand.\n\n")
        fh.write("- `chapter421_forecast_steps.csv`: one forecast cutoff per row. Level 1 records the shifted-lognormal parameters fitted leakage-free at that cutoff.\n")
        fh.write("- `chapter421_forecast_pmf.csv`: full probability mass functions. `chapter421_parametric_convolution` is the following-batch result; after batch 50 became direct, `chapter421_direct_next_batch` is its direct posterior.\n")
    return steps_path, pmf_path, readme_path, len(snaps)


if __name__ == "__main__":
    paths = build()
    print("working: %s (%d forecast dates)" % (os.path.relpath(paths[0], D()), paths[3]))
    print("working: %s" % os.path.relpath(paths[1], D()))
    print("working: %s" % os.path.relpath(paths[2], D()))
