#!/usr/bin/env python3
"""Build a source-attributed character seed from cached Hunterpedia chapters."""

from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw" / "hunterpedia"
CHARACTERS_CSV = ROOT / "data" / "story" / "characters.csv"
APPEARANCES_CSV = ROOT / "data" / "story" / "chapter_character_appearances.csv"


def latest_snapshot() -> Path:
    paths = sorted(RAW_DIR.glob("hunterpedia_chapters_*.json"))
    if not paths:
        raise FileNotFoundError(f"No Hunterpedia chapter snapshot in {RAW_DIR}")
    return paths[-1]


def character_id(title: str) -> str:
    normalized = unicodedata.normalize("NFKD", title)
    ascii_title = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_title).strip("_")
    if slug:
        return f"char_{slug}"
    return "char_" + title.encode("utf-8").hex()[:32]


def strip_templates(text: str) -> str:
    text = re.sub(r"\{\{\s*Sm\s*\|\s*([^{}]+?)\s*\}\}", r"\1", text, flags=re.IGNORECASE)
    for code, label in (("M", "Mentioned"), ("I", "Image"), ("D", "Debut"), ("V", "Voice only")):
        text = re.sub(r"\{\{\s*" + code + r"\s*\}\}", label, text, flags=re.IGNORECASE)
    previous = None
    while text != previous:
        previous = text
        text = re.sub(r"\{\{[^{}]*\}\}", "", text)
    return re.sub(r"\s+", " ", text).strip(" (){}")


def appearance_section(wikitext: str) -> str:
    match = re.search(
        r"^==\s*Characters in Order of Appearance\s*==\s*(.*?)(?=^==[^=]|\Z)",
        wikitext,
        flags=re.MULTILINE | re.DOTALL | re.IGNORECASE,
    )
    return match.group(1) if match else ""


def parse_chapter(chapter: int, wikitext: str) -> list[dict]:
    records = []
    order = 0
    for line in appearance_section(wikitext).splitlines():
        if not re.match(r"^\s*\*", line):
            continue
        link = re.search(r"\[\[([^\]|#]+)(?:#[^\]|]+)?(?:\|([^\]]+))?\]\]", line)
        if not link:
            continue
        target = link.group(1).strip()
        label = (link.group(2) or target).strip()
        if target.lower().startswith(("file:", "category:", "hunter association#")):
            continue
        order += 1
        raw_remainder = line[link.end():]
        remainder = strip_templates(raw_remainder)
        lowered = raw_remainder.lower()
        appearance_type = "appears"
        for marker, value in (
            ("mentioned", "mentioned"), ("flashback", "flashback"),
            ("image", "image"), ("photo", "image"), ("casket", "remains"),
            ("corpse", "remains"), ("debut", "debut"), ("{{m}}", "mentioned"),
            ("{{i}}", "image"), ("{{d}}", "debut"), ("{{v}}", "voice_only"),
        ):
            if marker in lowered:
                appearance_type = value
                break
        records.append({
            "chapter": chapter,
            "appearance_order": order,
            "character_id": character_id(target),
            "display_name": label,
            "hunterpedia_title": target,
            "appearance_type": appearance_type,
            "source_note": remainder,
        })
    return records


def build(snapshot: Path) -> tuple[int, int]:
    payload = json.loads(snapshot.read_text(encoding="utf-8"))
    retrieved = payload.get("retrieved_utc", "")
    appearances = []
    for page_name, page in payload["pages"].items():
        match = re.fullmatch(r"Chapter (\d+)", page_name)
        if match:
            appearances.extend(parse_chapter(int(match.group(1)), page.get("wikitext", "")))

    by_character = defaultdict(list)
    for row in appearances:
        by_character[row["character_id"]].append(row)

    characters = []
    for char_id, rows in by_character.items():
        first = min(rows, key=lambda row: (row["chapter"], row["appearance_order"]))
        characters.append({
            "character_id": char_id,
            "display_name": first["display_name"],
            "hunterpedia_title": first["hunterpedia_title"],
            "identity_status": "community_wiki_seed",
            "first_listed_chapter": min(row["chapter"] for row in rows),
            "source_type": payload.get("source_type", "community_wiki_secondary"),
            "source_url": "https://hunterxhunter.fandom.com/wiki/" + first["hunterpedia_title"].replace(" ", "_"),
            "retrieved_utc": retrieved,
            "notes": "Prototype seed; verify against the manga or an official source before treating as canon.",
        })

    CHARACTERS_CSV.parent.mkdir(parents=True, exist_ok=True)
    with CHARACTERS_CSV.open("w", newline="", encoding="utf-8") as handle:
        fields = list(characters[0])
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(sorted(characters, key=lambda row: (row["first_listed_chapter"], row["display_name"])))
    with APPEARANCES_CSV.open("w", newline="", encoding="utf-8") as handle:
        fields = ["chapter", "appearance_order", "character_id", "appearance_type", "source_note"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(({field: row[field] for field in fields} for row in appearances))
    return len(characters), len(appearances)


def main() -> int:
    snapshot = latest_snapshot()
    characters, appearances = build(snapshot)
    print(f"Built {characters} characters and {appearances} chapter appearances from {snapshot.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
