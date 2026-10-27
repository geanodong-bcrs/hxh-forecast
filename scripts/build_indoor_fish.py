#!/usr/bin/env python3
"""Indoor Fish — production progress as two sealed rooms, seen from inside.

    python3 scripts/build_indoor_fish.py   -> site/indoor-fish.html, site/indoor-fish-next.html

One page per room. Each room holds the ten manuscripts of one run: the run the forecast is about,
and the one after it. The fish eat a manuscript as Togashi draws it, so the
eaten share is the same per-chapter readiness the card's "drawn" meter sums
(build_readiness.ordered_trace, 'ordered'). Once the room's first chapter
has been published the room is open and the fish are gone.

Prototype: not in the deploy allowlist and not called by run_update.py.
"""
import csv
import json
import os
from datetime import date

import build_readiness as br

HERE = os.path.dirname(os.path.abspath(__file__))
D = lambda *p: os.path.join(HERE, "..", *p)


def last_published(today):
    with open(D("data", "processed", "chapters.csv"), encoding="utf-8") as fh:
        return max(int(r["chapter"]) for r in csv.DictReader(fh)
                   if r["publication_date_jp"] and date.fromisoformat(r["publication_date_jp"]) <= today)


def main():
    today = date.today()
    with open(D("data", "processed", "production_events.csv"), encoding="utf-8") as fh:
        events = list(csv.DictReader(fh))
    last = last_published(today)
    # Runs are aligned on x1 (391, 401, ... 421): the current room is the run
    # holding the next unpublished chapter.
    first = (last // 10) * 10 + 1
    rooms = []
    for f in (first, first + 10):
        chapters = list(range(f, f + 10))
        trace = br.ordered_trace(events, chapters, today)
        ordered = trace[-1][2]["ordered"] if trace else {}
        rooms.append({"first": f,
                      "progress": {str(c): round(ordered.get(c, 0.0), 3) for c in chapters},
                      "open": f <= last})
    # One room per page, so each room gets the full width. The filenames stay
    # fixed while the chapter ranges move on.
    files = ["indoor-fish.html", "indoor-fish-next.html"]
    with open(os.path.join(HERE, "templates", "indoor_fish.html"), encoding="utf-8") as fh:
        template = fh.read()
    for i, (room, name) in enumerate(zip(rooms, files)):
        pages = [{"href": f, "label": "Ch. %d–%d" % (r["first"], r["first"] + 9), "current": j == i}
                 for j, (r, f) in enumerate(zip(rooms, files))]
        data = {"asof": today.strftime("%-d %b %Y"), "room": room, "pages": pages}
        out = D("site", name)
        with open(out, "w", encoding="utf-8") as fh:
            fh.write(template.replace("__DATA__", json.dumps(data)))
        print("ch %d-%d  %3.0f%% eaten  room %-6s -> %s"
              % (room["first"], room["first"] + 9, 10 * sum(room["progress"].values()),
                 "open" if room["open"] else "sealed", os.path.relpath(out, D())))


if __name__ == "__main__":
    main()
