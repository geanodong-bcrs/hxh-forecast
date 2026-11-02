#!/usr/bin/env python3
"""Clean reviewed pages 1-7 and realign/check the prefill for pages 8-19."""

import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "private/story/story_annotations.sqlite"
H = "char_hisoka_morow"
C = "char_chrollo_lucilfer"
LOC = "Heavens Arena — spectator stands"


def s(speaker, mode, text):
    return speaker, mode, text


# Correct page-to-image mapping for 353-08.png through 353-19.png.
P = {
8: [
 (f"{H};{C}","Chrollo appears beside Hisoka and swings Skill Hunter toward his head.",[]),
 (f"{H};{C}","Chrollo strikes Hisoka with Skill Hunter.",[s("no_speaker","sound_effect","BASH")]),
],
9: [
 (f"{H};{C}","Chrollo repeatedly strikes the side of Hisoka's head with Skill Hunter.",[s("no_speaker","sound_effect","KRAK KRAK KRAK KRAK KRAK KRAK")]),
 (f"{H};{C};crowd","Hisoka falls toward the spectators as Chrollo moves away.",[s(H,"thought","HE WAS GOING FOR MY LEFT FLANK!!"),s(H,"thought","HOW COULD HE MODIFY HIS ATTACK ANGLE FROM THERE...?!")]),
],
10: [
 (H,"Hisoka twists his body in midair.",[s(H,"thought","I LOVE IT... ♥")]),
 (f"{H};crowd","Hisoka lands against the edge of the arena as the pursuing spectators descend.",[s("no_speaker","sound_effect","SLAM")]),
],
11: [
 (f"{H};crowd","Spectators close in around Hisoka from all sides.",[]),
 (f"{H};crowd","Hisoka kicks several attackers away.",[]),
 (f"{H};crowd","Hisoka strikes attackers rushing from the side.",[]),
 (f"{H};crowd","Hisoka swings a severed leg through the attackers.",[]),
],
12: [
 (f"{H};crowd","A spectator grabs Hisoka from behind as others reach for him.",[]),
 (H,"Close-up of Hisoka's eyes.",[s(H,"thought","THEY WON'T STOP UNLESS COMPLETELY DECAPITATED..."),s(H,"thought","WITH ZERO EMOTIONS, THEY'RE MORE TROUBLESOME THAN REGULAR ATTACKERS. ♦")]),
 (f"{H};crowd","Hisoka kicks nearby attackers.",[]),
 (H,"Hisoka looks to the side while pinned among bodies.",[s(H,"thought","!!")]),
 (f"{H};{C};crowd","Chrollo charges through the crowd and swings Skill Hunter toward Hisoka.",[s("no_speaker","sound_effect","BASH")]),
],
13: [
 (f"{H};{C}","Chrollo strikes Hisoka's head with Skill Hunter.",[s("no_speaker","sound_effect","KRAK KRAK")]),
 (f"{H};{C};crowd","Chrollo moves away through the spectators after striking Hisoka.",[s(H,"thought","HE'S WAITING FOR GUARANTEED HITS...!!"),s(H,"thought","COMING IN FOR A STRIKE, THEN SPRINGING AWAY, TRYING TO LAND MORTAL BLOWS... ♦")]),
 (f"{H};crowd","Hisoka pushes through the surrounding attackers.",[s(H,"thought","AND HE'S FORCING ME INTO THE THRONG OF PUPPETS..."),s(H,"thought","SO COLD-BLOODED AND CALCULATING. ♥")]),
 (f"{H};crowd","Hisoka faces reaching attackers on both sides.",[s(H,"thought","HE WON'T BE ABLE TO CREATE NEW PUPPETS WHILE HE'S CONTROLLING THE CURRENT CROP! ♣"),s(H,"thought","I'LL HAVE TO DECREASE THEIR NUMBERS ONE BY ONE. ♦")]),
 (f"{H};crowd","Hisoka cuts an attacker while turning.",[]),
 (f"{H};crowd","Hisoka strikes another attacker at close range.",[]),
],
14: [
 (f"{H};crowd","Several attackers loom over Hisoka.",[]),
 (f"{H};crowd","Hisoka moves farther from Chrollo while attackers surround him.",[s(H,"thought","ADDING THE EXTRA STEP MEANS FALLING FURTHER BEHIND...")]),
 (f"{H};crowd","Hisoka pushes through the attackers.",[s(H,"thought","REGROUPING WILL EVENTUALLY BECOME NECESSARY, RIGHT?")]),
 (f"{H};{C};crowd","Chrollo approaches as Hisoka is held among the attackers.",[s(H,"thought","AND THAT'S WHEN A STRIKE COMES...!!")]),
],
15: [
 (H,"Close-up of Hisoka looking upward.",[]),
 (f"{H};crowd","Hisoka strikes an attacker while surrounded by reaching arms.",[]),
 (f"{H};crowd","Hisoka moves through the surrounding attackers.",[]),
 (f"{H};crowd","Hisoka pulls a cord around an attacker's head.",[]),
 (H,"Close-up of Hisoka smiling.",[]),
 (f"{C};crowd","Chrollo crouches with Skill Hunter among the attackers.",[]),
 (f"{H};crowd","Hisoka strikes through a cluster of attackers.",[]),
],
16: [
 (f"{H};crowd","Hisoka faces attackers reaching toward him.",[]),
 (f"{H};crowd","Hisoka strikes an attacker at close range.",[s("no_speaker","sound_effect","SNAP")]),
 (f"{H};crowd","Hisoka moves past the attackers.",[]),
 (f"{H};{C}","Hisoka lies back and looks up at Chrollo crouching above him.",[]),
 (H,"Close-up of Hisoka lying back.",[s(H,"thought","HE KNOWS..."),s(H,"thought","...WHAT I'LL DO NEXT....!")]),
 (H,"Close-up of Hisoka's face.",[s(H,"thought","SO... ♥")]),
],
17: [
 (H,"A bright panel contains Hisoka's declaration.",[s(H,"thought","ACTIVATE BUNGEE GUM! ♥")]),
 (f"{H};crowd","Small pieces of aura attached to several attackers shrink.",[s(H,"thought","SHRINK!!!")]),
 (f"{H};crowd","The attached attackers are pulled rapidly through the air.",[s("no_speaker","sound_effect","ZOOOOM")]),
],
18: [
 (f"{H};crowd","Several attackers twist together through the air.",[s("no_speaker","sound_effect","TWIST")]),
 (H,"Hisoka watches the moving bodies.",[]),
 (C,"Chrollo watches from below.",[s(C,"dialogue","I WAS WATCHING YOU.")]),
 (f"{C};crowd","Chrollo drives the bundled attackers downward.",[s("no_speaker","sound_effect","WHAM")]),
],
19: [
 (f"{H};{C};crowd","Chrollo slams the bundled bodies into Hisoka.",[s("no_speaker","sound_effect","BAM")]),
 (H,"Hisoka lies beneath the impact with blood spraying upward.",[s(H,"dialogue","I KNOW. ♥")]),
],
}


