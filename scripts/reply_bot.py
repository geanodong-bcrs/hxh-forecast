#!/usr/bin/env python3
"""Reply to Togashi's PRODUCTION posts with an updated forecast card.

    python3 scripts/reply_bot.py                 # decide + render, never posts
    python3 scripts/reply_bot.py --post          # actually post (needs OAuth 2)

Scope is deliberately narrow. It replies only under posts that our own extractor
turned into production events — the threads that are already full of fans
tracking exactly this. It never replies to anything else he posts, and there is
no flag to make it.

Five gates, all of which must pass:

  1. the post produced at least one production event (it is a progress update)
  2. the forecast actually moved — see forecast_delta.newsworthy()
  3. we have not already replied to that post
  4. the daily cap has not been reached
  5. data/automation/PAUSE does not exist

Gate 2 matters more than it looks. Most production posts move the forecast a
little or not at all, and "the forecast is unchanged" under someone's post is
worse than silence.
"""
import argparse
import csv
import json
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
D = lambda *p: os.path.join(HERE, "..", *p)

import forecast_delta as fd
import build_card

STATE = D("data", "automation", "replies.json")
PAUSE = D("data", "automation", "PAUSE")
EVENTS = D("data", "processed", "production_events.csv")
MAX_PER_DAY = 2
PRODUCTION_CLASSES = {"chapter_stage", "page_completed", "batch_countdown", "batch_scope"}


def load_state():
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as fh:
            return json.load(fh)
    return {"replied": {}, "posted_dates": {}}


def save_state(s):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as fh:
        json.dump(s, fh, indent=2)


def production_events_for(tweet_ids):
    """Which of these posts our pipeline read as production updates."""
    hits = {}
    if not os.path.exists(EVENTS):
        return hits
    with open(EVENTS, encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            tid = (r.get("tweet_id") or "").strip()
            if tid in tweet_ids and r.get("event_class") in PRODUCTION_CLASSES:
                hits.setdefault(tid, []).append(r)
    return hits


def compose(d, evs):
    """The reply text. No link — a post containing one costs $0.20 against
    $0.015, so the URL lives in the bio and the card carries it as text."""
    kind = fd.newsworthy(d)[1]
    chs = sorted({int(float(e["chapter"])) for e in evs
                  if (e.get("chapter") or "").strip()})
    subject = ("ch. %s" % ", ".join(str(c) for c in chs)) if chs else "this update"
    med = datetime.fromisoformat(d["median"]).strftime("%-d %b")
    if kind == "date":
        n = abs(d["shift_days"])
        way = "earlier" if d["shift_days"] < 0 else "later"
        lead = "That moves the estimate for ch. %d %d day%s %s." % (
            d["chapter"], n, "" if n == 1 else "s", way)
    else:
        lead = "That shifts the odds for ch. %d by %+.1f points." % (
            d["chapter"], d["spike_pp"])
    return ("%s\n\nBest guess is now %s, with an 80%% range of %s to %s.\n\n"
            "Updated automatically from %s. Model + full history in bio."
            % (lead, med,
               datetime.fromisoformat(d["i80"][0]).strftime("%-d %b"),
               datetime.fromisoformat(d["i80"][1]).strftime("%-d %b %Y"),
               subject))


def post_to_x(text, image_path, in_reply_to):
    import x_post
    return x_post.post_reply(text, image_path, in_reply_to)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tweet", action="append", default=[],
                    help="candidate tweet ids (default: this run's new posts)")
    ap.add_argument("--post", action="store_true", help="actually post the reply")
    ap.add_argument("--force", action="store_true",
                    help="ignore the newsworthiness gate (still honours the rest)")
    args = ap.parse_args()

    if os.path.exists(PAUSE):
        print("PAUSED — data/automation/PAUSE exists; nothing will be posted")
        return 0

    ids = set(args.tweet) or set(
        (os.environ.get("TOGASHI_TRIGGER_DETAIL") or "").replace(",", " ").split())
    if not ids:
        print("no candidate posts")
        return 0

    hits = production_events_for(ids)
    if not hits:
        print("none of %s is a production update — not replying" % sorted(ids))
        return 0

    state = load_state()
    todo = [t for t in sorted(hits) if t not in state["replied"]]
    if not todo:
        print("already replied to %s" % sorted(hits))
        return 0

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if state["posted_dates"].get(today, 0) >= MAX_PER_DAY:
        print("daily cap of %d reached" % MAX_PER_DAY)
        return 0

    d = fd.compute()
    if d is None:
        # No honest baseline: either the first snapshot, or the model or target
        # changed since the last one. --force does not override this, because
        # there is no delta to report, only an incomparable pair.
        print("no comparable baseline (%s) — staying quiet" % fd.pick_pair()[2])
        return 0
    ok, kind = fd.newsworthy(d)
    if not ok and not args.force:
        print("forecast did not move materially (%s) — staying quiet"
              % fd.headline(d))
        return 0

    tid = todo[0]
    card = build_card.render(
        d, D("data", "cards", "%s_ch%d.png" % (d["run_id"], d["chapter"])))
    text = compose(d, hits[tid])

    print("=" * 62)
    print("reply to https://x.com/Un4v5s8bgsVk9Xp/status/%s" % tid)
    print("card: %s" % os.path.relpath(card, D()))
    print("-" * 62)
    print(text)
    print("=" * 62)
    print("%d characters" % len(text))

    if not args.post:
        print("\nDRY RUN — nothing posted. Re-run with --post when credentials exist.")
        return 0

    posted_id = post_to_x(text, card, tid)
    print("posted: https://x.com/i/status/%s" % posted_id)
    state["replied"][tid] = {"at": datetime.now(timezone.utc).isoformat(),
                             "run_id": d["run_id"], "reply_id": posted_id}
    state["posted_dates"][today] = state["posted_dates"].get(today, 0) + 1
    save_state(state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
