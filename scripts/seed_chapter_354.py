#!/usr/bin/env python3
"""Prefill Hunter x Hunter chapter 354 for review in the local annotator."""

import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "private/story/story_annotations.sqlite"
H = "char_hisoka_morow"
M = "char_machi_komacine"
LOC = "Heavens Arena — spectator stands"


def s(speaker, mode, text):
    return speaker, mode, text


# (panel_type, characters, visual description, text segments)
# Panels are ordered right-to-left, then top-to-bottom.
P = {
    1: [
        ("standard", H, "A diagram compares Hisoka's severed head with a bowling ball on a balance scale.", [s("no_speaker", "caption", "AN ADULT MALE HEAD WEIGHS ABOUT 7 TO 8 KG."), s("no_speaker", "caption", "ABOUT AS MUCH AS OR HEAVIER THAN A MALE PROFESSIONAL BOWLER'S REGULATION BOWLING BALL.")]),
        ("standard", f"{H};{M}", "Hisoka swings a severed head toward Machi while she lies on the floor.", []),
        ("standard", f"{H};{M}", "The severed head strikes Machi as Hisoka runs past her.", [s(H, "thought", "A SECOND HEAD SECURED AND LAUNCHED BY MY GUM..."), s(H, "thought", "...CAUGHT BY GUMMY AURA FROM MY LEFT LEG TO ATTACK FROM HIS BLIND SPOT!!")]),
    ],
    2: [
        ("standard", M, "Machi looks toward the approaching severed head.", [s(M, "dialogue", "...!")]),
        ("standard", f"{H};{M}", "The severed head reaches Machi's face.", []),
        ("standard", H, "Hisoka closes his fist and contracts Bungee Gum.", [s(H, "thought", "SHRINK!!"), s("no_speaker", "sound_effect", "ZNG")]),
        ("standard", f"{H};{M}", "Machi is pulled across the floor while Hisoka runs away.", [s("no_speaker", "sound_effect", "WHAM")]),
        ("floating", M, "A narrow inset shows Machi's widened eyes.", []),
    ],
    3: [
        ("standard", f"{H};{M}", "Hisoka drags Machi across the arena floor.", []),
        ("standard", H, "Hisoka swings the severed head repeatedly while running.", [s("no_speaker", "sound_effect", "SKSHH SKSHH SKSHH SKSHH SKSHH")]),
        ("floating", M, "A small inset shows Machi's eye under her hat.", [s("no_speaker", "sound_effect", "URF")]),
        ("standard", f"{H};{M}", "Hisoka faces Machi while holding the severed head by its neck.", [s(M, "dialogue", "WOW... ♥"), s(M, "dialogue", "YOU STILL..."), s(H, "dialogue", "...WON'T LET GO. ♥")]),
        ("standard", "temp_ch352_commentator;crowd", "The commentator holds her headset while the surrounding spectators shout.", [s("temp_ch352_commentator", "dialogue", "HISOKA SUCCEEDS IN STRIKING BACK!!"), s("temp_ch352_commentator", "dialogue", "HE'S DRAWN BLOOD FROM CHROLLO!!"), s("temp_ch352_commentator", "dialogue", "THE CROWD IS IN CHAOS!! THE JUDGE IS DEAD!! WHAT A MESS!!")]),
    ],
    4: [
        ("standard", H, "Hisoka swings the severed head past nearby spectators.", [s("no_speaker", "sound_effect", "FSSHH FSSHH FSSHH")]),
        ("standard", H, "Hisoka catches the severed head in one hand.", [s("no_speaker", "sound_effect", "FOM"), s("no_speaker", "sound_effect", "HRRN HRRN HRRN")]),
        ("standard", H, "Hisoka runs through the stands while swinging the severed head beside him.", [s("no_speaker", "sound_effect", "POP POP POP")]),
    ],
    5: [
        ("standard", H, "Hisoka swings the severed head through a group of attackers.", [s("no_speaker", "sound_effect", "DASH DASH DASH DASH")]),
        ("standard", H, "Hisoka swings the severed head toward more attackers.", [s("no_speaker", "sound_effect", "BAM BAM BAM BAM")]),
        ("standard", H, "Hisoka turns and strikes attackers behind him with the severed head.", [s("no_speaker", "sound_effect", "POP!! POP!! POP!!")]),
        ("standard", H, "Hisoka pulls the severed head back through the crowd.", []),
        ("standard", M, "Machi watches Hisoka from among the spectators.", [s("no_speaker", "sound_effect", "KOFF")]),
        ("standard", H, "Close-up of Hisoka's narrowed eye.", []),
    ],
    6: [
        ("standard", H, "Hisoka looks over the arena as people move through the stands.", []),
        ("standard", M, "Close-up of Machi watching the fight.", []),
        ("standard", H, "Close-up of Hisoka's bloodied face.", []),
        ("standard", H, "Hisoka grips the severed head.", [s("no_speaker", "sound_effect", "ZNG")]),
        ("standard", H, "Hisoka hurls the severed head through a line of attackers.", [s(H, "thought", "HE GOT AWAY... ♠")]),
        ("standard", H, "Hisoka drops back into the crowd.", [s(H, "thought", "... ☠"), s(H, "thought", "INTO THE CROWD AGAIN!!"), s("no_speaker", "sound_effect", "BAM")]),
        ("standard", H, "Hisoka strikes several nearby attackers in rapid succession.", [s("no_speaker", "sound_effect", "POP POP POP")]),
    ],
    7: [
        ("standard", H, "Hisoka faces an attacker while considering Chrollo's next action.", [s(H, "thought", "IF I ANNIHILATE THESE GUYS, HE WON'T NEED TO MAINTAIN THE STAMP..."), s(H, "thought", "THEN HE'LL GO BACK TO MAKING COPIES WITH THE BOOKMARKED GALLERY FAKE..."), s(H, "thought", "THE WORST KIND OF LOOP. ☠")]),
        ("standard", H, "Dark panels accompany Hisoka's count of remaining attackers.", [s(H, "thought", "FIVE MORE...!"), s(H, "thought", "FOUR...")]),
        ("standard", H, "A fallen attacker lies on the floor as Hisoka continues counting.", [s(H, "thought", "THREE..."), s(H, "thought", "TWO...")]),
        ("standard", H, "Hisoka approaches another attacker.", [s(H, "thought", "ONE... ♥")]),
        ("standard", H, "Hisoka's eyes track movement across the arena.", []),
        ("standard", H, "Hisoka strikes an attacker with the severed head.", [s("no_speaker", "sound_effect", "FSH FSH")]),
    ],
    8: [
        ("standard", H, "Hisoka holds an attacker from behind while watching Chrollo's possible next move.", [s(H, "thought", "AS LONG AS THIS ONE EXISTS AND THE STAMP REMAINS, CHROLLO'S ACTIONS WILL BE LIMITED...!"), s(H, "thought", "HIS NEXT BEST..."), s(H, "thought", "...MOVE IS...")]),
        ("standard", H, "Hisoka lays out two possible sequences of Chrollo's abilities.", [s(H, "thought", "1) KEEP THE STAMP ACTIVATED, AND GIVE A NEW COMMAND TO THE WAITING PUPPETS, OR..."), s(H, "thought", "2) DEACTIVATE THE STAMP, AND MAKE MORE COPY PUPPETS WITH GALLERY FAKE..."), s(H, "thought", "AND THEN..."), s(H, "thought", "A) ACTIVATE THE STAMP AND ISSUE NEW COMMANDS, OR..."), s(H, "thought", "B) CHANGE HIS APPEARANCE USING CONVERT HANDS WITH HIS LEFT HAND.")]),
        ("standard", H, "Hisoka stands before the remaining crowd and several fallen bodies.", [s(H, "thought", "OPTION 1 IS POSSIBLE...! I HAVEN'T BEEN CRIPPLED YET... THERE MAY BE AS MANY AS 50 MORE PUPPETS REMAINING... IT'S LIKELY CHROLLO WILL CONTINUE WITH THE SAME STRATEGY TO WEAR ME DOWN UNTIL HIS VICTORY IS CERTAIN!!"), s(H, "thought", "OPTION 2 IS JUST AS LIKELY!! THE BIGGER THE ARMY, THE BETTER, AND HE CAN SLIP INTO THE CROWD AFTER B AND TAKE SOMEONE'S CLOTHES TO MAKE A NEW DISGUISE...!!")]),
        ("standard", H, "Hisoka feels that the attacker he is holding has gone limp.", [s(H, "thought", "!"), s(H, "thought", "THE STAMP IS GONE...!!"), s(H, "thought", "OPTION 2 IT IS!!"), s("no_speaker", "sound_effect", "FSSSH"), s("no_speaker", "sound_effect", "DROP")]),
    ],
    9: [
        ("standard", H, "Close-up of Hisoka's eyes looking sideways.", []),
        ("standard", H, "Hisoka shifts his gaze in the opposite direction.", []),
        ("standard", H, "Hisoka stands in the arena while assessing the crowd.", [s(H, "thought", "IF THE BOOKMARK IS HOLDING GALLERY FAKE WHILE HE HIDES, HE DOESN'T HAVE TO HOLD THE BOOK... BUT THE AUDIENCE KNOWS WHAT HE LOOKS LIKE NOW AND WILL PANIC ON SIGHT, SO MAKING COPIES CARRIES A RISK..."), s(H, "thought", "BUT I DON'T WANT HIM TO SHUT OFF THE COPIES AND MOVE ON TO PLAN B / CONVERT HANDS!! IT WILL BE DIFFICULT TO SPOT CHROLLO IN THIS CHAOS WHEN HE LOOKS LIKE SOMEONE ELSE... ♠")]),
        ("standard", H, "Horizontal speed lines frame Hisoka's search.", [s(H, "thought", "I MUST..."), s(H, "thought", "WHERE IS HE...?!"), s(H, "thought", "FIND HIM FIRST...!!")]),
        ("standard", H, "Close-up of Hisoka's widened eyes.", [s(H, "thought", "IF HE MAKES COPIES..."), s(H, "thought", "...WHILE ON THE MOVE...")]),
        ("standard", f"{H};crowd", "Hisoka scans spectators moving through the stands.", [s(H, "thought", "...THEN HE'S BOUND TO GO WHERE..."), s(H, "thought", "...HE HAS COPIES ALREADY ON STANDBY!!")]),
        ("standard", "crowd", "A group of spectators stands together in the lower seats.", []),
        ("standard", "crowd", "Another group of spectators stands together nearby.", []),
        ("standard", "", "An impact burst appears against a field of speed lines.", []),
    ],
    10: [
        ("standard", f"{H};crowd", "Hisoka runs up the arena steps toward the upper seating.", [s(H, "thought", "THAT WAY HE CAN PRODUCE MORE COPIES..."), s(H, "thought", "...AND ALSO STAMP THE PREVIOUS PUPPETS...!!")]),
        ("standard", M, "Machi looks toward Hisoka's path.", []),
        ("standard", H, "Close-up of Hisoka running with a slight smile.", []),
        ("standard", f"{M};crowd", "Machi runs through spectators along the arena aisle.", []),
    ],
    11: [
        ("standard", H, "Hisoka swings the severed head while running.", [s("no_speaker", "sound_effect", "SHOOM")]),
        ("standard", M, "Machi strikes a spectator while moving through the crowd.", [s("no_speaker", "sound_effect", "SMASH")]),
        ("standard", "crowd", "Spectators jostle through the stands.", [s("no_speaker", "sound_effect", "SHP SHP SHP")]),
        ("standard", "crowd", "A cord stretches across spectators as objects fly overhead.", [s("crowd", "dialogue", "WHOA!"), s("crowd", "dialogue", "AIEEE!")]),
        ("standard", f"{M};crowd", "Machi runs between startled spectators.", [s("crowd", "dialogue", "WAH!"), s("crowd", "dialogue", "GAH!")]),
        ("standard", M, "Close-up of Machi's clenched gloved hand.", []),
        ("standard", M, "Close-up of Machi's boot stepping forward.", []),
        ("standard", H, "Close-up of Hisoka watching Machi.", [s(H, "thought", "IF...")]),
    ],
    12: [
        ("standard", f"{H};crowd", "Hisoka looks down over the crowd and arena floor.", [s(H, "thought", "THE PAGE CHROLLO HAS OPEN IN HIS POCKET ISN'T ORDER STAMP OR CONVERT HANDS, BUT BLACK VOICE ♠"), s(H, "thought", "...THAT MEANS HE'S HOLDING THE CELL PHONE AND THE ANTENNA CONCEALED IN HIS LEFT HAND...!!")]),
        ("standard", H, "Hisoka turns while keeping space from an approaching attacker.", [s(H, "thought", "I HAVE TO KEEP MY DISTANCE... BUT, IF I'M RIGHT, CHROLLO CAN ONLY BLOCK WITH HIS BODY... ♣"), s(H, "thought", "HARDLY A SITUATION HE DESIRES!")]),
        ("standard", M, "Machi launches herself toward Hisoka.", [s(H, "thought", "THEN..."), s("no_speaker", "sound_effect", "OMSHO")]),
        ("standard", H, "Hisoka watches the incoming attack.", [s(H, "thought", "THERE'S NO HOLDING BACK!!"), s(H, "thought", "DID MY COUNTER-ATTACK..."), s(H, "thought", "...SCREW UP HIS PLANS...!!?")]),
        ("standard", f"{H};{M}", "Machi flies feet-first toward Hisoka as he extends one arm.", [s("no_speaker", "sound_effect", "WSH")]),
        ("standard", H, "Close-up of Hisoka smiling.", [s(H, "thought", "YES..."), s(H, "thought", "THAT WAY... ♥")]),
    ],
    13: [
        ("standard", H, "Hisoka closes both fists.", [s(H, "thought", "GUM..."), s(H, "thought", "...SHRINK!!")]),
        ("standard", f"{H};{M};crowd", "Hisoka releases aura attached to fleeing people and the floor.", [s(H, "thought", "RELEASE GUM..."), s(H, "thought", "...FROM THE FLOOR!!!")]),
        ("standard", M, "Close-up of Machi reacting to Hisoka's move.", []),
    ],
    14: [
        ("standard", f"{H};{M};crowd", "A diagram shows fleeing people anchored with Bungee Gum as Hisoka and Machi run.", [s("crowd", "dialogue", "RUN!"), s(M, "dialogue", "STICK THE BUNGEE GUM ON THE BACKS OF THE FLEEING PEOPLE AND TO THE FLOOR..."), s(H, "dialogue", "STOP!"), s(M, "dialogue", "NO!"), s(H, "thought", "...AND MY HUMAN BULLETS WILL DO THE WORK TO STORE THEIR OWN POTENTIAL ENERGY... ♥"), s("no_speaker", "sound_effect", "STRETCH")]),
        ("standard", f"{M};crowd", "Machi runs among people pulled backward by stretched aura.", [s("no_speaker", "sound_effect", "SLAM SLAM SLAM SLAM SLAM SLAM")]),
        ("standard", f"{H};{M};crowd", "Hisoka leaps aside as the released people fly toward Machi.", []),
    ],
    15: [
        ("standard", H, "Hisoka throws the severed head like a ball.", []),
        ("standard", "", "The severed head strikes the floor.", []),
        ("standard", M, "Machi looks up at the incoming head.", []),
        ("standard", M, "Machi lunges aside as the head passes her.", []),
        ("standard", f"{H};{M}", "Hisoka extends his hand toward Machi after the head misses her.", [s(M, "dialogue", "WHOA, HE MISSED?!"), s(M, "dialogue", "HISOKA LOST A GOLDEN OPPORTUNITY!!"), s(H, "dialogue", "NO. ♪")]),
        ("standard", H, "Hisoka holds up his hand and smiles.", [s(H, "dialogue", "I ONLY PUT ASIDE WHAT I NO LONGER NEED. ♥")]),
    ],
    16: [
        ("standard", f"{H};{M}", "Hisoka pulls the severed head back toward Machi with Bungee Gum.", []),
        ("standard", H, "Close-up of Hisoka speaking while controlling the gum.", [s(H, "dialogue", "IT WAS ALREADY ON THERE..."), s(H, "dialogue", "...WHEN I SENT THE AUDIENCE FLYING...!!")]),
        ("standard", M, "Machi turns toward the returning head.", []),
        ("standard", M, "A dark panel contains Machi's reaction.", [s(M, "thought", "NO... IT'S IMPOSSIBLE...!!"), s(M, "thought", "WHEN?!")]),
        ("standard", H, "Hisoka clenches his fist.", [s(H, "thought", "SHRINK!!")]),
    ],
    17: [
        ("standard", f"{H};{M}", "Hisoka contracts the gum and pulls the severed head toward Machi.", [s("no_speaker", "sound_effect", "SHOOM")]),
        ("standard", H, "Hisoka pulls with his extended hand.", []),
        ("standard", f"{M};crowd", "The severed head strikes Machi among nearby spectators.", [s("no_speaker", "sound_effect", "BASH")]),
    ],
    18: [
        ("standard", f"{H};{M}", "Hisoka pulls Machi upward with aura lines extending from both hands.", []),
        ("standard", H, "Close-up of Hisoka pulling with his arm.", [s("no_speaker", "sound_effect", "WSH")]),
        ("standard", H, "Hisoka braces as the aura pulls taut.", [s("no_speaker", "sound_effect", "WHM")]),
        ("standard", H, "Close-up of Hisoka's lowered face.", []),
        ("standard", f"{H};{M}", "Machi is dragged toward Hisoka through a cloud of debris.", [s("no_speaker", "sound_effect", "KRAK KRAK KRASH")]),
        ("standard", f"{H};{M}", "Hisoka slams Machi into the arena wall.", []),
        ("standard", H, "Hisoka stands holding the severed head.", [s("no_speaker", "sound_effect", "FSSSH")]),
    ],
    19: [
        ("standard", "temp_ch354_convert_hands_copy", "A bearded man lies against the damaged wall.", [s(H, "thought", "IT'S NOT HIM!!")]),
        ("standard", f"{H};temp_ch354_convert_hands_copy", "Hisoka looks down at the bearded man.", [s(H, "thought", "HE MADE A COPY OF HIMSELF WITH RIGHT-HANDED CONVERT HANDS AND MANIPULATED HIM...?! WITH THE BOOKMARK ON CONVERT HANDS?!")]),
        ("standard", H, "Hisoka holds a broken control antenna beside his face.", [s(H, "thought", "IN CONJUNCTION WITH BLACK VOICE?!"), s(H, "thought", "BUT THEN...")]),
        ("standard", f"{H};temp_ch354_convert_hands_copy", "Hisoka looks toward the copy as debris falls nearby.", [s(H, "thought", "...WHY..."), s(H, "thought", "...IS THIS HERE...?!")]),
        ("standard", H, "Close-up of Hisoka's eye.", []),
        ("standard", H, "Hisoka snaps his fingers and invokes an ability.", [s(H, "thought", "THE SUN AND MOON!!"), s(H, "thought", "A FAKE OUT... ♣"), s("no_speaker", "sound_effect", "SNAP")]),
        ("standard", H, "Hisoka examines the broken antenna in his hand.", [s(H, "thought", "THE REAL TROUBLE IS... NOT THAT A MARK PLACED ON ME WOULD BE PERMANENT UNTIL IT EXPLODES..."), s(H, "thought", "BUT THAT A MARKED PUPPET WON'T VANISH!!")]),
    ],
}


