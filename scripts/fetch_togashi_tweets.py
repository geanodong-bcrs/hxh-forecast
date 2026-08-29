#!/usr/bin/env python3
"""Fetch Togashi's posts into the immutable raw layer (Agents.md sec. 7).

Two-stage, because neither stage can do the other's job:

  discovery  Wayback CDX gives the set of tweet IDs that ever existed at
             x.com|twitter.com/<handle>/status/<id>. It does NOT give text -
             modern X captures are JavaScript shells with no content in them.
  hydration  cdn.syndication.twimg.com (the endpoint X's own embed widget uses)
             returns full structured JSON per ID without authentication.

Raw rule: one JSON file per tweet, written once, never rewritten. The original
Japanese text is preserved verbatim; any reinterpretation happens downstream.
"""
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

HANDLE = "Un4v5s8bgsVk9Xp"          # 冨樫義博 - verified 2026-08-27
USER_ID = "1528978792617611264"
UA = {"User-Agent": "TogashiForecast/0.1 (research; +https://github.com/geanodong-bcrs/hxh-forecast)"}
HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "data", "raw", "tweets")
IDS = os.path.join(HERE, "..", "data", "raw", "wayback", "tweet_ids.json")

SYNDICATION = "https://cdn.syndication.twimg.com/tweet-result?id=%s&lang=ja&token=a"
CDX = ("http://web.archive.org/cdx/search/cdx?url=%s/" + HANDLE +
       "/status/*&output=json&fl=original,timestamp,statuscode&limit=50000")

# Twitter snowflake epoch: IDs carry their own creation time, so we get exact
# timestamps for every discovered tweet even if hydration later fails.
SNOWFLAKE_EPOCH_MS = 1288834974657


def snowflake_time(tweet_id):
    ms = (int(tweet_id) >> 22) + SNOWFLAKE_EPOCH_MS
    return datetime.fromtimestamp(ms / 1000, timezone.utc)


def get(url, timeout=45, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            if e.code in (404, 403):
                return None            # deleted / protected - a real outcome
            if attempt == retries - 1:
                raise
        except Exception:
            if attempt == retries - 1:
                raise
        time.sleep(2 * (attempt + 1))
    return None


def discover_ids():
    """Wayback CDX -> set of tweet IDs. Additive: never drops known IDs."""
    found = {}
    for host in ("x.com", "twitter.com"):
        try:
            rows = json.loads(get(CDX % host, timeout=120))
        except Exception as exc:
            print("  CDX %s failed: %s" % (host, exc))
            continue
        hdr, rows = rows[0], rows[1:]
        for row in rows:
            d = dict(zip(hdr, row))
            # Do not filter on statuscode. twitter.com captures are largely 301
            # redirects to x.com, but the ID in the URL is still a real tweet;
            # hydration is the actual availability test.
            m = re.search(r"/status/(\d+)", d["original"])
            if m:
                found.setdefault(m.group(1), []).append(d["timestamp"])
        print("  %-12s -> %d ids cumulative" % (host, len(found)))

    if os.path.exists(IDS):
        prior = json.load(open(IDS))
        for k, v in prior.items():
            found.setdefault(k, []).extend(v)
    merged = {k: sorted(set(v)) for k, v in found.items()}
    os.makedirs(os.path.dirname(IDS), exist_ok=True)
    json.dump(merged, open(IDS, "w"), indent=0)
    return merged


def hydrate(ids):
    os.makedirs(RAW, exist_ok=True)
    todo = [t for t in sorted(ids) if not os.path.exists(os.path.join(RAW, t + ".json"))]
    print("hydrating %d of %d (rest already on disk)" % (len(todo), len(ids)))
    ok = miss = 0
    for n, tid in enumerate(todo, 1):
        body = get(SYNDICATION % tid, timeout=30)
        rec = {
            "tweet_id": tid,
            "id_created_at_utc": snowflake_time(tid).isoformat(),
            "retrieved_utc": datetime.now(timezone.utc).isoformat(),
            "source": "cdn.syndication.twimg.com/tweet-result",
            "source_type": "x_syndication_api_unauthenticated",
            "wayback_snapshots": ids[tid],
            "hydrated": body is not None,
        }
        if body:
            try:
                rec["payload"] = json.loads(body)
                ok += 1
            except ValueError:
                rec["hydrated"] = False
                rec["raw_body"] = body[:5000]
                miss += 1
        else:
            miss += 1
        with open(os.path.join(RAW, tid + ".json"), "w") as fh:
            json.dump(rec, fh, ensure_ascii=False, indent=1)
        if n % 25 == 0 or n == len(todo):
            print("  %d/%d  ok=%d miss=%d" % (n, len(todo), ok, miss))
        time.sleep(0.7)
    return ok, miss


def main():
    if "--no-discover" in sys.argv and os.path.exists(IDS):
        ids = json.load(open(IDS))
        print("using %d cached ids" % len(ids))
    else:
        print("Discovering tweet IDs via Wayback CDX ...")
        ids = discover_ids()
        print("  %d distinct ids" % len(ids))
    ok, miss = hydrate(ids)
    print("\nhydrated ok=%d  unavailable=%d  total on disk=%d"
          % (ok, miss, len(os.listdir(RAW))))


if __name__ == "__main__":
    main()
