#!/usr/bin/env python3
"""The automation loop: poll X, rebuild what changed, forecast (Agents.md §16, §19).

One entry point for every scheduled and manual run. It decides what actually
needs doing rather than blindly running thirteen scripts:

    poll X (since_id)
        |
        +-- new posts?        -> media, corpus, vision, events, intervals   trigger=tweet
        +-- review_queue.csv changed? -> merge, events, intervals           trigger=annotation
        +-- new JST day?      -> nothing to rebuild                         trigger=daily
        +-- none of the above -> log the poll and stop, no snapshot
        |
    build prior -> level2 -> posterior -> append-only snapshot

WHY AN EMPTY POLL WRITES NO SNAPSHOT. §16 wants every forecast preserved, and it
is preserved: a run with no new evidence and no new day produces a forecast
identical to the one already on disk. Writing it eight times a day would bury the
§17 evolution chart in ~2,900 duplicate points a year and make a genuine change
harder to see, not easier. Empty polls go to poll_log.csv, which is the honest
record of "we looked and there was nothing".

WHAT COUNTS AS EVIDENCE CHANGING. Three things, and a human confirmation is one
of them — a reviewer accepting an image reading changes the evidence without any
new tweet, and must produce its own revised snapshot (§8, and the provisional ->
revised pattern in docs/next_session.md).
"""
import argparse
import csv
import glob
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
D = lambda *p: os.path.join(HERE, "..", *p)
AUTO = D("data", "automation")
STATE = os.path.join(AUTO, "state.json")
POLL_LOG = os.path.join(AUTO, "poll_log.csv")
RUN_LOG = os.path.join(AUTO, "runs")
RAW_TW = D("data", "raw", "tweets")
REVIEW = D("data", "annotations", "review_queue.csv")

JST = timezone(timedelta(hours=9))
POLL_COLS = ["polled_utc", "polled_jst", "run_id", "new_posts", "new_tweet_ids",
             "review_changed", "daily", "action", "note"]


def now():
    return datetime.now(timezone.utc)


def sha(path):
    if not os.path.exists(path):
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def load_state():
    if os.path.exists(STATE):
        with open(STATE, encoding="utf-8") as fh:
            return json.load(fh)
    return {}


