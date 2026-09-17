#!/usr/bin/env python3
"""Keep a local record of what THIS account has posted.

    python3 scripts/fetch_own_posts.py              # newest 10, incremental
    python3 scripts/fetch_own_posts.py --all        # backfill, paginated
    python3 scripts/fetch_own_posts.py --dry-run    # show, write nothing

Nothing in the project records the account's own output. `data/processed/
tweets.csv` is Togashi's timeline, `poll_log.csv` records polling actions, and
`reply_bot.py` stores only the reply ID -- not its text. So once the bot posts,
what was publicly claimed exists solely on X's servers.  That matters twice
over: the calibration work in `docs/announcement_record.md` turns on what was
publicly known and when, and a corpus of the account's own writing is the only
way to match its voice rather than guess at it.

Reads are metered per post, so the poll is incremental by default: the newest
id seen is kept in this folder's `state.json` and sent as `since_id`, and a
poll that returns nothing should cost nothing.  `scripts/x_usage.py` is the
instrument for confirming that -- run it either side of an empty poll.

Output is append-only JSONL, one object per post, deduplicated by id.  An
edited post keeps its id, so a later fetch appends a second record rather than
overwriting the first; both are kept and `fetched_at` distinguishes them.

This folder is NOT published.  `scripts/deploy_site.py` names each data
subdirectory it copies and this is not among them, and a DENY pattern catches
it as a second guard.
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

OUT_DIR = os.path.join(HERE, "..", "data", "own_posts")
POSTS = os.path.join(OUT_DIR, "posts.jsonl")
STATE = os.path.join(OUT_DIR, "state.json")

FIELDS = ("created_at,conversation_id,lang,public_metrics,referenced_tweets,"
          "in_reply_to_user_id,edit_history_tweet_ids")


def get_json(url, access):
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + access})
    try:
        with urllib.request.urlopen(req, timeout=45) as response:
            return json.loads(response.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode(errors="replace")[:800]
        raise SystemExit("own-posts request failed: HTTP %d\n%s" % (exc.code, body))


def load_state():
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as handle:
            return json.load(handle)
    return {}


def existing_ids():
    """Every (id, fetched_at) already on disk, so re-fetches are not appended."""
    seen = set()
    if not os.path.exists(POSTS):
        return seen
    with open(POSTS, encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                seen.add((str(row["tweet_id"]), row.get("text", "")))
    return seen


def classify(tweet):
    """What kind of post this is, from its referenced_tweets edge."""
    kinds = {ref.get("type") for ref in (tweet.get("referenced_tweets") or [])}
    if "retweeted" in kinds:
        return "retweet"
    if "replied_to" in kinds:
        return "reply"
    if "quoted" in kinds:
        return "quote"
    return "original"


def fetch(access, user_id, since_id, want_all, limit):
    """Newest-first pages from /2/users/:id/tweets, stopping at since_id."""
    collected, token = [], None
    while True:
        params = {"max_results": 100 if want_all else max(5, min(limit, 100)),
                  "tweet.fields": FIELDS}
        if since_id:
            params["since_id"] = since_id
        if token:
            params["pagination_token"] = token
        payload = get_json("https://api.x.com/2/users/%s/tweets?%s"
                           % (user_id, urllib.parse.urlencode(params)), access)
        collected.extend(payload.get("data", []) or [])
        token = (payload.get("meta") or {}).get("next_token")
        if not want_all or not token:
            break
        if not since_id and len(collected) >= 3200:
            # X caps the user-timeline endpoint around here; stop rather than
            # loop forever against a cursor that never empties.
            break
    return collected if want_all else collected[:limit]


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--limit", type=int, default=10,
                        help="newest posts to request (default: 10)")
    parser.add_argument("--all", action="store_true",
                        help="paginate the full available timeline (first backfill)")
    parser.add_argument("--since-id", default=None,
                        help="override the stored cursor")
    parser.add_argument("--dry-run", action="store_true",
                        help="print what would be written, write nothing")
    args = parser.parse_args()

    state = load_state()
    since_id = args.since_id or (None if args.all else state.get("newest_id"))

    access = x_post.refresh()
    me = get_json("https://api.x.com/2/users/me", access)["data"]
    tweets = fetch(access, me["id"], since_id, args.all, args.limit)

    seen = existing_ids()
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    fresh = []
    for tweet in tweets:
        tid, text = str(tweet["id"]), tweet.get("text", "")
        if (tid, text) in seen:
            continue
        seen.add((tid, text))
        fresh.append({
            "tweet_id": tid,
            "created_at": tweet.get("created_at"),
            "kind": classify(tweet),
            "text": text,
            "lang": tweet.get("lang"),
            "conversation_id": tweet.get("conversation_id"),
            "in_reply_to_user_id": tweet.get("in_reply_to_user_id"),
            "referenced_tweets": tweet.get("referenced_tweets") or [],
            "edit_history_tweet_ids": tweet.get("edit_history_tweet_ids") or [],
            "public_metrics": tweet.get("public_metrics"),
            "url": "https://x.com/%s/status/%s" % (me.get("username", "i"), tid),
            "author": {"id": me.get("id"), "username": me.get("username")},
            "fetched_at": now,
        })

    newest = max([str(t["id"]) for t in tweets] +
                 ([since_id] if since_id else []), key=int, default=None)

    if args.dry_run:
        print(json.dumps({"account": "@" + me.get("username", ""),
                          "returned": len(tweets), "new": len(fresh),
                          "would_set_newest_id": newest,
                          "posts": fresh}, ensure_ascii=False, indent=2))
        return 0

    os.makedirs(OUT_DIR, exist_ok=True)
    if fresh:
        with open(POSTS, "a", encoding="utf-8") as handle:
            for record in fresh:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    if newest:
        state.update({"newest_id": newest, "last_poll_utc": now,
                      "account": me.get("username")})
        with open(STATE, "w", encoding="utf-8") as handle:
            json.dump(state, handle, indent=1, ensure_ascii=False)
            handle.write("\n")

    total = sum(1 for line in open(POSTS, encoding="utf-8")) if os.path.exists(POSTS) else 0
    print("@%s: %d returned, %d new -> %s (%d on file)"
          % (me.get("username", "?"), len(tweets), len(fresh),
             os.path.relpath(POSTS, os.path.join(HERE, "..")), total))
    for record in fresh[:5]:
        print("  %s  %-8s %s" % (record["created_at"], record["kind"],
                                 record["text"].replace("\n", " ")[:70]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
