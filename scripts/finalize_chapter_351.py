#!/usr/bin/env python3
"""Normalize and finalize the reviewed Chapter 351 annotations."""

import importlib.util
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "private/story/story_annotations.sqlite"
BACKUPS = ROOT / "private/story/backups"
CANONICAL = ROOT / "private/story/chapter_351_panel_transcription.csv"


def load_annotator():
    spec = importlib.util.spec_from_file_location("story_annotator", ROOT / "scripts/story_annotator.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalize_tokens(value):
    mapping = {
        "Heavens Arena Referee 1": "temp_ch351_referee",
        "Commentator": "temp_ch351_announcer",
        "meteor_city": "",
    }
    tokens = []
    for token in (part.strip() for part in (value or "").split(";")):
        token = mapping.get(token, token)
        if token and token not in tokens:
            tokens.append(token)
    return ";".join(tokens)


def main():
    BACKUPS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = BACKUPS / f"story_annotations_before_ch351_review_{stamp}.sqlite"
    shutil.copy2(DB, backup)

    db = sqlite3.connect(DB)
    with db:
        rows = db.execute(
            "SELECT panel_id,characters_on_panel FROM panels WHERE chapter=351"
        ).fetchall()
        for panel_id, characters in rows:
            db.execute(
                "UPDATE panels SET characters_on_panel=? WHERE panel_id=?",
                (normalize_tokens(characters), panel_id),
            )

        speaker_map = {
            "Heavens Arena Referee 1": "temp_ch351_referee",
            "Commentator": "temp_ch351_announcer",
            "announcer": "temp_ch351_announcer",
        }
        for old, new in speaker_map.items():
            db.execute(
                "UPDATE text_segments SET speaker=? WHERE speaker=? AND panel_id LIKE 'ch351-%'",
                (new, old),
            )

        descriptions = {
            "ch351-p07-01": "Chrollo stands behind the referee and reaches toward the back of his neck while holding his open book.",
            "ch351-p07-03": "Close-up of the referee's face with blank eyes.",
            "ch351-p07-06": "Chrollo holds up a small handheld device.",
            "ch351-p08-02": "The referee stares forward with blank eyes.",
            "ch351-p11-01": "Hisoka pulls the referee toward Chrollo while defending himself on the floor.",
            "ch351-p14-02": "Chrollo stands behind the bent referee; enlarged marked hands appear in the foreground.",
            "ch351-p15-06": "A distant view of Meteor City.",
        }
        for panel_id, description in descriptions.items():
            db.execute(
                "UPDATE panels SET visual_description=? WHERE panel_id=?",
                (description, panel_id),
            )
        db.execute(
            "UPDATE panels SET location='Meteor City — illustrative cutaway' WHERE panel_id='ch351-p15-06'"
        )
        db.execute("UPDATE panels SET review_status='reviewed' WHERE chapter=351")

    annotator = load_annotator()
    with annotator.connect(DB) as export_db:
        export_path, text = annotator.export_chapter(export_db, 351)
    CANONICAL.write_text(text, encoding="utf-8")
    print(f"Backup: {backup}")
    print(f"Export: {export_path}")
    print(f"Canonical: {CANONICAL}")


if __name__ == "__main__":
    main()
