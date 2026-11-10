#!/usr/bin/env python3
"""Final cleanup and export for reviewed Hunter x Hunter chapter 354."""

import importlib.util
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "private/story/story_annotations.sqlite"
BACKUPS = ROOT / "private/story/backups"
STORY = ROOT / "private/story"
H = "char_hisoka_morow"
C = "char_chrollo_lucilfer"
COMMENTATOR = "temp_heavens_arena_commentator"
COPY = "temp_ch354_convert_hands_copy"


# Only grammar, visible-detail, and identity corrections. Human panel structure and
# transcription remain authoritative.
DESCRIPTIONS = {
    "ch354-p01-02": "Hisoka and Chrollo move through the air. Chrollo holds Skill Hunter open above Hisoka while Hisoka swings two severed heads with Bungee Gum attached to his left hand and foot.",
    "ch354-p01-03": "Close-up of Hisoka's face with blood spraying upward.",
    "ch354-p02-01": "Close-up of Chrollo's face after he is struck.",
    "ch354-p02-02": "Close-up of Hisoka's face with blood spraying outward.",
    "ch354-p02-03": "Close-up of Hisoka's hands as he contracts Bungee Gum.",
    "ch354-p02-05": "A severed head controlled by Hisoka strikes Chrollo.",
    "ch354-p03-01": "Hisoka controls a severed head with Bungee Gum near the arena floor while Chrollo, holding Skill Hunter, remains airborne after being struck.",
    "ch354-p03-02": "A small inset shows Chrollo in profile with one eye wide and blood leaving his mouth.",
    "ch354-p03-03": "Hisoka swings the severed head as Chrollo lands on the floor.",
    "ch354-p03-04": "Hisoka controls the severed head with Bungee Gum.",
    "ch354-p03-06": "The commentator holds her headset while surrounding spectators shout.",
    "ch354-p04-01": "Attackers run toward Hisoka.",
    "ch354-p04-02": "Hisoka holds the severed head in one hand.",
    "ch354-p04-03": "Hisoka throws the severed head through the attackers, striking two heads.",
    "ch354-p05-01": "Hisoka swings the severed head into two attackers while others reach toward him from behind.",
    "ch354-p05-02": "Hisoka continues striking attackers with the severed head.",
    "ch354-p05-05": "Chrollo appears between approaching spectators and coughs.",
    "ch354-p05-06": "Hisoka swings the severed head through the nearby crowd toward Chrollo.",
    "ch354-p06-01": "Hisoka throws the severed head toward Chrollo, who dodges as attackers continue toward Hisoka.",
    "ch354-p06-05": "Hisoka grips the severed head and attacks nearby spectators.",
    "ch354-p06-06": "Chrollo jumps into the crowd.",
    "ch354-p07-01": "Hisoka smashes attackers' heads with the severed head.",
    "ch354-p07-02": "Text and two bright radial bursts appear over speed lines.",
    "ch354-p07-03": "Two attackers are beheaded.",
    "ch354-p07-04": "The final attacker approaches Hisoka.",
    "ch354-p07-05": "Close-up of Hisoka moving his arm rapidly.",
    "ch354-p07-06": "Hisoka cuts the final attacker's arms with a card.",
    "ch354-p08-04": "Spectators remain in the stands while several bodies lie on the arena floor.",
    "ch354-p08-05": "Three subpanels show the attacker going limp, Hisoka holding him from behind, and Hisoka releasing him.",
    "ch354-p09-04": "Text appears over horizontal speed lines.",
    "ch354-p09-07": "Chrollo appears among a group of spectators in the stands.",
    "ch354-p09-08": "Chrollo disappears into the group of spectators.",
    "ch354-p10-01": "Hisoka runs up the arena steps toward Chrollo as he moves through the spectators.",
    "ch354-p10-04": "Chrollo looks back at Hisoka as Hisoka moves through the fleeing spectators toward him.",
    "ch354-p11-02": "The severed head flies toward Chrollo as he moves aside.",
    "ch354-p11-04": "Hisoka swings the severed head overhead as frightened spectators rush away.",
    "ch354-p11-08": "Close-up of Hisoka frowning.",
    "ch354-p12-01": "Overhead view of Hisoka swinging the severed head while running through fleeing spectators in the stands.",
    "ch354-p12-03": "Text appears over curved speed lines.",
    "ch354-p12-04": "Hisoka chases Chrollo and throws the severed head toward him as Chrollo runs ahead.",
    "ch354-p12-05": "Close-up of Hisoka after throwing the severed head.",
    "ch354-p12-06": "Chrollo jumps aside as Hisoka throws the severed head toward him.",
    "ch354-p13-01": "Hisoka opens the index finger and thumb of his left hand while chasing Chrollo.",
    "ch354-p13-02": "Spectators attached to Bungee Gum fly backward toward Chrollo as Hisoka faces him.",
    "ch354-p13-03": "Close-up of Chrollo reacting with widened eyes.",
    "ch354-p14-01": "A diagram shows fleeing people anchored to the floor with Bungee Gum as Hisoka chases Chrollo in the opposite direction.",
    "ch354-p14-02": "Spectators are pulled backward by Bungee Gum toward Chrollo.",
    "ch354-p15-01": "Hisoka throws the severed head.",
    "ch354-p15-02": "Chrollo notices the severed head through the group of airborne spectators.",
    "ch354-p15-03": "The severed head flies through the air.",
    "ch354-p15-04": "Chrollo lunges aside as the severed head strikes the airborne spectators.",
    "ch354-p15-05": "The severed head strikes the airborne spectators while Chrollo escapes to the side and Hisoka stands below.",
    "ch354-p15-06": "Hisoka holds up his left hand with his index finger and thumb extended.",
    "ch354-p16-01": "Hisoka attaches Bungee Gum to Chrollo's leg with his left hand while controlling the severed head with his right.",
    "ch354-p16-03": "Three subpanels show Chrollo glancing back and two progressively tighter views of Hisoka in profile.",
    "ch354-p16-04": "Text appears over a dark background.",
    "ch354-p17-01": "Hisoka contracts Bungee Gum and pulls both Chrollo and the severed head.",
    "ch354-p17-02": "Hisoka swings the severed head with great force.",
    "ch354-p17-03": "The severed head strikes Chrollo from behind as blood leaves his mouth.",
    "ch354-p18-01": "Hisoka pulls Chrollo with Bungee Gum from his left hand while controlling the severed head with his right.",
    "ch354-p18-02": "Close-up of Hisoka's face in rapid motion.",
    "ch354-p18-03": "Hisoka slams Chrollo onto the floor.",
    "ch354-p18-04": "Close-up of Hisoka's lowered face as he swings the severed head with Bungee Gum.",
    "ch354-p18-05": "Hisoka smashes the severed head into Chrollo's lower abdomen as blood leaves Chrollo's mouth.",
    "ch354-p18-06": "Chrollo lies partly embedded in the broken arena floor with blood around his body.",
    "ch354-p18-07": "Hisoka stands and looks at Chrollo's body on the floor.",
    "ch354-p19-01": "A bearded man's body lies with its lower abdomen crushed.",
    "ch354-p19-02": "Text appears over a dark background.",
    "ch354-p19-03": "Hisoka checks the bearded man's neck.",
    "ch354-p19-04": "Close-up of Hisoka holding a control antenna beside his face.",
    "ch354-p19-05": "Hisoka looks at the antenna in his right hand while the severed head remains attached to Bungee Gum.",
    "ch354-p19-06": "Close-up of Hisoka's startled face.",
    "ch354-p19-07": "Close-up of Hisoka snapping the antenna with his right hand.",
    "ch354-p19-08": "Hisoka opens his right hand as the broken antenna falls.",
}