def save_state(s):
    os.makedirs(AUTO, exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as fh:
        json.dump(s, fh, indent=2)


def tweet_ids():
    return {os.path.basename(p)[:-5] for p in glob.glob(os.path.join(RAW_TW, "*.json"))}


def log_poll(row):
    os.makedirs(AUTO, exist_ok=True)
    new = not os.path.exists(POLL_LOG)
    with open(POLL_LOG, "a", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=POLL_COLS)
        if new:
            w.writeheader()
        w.writerow(row)


class Runner:
    """Runs a pipeline step, tees its output to the run log, stops on failure."""

    def __init__(self, run_id, env, dry):
        self.run_id, self.env, self.dry = run_id, env, dry
        os.makedirs(RUN_LOG, exist_ok=True)
        self.path = os.path.join(RUN_LOG, "%s.log" % run_id)
        self.failed = []

    def __call__(self, script, *args):
        cmd = [sys.executable, os.path.join(HERE, script)] + list(args)
        label = " ".join([script] + list(args))
        print("  -> %s" % label)
        if self.dry:
            return True
        p = subprocess.run(cmd, capture_output=True, text=True,
                           env=self.env, cwd=D())
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write("\n%s\n$ %s\n%s\n%s" % ("=" * 70, label, "=" * 70, p.stdout))
            if p.stderr:
                fh.write("\n--- stderr ---\n%s" % p.stderr)
        if p.returncode != 0:
            print("     FAILED (exit %d) — see %s"
                  % (p.returncode, os.path.relpath(self.path, D())))
            tail = (p.stderr or p.stdout or "").strip().splitlines()[-6:]
            for line in tail:
                print("     | %s" % line)
            self.failed.append(label)
            return False
        return True


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--poll", dest="poll", action="store_true", default=True,
                    help="poll the X API first (default)")
    ap.add_argument("--no-poll", dest="poll", action="store_false",
                    help="skip the API call; rebuild and forecast from data on disk")
    ap.add_argument("--trigger", default=None,
                    choices=["daily", "tweet", "annotation", "manual"],
                    help="force the recorded trigger instead of inferring it")
    ap.add_argument("--daily", action="store_true",
                    help="guarantee one snapshot for today even with no new evidence "
                         "(the scheduled 09:30 run; guarded so it fires once a day)")
    ap.add_argument("--force", action="store_true",
                    help="forecast and snapshot even if nothing changed")
    ap.add_argument("--no-vision", action="store_true",
                    help="skip auto-transcription of new images")
    ap.add_argument("--no-reply", action="store_true",
                    help="skip the reply-bot decision entirely")
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would run; touch nothing")
    args = ap.parse_args()

    run_id = now().strftime("%Y%m%dT%H%M%SZ")
    state = load_state()
    t0 = now()
    jst_today = t0.astimezone(JST).strftime("%Y-%m-%d")

    print("run %s   %s UTC / %s JST"
          % (run_id, t0.strftime("%Y-%m-%d %H:%M"), jst_today))

    # ---------- 1. what changed? ----------
    before = tweet_ids()
    env = dict(os.environ, TOGASHI_RUN_ID=run_id)

    new_ids = set()
    if args.poll:
        print("polling X...")
        r = Runner(run_id, env, args.dry_run)
        if not r("fetch_x_api.py"):
            log_poll({"polled_utc": t0.isoformat(), "polled_jst": jst_today,
                      "run_id": run_id, "new_posts": "", "new_tweet_ids": "",
                      "review_changed": "", "daily": "", "action": "poll_failed",
                      "note": "fetch_x_api.py exited non-zero"})
            return 1
        new_ids = tweet_ids() - before
    else:
        print("poll skipped (--no-poll)")

    review_sha = sha(REVIEW)
    review_changed = bool(review_sha) and review_sha != state.get("review_queue_sha", "")

    # The daily snapshot is guarded on the LOCAL date, because that is what the
    # schedule is expressed in — one 09:30 run a day. The guard exists only for
    # idempotency: if launchd replays a run missed while the Mac slept, or the
    # job is kicked by hand, today still gets one daily snapshot rather than two.
    # The hourly polls never trigger on the date; they trigger on evidence.
    local_today = t0.astimezone().strftime("%Y-%m-%d")
    daily_due = args.daily and local_today != state.get("last_daily_local", "")

    print("  new posts:        %d%s"
          % (len(new_ids), ("  " + ", ".join(sorted(new_ids))) if new_ids else ""))
    print("  review_queue:     %s" % ("changed" if review_changed else "unchanged"))
    if args.daily:
        print("  daily snapshot:   %s"
              % ("due (%s)" % local_today if daily_due
                 else "already written for %s" % local_today))

    trigger = args.trigger or ("tweet" if new_ids else
                               "annotation" if review_changed else
                               "daily" if daily_due else
                               "manual" if args.force else None)

    if trigger is None:
        print("\nnothing changed — no snapshot written (see docstring)")
        log_poll({"polled_utc": t0.isoformat(), "polled_jst": jst_today,
                  "run_id": run_id, "new_posts": 0, "new_tweet_ids": "",
                  "review_changed": 0, "daily": 0, "action": "no_change",
                  "note": ""})
        return 0

    print("\ntrigger: %s" % trigger)
    detail = (",".join(sorted(new_ids)) if new_ids else
              "review_queue.csv updated" if review_changed else
              "scheduled daily run" if trigger == "daily" else "")
    env["TOGASHI_TRIGGER"] = trigger
    env["TOGASHI_TRIGGER_DETAIL"] = detail
    run = Runner(run_id, env, args.dry_run)

    # ---------- 1b. refresh the publication record ----------
    # Once a day only: this is the network side of the publication data, and it
    # does not change between hourly polls. Without it `chapters.csv` freezes at
    # whatever was last fetched by hand, so the loop cannot see a chapter
    # actually appearing -- which is the single most informative thing that can
    # happen to this forecast. A failure here is not fatal: the forecast is
    # still better rebuilt on stale publication data than not rebuilt at all.
    #
    # NOTE: this refreshes Hunterpedia (chapters) only. `wsj_issues.csv`, which
    # supplies `last_obs` and therefore the continuous no-start conditioning,
    # comes from jajanken and has no fetch script -- the raw HTML was collected
    # by hand. Until one exists, issues ruled out ahead of the calendar have to
    # be recorded in data/annotations/known_absent_issues.csv.
    if daily_due or trigger == "daily":
        print("\npublication record:")
        if run("fetch_hunterpedia_chapters.py"):
            run("build_chapter_dataset.py")
            run("validate_chapters.py")
        else:
            print("  publication fetch failed — continuing on the existing data")

    # ---------- 2. rebuild only what the change touches ----------
    if new_ids:
        print("\ningest:")
        run("fetch_tweet_media.py")
        run("build_tweet_corpus.py")
        if not args.no_vision:
            run("vision_pass.py")

    if new_ids or review_changed:
        print("\nderived data:")
        run("merge_review.py")
        run("review_pending.py")
        run("attribute_chapters.py")
        run("extract_events.py")
        run("build_intervals.py")

    # ---------- 3. forecast ----------
    print("\nforecast:")
    # build_level2.py is retained as the reproducible v1 analog implementation
    # for historical snapshots.  The live Level 2 calculation is now the
    # readiness-coordinate model inside build_posterior.py.
    ok = (run("build_batch_prior.py")
          and run("build_posterior.py"))
    if ok:
        # the page reads the snapshot just written, so it is never staler than
        # the forecast; if the forecast failed there is nothing new to render.
        run("build_site.py")
        # Publish. Until now the loop rebuilt site/ locally and stopped there,
        # so the public page only moved when someone ran the deploy by hand --
        # it sat 1.5 days behind the model. Ordered BEFORE the reply because the
        # reply text points readers at the site, and a link that lands on an
        # older forecast than the card is worse than a slow one.
        #
        # Not gated on: a push can fail on a network blip or an expired
        # credential, and that must not cost us the snapshot or the reply. The
        # deploy is a no-op when nothing changed, and its own denylist still
        # aborts before committing if anything unpublishable slipped in.
        if not run("deploy_site.py", "--push"):
            print("  deploy failed — the forecast is still written; publish by hand")
        # Reply consideration runs only for a tweet-triggered update. Live from
        # 2026-09-03: the credentials are authorised as @HxHforecast and the
        # dry-run output has been watched. Five gates still stand in front of
        # every post (production event, forecast moved, not already replied,
        # daily cap of 2, PAUSE file), and `touch data/automation/PAUSE` stops
        # it without touching code.
        if new_ids and not args.no_reply:
            run("reply_bot.py", "--post")

    if args.dry_run:
        print("\n(dry run — nothing written)")
        return 0

    # ---------- 4. record ----------
    log_poll({"polled_utc": t0.isoformat(), "polled_jst": jst_today, "run_id": run_id,
              "new_posts": len(new_ids), "new_tweet_ids": " ".join(sorted(new_ids)),
              "review_changed": int(review_changed), "daily": int(daily_due),
              "action": "forecast" if ok else "forecast_failed", "note": detail})

    if ok:
        state["review_queue_sha"] = review_sha
        if daily_due or trigger == "daily":
            state["last_daily_local"] = local_today
        if new_ids:
            state["last_tweet_id"] = max(tweet_ids(), key=int)
        state["last_run_id"] = run_id
        state["last_run_utc"] = now().isoformat()
        save_state(state)

    # ---------- 5. summarise for a human ----------
    latest = sorted(glob.glob(D("data", "forecasts", "%s_*_posterior.json" % run_id)))
    if latest:
        with open(latest[0], encoding="utf-8") as fh:
            f = json.load(fh)
        print("\n" + "=" * 62)
        print("  %s   trigger=%s" % (f["target"], f["trigger"]))
        print("  median        %s" % f["median"])
        print("  80%% interval  %s .. %s" % tuple(f["intervals"]["80"]))
        print("  annotation    %s" % f["annotation_status"])
        print("  snapshot      %s" % os.path.relpath(latest[0], D()))
        print("=" * 62)

    if run.failed:
        print("\n%d step(s) FAILED: %s" % (len(run.failed), ", ".join(run.failed)))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
