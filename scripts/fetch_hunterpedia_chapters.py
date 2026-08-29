#!/usr/bin/env python3
"""Fetch every Hunterpedia chapter page via the Fandom API into the raw layer.

Raw layer rule (Agents.md sec. 27): this script writes data/raw/ and nothing else
ever rewrites what it produces. Re-running it creates a NEW timestamped snapshot
rather than overwriting the previous one.
"""
import json
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime

API = "https://hunterxhunter.fandom.com/api.php"
UA = "TogashiForecast/0.1 (research; +https://github.com/geanodong-bcrs/hxh-forecast)"
RAW = os.path.join(os.path.dirname(__file__), "..", "data", "raw", "hunterpedia")


def api(params):
    params = dict(params, format="json", formatversion="2")
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                return json.loads(r.read().decode("utf-8"))
        except Exception as exc:  # transient network / rate limit
            if attempt == 3:
                raise
            print("  retry %d after %s" % (attempt + 1, exc))
            time.sleep(3 * (attempt + 1))


def list_chapter_titles():
    titles, cont = [], None
    while True:
        p = {"action": "query", "list": "categorymembers",
             "cmtitle": "Category:Chapters", "cmlimit": "500", "cmnamespace": "0"}
        if cont:
            p["cmcontinue"] = cont
        d = api(p)
        for m in d["query"]["categorymembers"]:
            if m["title"].startswith("Chapter "):
                titles.append(m["title"])
        cont = d.get("continue", {}).get("cmcontinue")
        if not cont:
            break
    # numeric sort, skipping any non-numeric stragglers
    def key(t):
        try:
            return (0, int(t.split(" ", 1)[1]))
        except ValueError:
            return (1, 0)
    return sorted(set(titles), key=key)


def fetch_contents(titles, batch=50):
    out = {}
    for i in range(0, len(titles), batch):
        chunk = titles[i:i + batch]
        d = api({"action": "query", "prop": "revisions", "rvprop": "content|ids|timestamp",
                 "rvslots": "main", "titles": "|".join(chunk)})
        for page in d["query"]["pages"]:
            if "revisions" not in page:
                print("  MISSING: %s" % page["title"])
                continue
            rev = page["revisions"][0]
            out[page["title"]] = {
                "pageid": page.get("pageid"),
                "title": page["title"],
                "revid": rev["revid"],
                "rev_timestamp": rev["timestamp"],
                "wikitext": rev["slots"]["main"]["content"],
            }
        print("  fetched %d/%d" % (min(i + batch, len(titles)), len(titles)))
        time.sleep(0.6)
    return out


def main():
    os.makedirs(RAW, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    print("Enumerating Category:Chapters ...")
    titles = list_chapter_titles()
    print("  %d chapter pages" % len(titles))
    print("Fetching page content ...")
    pages = fetch_contents(titles)
    path = os.path.join(RAW, "hunterpedia_chapters_%s.json" % stamp)
    with open(path, "w") as fh:
        json.dump({
            "source": "hunterxhunter.fandom.com (Hunterpedia)",
            "source_type": "community_wiki_secondary",
            "api_endpoint": API,
            "retrieved_utc": datetime.utcnow().isoformat() + "Z",
            "page_count": len(pages),
            "pages": pages,
        }, fh, ensure_ascii=False, indent=1)
    print("Wrote %s (%d pages)" % (path, len(pages)))


if __name__ == "__main__":
    main()
