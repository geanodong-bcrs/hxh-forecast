#!/usr/bin/env python3
"""Normalize names, polish descriptions, and finalize Chapter 352."""

import importlib.util
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "private/story/story_annotations.sqlite"
BACKUPS = ROOT / "private/story/backups"
CANONICAL = ROOT / "private/story/chapter_352_panel_transcription.csv"


def load_annotator():
    spec = importlib.util.spec_from_file_location("story_annotator", ROOT / "scripts/story_annotator.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def normalize_characters(value):
    mapping = {
        "Heavens Arena Referee 1": "temp_ch351_referee",
        "Heavens Arean Referee 1": "temp_ch351_referee",
        "Heavens Arena Commentator 1": "temp_ch352_commentator",
    }
    result = []
    for token in (part.strip() for part in (value or "").split(";")):
        token = mapping.get(token, token)
        if token and token not in result:
            result.append(token)
    return ";".join(result)


DESCRIPTIONS = {
    "ch352-p01-03": "Chrollo and Hisoka face each other across the arena. Chrollo holds the closed book in his right hand and the bookmark in his left. Hisoka holds the two of hearts behind his back.",
    "ch352-p02-05": "Chrollo holds the book in his right hand while his left hand rests along its edge.",
    "ch352-p02-06": "Chrollo's left hand pulls a small object from the edge of the book.",
    "ch352-p03-04": "Chrollo flips a page while a small object takes shape above his left hand.",
    "ch352-p03-05": "Close-up of Chrollo holding the book in his right hand and inserting the bookmark with his left.",
    "ch352-p03-06": "Chrollo kneels beside the fallen referee, who lies face down in a pool of blood with his left hand missing.",
    "ch352-p03-07": "Close-up of Hisoka in profile with widened eyes.",
    "ch352-p04-01": "Chrollo presses his left hand against the referee's body while an identical body appears beneath his right hand.",
    "ch352-p04-02": "Chrollo rolls the copied referee's body onto its back.",
    "ch352-p04-03": "Close-up of the open book with the bookmark inserted between its pages.",
    "ch352-p04-05": "Chrollo kneels with the open book in his right hand and a stamp in his left. A copied body lies beside him while Hisoka watches.",
    "ch352-p06-02": "Chrollo looks toward Hisoka.",
    "ch352-p06-04": "The copied referee reaches for Hisoka as Hisoka dodges.",
    "ch352-p06-06": "Hisoka catches and grips the copied referee's head.",
    "ch352-p06-07": "Hisoka twists the copied referee's head away from its body.",
    "ch352-p07-04": "Close-up of Hisoka's face.",
    "ch352-p08-02": "A diagram shows a target's face changing into Chrollo's beneath the up arrow and Chrollo's face changing into the target's beneath the down arrow.",
    "ch352-p08-05": "Close-up of Hisoka's face.",
    "ch352-p09-02": "Close-up of Hisoka stepping forward.",
    "ch352-p09-03": "Close-up of Chrollo stepping forward.",
    "ch352-p10-01": "Close-up of Hisoka frowning with widened eyes.",
    "ch352-p10-02": "A tighter close-up of Hisoka's face.",
    "ch352-p10-05": "Close-up of Chrollo looking toward Hisoka.",
    "ch352-p11-01": "A robed elder stands inside a damaged structure with one open palm extended.",
    "ch352-p11-02": "Close-up of Chrollo looking downward in profile against an indistinct crowd.",
    "ch352-p13-02": "Hisoka lowers his stance while Chrollo holds Skill Hunter open.",
    "ch352-p14-02": "Close-up of Hisoka with his brows knit.",
    "ch352-p16-01": "Chrollo jumps into the audience as Hisoka follows him.",
    "ch352-p16-02": "The commentator looks toward the fighters in the stands.",
    "ch352-p16-03": "Chrollo moves through the audience with Hisoka following as spectators recoil.",
    "ch352-p17-04": "Close-up of Hisoka's frowning eyes.",
    "ch352-p18-01": "A large spectator fills the foreground while a dark figure moves between his legs.",
    "ch352-p18-02": "Extreme close-up of Hisoka's left eye over speed lines.",
    "ch352-p18-03": "Text appears over speed lines.",
    "ch352-p18-04": "Hisoka runs toward the large spectator and raises both arms.",
    "ch352-p18-05": "Hisoka rapidly swings his arms beside the large spectator.",
    "ch352-p18-06": "The large spectator's arms and neck bend as Hisoka leaps to the left.",
    "ch352-p18-08": "A second spectator appears behind the large spectator and to Hisoka's left.",
    "ch352-p19-02": "Speed lines and sound-effect lettering fill the panel.",
    "ch352-p19-03": "The second spectator's arms and neck bend. Both spectators remain visible as Hisoka moves left.",
    "ch352-p19-04": "Hisoka moves through the audience while spectators scatter and the two manipulated spectators fall onto the stands.",
}


CHARACTER_FIXES = {
    "ch352-p18-01": "char_chrollo_lucilfer;temp_ch352_spectator_01",
    "ch352-p18-04": "char_hisoka_morow;temp_ch352_spectator_01",
    "ch352-p18-05": "char_hisoka_morow;temp_ch352_spectator_01",
    "ch352-p18-06": "char_hisoka_morow;temp_ch352_spectator_01",
    "ch352-p18-08": "temp_ch352_spectator_01;temp_ch352_spectator_02",
    "ch352-p19-01": "char_hisoka_morow;temp_ch352_spectator_02",
    "ch352-p19-03": "char_hisoka_morow;temp_ch352_spectator_01;temp_ch352_spectator_02",
    "ch352-p19-04": "char_hisoka_morow;temp_ch352_spectator_01;temp_ch352_spectator_02;crowd",
}


def main():
    BACKUPS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = BACKUPS / f"story_annotations_before_ch352_review_{stamp}.sqlite"
    shutil.copy2(DB, backup)

    db = sqlite3.connect(DB)
    with db:
        for panel_id, characters in db.execute(
            "SELECT panel_id,characters_on_panel FROM panels WHERE chapter=352"
        ).fetchall():
            db.execute(
                "UPDATE panels SET characters_on_panel=? WHERE panel_id=?",
                (normalize_characters(characters), panel_id),
            )

        for old, new in {
            "Heavens Arena Commentator 1": "temp_ch352_commentator",
            "audience": "crowd",
        }.items():
            db.execute(
                "UPDATE text_segments SET speaker=? WHERE panel_id LIKE 'ch352-%' AND speaker=?",
                (new, old),
            )

        for panel_id, description in DESCRIPTIONS.items():
            db.execute(
                "UPDATE panels SET visual_description=? WHERE panel_id=?",
                (description, panel_id),
            )
        for panel_id, characters in CHARACTER_FIXES.items():
            db.execute(
                "UPDATE panels SET characters_on_panel=? WHERE panel_id=?",
                (characters, panel_id),
            )

        db.execute("UPDATE panels SET review_status='reviewed' WHERE chapter=352")

    annotator = load_annotator()
    with annotator.connect(DB) as export_db:
        export_path, text = annotator.export_chapter(export_db, 352)
    CANONICAL.write_text(text, encoding="utf-8")
    print(f"Backup: {backup}")
    print(f"Export: {export_path}")
    print(f"Canonical: {CANONICAL}")


if __name__ == "__main__":
    main()
