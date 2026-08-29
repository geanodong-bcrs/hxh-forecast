#!/usr/bin/env python3
"""Phase 1A step 5 — corpus -> data/processed/production_events.csv

Turns three inputs into one structured event table under the Agents.md §8
taxonomy:

  tweets.csv                        text posts (verbatim Japanese)
  image_annotations.confirmed.csv   milestone text read off images, human-confirmed
  production_pages.csv              the page log, already chapter-attributed

Every event keeps the verbatim Japanese it came from and how it was derived, so
an interpretation can always be re-audited without going back to the raw layer.
"""
import csv
import os
import re
from collections import Counter

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
D = lambda *p: os.path.join(HERE, "..", *p)
TAX = D("data", "taxonomy", "production_events.yaml")
OUT = D("data", "processed", "production_events.csv")

# chapter reference, all observed notations
CH = re.compile(r"(?:No|NO|Mo)[.\s]?\s*(\d{3})")
# 「No398〜400」 - a range of chapters in one reference
RANGE = re.compile(r"(?:No|NO)[.\s]?\s*(\d{3})\s*[〜～~]\s*(\d{3})")
CONT = re.compile(r"^[\s　]+\S")          # indented continuation of the line above

COUNTDOWN = re.compile(r"あと\s*(\d+)\s*話")
BATCH_SCOPE = re.compile(r"(\d+)\s*話分")

DISRUPTION = [
    ("lost_manuscript", ["原稿捜索", "捜索中", "見つかりました", "紛失"]),
    ("health", ["治療", "回復", "症状", "体調", "入院"]),
    ("workspace", ["仕事場", "引っ越", "片付"]),
    ("staffing", ["スタッフを増員", "増員", "公募"]),
    ("workflow_change", ["半デジタル化", "作業細分化", "失敗でした", "模索中"]),
]
ANCILLARY = [
    ("tankobon", ["単行本"]),
    ("cover", ["表紙"]),
    ("colour_illustration", ["カラーの仕事", "カラー"]),
    ("commissioned", ["依頼イラスト"]),
]


def load_taxonomy():
    t = yaml.safe_load(open(TAX, encoding="utf-8"))
    stages = sorted([(p, s["id"]) for s in t["stages"] for p in s["patterns"]],
                    key=lambda x: -len(x[0]))
    statuses = sorted([(p, s["id"]) for s in t["statuses"] for p in s["patterns"]],
                      key=lambda x: -len(x[0]))
    return t, stages, statuses


def find_all(patterns, text):
    """Longest-first, non-overlapping, one hit per id.

    One id per phrase matters: 枠線 and フキダシ are separate patterns that both
    mean panel_layout, and without collapsing them a single phrase emits the
    same event twice.
    """
    hits, mask = [], [False] * len(text)
    for pat, pid in patterns:
        start = 0
        while True:
            i = text.find(pat, start)
            if i < 0:
                break
            if not any(mask[i:i + len(pat)]):
                hits.append((i, pid, pat))
                for j in range(i, i + len(pat)):
                    mask[j] = True
            start = i + 1
    seen, out = set(), []
    for pos, pid, pat in sorted(hits):
        if pid not in seen:
            seen.add(pid)
            out.append((pos, pid, pat))
    return out


def segment(text):
    """text -> [(chapter|None, phrase)], honouring indented continuation lines."""
    out, last_ch = [], None
    for line in str(text).split("\n"):
        if not line.strip():
            continue
        chapters = []
        for m in RANGE.finditer(line):
            a, b = int(m.group(1)), int(m.group(2))
            if 0 < b - a < 12:
                chapters.append((m.start(), list(range(a, b + 1)), m.end()))
        if not chapters:
            chapters = [(m.start(), [int(m.group(1))], m.end()) for m in CH.finditer(line)]
        if not chapters:
            # continuation of the previous chapter's statement
            out.append((last_ch if CONT.match(line) else None, line.strip()))
            continue
        for i, (pos, chs, end) in enumerate(chapters):
            stop = chapters[i + 1][0] if i + 1 < len(chapters) else len(line)
            phrase = line[end:stop].strip(" 　.、,…・:：")
            for c in chs:
                out.append((c, phrase))
            last_ch = chs[-1]
    return out


