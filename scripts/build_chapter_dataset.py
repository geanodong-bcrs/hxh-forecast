#!/usr/bin/env python3
"""raw/hunterpedia -> processed/chapters.csv  (Agents.md sec. 5)

Reads the immutable raw snapshot and emits the canonical historical publication
dataset. Never writes to data/raw/.

Two date-like things are kept strictly separate (sec. 5 "Do not conflate"):
  publication_date_jp  - on-sale date of the Japanese WSJ issue carrying the chapter
  volume_release_date  - tankobon date, a different event entirely
The English/Viz (NA) simulpub date is parsed where present and kept in its own
column; it is NOT the modelling target.
"""
import csv
import glob
import json
import os
import re
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "data", "raw", "hunterpedia")
OUT = os.path.join(HERE, "..", "data", "processed")
CORRECTIONS = os.path.join(HERE, "..", "data", "corrections", "chapter_corrections.csv")

# A new run starts when this many WSJ issues elapse without an HxH chapter.
# In the 2007+ regime any cutoff from ~3 to ~9 gives the same segmentation;
# in the 1998-2006 weekly era no cutoff is meaningful. See batch_segmentation.md.
BATCH_GAP_ISSUES = 4

# Runs longer than this are split into SPLIT_UNIT-chapter batches: chapters
# 291-310 and 311-340 are back-to-back 10-chapter batches with no waiting time
# between them, not single oversized batches (Agents.md sec. 3).
SPLIT_RUN_ABOVE = 15
SPLIT_UNIT = 10

# The prior is fitted on the 2007+ burst regime only. Earlier chapters are kept
# in the dataset for description and trend work, flagged modeling_era = 0.
MODELING_ERA_FIRST_CHAPTER = 261

MONTHS = {m: i + 1 for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July",
     "August", "September", "October", "November", "December"])}

# "June 29<sup>th</sup>, 2026" -> date
DATE_RE = re.compile(r"([A-Z][a-z]+)\s+(\d{1,2})(?:<sup>[a-z]{2}</sup>)?(?:st|nd|rd|th)?,\s*(\d{4})")
# Japanese edition: macron, and never the "(NA)" English edition
JP_ISSUE_RE = re.compile(r"Weekly Sh[ōo]nen Jump\s*#(\d+),\s*No\.\s*([\d]+(?:-\d+)?)")
NA_ISSUE_RE = re.compile(r"Weekly Shonen Jump \(NA\)\s*#(\d+),\s*No\.\s*([\d]+(?:-\d+)?)")
FIELD_RE = r"\|\s*%s\s*=\s*([^\n|]*)"


def field(wikitext, name):
    m = re.search(FIELD_RE % name, wikitext)
    return m.group(1).strip() if m else ""


def parse_date(s):
    m = DATE_RE.search(s)
    if not m:
        return None
    return datetime(int(m.group(3)), MONTHS[m.group(1)], int(m.group(2))).date()


def issue_year(pub_date, issue_no_first):
    """WSJ issues dated early in year N go on sale in late December of N-1."""
    if pub_date.month == 12 and issue_no_first <= 8:
        return pub_date.year + 1
    return pub_date.year


def parse_page(page):
    w = page["wikitext"]
    ch = int(re.search(r"\|\s*Chapter\s*=\s*(\d+)", w).group(1))
    rel = field(w, "Release Date")
    # The release-date field is "<jp date> (<jp issue>[; <na issue>]) <br /> <tankobon or na date>"
    segments = re.split(r"<br\s*/?>", rel)
    head = segments[0]

    pub = parse_date(head)
    jp = JP_ISSUE_RE.search(rel)
    na = NA_ISSUE_RE.search(rel)

    # tankobon date, when the field carries one, lives after the <br />
    vol_date = None
    for seg in segments[1:]:
        if "tank" in seg.lower():
            vol_date = parse_date(seg)

    # NA simulpub date: present only for the Viz-era chapters, same head date
    na_date = None
    if na:
        na_date = pub  # simulpub - same calendar day as the JP on-sale date

    label = jp.group(2) if jp else ""
    first_no = int(label.split("-")[0]) if label else None
    iy = issue_year(pub, first_no) if (pub and first_no) else None

    return {
        "chapter": ch,
        "title_en": field(w, "Name"),
        "arc": field(w, "Arc"),
        "page_length": field(w, "Page length"),
        "publication_date_jp": pub.isoformat() if pub else "",
        "wsj_issue_cumulative": int(jp.group(1)) if jp else "",
        "wsj_issue_year": iy or "",
        "wsj_issue_no": label,
        "is_combined_issue": int("-" in label) if label else "",
        "na_issue_cumulative": int(na.group(1)) if na else "",
        "na_issue_no": na.group(2) if na else "",
        "na_release_date": na_date.isoformat() if na_date else "",
        "volume_release_date": vol_date.isoformat() if vol_date else "",
        "release_date_raw": rel,
        "source_url": "https://hunterxhunter.fandom.com/wiki/" + page["title"].replace(" ", "_"),
        "source_type": "community_wiki_secondary",
        "source_revid": page["revid"],
        "source_rev_timestamp": page["rev_timestamp"],
    }


