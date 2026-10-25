#!/usr/bin/env python3
"""Prefill Hunter x Hunter chapter 352 for review in the local annotator."""

import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "private/story/story_annotations.sqlite"
H = "char_hisoka_morow"
C = "char_chrollo_lucilfer"
LOC = "Heavens Arena — battle arena"


def s(speaker, mode, text):
    return speaker, mode, text


P = {
1: [
 (H,"Close-up of Hisoka smiling.",[s("no_speaker","sound_effect","VMMM")]),
 (C,"Chrollo removes a bookmark from Skill Hunter.",[s("no_speaker","sound_effect","SHP")]),
 (f"{H};{C}","Chrollo and Hisoka face each other across the arena.",[s(C,"dialogue","ALL ABILITIES..."),s(C,"dialogue","...HAVE STRENGTHS AND WEAKNESSES.")]),
],
2: [
 (C,"Chrollo stands with his back partly turned.",[s(C,"dialogue","PEOPLE COMPENSATE BY GETTING CREATIVE."),s(C,"dialogue","THEY MAY KEEP THEIR ABILITIES SECRET..."),s(C,"dialogue","...OR PICK THEIR BATTLES CAREFULLY AND FIGHT AS A TEAM, FOR EXAMPLE.")]),
 (C,"Close-up of Chrollo's open book.",[s(C,"dialogue","IN ADDITION..."),s(C,"dialogue","...I CAN ACQUIRE MORE ABILITIES AS I NEED THEM.")]),
 (C,"Close-up of Chrollo's eyes.",[s(C,"dialogue","AND THEN I WAIT UNTIL THE CONDITIONS FOR A SURE VICTORY..."),s(C,"dialogue","...CAN BE MET!")]),
 (H,"Hisoka stands with his hands at his waist.",[s(H,"dialogue","THAT'S PRETTY STANDARD. ♣"),s(H,"dialogue","MY GREATEST PLEASURE COMES WHEN SUCH PEOPLE CRUMPLE TO THEIR KNEES..."),s(H,"dialogue","...AND I LOOK DOWN UPON THEIR DISBELIEVING FACES AS THEIR PLANS FAIL. ♥")]),
 (C,"Chrollo holds Skill Hunter open.",[s(C,"dialogue","BACK TO ABILITIES."),s(C,"dialogue","ORDER STAMP: ‘PROOF OF HUMANITY.’")]),
 ("hands","Two fists collide.",[s("no_speaker","sound_effect","VMM")]),
],
3: [
 (C,"Chrollo holds up a small stamp while keeping Skill Hunter open.",[s(C,"dialogue","SHALNARK'S BLACK VOICE MANIPULATES HUMANS."),s(C,"dialogue","THIS ONE MANIPULATES PUPPETS.")]),
 (H,"Hisoka watches Chrollo from across the arena.",[s(H,"thought","THE CELL PHONE CAN OVERRIDE PEOPLE'S AUTONOMY, BUT ONLY TWO PEOPLE AT A TIME."),s(H,"thought","THE STAMP CAN MANIPULATE MANY, BUT CAN'T GIVE COMPLEX COMMANDS."),s(H,"thought","SO THE PHONE IS FOR THE FINISH... ♦ BUT..."),s(H,"thought","...HUMANS AND PUPPETS CAN'T BE CONTROLLED TOGETHER!! IS THERE ANOTHER PLAN...?")]),
 (C,"Close-up of Chrollo's face.",[]),
 (f"{C};temp_ch351_referee","Chrollo kneels beside the referee's body.",[s(C,"dialogue","YOU'VE SEEN THIS ONE BEFORE.")]),
 (C,"Chrollo flips a page in Skill Hunter.",[s("no_speaker","sound_effect","FLIP"),s("no_speaker","sound_effect","FSHH")]),
 (C,"Chrollo presses the stamp onto a page while a bookmark holds another page.",[s(C,"dialogue","THE BOOKMARK KEEPS IT IN PLACE."),s("no_speaker","sound_effect","FUMP"),s("no_speaker","sound_effect","SHP")]),
],
4: [
 (f"{C};temp_ch351_referee","Chrollo presses both hands onto the referee's body.",[s(C,"dialogue","GALLERY FAKE: ‘DIVINE LEFT HAND, DEMONIC RIGHT HAND.’")]),
 (C,"Chrollo rolls the referee's body onto its back.",[s("no_speaker","sound_effect","ROLL")]),
 (C,"Close-up of Chrollo looking downward.",[s(C,"dialogue","HUMANS ARE STRANGE CREATURES...")]),
 (f"{H};{C};temp_ch351_referee","Chrollo crouches beside two identical bodies while Hisoka watches.",[s(C,"dialogue","TO ME, A CORPSE AND A PUPPET ARE SIMILAR INANIMATE OBJECTS..."),s(C,"dialogue","BUT NOT TO THE FORMER OWNER OF ORDER STAMP."),s(C,"dialogue","A CORPSE CANNOT BE CONTROLLED, BUT ITS COPY CAN.")]),
 ("temp_ch351_referee","Chrollo presses the stamp onto the copied referee's forehead.",[s("no_speaker","sound_effect","TMP")]),
],
5: [
 (f"{C};temp_ch351_referee;crowd","Chrollo stands between the two referee bodies as one copy rises.",[s(C,"dialogue","GET UP."),s("no_speaker","sound_effect","RRRMMM")]),
 (C,"Close-up of Chrollo's eyes.",[s(C,"dialogue","FOR THE FORMER OWNER, THE DIFFERENCE BETWEEN A PUPPET AND ONE THAT HAS CEASED TO BE ONE...")]),
 (f"{C};temp_ch351_referee","The copied referee runs while Chrollo points.",[s(C,"dialogue","...IS WHETHER THE HEAD IS CONNECTED TO THE TORSO."),s(C,"dialogue","BREAK HISOKA!"),s("no_speaker","sound_effect","SHF SHF")]),
],
6: [
 (f"{H};temp_ch351_referee","The copied referee runs toward Hisoka.",[s(C,"dialogue","HOW IT ACCEPTS COMMANDS DEPENDS ON THE PUPPET TOO.")]),
 (C,"Chrollo watches from the side.",[s(C,"dialogue","IF YOU ORDER A PUPPET CREATED BY COPYING A HUMAN TO KILL SOMEONE..."),s(C,"dialogue","...IT REFLECTS ITS ORIGINAL PERSONALITY.")]),
 (H,"Hisoka watches the copied referee approach.",[s(C,"dialogue","IT MAY FOCUS ON INEFFICIENT METHODS OR ASSUME THE DEED IS DONE BEFORE THE TARGET IS TRULY DEAD..."),s(C,"dialogue","IN THE WORST CASES, SOME PUPPETS OUTRIGHT IGNORE THE ORDER."),s(C,"dialogue","BUT CHANGE THE COMMAND TO ‘BREAK’..."),s(C,"dialogue","...AND THEY ALL GET TO WORK ON SEVERING THE HEAD.")]),
 (C,"Close-up of Chrollo's eyes.",[s(C,"dialogue","MAKING THE ABILITY YOURS WHILE EXPLORING THE DARKNESS WITHIN THE SOUL OF THE ORIGINAL OWNER..."),s(C,"dialogue","THAT'S THE TRUE PLEASURE OF A SKILL HUNTER.")]),
 (f"{H};temp_ch351_referee","The copied referee reaches for Hisoka.",[s("no_speaker","sound_effect","GRAB"),s("no_speaker","sound_effect","FFT")]),
 (f"{H};temp_ch351_referee","Hisoka strikes the copied referee's neck with a card.",[s("no_speaker","sound_effect","KRAK")]),
],
7: [
 (f"{H};temp_ch351_referee","Hisoka holds the severed head while the copied body remains behind him.",[]),
 (f"{H};{C};temp_ch351_referee","A distant view shows Hisoka, Chrollo, and the copied body.",[s(H,"dialogue","CORRECT."),s(H,"dialogue","SEVER THE HEAD AND THE PUPPET STOPS—THE STAMP DISAPPEARS."),s("crowd","sound_effect","GASP"),s("no_speaker","sound_effect","WORNUK")]),
 ("temp_ch351_referee","The copied body lies on the arena floor.",[s(C,"dialogue","BUT I HAVEN'T DEACTIVATED GALLERY FAKE, SO THE PUPPET REMAINS."),s(C,"dialogue","WHEN THE COPY VANISHES, YOU MAY CONCLUDE THAT GALLERY FAKE HAS BEEN DEACTIVATED.")]),
 (H,"Close-up of Hisoka smiling.",[s(H,"dialogue","..."),s(H,"dialogue","AND THE LAST ONE?")]),
 (f"{H};{C};temp_ch351_referee","Hisoka faces Chrollo while two heads lie on the floor.",[s("no_speaker","sound_effect","FSSSH"),s("no_speaker","sound_effect","FSSSH"),s("no_speaker","sound_effect","TMP"),s("no_speaker","sound_effect","FLIP")]),
],
8: [
 (C,"Chrollo displays symbols on both palms.",[s(C,"dialogue","THIS..."),s(C,"dialogue","...I CAN USE MY LEFT HAND WHILE HOLDING THE BOOK, BUT I USE THE BOOKMARK WHEN I WANT TO USE THE RIGHT."),s(C,"dialogue","THE ABILITY REMAINS IN EFFECT SO LONG AS I HOLD THE BOOK OPEN, EVEN IF I REMOVE THE BOOKMARK.")]),
 (f"{H};{C}","A diagram shows Hisoka and Chrollo facing one another.",[s(C,"dialogue","CONVERT HANDS: ‘TRANSFER STUDENT.’"),s(C,"dialogue","TOUCH WITH MY RIGHT HAND, AND THE TARGET TAKES MY FORM. TOUCH WITH MY LEFT HAND, AND I TAKE ON THE FORM OF THE TARGET.")]),
 (f"{H};{C};crowd","Chrollo and Hisoka stand before the audience.",[s(C,"dialogue","TOUCH WITH BOTH HANDS, AND WE INSTANTLY SWITCH FORMS."),s(C,"dialogue","ONLY THE APPEARANCE CHANGES—THE PERSONA DOES NOT SWITCH.")]),
 (C,"Close-up of one marked palm.",[s(C,"dialogue","IT'LL BE EASY TO FIGURE OUT WHICH IS REAL."),s(C,"dialogue","I'M THE ONE WITH THE ARROWS ON MY PALMS.")]),
 (H,"Close-up of Hisoka thinking.",[s(H,"thought","COULD GALLERY FAKE CREATE A COPY OF HIM WITH THE MARKS...? NO. ♦"),s(H,"thought","PLACE THE BOOKMARK, AND WITH THE MARKS REMAINING, ACTIVATE GALLERY FAKE—THE BOOK GETS IN THE WAY.")]),
 (f"{H};{C}","Hisoka and Chrollo stand far apart.",[s(H,"thought","GALLERY FAKE AND CONVERT HANDS CAN CREATE HUMAN COPIES, BUT YOU NEED A MANIPULATING ABILITY TO CONTROL THEM."),s(H,"thought","THE ABILITIES ARE SIMILAR, BUT THEY BOTH HAVE DISTINCT ROLES.")]),
],
9: [
 (f"{H};{C}","Close-ups of Hisoka and Chrollo facing one another.",[s(H,"dialogue","ALL TO DEFEAT YOU.")]),
 (H,"Hisoka steps forward.",[s(H,"dialogue","SO... THAT'S IT FOR THE LECTURE, RIGHT?"),s(H,"dialogue","TIME TO GET THIS STARTED...")]),
 (C,"Chrollo steps forward.",[s(C,"dialogue","ONE MORE THING..."),s(C,"dialogue","I'LL OFFER YOU THE MOST IMPORTANT BIT OF INFORMATION."),s("no_speaker","sound_effect","TP")]),
 (H,"Close-up of Hisoka listening.",[s(H,"dialogue","...")]),
 (C,"Chrollo looks down at Skill Hunter.",[s(C,"dialogue","THE ABILITIES IN MY BOOK VANISH, NEVER TO BE USED AGAIN..."),s(C,"dialogue","...WHEN THE PERSON I STOLE FROM DIES.")]),
 (C,"Close-up of Chrollo holding one finger to his lips.",[s(C,"dialogue","BUT ONE OF THE ABILITIES I JUST EXPLAINED..."),s(C,"dialogue","...IS AN ABILITY THAT REMAINS IN THE BOOK EVEN AFTER DEATH.")]),
],
10: [
 (H,"Close-up of Hisoka's face.",[s("no_speaker","sound_effect","RM")]),
 (H,"Extreme close-up of Hisoka's eyes.",[s(H,"thought","NEN THAT BECOMES STRONGER..."),s(H,"thought","...AFTER DEATH...!!")]),
 (f"{H};{C};crowd","Hisoka and Chrollo stand across the arena.",[]),
 (C,"Chrollo looks upward.",[s(C,"dialogue","LOOKS LIKE YOU GET IT."),s(C,"dialogue","THIS CAME AS A SURPRISE TO ME TOO.")]),
],
11: [
 ("meteor_city_elder","A robed elder stands inside a damaged structure.",[s(C,"dialogue","THE ORIGINAL OWNER WAS METEOR CITY'S ELDER."),s(C,"dialogue","WHEN SOMEONE IN THE OUTSIDE WORLD ATTACKED ONE OF THE RESIDENTS, HE TURNED ONE OF OUR BRETHREN INTO A BOMB TO DELIVER OUR MESSAGE.")]),
 (C,"Chrollo looks toward Hisoka.",[s(C,"dialogue","UNLIKE ORDER STAMP'S OWNER, THE ELDER THOUGHT THERE WASN'T MUCH DIFFERENCE BETWEEN HUMANS AND PUPPETS."),s(C,"dialogue","I TEND TO AGREE.")]),
 (H,"Hisoka listens in silence.",[]),
 (C,"Close-up of Chrollo's face.",[s(C,"dialogue","DO YOU UNDERSTAND..."),s(C,"dialogue","...WHAT I'M TRYING TO SAY?")]),
 (H,"Close-up of Hisoka's face.",[s(H,"dialogue","YES... ♣"),s(H,"dialogue","THE SUN AND MOON...")]),
 ("crowd","An overhead view shows a damaged public area with people gathered around a crater.",[s(H,"dialogue","...ONCE MARKED..."),s(H,"dialogue","...CANNOT BE REMOVED...!")]),
],
12: [
 (f"{H};{C};crowd","Hisoka and Chrollo face one another in the arena.",[s(C,"dialogue","EXACTLY."),s(C,"dialogue","WHETHER I CLOSE THE BOOK OR PUT IT AWAY, THEY REMAIN UNTIL THE BOMB GOES OFF."),s("crowd","sound_effect","RAAH RAAH RAAH")]),
 (H,"Close-up of Hisoka smiling.",[s(H,"thought","THIS IS GETTING..."),s(H,"thought","...EXTREMELY TROUBLESOME... ♠")]),
 (C,"Close-up of Chrollo.",[s(C,"dialogue","THAT'S THE END OF THE EXPLANATION."),s(C,"dialogue","I'M NOT SAYING THIS AS A CHALLENGE, BUT I'LL WIN. I'M 100 PERCENT SURE.")]),
 (C,"Chrollo asks Hisoka a question in profile.",[s(C,"dialogue","WILL YOU CONTINUE?")]),
 (H,"Hisoka answers in profile.",[s(H,"dialogue","..."),s(H,"dialogue","OF COURSE... ♥")]),
],
13: [
 (C,"Extreme close-up of Chrollo's eyes.",[s(C,"thought","HUMANS...")]),
 (f"{H};{C}","Hisoka lowers his stance while Chrollo holds Skill Hunter open.",[s(C,"thought","...ARE SO VERY..."),s(C,"thought","...INTERESTING.")]),
],
14: [
 (C,"Chrollo removes the bookmark from Skill Hunter.",[s(H,"thought","THE BOOKMARK...!!")]),
 (H,"Close-up of Hisoka reacting.",[]),
 (f"{H};{C};crowd","Chrollo leaps toward the stands while Hisoka runs after him.",[s("no_speaker","sound_effect","ZOOM")]),
],
15: [
 (C,"Chrollo holds a phone and antennas while Skill Hunter remains open.",[s(C,"dialogue","BLACK VOICE: ‘MOBILE FATE DIRECTOR’!!")]),
 (H,"Hisoka extends an arm forward.",[s(H,"dialogue","BUNGEE GUM: ‘ELASTIC LOVE’!!")]),
],
16: [
 (f"{C};crowd","Chrollo enters the audience as spectators recoil.",[s("crowd","dialogue","...!"),s("crowd","sound_effect","WHOOAAA")]),
 ("temp_ch352_commentator;crowd","A commentator watches the fighters move toward the audience.",[s("temp_ch352_commentator","dialogue","THE BATTLE RESUMES!! BUT... HISOKA GOES CHASING AFTER CHROLLO...")]),
 (f"{H};{C};crowd","Hisoka and Chrollo move among the spectators.",[s("temp_ch352_commentator","dialogue","...INTO THE STANDS?!"),s("crowd","dialogue","WHAT'S GOING ON?!"),s("crowd","sound_effect","RAAHHHHH")]),
],
17: [
 (H,"Hisoka moves through the stands.",[s(H,"thought","IF I GET TOO CLOSE, THE ANTENNA IS DANGEROUS. ♣"),s(H,"thought","...BUT IF I STAY AWAY, I PLAY INTO CHROLLO'S HANDS..."),s(H,"thought","BUT..."),s(H,"thought","...IF I GET CLOSER...")]),
 (f"{H};crowd","Hisoka charges toward a large spectator.",[s("no_speaker","sound_effect","BOOM")]),
 (H,"Close-up of Hisoka's eyes.",[s(H,"thought","I KNEW IT...!"),s(H,"thought","HE'LL TRY TO BLOCK MY SIGHT...!!")]),
],
18: [
 ("crowd","A spectator's body blocks the foreground.",[s(H,"thought","CHROLLO WENT LEFT!"),s("no_speaker","sound_effect","FFT")]),
 (H,"Hisoka turns sharply.",[s("no_speaker","sound_effect","ZSH"),s("no_speaker","sound_effect","RM")]),
 (f"{H};crowd","Hisoka runs toward two spectators.",[s("no_speaker","sound_effect","SLASH")]),
 (f"{H};crowd","Hisoka strikes between the two spectators.",[s(H,"thought","!!"),s("no_speaker","sound_effect","LEAP")]),
 (H,"Close-up of Hisoka's startled eyes.",[]),
 ("crowd","A spectator looks over his shoulder.",[s("no_speaker","sound_effect","RMM")]),
],
19: [
 (f"{H};crowd","Hisoka moves away as a spectator reaches toward him.",[s("crowd","dialogue","ANOTHER ONE...!!"),s("crowd","dialogue","HE USED BOTH ANTENNAS...!!"),s("no_speaker","sound_effect","SLASH")]),
 ("crowd","Spectators scramble up the arena steps.",[s("crowd","dialogue","HE'S GONE!"),s("crowd","sound_effect","WAAAAAAH")]),
 (H,"Close-up of Hisoka thinking.",[s(H,"thought","BLACK VOICE"),s(H,"thought","↓ BOOKMARK"),s(H,"thought","↓ ACTIVATE CONVERT HANDS"),s(H,"thought","↓ TRANSFORM INTO SOMEONE ELSE WITH HIS LEFT HAND"),s(H,"thought","↓ MOVE THE BOOKMARK TO CONVERT HANDS"),s(H,"thought","↓ CLOSE THE BOOK AND LIE IN WAIT")]),
 (H,"Hisoka smiles in profile.",[s(H,"thought","QUITE TROUBLESOME... ♠")]),
],
}


