#!/usr/bin/env python3
"""Final cleanup for Hunter x Hunter chapter 353."""

import importlib.util
import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "private/story/story_annotations.sqlite"
ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "private/story/chapter_353_panel_transcription.csv"
H = "char_hisoka_morow"
C = "char_chrollo_lucilfer"


# panel_id: (characters_on_panel, cleaned visual description)
CLEAN = {
    "ch353-p08-01": (C, "Close-up of Chrollo's face and rapidly moving fist."),
    "ch353-p08-02": (H, "Close-up of Hisoka noticing Chrollo behind him."),
    "ch353-p08-03": (f"{H};{C}", "Chrollo strikes Hisoka with his right leg while holding Skill Hunter open in his right hand."),
    "ch353-p09-01": (f"{H};{C}", "Close-up of Hisoka's head as Chrollo strikes him."),
    "ch353-p09-02": (f"{H};{C};crowd", "Hisoka falls as spectators watch and Chrollo remains airborne with Skill Hunter open."),
    "ch353-p10-01": (H, "Hisoka twists his body in midair."),
    "ch353-p10-02": (f"{H};{C};crowd", "Hisoka lands against the arena's edge while spectators and Chrollo remain airborne."),
    "ch353-p11-01": (f"{H};crowd", "Spectators close in around Hisoka as he lies at the center."),
    "ch353-p11-02": (f"{H};crowd", "Hisoka kicks several attackers away."),
    "ch353-p11-03": (f"{H};crowd", "Hisoka rapidly strikes the approaching attackers."),
    "ch353-p11-04": (f"{H};crowd", "Hisoka attacks spectators approaching from several directions."),
    "ch353-p12-01": (f"{H};crowd", "A spectator grabs Hisoka's head from behind as others reach toward him."),
    "ch353-p12-02": (H, "Close-up of Hisoka's eyes."),
    "ch353-p12-03": (f"{H};crowd", "Hisoka kicks away the surrounding attackers."),
    "ch353-p12-04": (H, "Close-up of Hisoka frowning and looking to the side."),
    "ch353-p12-05": (f"{H};{C};crowd", "Chrollo charges through the crowd with his right leg extended while holding Skill Hunter in his right hand."),
    "ch353-p13-01": (f"{H};{C}", "Close-up of Hisoka's head after Chrollo strikes him."),
    "ch353-p13-02": (f"{H};{C};crowd", "Chrollo moves through the spectators toward Hisoka."),
    "ch353-p13-03": (f"{H};crowd", "Hisoka attacks the surrounding spectators."),
    "ch353-p13-04": (f"{H};crowd", "Hisoka rapidly attacks the heads of spectators reaching toward him."),
    "ch353-p13-05": (f"{H};crowd", "Close-up of Hisoka severing an attacker's head."),
    "ch353-p13-06": (f"{H};crowd", "Close-up of Hisoka severing another attacker's head."),
    "ch353-p14-01": (f"{H};crowd", "Attackers loom over Hisoka and reach for his head while he holds a spectator's head and the two of diamonds."),
    "ch353-p14-02": (f"{H};crowd", "Hisoka breaks free from the surrounding attackers as the two of diamonds falls through the air."),
    "ch353-p14-03": (f"{H};crowd", "Hisoka pushes through the attackers."),
    "ch353-p14-04": (f"{H};{C};crowd", "Chrollo kicks Hisoka from behind while holding Skill Hunter half-open in his right hand."),
    "ch353-p15-01": (H, "Close-up of Hisoka's face as he is struck."),
    "ch353-p15-02": (f"{H};{C};crowd", "Chrollo's kick sends Hisoka away from the surrounding spectators."),
    "ch353-p15-03": (f"{H};{C};crowd", "Hisoka moves through the surrounding attackers after Chrollo's kick."),
    "ch353-p15-04": (f"{H};crowd", "Hisoka moves rapidly through the crowd of attackers."),
    "ch353-p15-05": (H, "Close-up of Hisoka looking sideways."),
    "ch353-p15-06": (f"{C};crowd", "Chrollo approaches through the attackers."),
    "ch353-p15-07": ("crowd", "A fast-moving dark shape passes through a cluster of attackers."),
    "ch353-p16-01": (f"{H};crowd", "Hisoka attacks spectators reaching toward him."),
    "ch353-p16-02": (f"{H};crowd", "Hisoka severs an attacker's head."),
    "ch353-p16-03": (f"{H};crowd", "Hisoka moves past the attackers while striking with a severed head."),
    "ch353-p16-04": (f"{H};{C}", "Chrollo crouches above Hisoka as Hisoka looks up at him."),
    "ch353-p16-05": (H, "Close-up of Hisoka's face."),
    "ch353-p16-06": (H, "Extreme close-up of Hisoka's face."),
    "ch353-p17-01": (H, "A text-only panel contains Hisoka's declaration."),
    "ch353-p17-02": (f"{H};{C};crowd", "A severed head fills the foreground while Hisoka, Chrollo, and the attackers appear behind it, surrounded by aura."),
    "ch353-p17-03": (f"{H};crowd", "The attached head is pulled rapidly through the air toward Hisoka."),
    "ch353-p18-01": (f"{H};{C}", "Chrollo rotates in the air as Hisoka pulls the severed head nearby."),
    "ch353-p18-02": (H, "Close-up of Hisoka looking upward in surprise."),
    "ch353-p18-03": (C, "Chrollo looks at Hisoka and speaks."),
    "ch353-p18-04": (f"{H};{C}", "Chrollo stomps Hisoka and knocks him to the floor."),
    "ch353-p19-01": (f"{H};{C}", "The head attached to Hisoka by Bungee Gum strikes Chrollo as blood sprays from both men."),
    "ch353-p19-02": (H, "Close-up of Hisoka's face with blood spraying upward."),
}


