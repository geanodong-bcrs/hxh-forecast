#!/usr/bin/env python3
"""Fetch jajanken's Weekly Shonen Jump year page(s) into the raw layer.

    python3 scripts/fetch_jajanken_calendar.py          # current year (+ next in Dec)
    python3 scripts/fetch_jajanken_calendar.py 2026     # a specific year

Feeds build_issue_calendar.py -> data/processed/wsj_issues.csv. Until this
existed the year pages were collected by hand once (2026-08-26), the calendar
froze at 2026 no.39, and every later issue was a projected slot -- which is how
issues 43-46 went on sale without the batch and kept probability.

Raw layer rule (Agents.md sec. 27): each run writes a NEW timestamped file,
years_<YYYY>_<UTC timestamp>.html, and never rewrites an earlier one.
build_issue_calendar.py reads the newest file per year.
"""
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone

URL = "https://www.jajanken.net/years/%d"
UA = "TogashiForecast/0.1 (research; +https://github.com/geanodong-bcrs/hxh-forecast)"
RAW = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "jajanken")


def fetch(year):
    req = urllib.request.Request(URL % year, headers={"User-Agent": UA})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                return r.read()
        except Exception as exc:  # transient network
            if attempt == 2:
                raise
            print("  retry %d after %s" % (attempt + 1, exc))
            time.sleep(3 * (attempt + 1))


def main():
    now = datetime.now(timezone.utc)
    if len(sys.argv) > 1:
        years = [int(a) for a in sys.argv[1:]]
    else:
        # December pages start listing next year's issue 1-2 on-sale dates.
        years = [now.year] + ([now.year + 1] if now.month == 12 else [])
    os.makedirs(RAW, exist_ok=True)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    for y in years:
        body = fetch(y)
        if b"/issues/" not in body:
            raise SystemExit("jajanken %d: no issue links in response — not saved" % y)
        path = os.path.join(RAW, "years_%d_%s.html" % (y, stamp))
        with open(path, "wb") as fh:
            fh.write(body)
        print("raw: %s (%.0f KB)" % (os.path.relpath(path), len(body) / 1024.0))


if __name__ == "__main__":
    main()