def dedupe(events):
    """Drop exact repeats of the same claim from the same post."""
    seen, out = set(), []
    for r in events:
        key = (r["tweet_id"], r["event_class"], str(r["chapter"]), r["stage"],
               r["status"], r["kind"], r["source_text_ja"], r["pages_manuscript"])
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


# A chapter mentioned far from the chapters in play around that date is almost
# certainly a typo. Togashi's 「No388.399…完成」 in Nov 2022 passes a static range
# check (388 is a real chapter) but is 10 chapters away from everything else he
# was working on, and ch.388 had been published four years earlier.
IMPLAUSIBLE_WINDOW_DAYS = 45
IMPLAUSIBLE_CHAPTER_DISTANCE = 15


def flag_implausible(events):
    from datetime import date

    pub = {}
    with open(D("data", "processed", "chapters.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["publication_date_jp"]:
                pub[int(r["chapter"])] = date.fromisoformat(r["publication_date_jp"])

    def mark(r, note):
        r["notes"] = (r["notes"] + "; " + note).strip("; ")
        r["confidence"] = "low"

    dated = [(date.fromisoformat(r["event_date"]), int(r["chapter"]), r)
             for r in events if str(r["chapter"]).strip().isdigit()]

    for d, ch, r in dated:
        # A chapter already in print cannot be reaching manuscript completion.
        # This is what catches 「No388.399…完成」 (388 published four years
        # earlier, a typo for 398) where a distance check does not: 388 is only
        # nine chapters from its neighbours. Retouch is exempt - Togashi really
        # does rework published chapters for the tankobon.
        p = pub.get(ch)
        if p and r["stage"] in ("manuscript_complete", "character_inking") \
                and (d - p).days > 30:
            mark(r, "chapter_already_published_%s" % p.isoformat())
            continue
        near = sorted(c for dd, c, _ in dated
                      if abs((dd - d).days) <= IMPLAUSIBLE_WINDOW_DAYS)
        if len(near) >= 3:
            med = near[len(near) // 2]
            if abs(ch - med) > IMPLAUSIBLE_CHAPTER_DISTANCE:
                mark(r, "chapter_temporally_implausible (neighbours ~%d)" % med)


def main():
    tax, stages, statuses = load_taxonomy()
    bare = tax.get("bare_status_scope", {})
    guard = tax["guards"]["chapter_number"]

    events, eid = [], 0

    def add(**kw):
        nonlocal eid
        eid += 1
        row = {c: "" for c in COLS}
        row["event_id"] = "E%05d" % eid
        row.update(kw)
        events.append(row)

    # ---------------- text posts + image milestone text ----------------
    sources = []
    with open(D("data", "processed", "tweets.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["is_togashi"] == "1" and r["has_text"] == "1" and r["text_body"].strip():
                sources.append((r["id_created_at_utc"], r["tweet_id"], r["text_body"],
                                "text_explicit", "high"))
    with open(D("data", "annotations", "image_annotations.confirmed.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["transcribed_text"].strip():
                conf = "high" if r["status"] == "confirmed" else "medium"
                sources.append((r["date"], r["tweet_id"], r["transcribed_text"],
                                "image_transcription", conf))

    for created, tid, text, method, conf in sources:
        date = created[:10]
        url = "https://x.com/Un4v5s8bgsVk9Xp/status/%s" % tid
        base = dict(event_date=date, post_created_at=created, tweet_id=tid,
                    source_url=url, extraction_method=method)

        segs = [(c, p) for c, p in segment(text) if p]
        for ch, phrase in segs:
            st_hits = find_all(stages, phrase)
            su_hits = find_all(statuses, phrase)

            if ch is not None:
                flag = "" if guard["min"] <= ch <= guard["max"] else "chapter_out_of_range"
                if st_hits:
                    for i, (pos, sid, pat) in enumerate(st_hits):
                        after = [h for h in su_hits if h[0] > pos]
                        su = (after[0][1] if after else (su_hits[-1][1] if su_hits else ""))
                        add(chapter=ch, event_class="chapter_stage", stage=sid, status=su,
                            source_text_ja=phrase, confidence=conf if su else "medium",
                            notes=("multi-stage phrase" if len(st_hits) > 1 else "") +
                                  ("; " + flag if flag else ""), **base)
                elif su_hits:
                    su = su_hits[0][1]
                    add(chapter=ch, event_class="chapter_stage",
                        stage=bare.get(su, "chapter_level"), status=su,
                        source_text_ja=phrase, confidence=conf,
                        notes="bare status, scoped to chapter" + ("; " + flag if flag else ""),
                        **base)

        # ---- non-chapter classes: scan each DISTINCT phrase once per post ----
        # A line naming three chapters yields three phrases; scanning per phrase
        # would fire the same disruption three times.
        for phrase in dict.fromkeys(p for _, p in segs):
            st_hits = find_all(stages, phrase)
            m = COUNTDOWN.search(phrase)
            if m:
                add(event_class="batch_countdown", chapters_remaining=m.group(1),
                    source_text_ja=phrase, confidence=conf, **base)
            m = BATCH_SCOPE.search(phrase)
            if m:
                add(event_class="batch_scope", n_chapters=m.group(1),
                    stage=st_hits[0][1] if st_hits else "",
                    source_text_ja=phrase, confidence=conf, **base)
            for kind, pats in DISRUPTION:
                if any(p in phrase for p in pats):
                    add(event_class="disruption", kind=kind,
                        source_text_ja=phrase, confidence=conf, **base)
                    break
            for kind, pats in ANCILLARY:
                if any(p in phrase for p in pats):
                    add(event_class="ancillary_work", kind=kind,
                        source_text_ja=phrase, confidence=conf, **base)
                    break

    # ---------------- page log ----------------
    with open(D("data", "processed", "production_pages.csv"), encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            add(chapter=r["chapter"], event_class="page_completed",
                pages_manuscript=r["pages_manuscript"], n_pages=r["n_pages"],
                event_date=r["date"], post_created_at=r["date"], tweet_id=r["tweet_id"],
                source_url="https://x.com/Un4v5s8bgsVk9Xp/status/%s" % r["tweet_id"],
                extraction_method=("image_transcription" if r["chapter_source"] != "enumerated"
                                   else "inferred"),
                confidence="high" if r["chapter_source"] == "reviewer_anchor" else "medium",
                source_text_ja=r["milestone_text"],
                notes="chapter via %s" % r["chapter_source"])

    events = dedupe(events)
    flag_implausible(events)

    events.sort(key=lambda r: (r["event_date"], r["event_id"]))
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLS)
        w.writeheader()
        w.writerows(events)

    # ---------------- report ----------------
    print("events: %d" % len(events))
    cls = Counter(r["event_class"] for r in events)
    for k, v in cls.most_common():
        print("  %-18s %4d" % (k, v))
    cs = [r for r in events if r["event_class"] == "chapter_stage"]
    print("\nchapter_stage stages:",
          dict(Counter(r["stage"] for r in cs).most_common()))
    print("chapter_stage statuses:",
          dict(Counter(r["status"] for r in cs).most_common()))
    print("\nextraction method:", dict(Counter(r["extraction_method"] for r in events)))
    print("confidence:       ", dict(Counter(r["confidence"] for r in events)))
    ch = [int(r["chapter"]) for r in events if str(r["chapter"]).strip().isdigit()]
    print("\nchapters covered: %d..%d (%d distinct)" % (min(ch), max(ch), len(set(ch))))
    print("date span: %s .. %s" % (events[0]["event_date"], events[-1]["event_date"]))
    bad = [r for r in events if "implausible" in r["notes"] or "out_of_range" in r["notes"]]
    if bad:
        print("\nflagged chapter numbers: %d" % len(bad))
        for r in bad[:8]:
            print("  %s ch%-5s %-24s %s" % (r["event_date"], r["chapter"],
                  r["source_text_ja"][:24], r["notes"][:52]))
    print("\nwrote %s" % OUT)


COLS = ["event_id", "event_date", "post_created_at", "chapter", "event_class",
        "stage", "status", "kind", "pages_manuscript", "n_pages",
        "chapters_remaining", "n_chapters",
        "source_text_ja", "extraction_method", "confidence", "notes",
        "tweet_id", "source_url"]

if __name__ == "__main__":
    main()
