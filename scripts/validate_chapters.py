#!/usr/bin/env python3
"""Independent cross-check of chapters.csv against jajanken.net (Agents.md sec. 26).

Hunterpedia (English community wiki) and jajanken (Japanese WSJ magazine index)
are independent of each other and record different things: Hunterpedia gives the
ON-SALE date, jajanken gives the COVER date plus the issue's table of contents.
Agreement on the issue assignment is therefore real corroboration, not an echo.

Writes data/processed/validation_report.csv and prints a summary. Does not
modify chapters.csv - disagreements are reported, not silently patched.
"""
import csv
import html
import os
import re
from datetime import datetime, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
PROC = os.path.join(HERE, "..", "data", "processed")
SRC = os.path.join(HERE, "..", "data", "raw", "jajanken", "hxh_chapters.html")

ROW_RE = re.compile(
    r'<td class="sequence[^"]*">\s*(\d+)\s*</td>\s*'
    r'<td class="issue">\s*<a href="/issues/(\d{4})-(\d{2})-(\d{2})/"[^>]*>\s*'
    r'(\d{4})年([\d・]+)号\s*</a>\s*</td>\s*'
    r'<td class="title">\s*(.*?)\s*</td>\s*'
    r'<td class="order">\s*(\d*)\s*</td>',
    re.S)

# A Japanese national holiday falling on the Monday on-sale day pushes the issue
# to the preceding Saturday, making cover-minus-on-sale 16 days instead of 14.
NORMAL_OFFSETS = {14, 16}


def explain_offset(off, on_sale, issue_no):
    """Why cover_date - on_sale_date departs from the standard 14 days.

    Anything left as "unexplained" is a candidate data error, not a quirk.
    """
    if off == 14:
        return "standard"
    if off == 16 and on_sale.weekday() == 5:
        return "holiday_saturday_shift"   # Monday national holiday -> Saturday on-sale
    if "-" in issue_no:
        return "combined_issue"           # 合併号 carries a stretched nominal date
    if int(issue_no.split("-")[0]) <= 8 or on_sale.month == 12:
        return "new_year_window"
    return "unexplained"


def parse_jajanken():
    txt = open(SRC, encoding="utf-8", errors="replace").read()
    out = []
    for seq, cy, cm, cd, iy, ino, title, order in ROW_RE.findall(txt):
        title_txt = html.unescape(re.sub(r"<[^>]+>", " ", title))
        # jajanken's own typos in this column include "Mo.195" and "NO.281"
        m = re.search(r"[NM]o\.\s*(\d+)", title_txt, re.I)
        out.append({
            "seq": int(seq),
            "cover_date": datetime(int(cy), int(cm), int(cd)).date(),
            "issue_year": int(iy),
            "issue_no": ino.replace("・", "-"),
            "chapter": int(m.group(1)) if m else None,
            "title_ja": re.sub(r"\s+", " ", title_txt).strip(),
            "toc_order": int(order) if order else None,
            "is_color": int("カラー" in title_txt),
        })
    return out


def main():
    ja = parse_jajanken()
    unnumbered = [r for r in ja if not r["chapter"]]
    # jajanken prints a chapter number per row and occasionally gets it wrong, so
    # the same number can appear twice. Its row ORDER is reliable; keep the first
    # occurrence and report the collisions rather than letting a later row win.
    ja_by_ch, dupes = {}, []
    for r in ja:
        if not r["chapter"]:
            continue
        if r["chapter"] in ja_by_ch:
            dupes.append((r["chapter"], ja_by_ch[r["chapter"]], r))
        else:
            ja_by_ch[r["chapter"]] = r

    hp = {}
    with open(os.path.join(PROC, "chapters.csv")) as fh:
        for r in csv.DictReader(fh):
            hp[int(r["chapter"])] = r

    rows = []
    for ch in sorted(set(hp) | set(ja_by_ch)):
        h, j = hp.get(ch), ja_by_ch.get(ch)
        rec = {"chapter": ch,
               "in_hunterpedia": int(h is not None),
               "in_jajanken": int(j is not None),
               "hp_on_sale": h["publication_date_jp"] if h else "",
               "hp_issue": ("%s-%s" % (h["wsj_issue_year"], h["wsj_issue_no"])) if h else "",
               "ja_issue": ("%s-%s" % (j["issue_year"], j["issue_no"])) if j else "",
               "ja_cover_date": j["cover_date"].isoformat() if j else "",
               "toc_order": j["toc_order"] if j else "",
               "is_color": j["is_color"] if j else "",
               "issue_match": "", "offset_days": "", "offset_explanation": "", "flag": ""}
        if h and j:
            rec["issue_match"] = int(rec["hp_issue"] == rec["ja_issue"])
            onsale = datetime.fromisoformat(h["publication_date_jp"]).date()
            off = (j["cover_date"] - onsale).days
            rec["offset_days"] = off
            rec["offset_explanation"] = explain_offset(off, onsale, j["issue_no"])
            flags = []
            if not rec["issue_match"]:
                flags.append("ISSUE_MISMATCH")
            if rec["offset_explanation"] == "unexplained":
                flags.append("UNEXPLAINED_OFFSET")
            rec["flag"] = ";".join(flags)
        else:
            rec["flag"] = "MISSING_FROM_ONE_SOURCE"
        rows.append(rec)

    path = os.path.join(PROC, "validation_report.csv")
    with open(path, "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)

    both = [r for r in rows if r["in_hunterpedia"] and r["in_jajanken"]]
    print("chapters in Hunterpedia: %d | in jajanken: %d | in both: %d"
          % (sum(r["in_hunterpedia"] for r in rows), sum(r["in_jajanken"] for r in rows), len(both)))
    print("issue assignment agrees: %d / %d" % (sum(r["issue_match"] for r in both), len(both)))
    print("\nnon-chapter jajanken rows (%d):" % len(unnumbered))
    for r in unnumbered:
        print("   seq %d  %d年%s号  %s" % (r["seq"], r["issue_year"], r["issue_no"], r["title_ja"][:60]))
    print("\njajanken duplicate chapter numbers (its typos, %d):" % len(dupes))
    for ch, first, second in dupes:
        print("   No.%d printed at seq %d (%d年%s号) and seq %d (%d年%s号)"
              % (ch, first["seq"], first["issue_year"], first["issue_no"],
                 second["seq"], second["issue_year"], second["issue_no"]))
    hard = [r for r in rows if any(f in r["flag"] for f in
                                   ("ISSUE_MISMATCH", "UNEXPLAINED_OFFSET",
                                    "OFFSET16_NOT_SATURDAY", "MISSING_FROM_ONE_SOURCE"))]
    print("\nhard flags: %d" % len(hard))
    for r in hard:
        print("   ch %s  hp=%s(%s)  ja=%s(cover %s)  off=%s  %s"
              % (r["chapter"], r["hp_issue"], r["hp_on_sale"], r["ja_issue"],
                 r["ja_cover_date"], r["offset_days"], r["flag"]))
    print("\nwrote %s" % path)


if __name__ == "__main__":
    main()
