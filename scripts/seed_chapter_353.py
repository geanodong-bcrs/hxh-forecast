#!/usr/bin/env python3
"""Prefill Hunter x Hunter chapter 353 for review in the local annotator."""

import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "private/story/story_annotations.sqlite"
H = "char_hisoka_morow"
C = "char_chrollo_lucilfer"
LOC = "Heavens Arena — spectator stands"


def s(speaker, mode, text):
    return speaker, mode, text


# Panels are ordered right-to-left, then top-to-bottom.
P = {
1: [
 (H,"Hisoka walks through spectators leaving their seats.",[s(H,"thought","THE ANTENNAS ARE GONE... ♦")]),
 (H,"Hisoka looks across the moving crowd.",[s(H,"thought","I THOUGHT SHAL'S ANTENNAS WERE REAL OBJECTS...?")]),
 (H,"Hisoka continues through the aisle.",[s(H,"thought","HE MUST'VE REELED THEM IN WITH A FISHING LINE OR SOMETHING... ♣")]),
 (f"{H};crowd","Spectators rush toward the exits while Hisoka stands among them.",[s("temp_ch352_commentator","dialogue","PEOPLE!! PLEASE, DO NOT PANIC!!"),s("temp_ch352_commentator","dialogue","IT'S DANGEROUS TO RUSH THE EXITS ALL AT ONCE!!")]),
],
2: [
 ("crowd","Spectators move through the stands.",[]),
 (H,"Close-up of Hisoka's eyes.",[s(H,"thought","GALLERY FAKE IS ACTIVATED...!")]),
 ("crowd","Spectators pass one another in the aisle.",[]),
 ("crowd","Rows of spectators react from the stands.",[]),
 ("crowd","More spectators look toward the arena.",[]),
 (H,"Hisoka watches the crowd from the aisle.",[s(H,"thought","THEN CONVERT HANDS MUST'VE BEEN DEACTIVATED...!!")]),
 (f"{H};crowd","Hisoka stands amid spectators moving in different directions.",[s(H,"thought","HE MUST'VE TAKEN SOMEONE ELSE'S CLOTHES FIRST TO DISGUISE HIMSELF...!! ♣"),s(H,"thought","WHERE IS HE...?!")]),
],
3: [
 ("crowd","Several spectators turn and move with stiff expressions.",[]),
 (H,"Hisoka notices the spectators.",[s(H,"thought","WHAT'S GOING ON?!")]),
 (f"{H};crowd","A group of spectators rushes toward Hisoka.",[s("temp_ch352_commentator","dialogue","THE AUDIENCE MEMBERS..."),s("temp_ch352_commentator","dialogue","...ARE ATTACKING HISOKA!!!")]),
],
4: [
 (f"{H};crowd","A large group of spectators charges toward Hisoka.",[s(H,"thought","OPEN BOOK TO GALLERY FAKE"),s(H,"thought","↓ BOOKMARK"),s(H,"thought","↓ CREATE A CROWD OF COPIES"),s(H,"thought","↓ ACTIVATE ORDER STAMP"),s(H,"thought","↓ COMMAND THEM TO ‘BREAK HISOKA’"),s(H,"thought","I SEE. ♦"),s(H,"thought","EVERYONE IN THE AUDIENCE HERE KNOWS WHO I AM... ♣")]),
 (f"{H};crowd","Hisoka faces a dense mass of approaching spectators.",[s(H,"thought","ABOUT 30 PUPPETS THAT WON'T STOP UNTIL THEY'RE BEHEADED..."),s(H,"thought","AT CHROLLO'S SPEED, HE MIGHT MAKE EVEN MORE...?"),s(H,"thought","THERE MUST BE MORE PUPPETS THAT HAVEN'T BEEN GIVEN COMMANDS YET...!!"),s(H,"thought","I SHOULD BIDE MY TIME UNTIL THERE ARE FEWER PEOPLE RUNNING ABOUT...!! ♦")]),
],
5: [
 (f"{H};crowd","Hisoka runs ahead of a pursuing crowd.",[s(H,"thought","ACTIVATE!!")]),
 (H,"Hisoka accelerates through the stands.",[]),
 (H,"Hisoka leaps high above the spectators.",[s("temp_ch352_commentator","dialogue","WHOA, HISOKA JUMPS HIGH TO AVOID THEM!!")]),
 (H,"Close-up of Hisoka reacting.",[s(H,"thought","!!")]),
],
6: [
 (f"{H};crowd","A mass of spectators leaps after Hisoka across the stands.",[]),
 (f"{H};crowd","Hisoka remains airborne as several spectators reach toward him.",[]),
],
7: [
 (f"{H};C","Chrollo appears directly behind Hisoka while holding Skill Hunter.",[]),
 (f"{H};{C}","Chrollo swings Skill Hunter into Hisoka.",[s("no_speaker","sound_effect","BASH")]),
],
8: [
 (f"{H};{C}","Close-up of Chrollo striking Hisoka's head with the book.",[s("no_speaker","sound_effect","KRAK KRAK KRAK KRAK KRAK KRAK")]),
 (f"{H};{C};crowd","Hisoka falls toward the spectators as Chrollo moves away.",[s(H,"thought","HE WAS GOING FOR MY LEFT FLANK!!"),s(H,"thought","HOW COULD HE MODIFY HIS ATTACK ANGLE FROM THERE...?!")]),
],
9: [
 (H,"Hisoka twists his body in midair.",[s(H,"thought","I LOVE IT... ♥")]),
 (f"{H};crowd","Hisoka lands against the edge of the arena as the pursuing crowd descends.",[s("no_speaker","sound_effect","SLAM")]),
],
10: [
 (f"{H};crowd","Spectators close in around Hisoka from all sides.",[]),
 (H,"Hisoka braces among the surrounding attackers.",[]),
],
11: [
 (f"{H};crowd","Hisoka spins while spectators reach toward him.",[]),
 (f"{H};crowd","Hisoka kicks several attackers away.",[]),
 (f"{H};crowd","Hisoka strikes another group rushing from the side.",[]),
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
 (f"{H};{C};crowd","Chrollo passes through the crowd toward Hisoka.",[s(H,"thought","HE'S WAITING FOR GUARANTEED HITS...!!"),s(H,"thought","COMING IN FOR A STRIKE, THEN SPRINGING AWAY, TRYING TO LAND MORTAL BLOWS... ♦")]),
 (H,"Hisoka forces his way through the attackers.",[s(H,"thought","AND HE'S FORCING ME INTO THE THRONG OF PUPPETS..."),s(H,"thought","SO COLD-BLOODED AND CALCULATING. ♥")]),
 (H,"Hisoka pushes through reaching arms.",[s(H,"thought","HE WON'T BE ABLE TO CREATE NEW PUPPETS WHILE HE'S CONTROLLING THE CURRENT CROP. ♣"),s(H,"thought","I'LL HAVE TO DECREASE THEIR NUMBERS ONE BY ONE. ♦")]),
 (f"{H};crowd","Hisoka strikes an attacker at close range.",[]),
 (f"{H};crowd","Hisoka cuts another attacker while turning.",[]),
],
14: [
 (f"{H};crowd","Hisoka is pulled backward among raised arms.",[s(H,"thought","ADDING THE EXTRA STEP MEANS FALLING FURTHER BEHIND..."),s(H,"thought","REGROUPING WILL EVENTUALLY BECOME NECESSARY, RIGHT?")]),
 (f"{H};crowd","Attackers crowd around Hisoka.",[]),
 (f"{C};crowd","Chrollo steps in beside the attackers.",[s(H,"thought","AND THAT'S WHEN A STRIKE COMES...!!")]),
],
15: [
 (f"{H};crowd","Hisoka is struck while surrounded by attackers.",[]),
 (H,"Close-up of Hisoka looking upward.",[]),
 (f"{H};crowd","Hisoka twists between approaching attackers.",[]),
 (f"{H};crowd","A cord loops around an attacker's head near Hisoka.",[]),
 (H,"Close-up of Hisoka smiling.",[]),
 (f"{C};crowd","Chrollo crouches with Skill Hunter among the attackers.",[]),
],
16: [
 (f"{H};crowd","Hisoka strikes an attacker at close range.",[]),
 (f"{H};crowd","Hisoka charges through the surrounding group.",[]),
 (f"{H};crowd","Hisoka slips beneath reaching arms.",[]),
 (f"{H};{C}","Hisoka looks up at Chrollo crouching above him.",[]),
 (H,"Close-up of Hisoka lying back.",[s(H,"thought","HE KNOWS..."),s(H,"thought","...WHAT I'LL DO NEXT....!")]),
 (H,"Close-up of Hisoka's face.",[s(H,"thought","SO... ♥")]),
],
17: [
 (H,"A bright panel contains Hisoka's declaration.",[s(H,"thought","ACTIVATE BUNGEE GUM! ♥")]),
 (f"{H};crowd","Small pieces of aura attach to several attackers.",[s(H,"thought","SHRINK!!!")]),
 (f"{H};crowd","The attached attackers are pulled rapidly through the air.",[s("no_speaker","sound_effect","ZOOOOM")]),
],
18: [
 (H,"Hisoka watches from below.",[]),
 (C,"Chrollo watches the bodies being pulled.",[s(C,"dialogue","I WAS WATCHING YOU.")]),
 (f"{H};crowd","Several attackers twist together through the air.",[s("no_speaker","sound_effect","TWIST")]),
 (f"{C};crowd","Chrollo drives a bundled mass of attackers downward.",[]),
],
19: [
 (f"{H};{C};crowd","Chrollo slams the bundled bodies into Hisoka.",[s("no_speaker","sound_effect","BAM")]),
 (H,"Hisoka lies beneath the impact with blood spraying upward.",[s(H,"dialogue","I KNOW. ♥")]),
],
}