CHARACTERS = {
    "ch354-p03-02": C,
    "ch354-p06-06": C,
    "ch354-p07-02": "crowd",
    "ch354-p07-03": "crowd",
    "ch354-p08-04": "crowd",
    "ch354-p09-07": f"{C};crowd",
    "ch354-p09-08": f"{C};crowd",
    "ch354-p10-01": f"{H};{C};crowd",
    "ch354-p10-04": f"{H};{C};crowd",
    "ch354-p11-02": C,
    "ch354-p11-03": f"{C};crowd",
    "ch354-p11-04": f"{H};crowd",
    "ch354-p11-05": f"{C};crowd",
    "ch354-p12-01": f"{H};crowd",
    "ch354-p13-02": f"{H};{C};crowd",
    "ch354-p14-01": f"{H};{C};crowd",
    "ch354-p14-02": f"{C};crowd",
    "ch354-p14-03": f"{H};{C};crowd",
    "ch354-p15-02": f"{C};crowd",
    "ch354-p15-04": f"{C};crowd",
    "ch354-p15-05": f"{H};{C};crowd",
    "ch354-p16-01": f"{H};{C}",
    "ch354-p19-01": COPY,
    "ch354-p19-03": f"{H};{COPY}",
}


def load_annotator():
    spec = importlib.util.spec_from_file_location("story_annotator", ROOT / "scripts/story_annotator.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main():
    BACKUPS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = BACKUPS / f"story_annotations_before_ch354_finalization_{stamp}.sqlite"
    shutil.copy2(DB, backup)

    db = sqlite3.connect(DB)
    db.execute("PRAGMA foreign_keys=ON")
    with db:
        for panel_id, description in DESCRIPTIONS.items():
            db.execute("UPDATE panels SET visual_description=? WHERE panel_id=?", (description, panel_id))
        for panel_id, characters in CHARACTERS.items():
            db.execute("UPDATE panels SET characters_on_panel=? WHERE panel_id=?", (characters, panel_id))

        # One stable identity for the recurring Heavens Arena commentator.
        db.execute(
            """UPDATE text_segments SET speaker=?
               WHERE panel_id IN (SELECT panel_id FROM panels WHERE chapter BETWEEN 351 AND 354)
                 AND speaker IN ('temp_ch351_announcer','temp_ch352_commentator','commentator')""",
            (COMMENTATOR,),
        )
        db.execute(
            """UPDATE panels SET characters_on_panel=
                   REPLACE(REPLACE(characters_on_panel,'temp_ch351_announcer',?), 'temp_ch352_commentator', ?)
               WHERE chapter BETWEEN 351 AND 354""",
            (COMMENTATOR, COMMENTATOR),
        )

        # Captions are unattributed text, never sound effects or character speech.
        db.execute(
            "UPDATE text_segments SET speaker='' WHERE mode='caption' AND panel_id IN (SELECT panel_id FROM panels WHERE chapter=354)"
        )
        # Two stylized effects retained from human review had a dialogue mode.
        db.execute(
            """UPDATE text_segments SET mode='sound_effect'
               WHERE panel_id IN ('ch354-p03-05','ch354-p05-06') AND speaker='no_speaker'"""
        )
        db.execute(
            "UPDATE text_segments SET text=TRIM(text) WHERE panel_id IN (SELECT panel_id FROM panels WHERE chapter=354)"
        )

        # Human approval authorizes the final status transition.
        db.execute("UPDATE panels SET review_status='reviewed' WHERE chapter=354")

    panels = db.execute("SELECT COUNT(*) FROM panels WHERE chapter=354").fetchone()[0]
    segments = db.execute(
        "SELECT COUNT(*) FROM text_segments t JOIN panels p USING(panel_id) WHERE p.chapter=354"
    ).fetchone()[0]
    pages = db.execute("SELECT COUNT(DISTINCT page_start) FROM panels WHERE chapter=354").fetchone()[0]
    unreviewed = db.execute("SELECT COUNT(*) FROM panels WHERE chapter=354 AND review_status!='reviewed'").fetchone()[0]
    silent_mismatch = db.execute(
        """SELECT COUNT(*) FROM panels p WHERE chapter=354 AND
           silent_panel != NOT EXISTS (SELECT 1 FROM text_segments t WHERE t.panel_id=p.panel_id)"""
    ).fetchone()[0]
    caption_speakers = db.execute(
        """SELECT COUNT(*) FROM text_segments t JOIN panels p USING(panel_id)
           WHERE p.chapter=354 AND t.mode='caption' AND t.speaker!=''"""
    ).fetchone()[0]
    assert panels == 104
    assert pages == 19
    assert unreviewed == 0
    assert silent_mismatch == 0
    assert caption_speakers == 0

    annotator = load_annotator()
    # Re-export previously reviewed chapters whose recurring commentator ID changed.
    for chapter in (351, 352, 353, 354):
        with annotator.connect(DB) as export_db:
            export_path, text = annotator.export_chapter(export_db, chapter)
        canonical = STORY / f"chapter_{chapter}_panel_transcription.csv"
        canonical.write_text(text, encoding="utf-8")
        print(f"Export {chapter}: {export_path}")
        print(f"Canonical {chapter}: {canonical}")

    print(f"Backup: {backup}")
    print(f"Finalized chapter 354: {panels} panels, {segments} text segments, {pages} pages")


if __name__ == "__main__":
    main()
