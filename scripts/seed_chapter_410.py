#!/usr/bin/env python3
"""Prefill Hunter x Hunter chapter 410 for review in the local annotator."""

import sqlite3
from pathlib import Path

DB = Path(__file__).resolve().parents[1] / "private/story/story_annotations.sqlite"

M = "char_morena_prudo"
B = "char_borksen"
BEN = "char_benjamin_hui_guo_rou"
BAL = "char_balsamilco_might"


def seg(speaker, mode, text):
    return (speaker, mode, text)


# page_start, page_end, characters, location, visual description, text segments
P = {
1: [
 (1,1,f"{M};{B}","B.W. between Tiers 2 and 3 — Morena's hideout","Morena and Borksen face each other in profile.",[seg(M,"dialogue","THIS IS FOR THE LAST TIME..."),seg(M,"dialogue","YOU CAN'T CHANGE YOUR ANSWER AFTER THIS."),seg("no_speaker","sound_effect","BRRM")]),
 (1,1,B,"B.W. between Tiers 2 and 3 — Morena's hideout","Close-up of Borksen in profile.",[seg(B,"dialogue","YES."),seg(B,"dialogue","THAT'S FINE.")]),
 (1,1,"","B.W. between Tiers 2 and 3 — Morena's hideout","The Yes card lies on the table among Borksen's dark thought balloons.",[seg(B,"thought","NO... NO!!"),seg(B,"thought","DON'T..."),seg(B,"thought","THAT'S NOT WHAT I WANT!!"),seg("no_speaker","sound_effect","MM")]),
],
2: [
 (2,2,B,"B.W. between Tiers 2 and 3 — Morena's hideout","Borksen stands behind the table with one hand extended toward the card.",[seg(B,"dialogue","THIS IS THE CARD I CHOSE."),seg(B,"dialogue","STOP!"),seg(B,"dialogue","THAT'S NOT TRUE!!"),seg(B,"thought","NO..."),seg(B,"thought","NO!!")]),
 (2,2,f"{M};{B}","B.W. between Tiers 2 and 3 — Morena's hideout","Morena and Borksen face each other across the table.",[seg(M,"dialogue","I SEE."),seg(M,"dialogue","I'M HAPPY YOU'RE GOING TO JOIN US..."),seg(M,"dialogue","...BUT JUST A LITTLE BIT DISAPPOINTED.")]),
 (2,2,f"{M};{B}","B.W. between Tiers 2 and 3 — Morena's hideout","Alternating close-ups of Morena and Borksen.",[seg(B,"dialogue","YOU CHEATED, DIDN'T YOU?")]),
],
3: [
 (3,3,"crowd","B.W. between Tiers 2 and 3 — Morena's hideout","Members of Heil-Ly stand around the table.",[seg(M,"dialogue","IT MUST'VE BEEN AFTER YOU USED THE ‘DEAL’ CARD."),seg(M,"dialogue","YOU STOPPED THE SHUFFLE AND DOUBLE-CHECKED THE TWO CARDS ON YOUR BOARD...")]),
 (3,3,M,"B.W. between Tiers 2 and 3 — Morena's hideout","Close-up of Morena's eye.",[seg(M,"dialogue","THAT'S WHEN YOU MARKED THE ‘RETURN’ CARD!")]),
 (3,3,B,"B.W. between Tiers 2 and 3 — Morena's hideout","Borksen points toward the cards.",[seg(B,"dialogue","THESE TWO CARDS..."),seg(B,"dialogue","CAN I TURN THEM OVER AND LOOK AT THEM?")]),
 (3,3,f"{M};{B}","B.W. between Tiers 2 and 3 — Morena's hideout","Borksen holds up both cards for Morena to see.",[seg(B,"dialogue","SEE?")]),
 (3,3,B,"B.W. between Tiers 2 and 3 — Morena's hideout","Borksen holds the two cards.",[seg(B,"dialogue","THEY'RE ‘NO’ AND ‘RETURN.’")]),
 (3,3,"hands","B.W. between Tiers 2 and 3 — Morena's hideout","Hands turn the cards over.",[seg(M,"dialogue","YES.")]),
 (3,3,"","B.W. between Tiers 2 and 3 — Morena's hideout","The Return card lies face up on the table.",[]),
 (3,3,"","B.W. between Tiers 2 and 3 — Morena's hideout","The No card lies face up on the table.",[]),
],
4: [
 (4,4,M,"B.W. between Tiers 2 and 3 — Morena's hideout","Morena stands beside an enlarged diagram of the Return card.",[seg(M,"dialogue","YOU MUST'VE PUT A TINY INDENTATION ON THE FRONT, ALONG BOTH EDGES!")]),
 (4,4,f"{M};{B}","B.W. between Tiers 2 and 3 — Morena's hideout","Morena explains while facing Borksen.",[seg(M,"dialogue","IT'S TOO FAR FOR ME TO SEE, AND ORARGE, THE SHUFFLER, WOULD ONLY SEE THE BACKS OF THE CARDS."),seg(M,"dialogue","BUT YOU COULD SEE IT NO MATTER WHICH WAY THE CARD WAS ORIENTED AFTER SHUFFLING.")]),
 (4,4,M,"B.W. between Tiers 2 and 3 — Morena's hideout","Close-up of Morena's eyes.",[seg(M,"dialogue","BY CRUSHING THE CARD IN YOUR MOMENT OF VICTORY..."),seg(M,"dialogue","...YOU COULD GET RID OF THE EVIDENCE.")]),
 (4,4,B,"B.W. between Tiers 2 and 3 — Morena's hideout","Close-up of Borksen's face.",[]),
 (4,4,M,"B.W. between Tiers 2 and 3 — Morena's hideout","Morena explains the rules.",[seg(M,"dialogue","THIS GAME AND THOSE CARDS ARE A PART OF MY ABILITY."),seg(M,"dialogue","IF YOU CHEAT, THE MANIPULATIVE ASPECT OF MY ABILITY IS AUTOMATICALLY TRIGGERED. YOU CAN ONLY PICK YES OR NO.")]),
 (4,4,f"{M};{B}","B.W. between Tiers 2 and 3 — Morena's hideout","Morena and Borksen stand facing one another.",[seg(M,"dialogue","YOUR CHOICES FOR THE LAST CARD WERE REDUCED TO TWO..."),seg(M,"dialogue","...BUT YOU ONLY HAVE YOURSELF TO BLAME FOR YOUR ULTIMATE CHOICE.")]),
 (4,4,f"{M};{B}","B.W. between Tiers 2 and 3 — Morena's hideout","Morena leans close to Borksen.",[seg(M,"dialogue","YOU SHOULD'VE INTUITED THAT CHEATING IS TANTAMOUNT..."),seg(M,"dialogue","...TO ABANDONING THIS SERIOUS GAME.")]),
],
5: [
 (5,5,M,"B.W. between Tiers 2 and 3 — Morena's hideout","Morena looks at Borksen.",[seg(M,"dialogue","SO."),seg(M,"dialogue","BY YES, YOU'RE GOING TO JOIN US?")]),
 (5,5,B,"B.W. between Tiers 2 and 3 — Morena's hideout","Borksen answers Morena.",[seg(B,"dialogue","YES."),seg(B,"dialogue","I WILL JOIN YOU.")]),
 (5,5,"crowd","B.W. between Tiers 2 and 3 — Morena's hideout","The Heil-Ly members clap around Morena and Borksen.",[seg("no_speaker","sound_effect","CLAP CLAP CLAP CLAP CLAP CLAP")]),
 (5,5,B,"B.W. between Tiers 2 and 3 — Morena's hideout","Borksen rises abruptly.",[seg("no_speaker","sound_effect","UNH")]),
 (5,5,B,"B.W. between Tiers 2 and 3 — Morena's hideout","Borksen drops to her knees.",[seg("no_speaker","sound_effect","THUNK")]),
 (5,5,M,"B.W. between Tiers 2 and 3 — Morena's hideout","Morena speaks to the kneeling Borksen.",[seg(M,"dialogue","TO WELCOME THE BRAND-NEW MEMBER OF OUR TEAM..."),seg(M,"dialogue","...I'LL EXPLAIN THE ‘YES?’ CARD THAT YOU DIDN'T CHOOSE DURING THE GAME.")]),
],
6: [
 (6,6,M,"B.W. between Tiers 2 and 3 — Morena's hideout","Morena smiles.",[seg(M,"dialogue","AS LONG AS YOU'RE ALIVE AND ON OUR SIDE, WE WON'T COME AFTER YOU..."),seg(M,"dialogue","...OR THE PEOPLE DEAR TO YOU, OF COURSE.")]),
 (6,6,B,"B.W. between Tiers 2 and 3 — Morena's hideout","Borksen listens with sweat on her face.",[]),
 (6,6,M,"B.W. between Tiers 2 and 3 — Morena's hideout","Morena appears at the center of a network of faces.",[seg(M,"dialogue","MY ABILITY IS CALLED ‘CONTAGION—WITH ETUDE OF LOVE.’ IT'S LIKE A GAME APP."),seg(M,"dialogue","IT'S INSTALLED IN YOU YOURSELF, AND I MANAGE THE PLAY DATA.")]),
 (6,6,"phone","B.W. between Tiers 2 and 3 — Morena's hideout","A phone is smashed.",[seg(M,"dialogue","I ALWAYS KNOW YOUR LEVEL, NUMBER OF POINTS, LOCATION, AND STATUS."),seg(M,"dialogue","YOU CANNOT REMOVE IT! THE GAME CONTINUES UNTIL YOU CLEAR THE GAME, THE ADMIN CEASES TO EXIST, OR THE ‘PHONE’ IS DESTROYED.")]),
 (6,6,f"{M};{B}","B.W. between Tiers 2 and 3 — Morena's hideout","Morena continues speaking while Borksen listens.",[seg(M,"dialogue","I ALREADY TOLD YOU THE THREE CONDITIONS TO JOIN US... CLEAR THEM, AND THE PROCESS WILL BE COMPLETE."),seg(M,"dialogue","YOU'RE ACTUALLY QUITE FREE TO DO WHAT YOU WANT AFTER THAT. FOR EXAMPLE, I DON'T RECOMMEND IT...")]),
 (6,6,M,"B.W. between Tiers 2 and 3 — Morena's hideout","Close-up of Morena's eye.",[seg(M,"dialogue","...BUT INFIGHTING AND BACKSTABBING AREN'T FORBIDDEN."),seg(M,"dialogue","AS LONG AS IT'S NOT TOO FLAGRANT.")]),
 (6,6,f"{M};{B}","B.W. between Tiers 2 and 3 — Morena's hideout","Morena looms in Borksen's view.",[seg("no_speaker","sound_effect","DOOM")]),
],
7: [
 (7,7,f"{M};{B}","B.W. between Tiers 2 and 3 — Morena's hideout","Borksen kneels as Morena explains.",[seg(M,"dialogue","RIGHT NOW, YOU ARE LEVEL 0... YOU HAVEN'T FULFILLED ALL THE CONDITIONS OF JOINING."),seg(M,"dialogue","ONCE YOU CLEAR THE LAST CONDITION, YOU WILL FORMALLY BE LEVEL 1..."),seg(M,"dialogue","YOU WILL GET A NEN ABILITY AT LEVEL 21."),seg(M,"dialogue","AT LEVEL 100, YOU WILL BE ABLE TO CREATE YOUR OWN TEAM LIKE ME."),seg(M,"dialogue","KILL ONE CIVILIAN TO GAIN ONE LEVEL."),seg(M,"dialogue","KILL SOMEONE WITH NEN, AND GAIN TEN LEVELS."),seg(M,"dialogue","KILL A PRINCE, AND YOU WILL GAIN 50 LEVELS.")]),
 (7,7,B,"B.W. between Tiers 2 and 3 — Morena's hideout","Borksen faces a dark silhouette surrounded by people.",[seg(M,"dialogue","WHETHER YOU LEVEL UP OR NOT IS UP TO YOU."),seg(M,"dialogue","WHETHER YOU STAY HERE OR GO BACK TO YOUR FRIENDS IS ALSO UP TO YOU... YOU'RE FREE."),seg(M,"dialogue","BUT WE WILL BETRAY YOU THE MOMENT WE REALIZE YOU'RE OF NO USE TO US."),seg(M,"dialogue","OUR GOAL IS TO KILL PEOPLE, AFTER ALL.")]),
],
8: [
 (8,8,B,"B.W. between Tiers 2 and 3 — Morena's hideout","Borksen's thoughts fill a dark background.",[seg(B,"thought","THERE'S AN UNDETERMINED TIME LIMIT... IF THEY FIND ANOTHER SPECIALIST CANDIDATE, I'LL NO LONGER BE VALUABLE!!"),seg(B,"thought","IF HER ABILITY IS INSTALLED IN ME LIKE AN APP, I SHOULD ASSUME IT COMES WITH SPYWARE THAT SHOWS HER EVERYTHING I SEE AND HEAR!!"),seg(B,"thought","I DO NEED POWER TO GO AGAINST THEM... BUT I HAVE TO KILL SOMEONE TO GET AN ABILITY IN THE SHORTEST AMOUNT OF TIME!!")]),
 (8,8,B,"B.W. between Tiers 2 and 3 — Morena's hideout","Borksen bows her head.",[]),
 (8,8,f"{M};{B}","B.W. between Tiers 2 and 3 — Morena's hideout","Morena and Borksen stand face to face.",[]),
 (8,8,B,"B.W. between Tiers 2 and 3 — Morena's hideout","Close-up of Borksen.",[seg(B,"dialogue","I'M GOING BACK TO MY PEOPLE!")]),
 (8,8,M,"B.W. between Tiers 2 and 3 — Morena's hideout","Close-up of Morena.",[seg(M,"dialogue","DON'T FORGET..."),seg(M,"dialogue","...WE'RE YOUR PEOPLE TOO NOW.")]),
],
9: [
 (9,9,f"{M};{B}","B.W. between Tiers 2 and 3 — Morena's hideout","Borksen walks forward with Morena behind her.",[seg(B,"thought","I HAVE A PURPOSE NOW!!"),seg("no_speaker","sound_effect","SHK")]),
 (9,9,f"{M};{B}","B.W. between Tiers 2 and 3 — Morena's hideout","Narrow close-ups of Morena and Borksen looking in opposite directions.",[seg(B,"dialogue","MORENA?"),seg(B,"dialogue","WILL YOU SHOW ME AROUND?")]),
 (9,9,"black_whale","Black Whale","The Black Whale sails through rough water.",[seg(B,"dialogue","BEFORE I GO BACK, I WANT TO KNOW MORE..."),seg(B,"dialogue","...ABOUT MY NEW COMRADES.")]),
],
10: [], 12: [], 13: [], 14: [], 16: [], 18: [], 19: []
}