def apply_corrections(rows):
    """Overlay verified fixes on the parsed raw values, keeping both visible.

    Raw stays raw (sec. 27); a correction is a separate, sourced record, never an
    in-place edit of the snapshot. Each corrected row keeps the original value in
    <field>_raw_value so nothing is lost.
    """
    for r in rows:
        r["date_provenance"] = "hunterpedia"
        r["correction_note"] = ""
    if not os.path.exists(CORRECTIONS):
        return rows, 0
    by_ch = {r["chapter"]: r for r in rows}
    n = 0
    with open(CORRECTIONS) as fh:
        for c in csv.DictReader(fh):
            ch = int(c["chapter"])
            row = by_ch.get(ch)
            if row is None:
                print("  WARNING: correction for absent chapter %d" % ch)
                continue
            field_name = c["field"]
            if row.get(field_name) != c["raw_value"]:
                print("  WARNING: ch%d %s is %r, correction expected %r - SKIPPED"
                      % (ch, field_name, row.get(field_name), c["raw_value"]))
                continue
            row[field_name + "_raw_value"] = c["raw_value"]
            row[field_name] = c["corrected_value"]
            row["date_provenance"] = "corrected"
            row["correction_note"] = c["source_url"]
            n += 1
    return rows, n


def add_derived(rows):
    """Intervals + batch structure (sec. 5). rows must be chapter-sorted."""
    run_id = 0
    for i, r in enumerate(rows):
        prev = rows[i - 1] if i else None
        d = datetime.fromisoformat(r["publication_date_jp"]).date() if r["publication_date_jp"] else None

        if prev and prev["publication_date_jp"] and d:
            pd = datetime.fromisoformat(prev["publication_date_jp"]).date()
            r["prev_chapter_pub_date"] = pd.isoformat()
            r["interval_days"] = (d - pd).days
        else:
            r["prev_chapter_pub_date"] = ""
            r["interval_days"] = ""

        # issue-count gap is the honest unit: calendar days conflate combined
        # issues and New Year breaks with actual publication skips
        if prev and prev["wsj_issue_cumulative"] and r["wsj_issue_cumulative"]:
            r["interval_issues"] = r["wsj_issue_cumulative"] - prev["wsj_issue_cumulative"]
        else:
            r["interval_issues"] = ""

        # a "run" is an uninterrupted stretch of issues carrying a chapter
        is_run_start = (i == 0) or (r["interval_issues"] != ""
                                    and r["interval_issues"] >= BATCH_GAP_ISSUES)
        if is_run_start:
            run_id += 1
        r["run_id"] = run_id
        # skipped issues immediately before this chapter (0 inside a clean run)
        r["issues_skipped_before"] = (r["interval_issues"] - 1) if r["interval_issues"] != "" else ""
        r["modeling_era"] = int(r["chapter"] >= MODELING_ERA_FIRST_CHAPTER)

    assign_batches(rows)

    # batch-level rollups
    sizes = {}
    starts = {}
    for r in rows:
        sizes[r["batch_id"]] = sizes.get(r["batch_id"], 0) + 1
        if r["is_batch_start"]:
            starts[r["batch_id"]] = datetime.fromisoformat(r["publication_date_jp"]).date()
    for r in rows:
        b = r["batch_id"]
        r["batch_size"] = sizes[b]
        if b > 1 and starts.get(b) and starts.get(b - 1):
            r["prev_batch_start_date"] = starts[b - 1].isoformat()
            r["interval_from_prev_batch_days"] = (starts[b] - starts[b - 1]).days
        else:
            r["prev_batch_start_date"] = ""
            r["interval_from_prev_batch_days"] = ""
    return rows