def main():
    db = sqlite3.connect(DB)
    db.execute("PRAGMA foreign_keys=ON")
    with db:
        for panel_id, (characters, visual) in CLEAN.items():
            db.execute(
                "UPDATE panels SET characters_on_panel=?,visual_description=? WHERE panel_id=?",
                (characters, visual, panel_id),
            )

        # Correct obvious mode/typography errors without rewriting the user's transcription.
        db.execute("UPDATE text_segments SET mode='sound_effect' WHERE panel_id IN ('ch353-p08-03','ch353-p11-03','ch353-p12-03','ch353-p14-01','ch353-p18-01') AND mode IN ('dialogue','caption')")
        db.execute("UPDATE text_segments SET speaker='no_speaker' WHERE panel_id='ch353-p18-01'")
        db.execute("UPDATE text_segments SET text='KRAK KRAK KRAK KRAK KRAK KRAK' WHERE panel_id='ch353-p09-01'")
        db.execute("UPDATE text_segments SET text=TRIM(text) WHERE panel_id IN (SELECT panel_id FROM panels WHERE chapter=353)")

        # Use stable cross-chapter identities for the recurring arena staff.
        db.execute("UPDATE text_segments SET speaker='temp_heavens_arena_commentator' WHERE speaker IN ('temp_ch351_announcer','temp_ch352_commentator') AND panel_id IN (SELECT panel_id FROM panels WHERE chapter BETWEEN 351 AND 353)")
        db.execute("UPDATE panels SET characters_on_panel=REPLACE(characters_on_panel,'temp_ch351_announcer','temp_heavens_arena_commentator') WHERE chapter BETWEEN 351 AND 353")
        db.execute("UPDATE text_segments SET speaker='temp_heavens_arena_referee' WHERE speaker='temp_ch351_referee' AND panel_id IN (SELECT panel_id FROM panels WHERE chapter BETWEEN 351 AND 353)")
        db.execute("UPDATE panels SET characters_on_panel=REPLACE(characters_on_panel,'temp_ch351_referee','temp_heavens_arena_referee') WHERE chapter BETWEEN 351 AND 353")

        # The user has completed the chapter and this cleanup is the final review pass.
        db.execute("UPDATE panels SET review_status='reviewed' WHERE chapter=353")

    panels = db.execute("SELECT COUNT(*) FROM panels WHERE chapter=353").fetchone()[0]
    segments = db.execute("SELECT COUNT(*) FROM text_segments t JOIN panels p USING(panel_id) WHERE p.chapter=353").fetchone()[0]
    pages = db.execute("SELECT COUNT(DISTINCT page_start) FROM panels WHERE chapter=353").fetchone()[0]
    unreviewed = db.execute("SELECT COUNT(*) FROM panels WHERE chapter=353 AND review_status!='reviewed'").fetchone()[0]
    assert panels == 76
    assert pages == 19
    assert unreviewed == 0
    spec = importlib.util.spec_from_file_location("story_annotator", ROOT / "scripts/story_annotator.py")
    annotator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(annotator)
    with annotator.connect(DB) as export_db:
        export_path, text = annotator.export_chapter(export_db, 353)
    CANONICAL.write_text(text, encoding="utf-8")
    print(f"Finalized chapter 353: {panels} panels, {segments} text segments, {pages} pages")
    print(f"Export: {export_path}")
    print(f"Canonical: {CANONICAL}")


if __name__ == "__main__":
    main()
