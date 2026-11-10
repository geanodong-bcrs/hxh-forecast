#!/usr/bin/env python3
"""Prefill Hunter x Hunter chapter 355 for review in the local annotator."""

import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "private/story/story_annotations.sqlite"
H = "char_hisoka_morow"
C = "char_chrollo_lucilfer"
COMMENTATOR = "temp_heavens_arena_commentator"
LOC = "Heavens Arena — spectator stands"


def s(speaker, mode, text):
    return speaker, mode, text


# (page_end, panel_type, characters, visual description, text segments)
# Panels follow right-to-left, then top-to-bottom manga reading order.
P = {
    1: [
        (1, "standard", C, "Chrollo displays marks on both hands while explaining Sun and Moon.", [s(C, "dialogue", "THE SUN AND MOON: PAIRED DESTRUCTION."), s(C, "dialogue", "AS YOU CAN SEE, IT USES BOTH HANDS.")]),
        (1, "standard", C, "Chrollo holds Skill Hunter open while one hand rests on its edge.", [s(C, "dialogue", "WHEN I STOLE AN ABILITY THAT REQUIRED BOTH HANDS..."), s(C, "dialogue", "...I WAS FORCED TO MAKE SOME ADJUSTMENTS.")]),
        (1, "standard", H, "Close-up of Hisoka's smiling mouth.", [s(H, "thought", "HEH HEH...")]),
        (1, "standard", f"{H};crowd", "Hisoka stands before the arena seats while holding a severed head.", [s(H, "thought", "THE EXPLANATION GOT ME TO ASSUME THAT, LIKE GALLERY FAKE, AN ABILITY THAT REQUIRES BOTH HANDS MEANS THAT IT CAN'T BE USED IN CONJUNCTION WITH ANOTHER ABILITY..."), s(H, "thought", "BUT THE SUN AND MOON CAN BE USED WHEN ANOTHER ABILITY IS BOOKMARKED AND THE PAGE IS OPENED WITH HIS RIGHT HAND... IN OTHER WORDS, HE CAN IMPRINT THE SUN WITH JUST HIS LEFT HAND...!!")]),
        (1, "standard", H, "Close-up of Hisoka's face in profile.", [s(H, "thought", "WHEN THE COPY VANISHES, YOU MAY CONCLUDE THAT GALLERY FAKE HAS BEEN DEACTIVATED."), s(H, "thought", "AGAIN..."), s(H, "thought", "HE NEVER SAID 'YOU MAY CONCLUDE THAT GALLERY FAKE IS STILL IN USE WHILE THE COPIES REMAIN'... ♣")]),
        (1, "standard", H, "Hisoka walks across the arena floor.", [s(H, "thought", "EVERYTHING SO FAR..."), s(H, "thought", "...IS TO CONFIRM MY UNDERSTANDING OF CHROLLO'S EXPLANATIONS... ♦")]),
    ],
    2: [
        (2, "standard", f"{H};temp_ch354_convert_hands_copy;crowd", "Hisoka stands beside the crushed copy while a diagram contrasts two ability sequences.", [s(H, "thought", "INSTEAD OF..."), s(H, "thought", "ACTIVATE GALLERY FAKE ← BOOKMARK (CLOSE THE BOOK) ← CREATE A CROWD OF COPIES ← ACTIVATE ORDER STAMP ← COMMAND THEM TO 'BREAK HISOKA'"), s(H, "thought", "IT'S ACTUALLY..."), s(H, "thought", "ACTIVATE GALLERY FAKE ← BOOKMARK (CLOSE THE BOOK) ← CREATE A CROWD OF COPIES ← ACTIVATE THE SUN AND MOON ↓ IMPRESS THE SUN MARK ON THE COPIES ↓ DEACTIVATE (EITHER OR BOTH) A MARKED COPY IS 'PROTECTED' BY POST-DEATH INTENSIFIED NEN AND WON'T VANISH ↓ ACTIVATE ORDER STAMP ↓ COMMAND THEM TO 'BREAK HISOKA'"), s(H, "thought", "SO THAT'S HOW IT WAS...")]),
        (2, "standard", H, "Close-up of Hisoka's narrowed eyes.", [s(H, "thought", "WITH THE SUN AND MOON AS AN ADDITIONAL STEP, THE NUMBER OF PUPPETS SHOULD BE FEWER THAN MY INITIAL CALCULATIONS..."), s(H, "thought", "MAYBE... 20 TO 30 MORE...?")]),
    ],
    3: [
        (3, "standard", H, "Hisoka jumps upward while holding the severed head.", [s(H, "thought", "BUT IF I TAKE TOO LONG TO FIND HIM, HE'LL KEEP MAKING NEW PUPPETS...!!!"), s(H, "thought", "...AT A PACE OF ONE EVERY COUPLE SECONDS!!"), s("no_speaker", "sound_effect", "SHUP")]),
        (3, "standard", "crowd", "Debris and smoke rise from the arena floor.", [s("no_speaker", "sound_effect", "SHF")]),
        (3, "standard", H, "Close-up of Hisoka looking upward.", []),
        (3, "standard", f"{H};crowd", "Hisoka stands in the arena holding the severed head as spectators remain in the stands.", [s(H, "thought", "MOST OF THE AUDIENCE HAS SURPRISINGLY STAYED PUT... I CAN'T TELL IF ANY OF THE PEOPLE TAKING CARE OF EACH OTHER ARE CHROLLO."), s(H, "thought", "THOSE WHO THINK THEY'RE OUT OF RANGE ARE PRETTY CALM... ♦"), s(COMMENTATOR, "dialogue", "WHAT NOW?! HISOKA STANDS IN THE MIDDLE OF THE ARENA!!"), s(COMMENTATOR, "dialogue", "HE'S LOOKING FOR CHROLLO, WHO'S DISAPPEARED!!"), s(H, "thought", "CHROLLO CAN PREPARE ALL HE WANTS RIGHT NOW... ♦"), s(H, "thought", "BUT HE CAN'T EXACTLY TAKE HIS TIME...!")]),
    ],
    4: [
        (4, "standard", f"{H};crowd", "Hisoka looks toward spectators moving through the stands.", [s(H, "thought", "IN TEN MINUTES OR SO, PARAMEDICS AND SECURITY PERSONNEL WILL COME POURING IN...! ♣"), s(H, "thought", "HE HAS TO FINISH THIS BEFORE THEN... OR THE WAITING PUPPETS WILL BE MISTAKEN FOR THE INJURED AND BE CARRIED OUT! ♦")]),
        (4, "standard", "temp_sun_moon_puppet;crowd", "A marked puppet stands among spectators.", [s(H, "thought", "THIS NEXT ATTACK WILL BE THE REAL THING... ♣")]),
        (4, "standard", "temp_sun_moon_puppet", "Close-up of a marked puppet's face.", [s(H, "thought", "HE'LL MAKE EXPLOSIVE PUPPETS WITH THE SUN AND MOON AT MAXIMUM POWER AND TRY TO DETONATE THEM AT CLOSE RANGE...!!")]),
        (4, "standard", H, "Close-up of Hisoka's left hand holding cards.", [s(H, "thought", "NO MATTER HOW MANY THERE ARE..."), s(H, "thought", "...I CAN'T LET THE PUPPETS CLOSE IN ON ME... ♠")]),
        (4, "standard", H, "Hisoka stands holding the severed head while spectators shout around him.", [s("crowd", "sound_effect", "RAAAH YADDA YADDA RAAH EEEEEK")]),
    ],
    5: [
        (5, "standard", "crowd", "Marked spectators rush down the arena steps.", [s("crowd", "sound_effect", "WAAAAA EEEEEK RAAAH")]),
        (5, "standard", "crowd", "More marked spectators run through the stands.", [s("crowd", "sound_effect", "RAAAH EEEEEK RAAAH")]),
        (5, "standard", f"{H};{COMMENTATOR};crowd", "Hisoka stands in the arena as the commentator addresses the panicking audience.", [s(COMMENTATOR, "dialogue", "PLEASE, DO NOT PANIC!!"), s(COMMENTATOR, "dialogue", "A STAMPEDE WILL BE VERY DANGEROUS!!"), s("crowd", "sound_effect", "WAAAAH RAAAH EEEEEK")]),
        (5, "standard", H, "Close-up of Hisoka looking across the stands.", [s(H, "thought", "HE'S SENDING THE PUPPETS ON A RAMPAGE TO CONFUSE THE CROWD...!!"), s(H, "thought", "IS HE SETTING UP SOMETHING ELSE IN THIS CHAOS...?")]),
    ],
    6: [
        (6, "standard", f"{COMMENTATOR};crowd", "The commentator sits at her desk while spectators press around her.", [s(COMMENTATOR, "dialogue", "PARAMEDICS AND SECURITY ARE ON THEIR WAY!!"), s(COMMENTATOR, "dialogue", "PLEASE TRY TO STAY IN YOUR SEATS!!"), s("crowd", "sound_effect", "YADDA YADDA YADDA")]),
        (6, "standard", COMMENTATOR, "The commentator pulls off her headset.", [s("no_speaker", "sound_effect", "RIP")]),
        (6, "standard", H, "Close-up of Hisoka listening.", [s("crowd", "dialogue", "BREAK HISOKA...!!")]),
        (6, "standard", H, "Hisoka looks toward the stands from the arena floor.", []),
        (6, "standard", f"{COMMENTATOR};crowd", "The commentator stands at her desk and addresses the audience without her headset.", [s(COMMENTATOR, "dialogue", "UHH, SORRY ABOUT THAT!!"), s(COMMENTATOR, "dialogue", "I APOLOGIZE FOR THAT BIASED STATEMENT DURING THE BROADCAST.")]),
        (6, "standard", H, "Close-up of Hisoka's eyes with an Order Stamp mark superimposed above them.", [s(H, "thought", "I SEE. ♥ HE ATTRACTED MY ATTENTION WITH THE BRAWL..."), s(H, "thought", "...AND USED THE P.R. SYSTEM TO SPEAK TO THE ENTIRE AUDIENCE..."), s(H, "thought", "...EFFICIENTLY GIVING A COMMAND TO ALL THE PUPPETS..."), s(H, "thought", "...AND MAKING IT EVEN EASIER TO HIDE...!!")]),
    ],
    7: [
        (7, "standard", "crowd", "Marked spectators look forward and hiss.", [s("crowd", "sound_effect", "SSH SSH SSH SSH")]),
        (7, "standard", "crowd", "Spectators rush down the arena steps.", [s("crowd", "sound_effect", "HSS HSS HSS")]),
        (7, "standard", "crowd", "A dense crowd runs toward the arena floor.", [s("crowd", "sound_effect", "HSSH HSSH HSSH HSSH HSSH")]),
        (7, "standard", "crowd", "Several spectators climb over the railing into the arena.", [s("crowd", "dialogue", "?!"), s("crowd", "dialogue", "WHAT'S GOING ON...?!"), s("no_speaker", "sound_effect", "DASH DASH DASH")]),
        (7, "standard", "crowd", "A large wave of spectators forces its way down the steps.", [s("crowd", "dialogue", "THE CROWD IS FORCING THEIR WAY IN?!"), s("crowd", "dialogue", "A LOT MORE THIS TIME?!"), s("crowd", "sound_effect", "VMM VMM VMM VMM VMM")]),
    ],
    8: [
        (9, "standard", f"{H};crowd", "A double-page view shows Hisoka facing spectators pouring from every section of the arena.", []),
    ],
    10: [
        (10, "standard", H, "Close-up of Hisoka grinning while raising the severed head.", []),
        (10, "standard", f"{H};crowd", "Hisoka swings the severed head into an approaching attacker.", [s("no_speaker", "sound_effect", "SHOOM")]),
    ],
    11: [
        (11, "standard", H, "Hisoka spreads Bungee Gum from the fingers of his left hand toward several attackers.", []),
        (11, "standard", "crowd", "Bungee Gum strands attach to a row of approaching attackers.", [s("no_speaker", "sound_effect", "PCH PCH PCH PCH SPLAT")]),
        (11, "standard", f"{H};crowd", "Hisoka pulls the attached attackers off balance while swinging the severed head.", [s("no_speaker", "sound_effect", "SHOOM")]),
    ],
    12: [
        (12, "standard", f"{H};crowd", "Hisoka twists a bundle of attackers together with Bungee Gum.", [s("no_speaker", "sound_effect", "TWIRL")]),
        (12, "standard", "crowd", "The bundled attackers collide with one another.", [s("no_speaker", "sound_effect", "BAM BAM BAM")]),
        (12, "standard", f"{H};crowd", "Hisoka runs while dragging the bundled attackers behind him.", [s("no_speaker", "sound_effect", "DM DM DM DM DM DM"), s("no_speaker", "sound_effect", "FSH")]),
        (12, "standard", f"{H};crowd", "Hisoka swings the bundled attackers into another group.", [s("no_speaker", "sound_effect", "FOOM")]),
    ],
    13: [
        (13, "standard", f"{H};crowd", "Hisoka swings the bundled attackers through the crowd.", [s("no_speaker", "sound_effect", "KABLAM")]),
        (13, "standard", f"{H};crowd", "The bundle strikes more attackers as Hisoka continues swinging it.", []),
        (13, "standard", f"{H};crowd", "The bundled attackers slam across the arena floor.", [s("no_speaker", "sound_effect", "SLAMSMASH")]),
    ],
    14: [
        (15, "standard", f"{H};{COMMENTATOR};crowd", "A double-page view shows Hisoka swinging a dense human hammer through hundreds of people rushing into the arena.", [s(COMMENTATOR, "dialogue", "WHAT THE?!"), s(COMMENTATOR, "dialogue", "A RIOT?! HUNDREDS OF AUDIENCE MEMBERS ARE RUSHING TO ATTACK HISOKA!!!"), s(COMMENTATOR, "dialogue", "AND HE'S BEATING THEM BACK WITH A HUMAN HAMMER!!!"), s(COMMENTATOR, "dialogue", "SMASH!!! SMASH!!!")]),
    ],
    16: [
        (16, "standard", "crowd", "An attacker is crushed against the arena floor.", [s("no_speaker", "sound_effect", "KRSPLAT")]),
        (16, "standard", f"{H};crowd", "Hisoka watches the approaching attackers while holding the human hammer behind him.", [s(H, "thought", "BROKEN ALREADY... ♦"), s(H, "thought", "THEY'RE TOO FRAGILE UNLESS THE WHOLE THING IS ENVELOPED IN AURA... ♠")]),
        (16, "standard", "temp_sun_moon_puppet", "A marked puppet runs toward Hisoka.", [s("no_speaker", "sound_effect", "DASH DASH DASH DASH DASH")]),
        (16, "standard", H, "Hisoka notices the marked puppet and releases part of the human hammer.", [s("no_speaker", "sound_effect", "POP!!")]),
        (16, "standard", f"{H};crowd", "Hisoka throws part of the human hammer toward the marked puppet and nearby attackers.", [s("no_speaker", "sound_effect", "POP!! POPPOPPOP!")]),
    ],
    17: [
        (17, "standard", f"{H};crowd", "Hisoka swings the remaining human hammer as marked attackers close in.", []),
        (17, "standard", H, "Hisoka moves aside while debris and attackers fly past.", [s("no_speaker", "sound_effect", "WHAM")]),
        (17, "standard", "temp_sun_moon_puppet", "A marked attacker is struck in the face.", [s("no_speaker", "sound_effect", "BASH BASH BASH")]),
        (17, "standard", f"{H};crowd", "Hisoka pulls Bungee Gum taut across the arena.", [s("no_speaker", "sound_effect", "SPLATT SPLATT"), s("no_speaker", "sound_effect", "TUG!!")]),
        (17, "standard", H, "Close-up of Hisoka's hand gripping stretched strands of Bungee Gum.", []),
        (17, "standard", f"{H};crowd", "Hisoka yanks attackers across the arena with Bungee Gum.", [s("no_speaker", "sound_effect", "BASH BASH BASH"), s("no_speaker", "sound_effect", "KRAK KRAK")]),
    ],
    18: [
        (18, "standard", "crowd", "Spectators watch the chaos from the stands while marked attackers run across the arena.", [s("crowd", "dialogue", "WOW, WHAT A RIOT."), s("crowd", "dialogue", "WHY ARE THEY RUSHING HISOKA?"), s("crowd", "dialogue", "CHROLLO'S CONTROLLING THEM, RIGHT?"), s("crowd", "dialogue", "WHOA, SEVERED ARM?!"), s("crowd", "sound_effect", "YADDA YADDA DM DM DM DM")]),
        (18, "standard", C, "A close-up shows the lower half of Chrollo's disguised face.", [s(C, "dialogue", "YES, RIGHT THERE.")]),
        (18, "standard", C, "Chrollo holds a phone with a face-shaped case and presses a numbered button.", [s(C, "dialogue", "NOW SQUAT."), s("no_speaker", "sound_effect", "BIP BIP")]),
        (18, "standard", H, "Close-up of Hisoka watching the attackers.", [s(H, "thought", "...BUT THEY STILL WON'T STOP UNLESS THEIR HEADS ARE DESTROYED...!!")]),
        (18, "standard", f"{H};crowd", "Hisoka swings the human hammer through another group of attackers.", [s(H, "thought", "I MAY KNOCK THEM BACK ALL DAY WITH THE HUMAN HAMMER...")]),
        (18, "standard", f"{H};crowd", "The human hammer strikes attackers at close range.", [s("no_speaker", "sound_effect", "POP!! POP!!")]),
    ],
    19: [
        (19, "standard", C, "Chrollo looks sideways while holding the phone behind him.", [s("no_speaker", "sound_effect", "BIP")]),
        (19, "floating", C, "A small inset shows Chrollo's eye beneath his disguise.", [s(C, "dialogue", "NOW.")]),
        (19, "standard", H, "Hisoka turns toward a sudden explosion.", [s("no_speaker", "sound_effect", "BOOM")]),
        (19, "standard", "crowd", "Spectators react with alarm.", []),
        (19, "standard", H, "Close-up of Hisoka's widened eye.", []),
        (19, "standard", H, "Hisoka's hand is torn apart by the explosion.", []),
    ],
}