def main():
    db = sqlite3.connect(DB)
    db.execute("PRAGMA foreign_keys=ON")
    with db:
        db.execute("DELETE FROM text_segments WHERE panel_id IN (SELECT panel_id FROM panels WHERE chapter=354)")
        db.execute("DELETE FROM panels WHERE chapter=354")
        db.execute(
            "INSERT OR REPLACE INTO chapters(chapter,title,page_count,edition,language) VALUES(354,?,?,?,?)",
            ("Head", 19, "", "en"),
        )
        for page in range(1, 20):
            for order, (panel_type, chars, visual, segs) in enumerate(P[page], 1):
                pid = f"ch354-p{page:02d}-{order:02d}"
                db.execute(
                    """INSERT INTO panels(panel_id,chapter,page_start,page_end,panel_order,panel_types,characters_on_panel,location,visual_description,review_status,silent_panel)
                       VALUES(?,354,?,?,?,?,?,?,?,'needs_review',?)""",
                    (pid, page, page, order, panel_type, chars, LOC, visual, int(not segs)),
                )
                for i, (speaker, mode, text) in enumerate(segs, 1):
                    db.execute(
                        "INSERT INTO text_segments(panel_id,segment_order,speaker,mode,text) VALUES(?,?,?,?,?)",
                        (pid, i, speaker, mode, text),
                    )
    panels = db.execute("SELECT COUNT(*) FROM panels WHERE chapter=354").fetchone()[0]
    segments = db.execute(
        "SELECT COUNT(*) FROM text_segments t JOIN panels p USING(panel_id) WHERE p.chapter=354"
    ).fetchone()[0]
    print(f"Seeded chapter 354: {panels} panels, {segments} text segments")


if __name__ == "__main__":
    main()
