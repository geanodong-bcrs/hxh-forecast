#!/usr/bin/env python3
"""Add canonical chapter numbers and arc labels to the story annotation table."""

from __future__ import annotations

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CANONICAL_PATH = ROOT / "data" / "processed" / "chapters.csv"
STORY_PATH = ROOT / "data" / "story" / "chapter_story_annotations.csv"
FIELDS = [
    "chapter",
    "arc",
    "short_summary",
    "narrative_function",
    "phase_assessment",
    "major_state_change",
    "notes",
    "annotator",
    "review_status",
    "reviewed_at",
]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    canonical = read_rows(CANONICAL_PATH)
    existing = {
        row["chapter"]: {field: row.get(field, "") for field in FIELDS}
        for row in read_rows(STORY_PATH)
    }

    for chapter in canonical:
        number = chapter["chapter"]
        row = existing.setdefault(number, {field: "" for field in FIELDS})
        row["chapter"] = number
        row["arc"] = chapter["arc"]

    def chapter_sort(item: dict[str, str]) -> tuple[int, str]:
        value = item["chapter"]
        return (int(value), value) if value.isdigit() else (10**9, value)

    with STORY_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(sorted(existing.values(), key=chapter_sort))

    print(f"Synced {len(canonical)} canonical chapters into {STORY_PATH.relative_to(ROOT)}.")


if __name__ == "__main__":
    main()
