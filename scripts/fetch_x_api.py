#!/usr/bin/env python3
"""Full timeline backfill / incremental poll via the X API v2.

Two modes:
  --backfill   page back through the whole timeline (one-time, ~$0.005/post)
  (default)    incremental: pass --since <id> or use the newest id on disk

Wayback discovery is a lower bound — a single five-post sample already showed a
20% miss rate, and the missing post was ch.424's manuscript completion on the
batch being actively forecast. This is the authoritative discovery channel; the
syndication endpoint stays as a free hydrator and Wayback as the archival
backstop.

Raw API responses are written verbatim to data/raw/x_api/ before anything is
derived from them.
"""
import glob
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
D = lambda *p: os.path.join(HERE, "..", *p)
USER_ID = "1528978792617611264"
RAW_API = D("data", "raw", "x_api")
RAW_TW = D("data", "raw", "tweets")

FIELDS = {
    "max_results": "100",
    "tweet.fields": "created_at,text,attachments,entities,public_metrics,lang,referenced_tweets",
    "expansions": "attachments.media_keys",
    "media.fields": "url,type,media_key,width,height",
}


def token():
    for line in open(D(".env")):
        m = re.match(r"\s*X_BEARER_TOKEN\s*=\s*(.+?)\s*$", line)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    sys.exit("X_BEARER_TOKEN not found in .env")


def call(tok, params):
    url = ("https://api.x.com/2/users/%s/tweets?" % USER_ID) + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + tok,
                                               "User-Agent": "TogashiForecast/0.1"})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode()[:400]
            if e.code == 429:                      # rate limited
                print("  429, backing off 60s"); time.sleep(60); continue
            print("  HTTP %d: %s" % (e.code, body))
            raise
        except Exception as exc:
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))


def snowflake(tid):
    return datetime.fromtimestamp((((int(tid) >> 22) + 1288834974657)) / 1000, timezone.utc)


def main():
    tok = token()
    os.makedirs(RAW_API, exist_ok=True)
    os.makedirs(RAW_TW, exist_ok=True)
    have = {os.path.basename(f)[:-5] for f in glob.glob(os.path.join(RAW_TW, "*.json"))}
    print("on disk before: %d posts" % len(have))

    backfill = "--backfill" in sys.argv
    params = dict(FIELDS)
    if not backfill:
        since = None
        if "--since" in sys.argv:
            since = sys.argv[sys.argv.index("--since") + 1]
        elif have:
            since = max(have, key=int)
        if since:
            params["since_id"] = since
            print("incremental poll since_id=%s" % since)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    pages, total, new = 0, 0, 0
    media_by_key = {}
    while True:
        d = call(tok, params)
        pages += 1
        with open(os.path.join(RAW_API, "timeline_%s_p%02d.json" % (stamp, pages)), "w") as fh:
            json.dump(d, fh, ensure_ascii=False, indent=1)
        posts = d.get("data", []) or []
        for m in (d.get("includes", {}) or {}).get("media", []) or []:
            media_by_key[m["media_key"]] = m
        total += len(posts)

        for p in posts:
            tid = p["id"]
            if tid in have:
                continue
            keys = (p.get("attachments") or {}).get("media_keys", []) or []
            photos = [{"url": media_by_key[k]["url"]} for k in keys
                      if k in media_by_key and media_by_key[k].get("url")]
            rec = {
                "tweet_id": tid,
                "id_created_at_utc": snowflake(tid).isoformat(),
                "retrieved_utc": datetime.now(timezone.utc).isoformat(),
                "source": "api.x.com/2/users/:id/tweets",
                "source_type": "x_api_v2_bearer",
                "wayback_snapshots": [],
                "discovery": "x_api_v2_user_timeline",
                "hydrated": True,
                "payload": {
                    "id_str": tid, "text": p.get("text", ""),
                    "created_at": p.get("created_at"), "lang": p.get("lang"),
                    "photos": photos,
                    "favorite_count": (p.get("public_metrics") or {}).get("like_count"),
                    "conversation_count": (p.get("public_metrics") or {}).get("reply_count"),
                    "user": {"id_str": USER_ID, "screen_name": "Un4v5s8bgsVk9Xp",
                             "name": "冨樫義博"},
                    "entities": p.get("entities", {}),
                },
            }
            with open(os.path.join(RAW_TW, tid + ".json"), "w") as fh:
                json.dump(rec, fh, ensure_ascii=False, indent=1)
            have.add(tid)
            new += 1

        nxt = (d.get("meta") or {}).get("next_token")
        print("  page %2d: %3d posts (%d new so far)" % (pages, len(posts), new))
        if not backfill or not nxt or not posts:
            break
        params["pagination_token"] = nxt
        time.sleep(1.0)

    print("\npages=%d  posts_read=%d  new_to_disk=%d  total_on_disk=%d"
          % (pages, total, new, len(have)))
    print("approx cost: $%.2f  (%d posts read x $0.005)" % (total * 0.005, total))


if __name__ == "__main__":
    main()