VISUALS_1_7 = {
 "ch353-p01-01": ("crowd", "Frightened spectators rush to leave while looking back over their shoulders."),
 "ch353-p01-02": (f"{H};crowd", "Two spectators lie face down as the crowd flees and Hisoka walks through the stands."),
 "ch353-p01-03": (H, "Close-up of Hisoka's face in profile."),
 "ch353-p01-04": (f"{H};crowd", "Hisoka searches the stands while spectators rush toward the exits and abandoned belongings remain on the floor."),
 "ch353-p02-01": (H, "Close-up of Hisoka's left eye looking left."),
 "ch353-p02-02": ("crowd", "Spectators move through the stands."),
 "ch353-p02-03": (H, "Close-up of Hisoka's right eye looking right."),
 "ch353-p02-04": ("crowd", "Spectators pass one another in the aisle."),
 "ch353-p02-05": ("crowd", "A row of spectators looks at two visually identical pairs among them."),
 "ch353-p02-06": ("crowd", "Two more visually identical pairs stand among the spectators."),
 "ch353-p02-07": ("crowd", "Three more visually identical pairs stand among the spectators."),
 "ch353-p02-08": (f"{H};crowd", "Hisoka watches as spectators look toward him."),
 "ch353-p02-09": (f"{H};crowd", "Spectators stand in the aisles and look around while Hisoka searches the crowd."),
 "ch353-p03-01": ("crowd", "Spectators begin jumping and running toward Hisoka."),
 "ch353-p03-02": (H, "Close-up of Hisoka's startled eyes."),
 "ch353-p03-03": (f"{H};crowd", "A group of spectators rushes toward Hisoka."),
 "ch353-p04-01": ("crowd", "A large group of spectators with stamps on their foreheads charges toward Hisoka."),
 "ch353-p04-02": (H, "Close-up of Hisoka's face in profile."),
 "ch353-p04-03": (f"{H};crowd", "Spectators with stamps on their foreheads rush toward Hisoka."),
 "ch353-p04-04": (f"{H};crowd", "Hisoka extends his hand as the spectators approach."),
 "ch353-p05-01": (f"{H};crowd", "Hisoka jumps high above spectators looking up and reaching toward him."),
 "ch353-p05-02": (f"{H};crowd", "Hisoka rises with his left arm raised as spectators look up at him."),
 "ch353-p05-03": ("", "Speed lines fill the panel."),
 "ch353-p05-04": (H, "Close-up of Hisoka reacting in surprise."),
 "ch353-p06-01": (f"{H};crowd", "A mass of spectators leaps after Hisoka across the stands."),
 "ch353-p06-02": (f"{H};crowd", "Hisoka remains airborne as several spectators reach toward him."),
 "ch353-p07-01": (f"{H};crowd", "Hisoka kicks away the spectators nearest him."),
 "ch353-p07-02": (f"{H};{C}", "Chrollo appears behind Hisoka in another person's clothes and prepares to strike as Hisoka notices him."),
}


