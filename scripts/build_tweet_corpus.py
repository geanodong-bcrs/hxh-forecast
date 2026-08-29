#!/usr/bin/env python3
"""raw/tweets -> processed/tweets.csv  (Agents.md sec. 7)

The raw Japanese text is copied through VERBATIM into text_ja and is never
normalised, trimmed or reinterpreted here. text_body is a convenience column
holding the same text with t.co links stripped; downstream event extraction
should read text_ja and treat text_body as a hint only.
"""
import csv
import glob
import json
import os
import re
from collections import Counter
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "data", "raw", "tweets")
PROC = os.path.join(HERE, "..", "data", "processed")
TOGASHI_USER_ID = "1528978792617611264"

TCO = re.compile(r"https://t\.co/\w+")
CHAPTER_RE = re.compile(r"No\.?\s*(\d{3})")


def body_text(p):
    t = p.get("text") or ""
    dtr = p.get("display_text_range")
    if dtr and len(dtr) == 2:
        t = t[dtr[0]:dtr[1]]
    return TCO.sub("", t).strip()


def main():
    rows = []
    for path in sorted(glob.glob(os.path.join(RAW, "*.json"))):
        rec = json.load(open(path))
        p = rec.get("payload")
        if not p:
            continue
        user = p.get("user") or {}
        photos = p.get("photos") or []
        media = p.get("mediaDetails") or []
        text = p.get("text") or ""
        body = body_text(p)
        chapters = sorted(set(CHAPTER_RE.findall(body)))
        rows.append({
            "tweet_id": rec["tweet_id"],
            "created_at_utc": p.get("created_at") or rec["id_created_at_utc"],
            "id_created_at_utc": rec["id_created_at_utc"],
            "author_id": user.get("id_str", ""),
            "author_screen_name": user.get("screen_name", ""),
            "is_togashi": int(user.get("id_str") == TOGASHI_USER_ID),
            "lang": p.get("lang", ""),
            "text_ja": text,
            "text_body": body,
            "has_text": int(bool(body)),
            "n_media": len(photos) or len(media),
            "media_urls": " ".join(ph.get("url", "") for ph in photos if ph.get("url")),
            "chapters_mentioned": " ".join(chapters),
            "n_chapters_mentioned": len(chapters),
            "favorite_count": p.get("favorite_count", ""),
            "conversation_count": p.get("conversation_count", ""),
            "is_edited": int(bool(p.get("isEdited"))),
            "tweet_url": "https://x.com/%s/status/%s" % (
                user.get("screen_name", "i"), rec["tweet_id"]),
            "source": rec["source"],
            "source_type": rec["source_type"],
            "retrieved_utc": rec["retrieved_utc"],
            "wayback_snapshots": len(rec.get("wayback_snapshots") or []),
        })
    rows.sort(key=lambda r: r["id_created_at_utc"])

    os.makedirs(PROC, exist_ok=True)
    with open(os.path.join(PROC, "tweets.csv"), "w", newline="") as fh:
        wr = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)

    own = [r for r in rows if r["is_togashi"]]
    with_text = [r for r in own if r["has_text"]]
    with_ch = [r for r in own if r["n_chapters_mentioned"]]
    months = Counter(r["id_created_at_utc"][:7] for r in own)
    meta = {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "handle": "Un4v5s8bgsVk9Xp",
        "row_count": len(rows),
        "by_togashi": len(own),
        "span": [own[0]["id_created_at_utc"][:10], own[-1]["id_created_at_utc"][:10]],
        "with_text": len(with_text),
        "image_only": len(own) - len(with_text),
        "image_only_pct": round(100.0 * (len(own) - len(with_text)) / len(own), 1),
        "mentioning_chapter_number": len(with_ch),
        "active_months": len(months),
        "discovery": "Wayback CDX enumeration of status URLs",
        "hydration": "cdn.syndication.twimg.com (unauthenticated)",
        "completeness": "UNKNOWN - discovery is limited to tweets the Wayback "
                        "Machine captured. Deleted tweets and never-archived "
                        "tweets are invisible. Treat counts as a lower bound.",
    }
    with open(os.path.join(PROC, "tweets.meta.json"), "w") as fh:
        json.dump(meta, fh, indent=2, ensure_ascii=False)
    print(json.dumps(meta, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