# Martial-law section. Spreads are keyed by their first page.
P[10] = [
 (10,11,"military;crowd","B.W. Tier 3 central area","Armed soldiers supervise civilians kneeling along a broad passageway.",[seg("soldier","dialogue","DO NOT MOVE UNTIL YOU'VE BEEN PATTED DOWN!!"),seg("soldier","dialogue","IF YOU MOVE SO MUCH AS AN INCH, YOU WILL BE SHOT WITHOUT WARNING!! SPECIAL MARTIAL LAW!! THIS IS NOT A DRILL!!")]),
 (10,11,"military;crowd","B.W. Tier 3 central area","Soldiers escort civilians along stairs.",[]),
 (10,11,"soldier","B.W. Tier 3 central area","A soldier reports by radio.",[seg("soldier","dialogue","TIER 3 CENTRAL AREA, CLEAR!")]),
 (10,11,"soldier","B.W. Tier 3 central area","A soldier runs through the passageway.",[seg("soldier","dialogue","CAPTAIN!!")]),
 (10,11,"military","B.W. Tier 3 central area","Several soldiers confer.",[]),
 (10,11,"soldier","B.W. Tier 3 central area","Close-up of a soldier reacting.",[seg("soldier","dialogue","CASE S?!")]),
]
P[12] = [
 (12,12,"military","B.W. Tier 3 — Room 310","Room 310 is sealed with tape and guarded by two soldiers.",[]),
 (12,12,"military","B.W. Tier 3","Soldiers walk down a corridor.",[seg("soldier","dialogue","THREE SOLDIERS TOTAL WHO ENTERED THIS DOOR DISAPPEARED."),seg("soldier","dialogue","THE WITNESSING SOLDIER SAID THEY VANISHED INTO THIN AIR AS THEY ENTERED."),seg("soldier","dialogue","TEXTBOOK CASE S: A ‘SUPERNATURAL INCIDENT’...")]),
 (12,12,"soldier","B.W. Tier 3","Two soldiers discuss the investigation.",[seg("soldier","dialogue","THIS MAY BE WHY THE CORPORAL AND OTHERS WENT MISSING."),seg("soldier","dialogue","WE FOUND A HIDDEN ROOM BEHIND THE BATHROOM EXIT DOOR!")]),
 (12,12,"soldier","B.W. Tier 3","A soldier speaks from the corridor.",[seg("soldier","dialogue","LOOKS LIKE SOMEONE CUT THROUGH THE BATHROOM WALL!")]),
 (12,12,"military","B.W. Tier 3","Soldiers stand near Room 125.",[seg("soldier","dialogue","THE HIDDEN ROOM WAS CONNECTED TO ROOM 125."),seg("soldier","dialogue","IN ROOM 125, THE BATHROOM WALL WAS THE TRICK DOOR."),seg("soldier","dialogue","TIER 3 IS... HEIL-LY'S TERRITORY. CONTACT TIER 1.")]),
 (12,12,"military","B.W. Tier 3","Two soldiers receive an urgent report.",[seg("soldier","dialogue","YOUR HIGHNESS!! THEY'VE FOUND WHAT LOOKS TO BE HEIL-LY'S HIDEOUT!! NEN IS INVOLVED!"),seg("soldier","dialogue","THE ROOM WAS EMPTY!! WE'RE SEARCHING FOR OTHER HIDEOUT LOCATIONS!!")]),
]
P[13] = [
 (13,13,"military","B.W. Tier 3 central area","A military commander issues orders while holding a rifle.",[seg("commander","dialogue","SQUAD 3 WILL DEAL WITH HEIL-LY!! OUR PRIORITY IS SECURING THE PRINCES!!"),seg("commander","dialogue","THIRD PRINCE ZHANG-LEI AND SEVENTH PRINCE LUZURUS ARE CURRENTLY UNACCOUNTED FOR. FIND THEM!! LEAVE THE LOWER-RANKED PRINCES FOR LATER!!"),seg("commander","dialogue","ZHANG-LEI WENT TO TIER 2 RIGHT BEFORE THE DECLARATION, VIA CROSS-BRIDGE FROM INSIDE THE XI-YU BOSS RESIDENCE!"),seg("commander","dialogue","CURRENTLY CONFIRMING THE ROUTE AND FOLLOWING HIS TRAIL. FOLLOW-UP REPORT IN 15 MINUTES!"),seg("commander","dialogue","ZHANG-LEI LIKELY SOUGHT REFUGE AT THE JUSTICE DEPT.!! IT'S POSSIBLE HE WENT FARTHER DOWN TO MEET UP WITH THE MAFIA!!"),seg("commander","dialogue","TELL THE SQUAD 2 RECON TEAM AND THE SCOUTS TO FOCUS ON ZHANG-LEI!!"),seg("soldier","dialogue","YESSIR!!!!")]),
 (13,13,"commander","B.W. Tier 3 central area","Close-up of the commander's face.",[seg("commander","thought","TEN HOURS FROM ONSET TO COMA!! DEATH COMES TWO HOURS AFTER THAT."),seg("commander","thought","I HAVE ABOUT NINE AND A HALF MORE HOURS... I NEED TO ELIMINATE THE PRINCES BY THEN!!")]),
]
P[14] = [
 (14,15,"military","B.W. Tier 1 — First Prince's quarters","Soldiers stand before an ornate residence as a commander walks toward it.",[seg("announcement","dialogue","FIRST PRINCE BENJAMIN ON DECK!!"),seg(BEN,"thought","AS LONG AS I AM OFFICIALLY ANOINTED AS SUCCESSOR, EVEN IF I DIE..."),seg(BEN,"thought","I CAN HAND THE THRONE OVER TO MY CHILD!!"),seg(BEN,"thought","EMERGENCY LAW ARTICLE 11! ‘SUSTAINING THE MONARCHY IN A CRISIS’ WILL APPLY!!!")]),
 (14,15,BEN,"B.W. Tier 1 — First Prince's quarters","Benjamin's face fills the foreground.",[seg(BEN,"thought","I MUST GET FATHER'S DECLARATION OF SUCCESSION AND THE DOCUMENTATION!! THEN, TAKING INTO ACCOUNT THE TIME REQUIRED FOR THE LEGAL PROCEEDINGS OF HAVING MY ILLEGITIMATE CHILD NAMED AS MY OFFICIAL SUCCESSOR, I DON'T HAVE A MOMENT TO LOSE!!"),seg(BEN,"thought","FOUR PRINCES LEFT!!!")]),
]
P[16] = [
 (16,17,"military;char_benjamin_hui_guo_rou","B.W. Tier 1 — Central Court","Benjamin and his party approach officials surrounded by soldiers.",[]),
 (16,17,"official","B.W. Tier 1 — Central Court","Close-up of a helmeted official.",[]),
 (16,17,"official","B.W. Tier 1 — Central Court","Close-up of an older official.",[]),
 (16,17,"official","B.W. Tier 1 — Central Court","Close-up of a bespectacled official.",[]),
 (16,17,BEN,"B.W. Tier 1 — Central Court","Close-up of Benjamin.",[seg(BEN,"dialogue","YOU THREE WILL BE MY WITNESSES.")]),
 (16,17,"officials;military","B.W. Tier 1 — Central Court","Officials and soldiers stand in a line.",[seg("official","dialogue","I AM BENJAMIN, DEPUTY CHIEF COUNSEL. WITHOUT FURTHER ADO..."),seg("official","dialogue","...AT THE CENTRAL COURT, I WILL CONSOLIDATE ALL THREE BRANCHES OF GOVERNMENT BY MILITARY FORCE..."),seg("official","dialogue","...AND WE ARE TAKING OVER THIS BUILDING AS OUR JOINT FORCE COMMAND CENTER.")]),
]
P[18] = [
 (18,18,"official;char_benjamin_hui_guo_rou","B.W. Tier 1 — Central Court","An official questions Benjamin.",[seg("official","dialogue","FIRST, CAN YOU PROVIDE YOUR BASIS FOR DECLARING MARTIAL LAW AND THE LETTER OF AUTHORIZATION FROM THE KING?")]),
 (18,18,BEN,"B.W. Tier 1 — Central Court","Benjamin answers.",[seg(BEN,"dialogue","TERRORISM WITH A BIOLOGICAL WEAPON, ORCHESTRATED BY FOURTH PRINCE TSERRIEDNICH AND NINTH PRINCE HALKENBURG."),seg(BEN,"dialogue","THERE WAS A COLLABORATOR IN MY MILITARY—A SAMPLE UNDER DEVELOPMENT WAS BROUGHT ON BOARD.")]),
 (18,18,BEN,"B.W. Tier 1 — Central Court","Close-up of Benjamin.",[seg(BEN,"dialogue","THERE WERE MULTIPLE CO-CONSPIRATORS. SEVERAL SUSPECTS WERE ARRESTED AND ARE NOW BEING QUESTIONED.")]),
 (18,18,"official","B.W. Tier 1 — Central Court","The official responds.",[seg("official","dialogue","SOME OF THE SUSPECTS WERE ACCOMPANYING THE PRINCES' SECURITY TEAMS WHEN THEY WERE TAKEN TO SECURE LOCATIONS... TO BE SAFE, I'D LIKE TO COMPLETE THE ADMINISTRATIVE STEPS WITHOUT DELAY!")]),
 (18,18,"official","B.W. Tier 1 — Central Court","Close-up of the official in profile.",[seg("official","thought","HIS PLAN...")]),
 (18,18,"officials;military","B.W. Tier 1 — Central Court","Officials face Benjamin and the soldiers.",[seg("official","thought","...IS TO LEVERAGE THE PRINCES IN TIER 1 AS HOSTAGES TO SECURE THE THREE BRANCHES!!"),seg("official","thought","HE'S AN IMPULSIVE DICTATOR WHO PREFERS SHORTCUTS, TRUE TO HIS PROFILE."),seg("official","thought","PROBABLY MOST OF THIS IS CONVENIENTLY TWISTED HALF-TRUTHS."),seg("official","dialogue","WE CANNOT RELEASE THOSE WHO ARE SUSPECTED OF INFECTION FROM ISOLATION UNTIL COMPLETE ANALYSIS OF THE SAMPLE."),seg("official","dialogue","WITHOUT THE INTEGRATION OF THE THREE POWERS, I CANNOT PERMIT THEIR TRANSFER TO A HOSPITAL WHILE I'M UNSURE OF YOUR ‘SITUATION.’"),seg("official","dialogue","THE KING'S LETTER OF AUTHORIZATION IS BEING WRITTEN AS WE SPEAK. THEY WILL CONTACT YOU ONCE IT'S BEEN SIGNED AND SEALED. YOU CAN RETRIEVE IT THEN.")]),
 (18,18,BEN,"B.W. Tier 1 — Central Court","Close-up of Benjamin.",[seg(BEN,"dialogue","LET'S GET THIS DONE.")]),
 (18,18,"official","B.W. Tier 1 — Central Court","Close-up of an older official.",[seg("official","dialogue","YOUR HIGHNESS.")]),
]
P[19] = [
 (19,19,"char_benjamin_hui_guo_rou;official","B.W. Tier 1 — Central Court","Benjamin and an older official face one another.",[seg("official","dialogue","YOU LOOK RATHER PALE..."),seg("official","dialogue","ARE YOU ALL RIGHT?")]),
 (19,19,BEN,"B.W. Tier 1 — Central Court","Close-up of Benjamin's face.",[seg(BEN,"dialogue","THERE'S NO PROBLEM AT ALL.")]),
 (19,19,"officials;military","B.W. Tier 1 — Central Court","Officials and soldiers stand together.",[seg("official","thought","IF BENJAMIN IS PUSHING SO HARD, BECAUSE HE HIMSELF HAS BEEN INFECTED...")]),
 (19,19,"official","B.W. Tier 1 — Central Court","A bespectacled official thinks in profile.",[seg("official","thought","...CONSIDERING HALKENBURG'S PROGRESSION... HE HAS 24 HOURS AT MOST.")]),
 (19,19,"","B.W. Tier 1 — Central Court","Text on a black background.",[seg("official","thought","IF WE CAN SOMEHOW STAVE THIS OFF FOR ONE MORE DAY... WE'LL BE ABLE TO SEE THE LIGHT.")]),
 (19,19,"","B.W. Tier 1 — Central Court","Text on a black background with a time caption.",[seg("official","thought","I STILL HAVE MY FINAL STRONGHOLD!"),seg("narrator","caption","40 MINUTES INTO SPECIAL MARTIAL LAW")]),
]


