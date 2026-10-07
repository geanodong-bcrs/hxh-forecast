#!/usr/bin/env python3
"""Rebuild chapter-level statistics from completed panel-annotation CSV files."""

from __future__ import annotations

import csv
import json
import re
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STORY_DIR = ROOT / "private" / "story"
DB_PATH = STORY_DIR / "story_annotations.sqlite"
OUTPUT_PATH = ROOT / "data" / "story" / "chapter_annotation_stats.csv"
FIELDS = (
    "chapter",
    "title",
    "printed_pages",
    "page_records",
    "total_panels",
    "floating_panels",
    "base_layout_panels",
    "panels_per_printed_page",
    "base_panels_per_printed_page",
    "text_panels",
    "silent_panels",
    "silent_panel_pct",
    "text_segments",
    "transcribed_english_words",
    "unique_characters_shown",
    "unique_characters_mentioned",
    "source_csv",
)


def split_ids(value: str) -> list[str]:
    return [item.strip() for item in re.split(r"[;,|]", value or "") if item.strip()]


def word_count(text: str) -> int:
    return len(re.findall(r"\b[\w’'-]+\b", text or ""))


def main() -> None:
    db = sqlite3.connect(DB_PATH)
    titles = dict(db.execute("SELECT chapter,title FROM chapters"))
    db.close()
    output_rows = []
    for path in sorted(STORY_DIR.glob("chapter_*_panel_transcription.csv")):
        with path.open(newline="", encoding="utf-8-sig") as handle:
            rows = list(csv.DictReader(handle))
        if not rows or any(row["review_status"] != "reviewed" for row in rows):
            continue
        chapter = int(rows[0]["chapter"])
        printed_pages = max(int(row["page_end"]) for row in rows)
        page_records = len({(row["page_start"], row["page_end"]) for row in rows})
        floating_panels = sum(
            "floating" in {part.strip() for part in re.split(r"[;,|]", row["panel_types"])}
            for row in rows
        )
        segments = [
            segment
            for row in rows
            for segment in json.loads(row["text_segments_json"] or "[]")
        ]
        text_panels = sum(bool(json.loads(row["text_segments_json"] or "[]")) for row in rows)
        silent_panels = len(rows) - text_panels
        shown = {item for row in rows for item in split_ids(row["characters_on_panel"])}
        mentioned = {item for row in rows for item in split_ids(row["characters_mentioned"])}
        base_panels = len(rows) - floating_panels
        output_rows.append(
            {
                "chapter": chapter,
                "title": titles.get(chapter, ""),
                "printed_pages": printed_pages,
                "page_records": page_records,
                "total_panels": len(rows),
                "floating_panels": floating_panels,
                "base_layout_panels": base_panels,
                "panels_per_printed_page": f"{len(rows) / printed_pages:.4f}",
                "base_panels_per_printed_page": f"{base_panels / printed_pages:.4f}",
                "text_panels": text_panels,
                "silent_panels": silent_panels,
                "silent_panel_pct": f"{silent_panels / len(rows):.4f}",
                "text_segments": len(segments),
                "transcribed_english_words": sum(word_count(s.get("text", "")) for s in segments),
                "unique_characters_shown": len(shown),
                "unique_characters_mentioned": len(mentioned),
                "source_csv": str(path.relative_to(ROOT)),
            }
        )

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(sorted(output_rows, key=lambda row: row["chapter"]))


if __name__ == "__main__":
    main()
