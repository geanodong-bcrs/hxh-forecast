#!/usr/bin/env python3
"""Prefill Hunter x Hunter chapter 351 for review in the local annotator."""

import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "private/story/story_annotations.sqlite"
H = "char_hisoka_morow"
C = "char_chrollo_lucilfer"
R = "temp_ch351_referee"
LOC = "Heavens Arena — battle arena"


def s(speaker, mode, text):
    return speaker, mode, text


# characters, visual description, segments
P = {
1: [
 ("crowd", "Heavens Arena rises above a crowd approaching the venue.", [s("announcer","dialogue","LADIES AND GENTLEMEN!!! THE OPPONENT THE ELUSIVE ‘GRIM REAPER’ HAS PICKED FOR THIS FLOOR MASTER BATTLE...!!"),s("announcer","dialogue","HERE FOR HIS FIRST MATCH AS FLOOR MASTER!! HIS NAME IS..."),s("crowd","sound_effect","RAAH RAAH RAAH")]),
],
2: [
 (f"{H};{C};{R}", "Hisoka and Chrollo face each other across the arena with the referee between them.", [s("announcer","dialogue","CHROLLO-O-O-OH LUCI-III-FERRRRR!!!"),s("announcer","dialogue","VS.!"),s("announcer","dialogue","HISOKA-A-A-AH MO-O-O-O-O-RRRRO-O-O-O-OW!!!"),s("crowd","sound_effect","OOOOOH")]),
],
3: [
 (C, "Close-up of Chrollo looking forward.", [s("crowd","sound_effect","RAAH RAAH RAAH RAAH RAAH")]),
 (H, "Close-up of Hisoka smiling.", [s(H,"dialogue","FINALLY..."),s(H,"dialogue","...MY DREAM IS REALIZED. ♥"),s("crowd","sound_effect","RAAH")]),
 (f"{H};{C};{R}", "Hisoka and Chrollo stand beside the referee.", [s(H,"dialogue","I'VE WAITED THIS LONG—I DON'T WANT A FRIENDLY SPARRING MATCH. ♣"),s(C,"dialogue","I KNOW."),s(C,"dialogue","BEING PURSUED HAS BECOME ANNOYING."),s(C,"dialogue","THIS WILL BE...")]),
],
4: [
 (f"{H};{C}", "Close-ups of Chrollo and Hisoka smiling at one another.", [s(C,"dialogue","...A BATTLE TO THE DEATH."),s(H,"dialogue","OKAY. ♥"),s("crowd","sound_effect","OOOOOOOH")]),
 ("crowd", "The crowd raises its arms around the distant arena floor.", [s("announcer","dialogue","WOW!! FLOOR MASTER CHROLLO PROPOSES A BATTLE TO THE DEATH!! AND HISOKA CONSENTS!! MORTAL COMBAT IT IS!!"),s("announcer","dialogue","ONLY ONE WILL SURVIVE!! VICTORY IS WON THROUGH THE OTHER'S DEATH!!")]),
],
5: [
 (f"{H};{C};{R}", "The referee stands between Chrollo and Hisoka.", [s(R,"dialogue","THE USE OF WEAPONS IS ALLOWED."),s(R,"dialogue","FOR YOUR PRIDE AND HONOR...")]),
 (f"{H};{C}", "Narrow close-ups of Chrollo and Hisoka.", []),
 (R, "The referee raises one arm to begin the match.", [s(R,"dialogue","LET'S..."),s(R,"dialogue","FIGHT!")]),
],
6: [
 (H, "Hisoka reaches toward a playing card.", [s("no_speaker","sound_effect","VM")]),
 (C, "Chrollo opens Skill Hunter.", [s("no_speaker","sound_effect","VM")]),
 (f"{H};{C};{R}", "Hisoka and Chrollo move while the referee spreads his arms between them.", []),
 (C, "Close-up of Chrollo holding a small device.", []),
 (C, "Chrollo holds his open book.", []),
 (H, "Close-up of Hisoka watching Chrollo.", []),
],
7: [
 (f"{C};{R}", "The referee's face changes as Chrollo's hand approaches him.", [s(R,"dialogue","HUH?")]),
 (R, "Close-up of the referee's face.", []),
 (R, "The referee turns his head.", []),
 (C, "Chrollo watches the referee while holding his book.", []),
 (C, "Chrollo holds up a small human-shaped device.", [s(C,"dialogue","BLACK VOICE: ‘MOBILE FATE DIRECTOR.’"),s(H,"dialogue","I SEE... ♦")]),
 (f"{H};{C}", "A simplified drawing shows Chrollo running after Hisoka.", [s(H,"thought","HE'D LEFT ME HANGING AFTER THE EXORCISM..."),s(H,"thought","...IN ORDER TO GATHER HIS CARDS... ♪"),s(C,"dialogue","NO!"),s(H,"dialogue","C'MON! ♥")]),
],
8: [
 (C, "Chrollo holds the device and his open book.", [s("device","sound_effect","BIP BIP BIP BIP")]),
 (R, "The referee stares forward.", []),
 (R, "The referee raises a clenched hand.", []),
 (H, "Hisoka watches with a smile.", [s(H,"thought","HE HAS...")]),
 (H, "Hisoka looks closely at the antenna in Chrollo's hand.", [s(H,"thought","...ANOTHER ANTENNA...!!")]),
 (f"{H};{C};{R}", "The referee lunges toward Hisoka while Chrollo stands behind him.", [s("announcer","dialogue","?!"),s("announcer","dialogue","THE JUDGE?!"),s("announcer","dialogue","HE'S ATTACKING HISOKA TOGETHER WITH CHROLLO?!")]),
],
9: [
 (H, "Hisoka watches the referee approach.", [s(H,"thought","HE PLANS TO PIN ME WITH THE JUDGE..."),s(H,"thought","...AND STAB ME WITH THE ANTENNA...!!")]),
 (f"{H};{R}", "Hisoka strikes the charging referee.", [s("no_speaker","sound_effect","POW")]),
 (f"{H};{R}", "The referee's leg swings toward Hisoka.", [s(R,"dialogue","MY LEG...")]),
 (f"{H};{R}", "Hisoka throws the referee aside.", [s(H,"thought","HERE HE COMES!"),s("no_speaker","sound_effect","BASH")]),
 (R, "Close-up of the referee's startled face.", []),
 (f"{H};{R}", "The referee falls as Hisoka moves away.", [s(H,"dialogue","TSK... A FEINT...!!")]),
],
10: [
 (f"{H};{R}", "The controlled referee repeatedly stomps Hisoka.", [s(H,"thought","THE ADVANTAGE OF BEING A MANIPULATOR IS THAT IT'S ‘GAME OVER’ ONCE YOUR CONDITIONS ARE FULFILLED."),s(H,"thought","HE ONLY HAS ONE PHONE ♣ SO CAN HE MANIPULATE ONE PERSON? OR..."),s(H,"thought","...TWO AT ONCE? IT COULD BE POSSIBLE TO SEND COMMANDS THROUGH A GROUP TEXT!!"),s("announcer","dialogue","STOMP!!! STOMP!!! STOMP!!! STOMP!!! A SAVAGE STOMPING!!!"),s("no_speaker","sound_effect","BAM BAM BAM BAM BAM BAM BAM BAM")]),
 ("crowd", "Spectators react from the stands.", [s(H,"thought","PULL OUT THE ANTENNA OR KILL THE JUDGE, AND THE CONTROL PROBABLY ENDS..."),s(H,"thought","BUT IF HE CAN ONLY CONTROL ONE PERSON, THAT'S WHAT CHROLLO'S WAITING FOR...!")]),
],
11: [
 (f"{H};{C};{R}", "Hisoka uses Bungee Gum to pull Chrollo and the referee through the air.", [s(H,"thought","BUNGEE GUM: ‘ELASTIC LOVE’!!!"),s(H,"thought","CONTRACT AT MAX SPEED!!"),s("no_speaker","sound_effect","ZOOM")]),
 (f"{H};{C}", "A narrow inset shows Hisoka and Chrollo watching each other.", [s("no_speaker","sound_effect","FFT")]),
],
12: [
 (f"{H};{C};{R}", "Chrollo and the referee fly toward Hisoka as Hisoka moves forward.", [s("no_speaker","sound_effect","THUD"),s("no_speaker","sound_effect","FFT")]),
 (f"{C};{R}", "Chrollo and the referee move together.", [s("no_speaker","sound_effect","SHK SHK"),s("no_speaker","sound_effect","SHP SHP SHP")]),
 (H, "Close-up of Hisoka smiling.", [s(H,"thought","WAITING FOR HIS OPPORTUNITY WITH THE JUDGE AS HIS SHIELD... ♦"),s(H,"thought","IT'S THE BEST STRATEGY, WHETHER HE CAN CONTROL ONE OR MULTIPLE TARGETS. ♣")]),
 (R, "The referee reaches forward.", [s(H,"thought","HE SHOWED ME HE COULD INSTA-KILL ON PURPOSE TO MAKE ME ALWAYS VIGILANT OF THE ANTENNA..."),s(H,"thought","...TO WEAR ME OUT!!"),s(H,"thought","HE'S BASICALLY DECLARING A DRAWN-OUT BATTLE!!")]),
 (H, "Hisoka smiles and displays the two of hearts.", [s(H,"thought","I'M SO HAPPY, CHROLLO... ♥")]),
],
13: [
 (f"{H};{R}", "Hisoka rushes beneath the referee's raised arm.", [s(H,"thought","YOU MAKE ME FEEL..."),s(H,"thought","...SO GOOD... ♥"),s("no_speaker","sound_effect","SHF")]),
 (f"{H};{R}", "The referee's body swells as Hisoka approaches.", [s(H,"thought","!!"),s("no_speaker","sound_effect","BOOM")]),
 (H, "Hisoka reacts to the swelling referee.", [s(H,"thought","A BLAST...?! THE BLOOD COULD BE BAD!")]),
 (H, "A dark speed-line panel contains Hisoka's thought.", [s(H,"thought","BUNGEE!!")]),
],
14: [
 (R, "The referee is suspended above the arena floor as his body bursts.", []),
 (f"{C};{R}", "Chrollo stands behind the referee with symbols visible on the referee's hands.", []),
],
15: [
 (f"{H};{C};{R}", "Chrollo displays marked hands while the referee lies on the floor and Hisoka watches.", [s(C,"dialogue","THE SUN AND MOON: ‘PAIRED DESTRUCTION.’"),s(C,"dialogue","AS YOU CAN SEE, IT USES BOTH HANDS."),s(C,"dialogue","THE MARK OF THE SUN IS IMPRESSED WITH THE LEFT HAND, AND THE MOON WITH THE RIGHT."),s(H,"dialogue","BUT..."),s(H,"dialogue","...WHERE'S THE BOOK...?!"),s("no_speaker","sound_effect","SPLAT"),s("crowd","dialogue","HE'S DEAD...?"),s("crowd","dialogue","FOR REAL?!")]),
 ("crowd", "Spectators stare from the stands.", [s("crowd","sound_effect","GASP")]),
 (C, "Close-up of one marked hand touching the referee's back.", [s(C,"dialogue","WHEN THE MARKS TOUCH EACH OTHER, THEY EXPLODE... I JUST MARKED THE JUDGE'S LEFT HAND AND BACK."),s(C,"dialogue","THE MARKS THEMSELVES CAN BE MADE IN AN INSTANT, BUT FOR MAXIMUM EFFECT, I NEED TO TOUCH THE TARGET FOR THREE TO FIVE SECONDS."),s(C,"dialogue","AN INSTANT MARK WILL RESULT IN THAT SMALL BLAST..."),s(C,"dialogue","...BUT A COMPLETE BOMB CAN BLOW NEARBY PEOPLE TO SMITHEREENS.")]),
 ("meteor_city", "A distant view of Meteor City.", [s(C,"dialogue","I GAINED THIS ABILITY BACK HOME..."),s(C,"dialogue","...IN METEOR CITY.")]),
],
16: [
 (H, "Hisoka advances while holding a playing card overhead.", [s(H,"dialogue","..."),s(H,"dialogue","YOU'RE SO KIND. ♦"),s(H,"dialogue","ARE YOU BEING CONDESCENDING?"),s("no_speaker","sound_effect","TP")]),
 (H, "Close-up of Hisoka smiling.", [s(H,"dialogue","OR..."),s(H,"dialogue","...ARE YOU REALLY EXPECTING ME TO JUST BEND OVER?")]),
 (C, "Chrollo holds Skill Hunter open.", [s(C,"dialogue","I WON'T TAKE ANOTHER DRAW STEP."),s(C,"dialogue","I'LL PLAY WITH MY HAND FACEUP.")]),
 (C, "Chrollo looks toward Hisoka.", [s(C,"dialogue","STYLE IS IMPORTANT IN A GAME, RIGHT?"),s(C,"dialogue","MORE THAN THE OUTCOME.")]),
 (H, "Hisoka answers in profile.", [s(H,"dialogue","WON'T YOU BE MORE INSISTENT ON WINNING?"),s(H,"dialogue","DON'T BE SUCH A TURN-OFF. ♠")]),
 (C, "Close-up of Chrollo smiling and pointing forward.", [s(C,"dialogue","OF COURSE, I PLAN TO WIN."),s(C,"dialogue","BUT WHAT ABOUT YOURSELF?")]),
],
17: [
 (f"{H};{C}", "Chrollo demonstrates with Skill Hunter while Hisoka watches from below.", [s(C,"dialogue","THINK CAREFULLY BEFORE YOU CALL AFTER SEEING MY HAND."),s(C,"dialogue","DOUBLE FACE: ‘BOOKMARK THEME.’"),s(C,"dialogue","LIKE I JUST DEMONSTRATED, BY USING A BOOKMARK, I CAN MAINTAIN THAT PAGE'S ABILITY EVEN AFTER CLOSING THE BOOK."),s(C,"dialogue","I CAN USE IT CONCURRENTLY WITH AN ABILITY ON ANOTHER PAGE.")]),
 (H, "Close-up of Hisoka smiling.", [s(H,"thought","AS LONG AS YOU CAN FIGHT COMFORTABLY. ♥"),s(H,"thought","A BATTLE IS A DANCE...! WE MUST MOVE TO EACH OTHER'S BEAT...")]),
],
18: [
 (f"{H};{C}", "Hisoka asks Chrollo a question from across the arena.", [s(H,"dialogue","CAN I NITPICK?"),s(H,"dialogue","THE BOOKMARK, THE ABILITY ON THE BOOKMARKED PAGE AND THE ABILITY ON THE OPEN PAGE..."),s(H,"dialogue","WOULDN'T THAT MAKE IT TRIPLE, NOT DOUBLE?")]),
 (C, "Close-up of Chrollo holding the book.", [s(C,"dialogue","IN THAT CASE, THE BOOK ITSELF WOULD MAKE IT QUADRUPLE."),s(C,"dialogue","THE BOOKMARK COMES WITH THE BOOK. IT'S MY OWN ABILITY AND NOT STOLEN.")]),
 (C, "Chrollo holds up the bookmark.", [s(C,"dialogue","SO IT'S BASICALLY AN ABILITY TO USE TWO STOLEN ABILITIES AT ONCE."),s(C,"dialogue","I ONLY HAVE ONE BOOKMARK, BY THE WAY.")]),
 (C, "Close-up of Chrollo in profile.", [s(C,"dialogue","BEING ABLE TO MAKE A COMBO OF TWO ABILITIES IS POWERFUL..."),s(C,"dialogue","BUT THE TRUE ADVANTAGE OF THE BOOKMARK IS NOT HAVING TO HOLD THE BOOK.")]),
 (f"{H};{C}", "Chrollo explains while Hisoka listens across the arena.", [s(C,"dialogue","SKILL HUNTER REQUIRED ME TO HOLD THE BOOK WITH MY RIGHT HAND WHEN I CONCEIVED IT..."),s(C,"dialogue","BUT WHEN I STOLE AN ABILITY THAT REQUIRED BOTH HANDS, I WAS FORCED TO MAKE SOME ADJUSTMENTS."),s(C,"dialogue","NOW I HAVE MORE ANNOYING CONDITIONS TO DEAL WITH..."),s(C,"dialogue","BUT I FIND THAT MY COMBAT EFFICIENCY HAS VASTLY IMPROVED."),s("no_speaker","sound_effect","SHP")]),
],
19: [
 (C, "Chrollo displays the marks on both hands.", [s(C,"dialogue","I CAN USE ONE ABILITY WITH BOTH HANDS FREE."),s(C,"dialogue","ISN'T IT WONDERFUL?"),s(C,"dialogue","WITH THAT IN MIND..."),s(C,"dialogue","I'LL SHOW YOU THREE MORE ABILITIES.")]),
 (H, "Close-up of Hisoka looking forward.", [s(H,"thought","YES, WONDERFUL..."),s(H,"thought","...AND ANNOYING...")]),
 (C, "Close-up of Chrollo smiling.", [s(C,"dialogue","YOU'RE SETTING A NEW RECORD FOR THE NUMBER OF ABILITIES IT HAS EVER TAKEN ME..."),s(C,"dialogue","...TO KILL SOMEONE. YOU SHOULD BE PROUD.")]),
],
}