def main():
    db = sqlite3.connect(DB)
    db.execute("PRAGMA foreign_keys=ON")
    with db:
        old = [r[0] for r in db.execute("SELECT panel_id FROM panels WHERE chapter=410")]
        for panel_id in old:
            db.execute("DELETE FROM text_segments WHERE panel_id=?", (panel_id,))
        db.execute("DELETE FROM panels WHERE chapter=410")
        db.execute("INSERT OR REPLACE INTO chapters(chapter,title,page_count,edition,language) VALUES(410,?,?,?,?)", ("Negotiation: Part 4",19,"","en"))
        for key in sorted(P):
            for order, (ps, pe, chars, loc, visual, texts) in enumerate(P[key], 1):
                page = f"p{ps:02d}" if ps == pe else f"p{ps:02d}-{pe:02d}"
                panel_id = f"ch410-{page}-{order:02d}"
                db.execute("""INSERT INTO panels(panel_id,chapter,page_start,page_end,panel_order,panel_types,characters_on_panel,location,visual_description,review_status,silent_panel)
                              VALUES(?,410,?,?,?,'standard',?,?,?,'needs_review',?)""",
                           (panel_id, ps, pe, order, chars, loc, visual, int(not texts)))
                for n, (speaker, mode, text) in enumerate(texts, 1):
                    db.execute("INSERT INTO text_segments(panel_id,segment_order,speaker,mode,text) VALUES(?,?,?,?,?)",
                               (panel_id,n,speaker,mode,text))
    panels = db.execute("SELECT COUNT(*) FROM panels WHERE chapter=410").fetchone()[0]
    segments = db.execute("SELECT COUNT(*) FROM text_segments t JOIN panels p USING(panel_id) WHERE p.chapter=410").fetchone()[0]
    print(f"Seeded chapter 410: {panels} panels, {segments} text segments")


if __name__ == "__main__":
    main()
