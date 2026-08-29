#!/usr/bin/env python3
"""Archive every image attached to a Togashi post (Agents.md sec. 7 "media information").

pbs.twimg.com URLs rot. Once an image is gone, an un-transcribed image-only post
is permanently unrecoverable evidence, so the images are pulled down before any
transcription work starts.

Idempotent: files already on disk are skipped, so this is safe to re-run.
"""
import glob
import json
import os
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "data", "raw", "tweets")
MEDIA = os.path.join(HERE, "..", "data", "raw", "tweet_media")
UA = {"User-Agent": "TogashiForecast/0.1 (research; +https://github.com/geanodong-bcrs/hxh-forecast)"}


def media_urls(payload):
    """Collect from both photos[] and mediaDetails[] - neither is complete alone."""
    urls = []
    for ph in payload.get("photos") or []:
        if ph.get("url"):
            urls.append(ph["url"])
    for md in payload.get("mediaDetails") or []:
        u = md.get("media_url_https")
        if u and u not in urls:
            urls.append(u)
    return urls


def main():
    os.makedirs(MEDIA, exist_ok=True)
    have = {os.path.basename(p) for p in glob.glob(os.path.join(MEDIA, "*"))}
    todo, skipped = [], 0
    for path in sorted(glob.glob(os.path.join(RAW, "*.json"))):
        rec = json.load(open(path))
        p = rec.get("payload") or {}
        tid = rec["tweet_id"]
        for u in media_urls(p):
            base = u.split("/")[-1].split("?")[0]
            name = "%s_%s" % (tid, base)
            if not name.lower().endswith((".jpg", ".png", ".jpeg", ".webp")):
                name += ".jpg"
            if name in have:
                skipped += 1
                continue
            todo.append((name, u))

    print("to download: %d   already on disk: %d" % (len(todo), skipped))
    ok = fail = 0
    for i, (name, u) in enumerate(todo, 1):
        # ask for the large rendition; twimg ignores the param if unsupported
        url = u if "?" in u else u + "?format=jpg&name=large"
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                data = r.read()
            with open(os.path.join(MEDIA, name), "wb") as fh:
                fh.write(data)
            ok += 1
        except Exception as exc:
            print("  FAIL %s: %s" % (name, exc))
            fail += 1
        if i % 50 == 0:
            print("  %d/%d  ok=%d fail=%d" % (i, len(todo), ok, fail))
        time.sleep(0.25)
    print("done: ok=%d fail=%d  total files=%d" % (ok, fail, len(os.listdir(MEDIA))))


if __name__ == "__main__":
    main()