def main():
    db=sqlite3.connect(DB)
    db.execute("PRAGMA foreign_keys=ON")
    with db:
        db.execute("DELETE FROM text_segments WHERE panel_id IN (SELECT panel_id FROM panels WHERE chapter=352)")
        db.execute("DELETE FROM panels WHERE chapter=352")
        db.execute("INSERT OR REPLACE INTO chapters(chapter,title,page_count,edition,language) VALUES(352,?,?,?,?)",("Troublesome",19,"","en"))
        for page in range(1,20):
            for order,(chars,visual,segs) in enumerate(P[page],1):
                pid=f"ch352-p{page:02d}-{order:02d}"
                db.execute("""INSERT INTO panels(panel_id,chapter,page_start,page_end,panel_order,panel_types,characters_on_panel,location,visual_description,review_status,silent_panel)
                              VALUES(?,352,?,?,?,'standard',?,?,?,'needs_review',?)""",
                           (pid,page,page,order,chars,LOC,visual,int(not segs)))
                for i,(speaker,mode,text) in enumerate(segs,1):
                    db.execute("INSERT INTO text_segments(panel_id,segment_order,speaker,mode,text) VALUES(?,?,?,?,?)",(pid,i,speaker,mode,text))
    panels=db.execute("SELECT COUNT(*) FROM panels WHERE chapter=352").fetchone()[0]
    segments=db.execute("SELECT COUNT(*) FROM text_segments t JOIN panels p USING(panel_id) WHERE p.chapter=352").fetchone()[0]
    print(f"Seeded chapter 352: {panels} panels, {segments} text segments")


if __name__=="__main__":
    main()