def main():
    db = sqlite3.connect(DB)
    db.execute("PRAGMA foreign_keys=ON")
    with db:
        db.execute("DELETE FROM text_segments WHERE panel_id IN (SELECT panel_id FROM panels WHERE chapter=351)")
        db.execute("DELETE FROM panels WHERE chapter=351")
        db.execute("INSERT OR REPLACE INTO chapters(chapter,title,page_count,edition,language) VALUES(351,?,?,?,?)", ("Battle to the Death",19,"","en"))
        for page in range(1,20):
            for order,(chars,visual,segs) in enumerate(P[page],1):
                pid=f"ch351-p{page:02d}-{order:02d}"
                db.execute("""INSERT INTO panels(panel_id,chapter,page_start,page_end,panel_order,panel_types,characters_on_panel,location,visual_description,review_status,silent_panel)
                              VALUES(?,351,?,?,?,'standard',?,?,?,'needs_review',?)""",
                           (pid,page,page,order,chars,LOC,visual,int(not segs)))
                for i,(speaker,mode,text) in enumerate(segs,1):
                    db.execute("INSERT INTO text_segments(panel_id,segment_order,speaker,mode,text) VALUES(?,?,?,?,?)",(pid,i,speaker,mode,text))
    panels=db.execute("SELECT COUNT(*) FROM panels WHERE chapter=351").fetchone()[0]
    segments=db.execute("SELECT COUNT(*) FROM text_segments t JOIN panels p USING(panel_id) WHERE p.chapter=351").fetchone()[0]
    print(f"Seeded chapter 351: {panels} panels, {segments} text segments")


if __name__ == "__main__":
    main()
