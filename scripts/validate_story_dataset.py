#!/usr/bin/env python3
"""Validate the story-prediction CSVs and their cross-table references."""

from __future__ import annotations

import csv
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STORY = ROOT / "data" / "story"

VOCAB = {
    "chapter_story_annotations.csv": {
        "narrative_function": {
            "setup", "expansion", "complication", "preparation",
            "confrontation", "convergence", "revelation", "resolution",
            "aftermath", "transition",
        },
        "review_status": {"ai_proposed", "human_reviewed", "disputed"},
    },
    "story_threads.csv": {
        "thread_type": {
            "objective", "conflict", "mystery", "threat", "relationship",
            "promised_event", "journey", "institutional_process",
        },
        "current_status": {
            "open", "active", "blocked", "converging", "transformed",
            "resolved", "abandoned", "uncertain",
        },
        "centrality": {"core", "major", "supporting", "minor", "uncertain"},
        "review_status": {"ai_proposed", "human_reviewed", "disputed"},
    },
    "chapter_thread_events.csv": {
        "event_type": {
            "introduced", "mentioned", "advanced", "complicated",
            "connected", "converged", "escalated", "partially_resolved",
            "resolved", "deferred", "transformed",
        },
        "importance": {"major", "moderate", "minor"},
        "confidence": {"high", "medium", "low"},
        "review_status": {"ai_proposed", "human_reviewed", "disputed"},
    },
    "story_predictions.csv": {
        "status": {"open", "resolved", "withdrawn", "superseded"},
    },
}


def read_csv(name: str) -> list[dict[str, str]]:
    with (STORY / name).open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> int:
    errors: list[str] = []
    tables = {name: read_csv(name) for name in VOCAB}

    chapter_rows = read_csv("chapter_story_annotations.csv")
    thread_rows = read_csv("story_threads.csv")
    event_rows = read_csv("chapter_thread_events.csv")
    prediction_rows = read_csv("story_predictions.csv")

    canonical_chapters = {
        row["chapter"]
        for row in read_csv_from_path(ROOT / "data" / "processed" / "chapters.csv")
    }
    thread_ids = {row["thread_id"] for row in thread_rows if row["thread_id"]}

    for name, fields in VOCAB.items():
        for line, row in enumerate(tables[name], start=2):
            for field, allowed in fields.items():
                value = row.get(field, "")
                if value and value not in allowed:
                    errors.append(f"{name}:{line}: invalid {field}={value!r}")

    check_unique(chapter_rows, "chapter", "chapter_story_annotations.csv", errors)
    check_unique(thread_rows, "thread_id", "story_threads.csv", errors)
    check_unique(event_rows, "event_id", "chapter_thread_events.csv", errors)
    check_unique(prediction_rows, "prediction_id", "story_predictions.csv", errors)

    for name, rows, field in (
        ("chapter_story_annotations.csv", chapter_rows, "chapter"),
        ("story_threads.csv", thread_rows, "introduced_chapter"),
        ("chapter_thread_events.csv", event_rows, "chapter"),
        ("story_predictions.csv", prediction_rows, "forecast_after_chapter"),
    ):
        for line, row in enumerate(rows, start=2):
            value = row.get(field, "")
            if value and value not in canonical_chapters:
                errors.append(f"{name}:{line}: unknown {field}={value!r}")

    for line, row in enumerate(event_rows, start=2):
        if row["thread_id"] and row["thread_id"] not in thread_ids:
            errors.append(
                f"chapter_thread_events.csv:{line}: unknown thread_id={row['thread_id']!r}"
            )

    for line, row in enumerate(prediction_rows, start=2):
        value = row.get("probability", "")
        if not value:
            continue
        try:
            probability = float(value)
        except ValueError:
            errors.append(f"story_predictions.csv:{line}: invalid probability={value!r}")
        else:
            if not 0 <= probability <= 1:
                errors.append(
                    f"story_predictions.csv:{line}: probability outside [0, 1]: {value!r}"
                )

    if errors:
        print("Story dataset validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    row_count = sum(len(rows) for rows in tables.values())
    print(f"Story dataset valid ({row_count} data rows).")
    return 0


def read_csv_from_path(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def check_unique(
    rows: list[dict[str, str]], field: str, name: str, errors: list[str]
) -> None:
    seen: set[str] = set()
    for line, row in enumerate(rows, start=2):
        value = row.get(field, "")
        if not value:
            errors.append(f"{name}:{line}: missing {field}")
        elif value in seen:
            errors.append(f"{name}:{line}: duplicate {field}={value!r}")
        seen.add(value)


if __name__ == "__main__":
    sys.exit(main())
