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
  2. something actually changed — see below
  3. we have not already replied to that post
  4. the daily cap has not been reached
  5. data/automation/PAUSE does not exist

Gate 2 matters more than it looks. Most production posts move the forecast a
little or not at all, and "the forecast is unchanged" under someone's post is
worse than silence.

What counts as "changed" depends on which run the post is about, because Togashi
draws two runs ahead:

  * a post about the run BEING FORECAST (ch. 421-430) -> the forecast moved,
    forecast_delta.newsworthy();
  * a post about the run AFTER it (ch. 431-440) -> that run's readiness moved.
    Its forecast is Level 1 convolved with the predecessor's posterior and does
    not consume following-batch production, so its date is structurally fixed
    against these posts; gating on it would mean never replying, and bypassing
    the gate would mean the same card under every post. The progress bar is what
    that card actually reports, so the progress bar is what is gated on.

A post about neither run is left alone.
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
        # No date named, for the reason in build_card: the peak issue is the
        # argmax of a nearly flat front and moves around meaninglessly.
        pp = d["spike_pp"]
        lead = "That makes ch. %d %.1f points %s likely." % (
            d["chapter"], abs(pp), "more" if pp > 0 else "less")
    return ("%s\n\nBest guess is now %s, with an 80%% range of %s to %s.\n\n"
            "Updated automatically from %s. Model + full history in bio."
            % (lead, med,
               datetime.fromisoformat(d["i80"][0]).strftime("%-d %b"),
               datetime.fromisoformat(d["i80"][1]).strftime("%-d %b %Y"),
               subject))


def compose_following(d, evs, level):
    """Reply text for a post about the run AFTER the one being forecast.

    Deliberately not phrased as news about the date. That forecast cannot move
    on this evidence, so claiming it did would be false; what genuinely changed
    is how much of the run is drawn.
    """
    chs = sorted({int(float(e["chapter"])) for e in evs
                  if (e.get("chapter") or "").strip()})
    subject = ("Ch. %s" % ", ".join(str(c) for c in chs)) if chs else "This"
    med = datetime.fromisoformat(d["median"]).strftime("%-d %b %Y")
    return ("%s — that's the run after next.\n\n"
            "Chapters %d–%d are %.0f%% drawn. Best guess for ch. %d is %s "
            "(80%% range %s – %s), and ch. %d–%d has no schedule yet.\n\n"
            "Updated automatically. Model in bio."
            % (subject, d["chapter"], d["chapter"] + 9, level * 10, d["chapter"], med,
               datetime.fromisoformat(d["i80"][0]).strftime("%-d %b %y"),
               datetime.fromisoformat(d["i80"][1]).strftime("%-d %b %y"),
               d["chapter"] - 10, d["chapter"] - 1))


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

    # Reply only under a post about the run being forecast. Togashi draws two
    # runs ahead -- 431-433 are inked while 421-427 sit finished -- so a post
    # can easily concern chapters this forecast is not about. Without this the
    # oldest unreplied production post wins on tweet-id order, which means a
    # ch. 427 post can move the forecast while the reply lands under a ch. 433
    # post, telling his readers that 433 moved the ch. 421 estimate.
    #
    # A post carrying only chapter-less events (batch_scope, batch_countdown)
    # stays eligible: those are unattributed progress reports, and the running
    # batch is the only reading available for them.
    lo, hi = d["chapter"], d["chapter"] + 9
    nlo, nhi = hi + 1, hi + 10

    def run_of(tid):
        seen = [int(float(e["chapter"])) for e in hits[tid]
                if (e.get("chapter") or "").strip()]
        if not seen or any(lo <= c <= hi for c in seen):
            return "target"          # chapter-less reports read as the running batch
        if any(nlo <= c <= nhi for c in seen):
            return "following"
        return "other"

    routed = {t: run_of(t) for t in todo}
    on_target = [t for t in todo if routed[t] == "target"]
    on_following = [t for t in todo if routed[t] == "following"]

    if on_target:
        # The run being forecast: reply only when the forecast actually moved.
        ok, kind = fd.newsworthy(d)
        if not ok and not args.force:
            print("forecast did not move materially (%s) — staying quiet"
                  % fd.headline(d))
            return 0
        tid = on_target[0]
        text_fn = lambda: compose(d, hits[tid])
    elif on_following:
        # The run AFTER it. Its forecast is Level 1 convolved with the
        # predecessor's posterior and explicitly does not consume following-batch
        # production, so shift_days is structurally zero and the usual gate would
        # block for ever. The card's claim here is the progress bar, so that is
        # what is gated on: reply only when readiness has actually changed since
        # the last such reply. Without this the same card would go out under
        # every post in the run.
        d = fd.compute(target="next")
        if d is None:
            print("no comparable baseline for the following run — staying quiet")
            return 0
        level, _ = build_card.readiness_state(d["chapter"])
        last = state.get("last_following_level")
        if level is None:
            print("no readiness for ch. %d–%d — staying quiet"
                  % (d["chapter"], d["chapter"] + 9))
            return 0
        if last is not None and abs(level - last) < 1e-9 and not args.force:
            print("ch. %d–%d readiness unchanged at %.1f since the last reply — "
                  "staying quiet" % (d["chapter"], d["chapter"] + 9, level))
            return 0
        tid = on_following[0]
        text_fn = lambda: compose_following(d, hits[tid], level)
    else:
        chs = sorted({int(float(e["chapter"])) for t in todo for e in hits[t]
                      if (e.get("chapter") or "").strip()})
        print("post concerns ch. %s — neither the ch. %d–%d run being forecast "
              "nor the one after it; staying quiet"
              % (", ".join(str(c) for c in chs), lo, hi))
        return 0

    card = build_card.render(
        d, D("data", "cards", "%s_ch%d.png" % (d["run_id"], d["chapter"])))
    text = text_fn()

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
    if d.get("target_view") == "next":
        state["last_following_level"] = build_card.readiness_state(d["chapter"])[0]
    save_state(state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
