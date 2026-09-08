#!/usr/bin/env python3
"""Import recent @HxHforecast bookmarks into the private editorial inbox.

The first run defaults to the two newest bookmarks so an existing bookmark
library is not mistaken for a new editorial queue. Later runs may request more
and duplicate tweet IDs are ignored.
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import x_post

ROOT = os.path.join(HERE, "..")
OUT = os.path.join(ROOT, "data", "editorial", "bookmarks.jsonl")


def get_json(url, access):
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + access})
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")[:800]
        raise SystemExit("bookmark request failed: HTTP %d\n%s" % (exc.code, body))


def existing_ids():
    ids = set()
    if not os.path.exists(OUT):
        return ids
    with open(OUT, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                ids.add(str(json.loads(line)["tweet_id"]))
    return ids


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=2,
                        help="number of newest bookmarks to inspect (default: 2)")
    args = parser.parse_args()
    if not 1 <= args.limit <= 100:
        parser.error("--limit must be between 1 and 100")

    access = x_post.refresh()
    me = get_json("https://api.x.com/2/users/me", access)["data"]
    query = urllib.parse.urlencode({
        "max_results": max(10, args.limit),
        "tweet.fields": "created_at,author_id,conversation_id,lang,public_metrics,referenced_tweets",
        "expansions": "author_id,referenced_tweets.id,referenced_tweets.id.author_id",
        "user.fields": "name,username",
    })
    payload = get_json(
        "https://api.x.com/2/users/%s/bookmarks?%s" % (me["id"], query), access)

    users = {str(u["id"]): u for u in payload.get("includes", {}).get("users", [])}
    referenced = {str(t["id"]): t for t in payload.get("includes", {}).get("tweets", [])}
    seen = existing_ids()
    imported = []
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    for tweet in payload.get("data", [])[:args.limit]:
        tid = str(tweet["id"])
        if tid in seen:
            continue
        author = users.get(str(tweet.get("author_id")), {})
        refs = []
        for ref in tweet.get("referenced_tweets", []) or []:
            item = dict(ref)
            if str(ref.get("id")) in referenced:
                item["tweet"] = referenced[str(ref["id"])]
            refs.append(item)
        record = {
            "tweet_id": tid,
            "url": "https://x.com/%s/status/%s" % (author.get("username", "i"), tid),
            "text": tweet.get("text", ""),
            "created_at": tweet.get("created_at"),
            "lang": tweet.get("lang"),
            "author": {"id": tweet.get("author_id"),
                       "username": author.get("username"), "name": author.get("name")},
            "conversation_id": tweet.get("conversation_id"),
            "referenced_tweets": refs,
            "public_metrics": tweet.get("public_metrics"),
            "imported_at": now,
            "review_status": "new",
        }
        imported.append(record)
    if imported:
        with open(OUT, "a", encoding="utf-8") as handle:
            for record in imported:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(json.dumps({"account": "@" + me.get("username", ""),
                      "inspected": min(args.limit, len(payload.get("data", []))),
                      "imported": len(imported),
                      "bookmarks": imported}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
