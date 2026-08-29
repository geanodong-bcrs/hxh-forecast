#!/usr/bin/env python3
"""raw/jajanken -> processed/wsj_issues.csv  (Agents.md sec. 4)

The publication calendar the model is allowed to predict into. Every WSJ issue
1997-2026 in sequence, with combined issues collapsed to the single slot they
actually occupy, so "next eligible publication week" is a real lookup rather
than an assumption that every calendar week is available.

Date semantics, which the two sources disagree about and which sec. 5 forbids
conflating:
  cover_date    - the nominal date printed on the issue (jajanken's URL slug)
  on_sale_date  - the day it actually reached shops; what a forecast resolves on
On-sale is ~14 days before cover date, but that offset breaks around New Year,
so on-sale is ANCHORED to observed Hunterpedia dates wherever we have one and
only inferred elsewhere. The distinction is carried in on_sale_provenance.
"""
import csv
import glob
import html
import os
import re
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "data", "raw", "jajanken")
PROC = os.path.join(HERE, "..", "data", "processed")

NOMINAL_OFFSET_DAYS = 14
LINK_RE = re.compile(r'href="/issues/(\d{4})-(\d{2})-(\d{2})/"[^>]*>\s*([^<]+?)\s*</a>')


def parse_year(path, year):
    txt = open(path, encoding="utf-8", errors="replace").read()
    out = []
    seen = set()
    for y, m, d, label in LINK_RE.findall(txt):
        label = html.unescape(label).strip()
        if not label.endswith("号"):
            continue
        cover = datetime(int(y), int(m), int(d)).date()
        nums = [int(n) for n in re.findall(r"\d+", label.replace("号", ""))]
        if not nums:
            continue
        key = (cover, tuple(nums))
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "issue_year": year,
            "issue_label": label,
            "issue_no_first": nums[0],
            "issue_no_last": nums[-1],
            "is_combined": int(len(nums) > 1),
            "cover_date": cover,
        })
    out.sort(key=lambda r: (r["issue_no_first"], r["cover_date"]))
    return out


def load_anchors():
    """observed on-sale dates, keyed by (issue_year, issue_no_first)"""
    anchors = {}
    path = os.path.join(PROC, "chapters.csv")
    with open(path) as fh:
        for r in csv.DictReader(fh):
            if not r["publication_date_jp"] or not r["wsj_issue_year"]:
                continue
            key = (int(r["wsj_issue_year"]), int(r["wsj_issue_no"].split("-")[0]))
            anchors.setdefault(key, []).append(
                (datetime.fromisoformat(r["publication_date_jp"]).date(), int(r["chapter"]),
                 int(r["wsj_issue_cumulative"])))
    return anchors


def main():
    rows = []
    for path in sorted(glob.glob(os.path.join(RAW, "years_*.html"))):
        year = int(re.search(r"years_(\d{4})", path).group(1))
        rows.extend(parse_year(path, year))
    rows.sort(key=lambda r: (r["issue_year"], r["issue_no_first"]))

    anchors = load_anchors()
    for i, r in enumerate(rows):
        r["seq"] = i  # position in the global issue sequence
        key = (r["issue_year"], r["issue_no_first"])
        if key in anchors:
            obs, ch, cum = anchors[key][0]
            r["on_sale_date"] = obs
            r["on_sale_provenance"] = "observed_hunterpedia"
            r["hxh_chapter"] = ch
            r["hxh_issue_cumulative"] = cum
        else:
            r["on_sale_date"] = r["cover_date"] - timedelta(days=NOMINAL_OFFSET_DAYS)
            r["on_sale_provenance"] = "inferred_cover_minus_14d"
            r["hxh_chapter"] = ""
            r["hxh_issue_cumulative"] = ""

    # gap to the next issue, in days - this is what makes a "week" eligible or not
    for i, r in enumerate(rows):
        nxt = rows[i + 1] if i + 1 < len(rows) else None
        r["days_to_next_issue"] = (nxt["on_sale_date"] - r["on_sale_date"]).days if nxt else ""

    os.makedirs(PROC, exist_ok=True)
    cols = ["seq", "issue_year", "issue_label", "issue_no_first", "issue_no_last",
            "is_combined", "cover_date", "on_sale_date", "on_sale_provenance",
            "days_to_next_issue", "hxh_chapter", "hxh_issue_cumulative"]
    with open(os.path.join(PROC, "wsj_issues.csv"), "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=cols)
        wr.writeheader()
        for r in rows:
            wr.writerow({c: r[c] for c in cols})
    print("wrote wsj_issues.csv: %d issues, %s..%s" % (
        len(rows), rows[0]["issue_year"], rows[-1]["issue_year"]))
    obs = sum(1 for r in rows if r["on_sale_provenance"] == "observed_hunterpedia")
    print("  on-sale observed: %d   inferred: %d" % (obs, len(rows) - obs))
    print("  combined issues:  %d" % sum(r["is_combined"] for r in rows))


if __name__ == "__main__":
    main()
