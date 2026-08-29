#!/usr/bin/env python3
"""Post a reply with an image, using OAuth 2.0 user context.

Two things make this fiddlier than it looks:

REFRESH TOKENS ROTATE. Every refresh returns a NEW refresh token and invalidates
the old one. Miss the write-back and the bot authenticates once, then locks
itself out. `refresh()` writes the new token to .env before returning.

MEDIA UPLOAD IS A SEPARATE ENDPOINT. A tweet cannot carry image bytes; you upload
first, get a media_id, then reference it. This targets the v2 endpoint
(/2/media/upload), which accepts OAuth 2.0 user context — the older v1.1 endpoint
requires OAuth 1.0a, an entirely different credential set we deliberately did not
set up.
"""
import base64
import json
import mimetypes
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid

HERE = os.path.dirname(os.path.abspath(__file__))
ENV = os.path.join(HERE, "..", ".env")
TOKEN_URL = "https://api.x.com/2/oauth2/token"
TWEETS_URL = "https://api.x.com/2/tweets"
MEDIA_URL = "https://api.x.com/2/media/upload"


def env(key):
    if not os.path.exists(ENV):
        return None
    for line in open(ENV, encoding="utf-8"):
        m = re.match(r"\s*%s\s*=\s*(.*?)\s*$" % key, line)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    return None


def set_env(key, value):
    lines = open(ENV, encoding="utf-8").read().splitlines() if os.path.exists(ENV) else []
    for i, line in enumerate(lines):
        if re.match(r"\s*%s\s*=" % key, line):
            lines[i] = "%s=%s" % (key, value)
            break
    else:
        lines.append("%s=%s" % (key, value))
    with open(ENV, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


def refresh():
    """Exchange the stored refresh token for an access token, and persist the
    rotated refresh token immediately."""
    cid, secret, rt = env("X_CLIENT_ID"), env("X_CLIENT_SECRET"), env("X_REFRESH_TOKEN")
    if not rt:
        raise SystemExit("X_REFRESH_TOKEN missing — run: python3 scripts/x_auth.py")
    basic = base64.b64encode(("%s:%s" % (cid, secret)).encode()).decode()
    body = urllib.parse.urlencode({"refresh_token": rt,
                                   "grant_type": "refresh_token",
                                   "client_id": cid}).encode()
    req = urllib.request.Request(TOKEN_URL, data=body, headers={
        "Authorization": "Basic " + basic,
        "Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            tok = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise SystemExit("refresh failed: HTTP %d\n%s\n"
                         "If this says invalid_grant, the stored refresh token was "
                         "already used or revoked — re-run scripts/x_auth.py."
                         % (e.code, e.read().decode()[:400]))
    if "refresh_token" in tok:
        set_env("X_REFRESH_TOKEN", tok["refresh_token"])   # rotate, immediately
    return tok["access_token"]


def _multipart(fields, files):
    b = "----togashi" + uuid.uuid4().hex
    out = []
    for k, v in fields.items():
        out.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n"
                    % (b, k, v)).encode())
    for k, (name, data, ctype) in files.items():
        out.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"; "
                    "filename=\"%s\"\r\nContent-Type: %s\r\n\r\n"
                    % (b, k, name, ctype)).encode())
        out.append(data)
        out.append(b"\r\n")
    out.append(("--%s--\r\n" % b).encode())
    return b"".join(out), "multipart/form-data; boundary=" + b


def upload_media(access, path):
    data = open(path, "rb").read()
    ctype = mimetypes.guess_type(path)[0] or "image/png"
    body, content_type = _multipart({"media_category": "tweet_image"},
                                    {"media": (os.path.basename(path), data, ctype)})
    req = urllib.request.Request(MEDIA_URL, data=body, headers={
        "Authorization": "Bearer " + access, "Content-Type": content_type})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            d = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise SystemExit("media upload failed: HTTP %d\n%s" % (e.code, e.read().decode()[:400]))
    return str((d.get("data") or d).get("id") or (d.get("data") or d).get("media_id_string"))


def post_reply(text, image_path=None, in_reply_to=None):
    access = refresh()
    payload = {"text": text}
    if image_path:
        payload["media"] = {"media_ids": [upload_media(access, image_path)]}
    if in_reply_to:
        payload["reply"] = {"in_reply_to_tweet_id": str(in_reply_to)}
    req = urllib.request.Request(
        TWEETS_URL, data=json.dumps(payload).encode(),
        headers={"Authorization": "Bearer " + access,
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            d = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        raise SystemExit("post failed: HTTP %d\n%s" % (e.code, e.read().decode()[:400]))
    return (d.get("data") or {}).get("id")


def whoami():
    access = refresh()
    req = urllib.request.Request("https://api.x.com/2/users/me",
                                 headers={"Authorization": "Bearer " + access})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode())


if __name__ == "__main__":
    if "--whoami" in sys.argv:
        print(json.dumps(whoami(), indent=2))
    else:
        print(__doc__)
        print("  python3 scripts/x_post.py --whoami   # verify credentials work")
