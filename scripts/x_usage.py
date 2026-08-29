#!/usr/bin/env python3
"""Read the X API project usage counter (GET /2/usage/tweets).

docs/next_session.md left one question open that decides the poll schedule:

    "Is a since_id poll returning zero results billed?"

Billing is per POST READ, so the answer should be no — but should-be is not
evidence. Run this before and after an empty poll and compare `project_usage`.

    python3 scripts/x_usage.py            # print the counter
    python3 scripts/x_usage.py --json     # machine-readable

The usage endpoint has its own daily request limit, so this is a diagnostic to
run deliberately, not something the poller calls on every cycle.
"""
import json
import os
import re
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
D = lambda *p: os.path.join(HERE, "..", *p)


def token():
    for line in open(D(".env")):
        m = re.match(r"\s*X_BEARER_TOKEN\s*=\s*(.+?)\s*$", line)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    sys.exit("X_BEARER_TOKEN not found in .env")


def main():
    url = ("https://api.x.com/2/usage/tweets"
           "?usage.fields=cap_reset_day,project_cap,project_id,project_usage,"
           "daily_project_usage,daily_client_app_usage")
    req = urllib.request.Request(url, headers={
        "Authorization": "Bearer " + token(),
        "User-Agent": "TogashiForecast/0.1"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:500]
        print("HTTP %d: %s" % (e.code, body))
        if e.code == 403:
            print("\n(403 usually means the access tier does not expose this "
                  "endpoint. Read the monthly counter from the developer portal "
                  "dashboard instead.)")
        return 1

    if "--json" in sys.argv:
        print(json.dumps(d, indent=2))
        return 0

    u = d.get("data", d)
    print("project usage this cycle : %s / %s posts"
          % (u.get("project_usage"), u.get("project_cap")))
    print("cap resets on day        : %s of the month" % u.get("cap_reset_day"))
    daily = u.get("daily_project_usage") or {}
    for row in (daily.get("usage") or [])[-7:]:
        print("   %s  %s posts" % (row.get("date", "")[:10], row.get("usage")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