def reset_segments(db, panel_id, segments):
    db.execute("DELETE FROM text_segments WHERE panel_id=?", (panel_id,))
    for order, (speaker, mode, text) in enumerate(segments, 1):
        db.execute(
            "INSERT INTO text_segments(panel_id,segment_order,speaker,mode,text) VALUES(?,?,?,?,?)",
            (panel_id, order, speaker, mode, text),
        )
    db.execute("UPDATE panels SET silent_panel=? WHERE panel_id=?", (int(not segments), panel_id))


def main():
    db = sqlite3.connect(DB)
    db.execute("PRAGMA foreign_keys=ON")
    with db:
        # Preserve the user's panel structure and wording on pages 1-7; clean only
        # grammar, visible descriptions, character tags, and obvious segment modes.
        for panel_id, (characters, visual) in VISUALS_1_7.items():
            db.execute(
                "UPDATE panels SET characters_on_panel=?,visual_description=? WHERE panel_id=?",
                (characters, visual, panel_id),
            )

        reset_segments(db, "ch353-p01-01", [s("crowd","dialogue","AIEEE!! RUN!!"),s("no_speaker","sound_effect","DM DM DM DM DM DM DM")])
        reset_segments(db, "ch353-p01-03", [s(H,"thought","THE ANTENNAS ARE GONE... ♦ I THOUGHT SHAL'S ANTENNAS WERE REAL OBJECTS...? HE MUST'VE REELED THEM IN WITH A FISHING LINE OR SOMETHING... ♣")])
        reset_segments(db, "ch353-p01-04", [s("temp_heavens_arena_commentator","dialogue","PEOPLE!! PLEASE, DO NOT PANIC!! IT'S DANGEROUS TO RUSH THE EXITS ALL AT ONCE!!"),s("crowd","sound_effect","RAAH RAAH RAAH")])
        reset_segments(db, "ch353-p02-08", [s(H,"thought","GALLERY FAKE IS ACTIVATED...! THEN CONVERT HANDS MUST'VE BEEN DEACTIVATED...!!")])
        reset_segments(db, "ch353-p02-09", [s(H,"thought","HE MUST'VE TAKEN SOMEONE ELSE'S CLOTHES FIRST TO DISGUISE HIMSELF...!! ♣ WHERE IS HE...?!")])
        reset_segments(db, "ch353-p03-03", [s("temp_heavens_arena_commentator","dialogue","THE AUDIENCE MEMBERS... ARE ATTACKING HISOKA!!!")])
        reset_segments(db, "ch353-p04-01", [s("no_speaker","sound_effect","DM DM DM DM DM DM")])
        reset_segments(db, "ch353-p04-02", [s(H,"thought","OPEN BOOK TO GALLERY FAKE ↓ BOOKMARK ↓ CREATE A CROWD OF COPIES ↓ ACTIVATE ORDER STAMP ↓ COMMAND THEM TO \"BREAK HISOKA\""),s(H,"thought","I SEE. ♦"),s(H,"thought","EVERYONE IN THE AUDIENCE HERE KNOWS WHO I AM... ♣")])
        reset_segments(db, "ch353-p04-03", [s(H,"thought","ABOUT 30 PUPPETS THAT WON'T STOP UNTIL THEY'RE BEHEADED... AT CHROLLO'S SPEED, HE MIGHT MAKE EVEN MORE...?"),s("no_speaker","sound_effect","VSH VSH")])
        reset_segments(db, "ch353-p04-04", [s(H,"thought","THERE MUST BE MORE PUPPETS THAT HAVEN'T BEEN GIVEN COMMANDS YET...!! I SHOULD BIDE MY TIME UNTIL THERE ARE FEWER PEOPLE RUNNING ABOUT...!! ♦"),s("no_speaker","sound_effect","VSH")])
        reset_segments(db, "ch353-p05-02", [s("temp_heavens_arena_commentator","dialogue","WHOA, HISOKA JUMPS HIGH TO AVOID THEM!!")])

        # Replace the unchecked portion so each annotation page matches the image
        # with the same two-digit filename.
        db.execute("DELETE FROM text_segments WHERE panel_id IN (SELECT panel_id FROM panels WHERE chapter=353 AND page_start BETWEEN 8 AND 19)")
        db.execute("DELETE FROM panels WHERE chapter=353 AND page_start BETWEEN 8 AND 19")
        for page in range(8, 20):
            for order, (characters, visual, segments) in enumerate(P[page], 1):
                panel_id = f"ch353-p{page:02d}-{order:02d}"
                db.execute(
                    """INSERT INTO panels(panel_id,chapter,page_start,page_end,panel_order,panel_types,characters_on_panel,location,visual_description,review_status,silent_panel)
                       VALUES(?,353,?,?,?,'standard',?,?,?,'needs_review',?)""",
                    (panel_id, page, page, order, characters, LOC, visual, int(not segments)),
                )
                for segment_order, (speaker, mode, text) in enumerate(segments, 1):
                    db.execute(
                        "INSERT INTO text_segments(panel_id,segment_order,speaker,mode,text) VALUES(?,?,?,?,?)",
                        (panel_id, segment_order, speaker, mode, text),
                    )

    counts = db.execute(
        "SELECT page_start,COUNT(*) FROM panels WHERE chapter=353 GROUP BY page_start ORDER BY page_start"
    ).fetchall()
    assert [page for page, _ in counts] == list(range(1, 20))
    assert sum(count for _, count in counts) == 75
    print("Cleaned chapter 353; panel counts:", ", ".join(f"p{p}={n}" for p, n in counts))


if __name__ == "__main__":
    main()