def main():
    db = sqlite3.connect(DB)
    db.execute("PRAGMA foreign_keys=ON")
    with db:
        db.execute("DELETE FROM text_segments WHERE panel_id IN (SELECT panel_id FROM panels WHERE chapter=353)")
        db.execute("DELETE FROM panels WHERE chapter=353")
        db.execute("INSERT OR REPLACE INTO chapters(chapter,title,page_count,edition,language) VALUES(353,?,?,?,?)", ("Cold-Blooded",19,"","en"))
        for page in range(1,20):
            for order,(chars,visual,segs) in enumerate(P[page],1):
                pid=f"ch353-p{page:02d}-{order:02d}"
                db.execute("""INSERT INTO panels(panel_id,chapter,page_start,page_end,panel_order,panel_types,characters_on_panel,location,visual_description,review_status,silent_panel)
                              VALUES(?,353,?,?,?,'standard',?,?,?,'needs_review',?)""",
                           (pid,page,page,order,chars,LOC,visual,int(not segs)))
                for i,(speaker,mode,text) in enumerate(segs,1):
                    db.execute("INSERT INTO text_segments(panel_id,segment_order,speaker,mode,text) VALUES(?,?,?,?,?)",(pid,i,speaker,mode,text))
    panels=db.execute("SELECT COUNT(*) FROM panels WHERE chapter=353").fetchone()[0]
    segments=db.execute("SELECT COUNT(*) FROM text_segments t JOIN panels p USING(panel_id) WHERE p.chapter=353").fetchone()[0]
    print(f"Seeded chapter 353: {panels} panels, {segments} text segments")


if __name__ == "__main__":
    main()