def assign_batches(rows):
    """Split over-long runs into SPLIT_UNIT-chapter batches (Agents.md sec. 3).

    Chapters 291-310 (20) and 311-340 (30) are back-to-back 10-chapter batches
    published with no waiting time, not single oversized batches. Splitting them
    puts genuine ZEROES into the batch-to-batch gap distribution, which is the
    point: the gap distribution is bimodal - the next batch either follows
    immediately or after a long hiatus.
    """
    batch_id = 0
    by_run = {}
    for r in rows:
        by_run.setdefault(r["run_id"], []).append(r)

    for run in sorted(by_run):
        members = by_run[run]
        if len(members) > SPLIT_RUN_ABOVE:
            chunks = [members[i:i + SPLIT_UNIT] for i in range(0, len(members), SPLIT_UNIT)]
        else:
            chunks = [members]
        for chunk in chunks:
            batch_id += 1
            for pos, r in enumerate(chunk, start=1):
                r["batch_id"] = batch_id
                r["position_in_batch"] = pos
                r["is_batch_start"] = int(pos == 1)
        # gap before a batch, in issues: 0 for a continuation of the same run
        for ci, chunk in enumerate(chunks):
            head = chunk[0]
            head["issues_gap_before_batch"] = 0 if ci else head["issues_skipped_before"]
    for r in rows:
        r.setdefault("issues_gap_before_batch", "")


COLUMNS = ["chapter", "title_en", "arc", "page_length",
           "publication_date_jp", "wsj_issue_cumulative", "wsj_issue_year",
           "wsj_issue_no", "is_combined_issue",
           "prev_chapter_pub_date", "interval_days", "interval_issues",
           "issues_skipped_before", "modeling_era", "run_id",
           "batch_id", "position_in_batch", "is_batch_start", "batch_size",
           "issues_gap_before_batch",
           "prev_batch_start_date", "interval_from_prev_batch_days",
           "na_issue_cumulative", "na_issue_no", "na_release_date",
           "volume_release_date", "release_date_raw",
           "date_provenance", "publication_date_jp_raw_value", "correction_note",
           "source_url", "source_type", "source_revid", "source_rev_timestamp"]


def main():
    snap = sorted(glob.glob(os.path.join(RAW, "hunterpedia_chapters_*.json")))[-1]
    raw = json.load(open(snap))
    rows = sorted((parse_page(p) for p in raw["pages"].values()), key=lambda r: r["chapter"])
    rows, n_corr = apply_corrections(rows)
    rows = add_derived(rows)

    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "chapters.csv")
    with open(path, "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore", restval="")
        wr.writeheader()
        wr.writerows(rows)

    meta = {
        "built_utc": datetime.utcnow().isoformat() + "Z",
        "raw_snapshot": os.path.basename(snap),
        "raw_retrieved_utc": raw["retrieved_utc"],
        "source": raw["source"],
        "source_type": raw["source_type"],
        "row_count": len(rows),
        "chapter_range": [rows[0]["chapter"], rows[-1]["chapter"]],
        "batch_gap_issues_threshold": BATCH_GAP_ISSUES,
        "split_run_above": SPLIT_RUN_ABOVE,
        "split_unit": SPLIT_UNIT,
        "modeling_era_first_chapter": MODELING_ERA_FIRST_CHAPTER,
        "run_count": rows[-1]["run_id"],
        "batch_count": rows[-1]["batch_id"],
        "batch_count_modeling_era": len({r["batch_id"] for r in rows if r["modeling_era"]}),
        "corrections_applied": n_corr,
        "corrections_file": os.path.basename(CORRECTIONS),
        "verification_status": "CROSS-CHECKED against jajanken.net (independent JP magazine "
                               "index); see data/processed/validation_report.csv",
    }
    with open(os.path.join(OUT, "chapters.meta.json"), "w") as fh:
        json.dump(meta, fh, indent=2)
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