def main():
    db = sqlite3.connect(DB)
    db.execute("PRAGMA foreign_keys=ON")
    with db:
        db.execute("DELETE FROM text_segments WHERE panel_id IN (SELECT panel_id FROM panels WHERE chapter=355)")
        db.execute("DELETE FROM panels WHERE chapter=355")
        db.execute(
            "INSERT OR REPLACE INTO chapters(chapter,title,page_count,edition,language) VALUES(355,?,?,?,?)",
            ("Detonation", 19, "", "en"),
        )
        for page_start in sorted(P):
            for order, (page_end, panel_type, chars, visual, segs) in enumerate(P[page_start], 1):
                page_label = f"{page_start:02d}" if page_end == page_start else f"{page_start:02d}-{page_end:02d}"
                pid = f"ch355-p{page_label}-{order:02d}"
                db.execute(
                    """INSERT INTO panels(panel_id,chapter,page_start,page_end,panel_order,panel_types,characters_on_panel,location,visual_description,review_status,silent_panel)
                       VALUES(?,355,?,?,?,?,?,?,?,'needs_review',?)""",
                    (pid, page_start, page_end, order, panel_type, chars, LOC, visual, int(not segs)),
                )
                for segment_order, (speaker, mode, text) in enumerate(segs, 1):
                    db.execute(
                        "INSERT INTO text_segments(panel_id,segment_order,speaker,mode,text) VALUES(?,?,?,?,?)",
                        (pid, segment_order, speaker, mode, text),
                    )

    panels = db.execute("SELECT COUNT(*) FROM panels WHERE chapter=355").fetchone()[0]
    segments = db.execute(
        "SELECT COUNT(*) FROM text_segments t JOIN panels p USING(panel_id) WHERE p.chapter=355"
    ).fetchone()[0]
    print(f"Seeded chapter 355: {panels} panels, {segments} text segments")


if __name__ == "__main__":
    main()
