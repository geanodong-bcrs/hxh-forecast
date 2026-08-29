#!/usr/bin/env python3
"""One-time OAuth 2.0 authorisation — produces the refresh token.

    python3 scripts/x_auth.py

X does not hand you a refresh token in the developer portal. You get one by
running the authorization-code flow once, as yourself, in a browser. This script
does that end to end:

    build the authorize URL (PKCE) -> open your browser -> you click Authorize
    -> X redirects to http://localhost:8080/callback -> this catches the code
    -> exchanges it for tokens -> writes X_REFRESH_TOKEN into .env

Run it once. After that the bot refreshes silently forever, as long as it keeps
writing the rotated token back (X rotates the refresh token on every use — save
the new one or the next refresh fails).

The redirect URI must match what is registered in the portal EXACTLY, including
the trailing path. Register: http://localhost:8080/callback
"""
import base64
import hashlib
import http.server
import json
import os
import re
import secrets
import sys
import threading
import urllib.parse
import urllib.request
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
ENV = os.path.join(HERE, "..", ".env")
REDIRECT = "http://localhost:8080/callback"
# media.write is REQUIRED for POST /2/media/upload and is NOT implied by
# tweet.write — without it the upload returns a bare 403 Forbidden with no
# explanation of which permission is missing.
SCOPES = "tweet.read tweet.write users.read media.write offline.access"
AUTHORIZE = "https://x.com/i/oauth2/authorize"
TOKEN = "https://api.x.com/2/oauth2/token"

_got = {}


def env(key):
    for line in open(ENV, encoding="utf-8"):
        m = re.match(r"\s*%s\s*=\s*(.*?)\s*$" % key, line)
        if m:
            return m.group(1).strip().strip('"').strip("'")
    return None


def set_env(key, value):
    """Write or replace a key in .env, preserving everything else."""
    lines, found = [], False
    if os.path.exists(ENV):
        lines = open(ENV, encoding="utf-8").read().splitlines()
    for i, line in enumerate(lines):
        if re.match(r"\s*%s\s*=" % key, line):
            lines[i] = "%s=%s" % (key, value)
            found = True
    if not found:
        lines.append("%s=%s" % (key, value))
    with open(ENV, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        _got.update({k: v[0] for k, v in q.items()})
        ok = "code" in _got
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write((
            "<body style='font:16px -apple-system;padding:3rem;background:#0f1115;color:#e8eaed'>"
            "<h2>%s</h2><p>%s</p></body>"
            % ("Authorised" if ok else "Something went wrong",
               "You can close this tab and go back to the terminal."
               if ok else "No authorisation code came back: %s" % _got)
        ).encode())

    def log_message(self, *a):
        pass


def main():
    cid, secret = env("X_CLIENT_ID"), env("X_CLIENT_SECRET")
    if not cid or not secret:
        sys.exit("X_CLIENT_ID / X_CLIENT_SECRET missing from .env")

    verifier = base64.urlsafe_b64encode(secrets.token_bytes(64)).rstrip(b"=").decode()
    challenge = base64.urlsafe_b64encode(
        hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    state = secrets.token_urlsafe(16)

    url = AUTHORIZE + "?" + urllib.parse.urlencode({
        "response_type": "code", "client_id": cid, "redirect_uri": REDIRECT,
        "scope": SCOPES, "state": state,
        "code_challenge": challenge, "code_challenge_method": "S256"})

    srv = http.server.HTTPServer(("localhost", 8080), Handler)
    threading.Thread(target=srv.handle_request, daemon=True).start()

    print("Opening your browser to authorise the app.")
    print("If it does not open, paste this into a browser:\n\n%s\n" % url)
    try:
        webbrowser.open(url)
    except Exception:
        pass
    print("waiting for the redirect to %s ..." % REDIRECT)

    for _ in range(300):
        if _got:
            break
        threading.Event().wait(1)
    srv.server_close()

    if "code" not in _got:
        sys.exit("no code received. %s" % (_got or "timed out after 5 minutes"))
    if _got.get("state") != state:
        sys.exit("state mismatch — aborting")

    # confidential client: authenticate the token call with HTTP Basic
    basic = base64.b64encode(("%s:%s" % (cid, secret)).encode()).decode()
    body = urllib.parse.urlencode({
        "code": _got["code"], "grant_type": "authorization_code",
        "client_id": cid, "redirect_uri": REDIRECT,
        "code_verifier": verifier}).encode()
    req = urllib.request.Request(TOKEN, data=body, headers={
        "Authorization": "Basic " + basic,
        "Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            tok = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        sys.exit("token exchange failed: HTTP %d\n%s" % (e.code, e.read().decode()[:400]))

    if "refresh_token" not in tok:
        sys.exit("no refresh_token in the response — was 'offline.access' in the "
                 "app's scopes?\n%s" % json.dumps(tok, indent=2)[:400])

    set_env("X_REFRESH_TOKEN", tok["refresh_token"])
    set_env("X_REFRESH_TOKEN", tok["refresh_token"]) if False else None
    granted = set((tok.get("scope") or "").split())
    print("\nrefresh token written to .env")
    print("  scopes granted : %s" % " ".join(sorted(granted)))
    missing = set(SCOPES.split()) - granted
    if missing:
        print("  WARNING missing : %s" % " ".join(sorted(missing)))
        print("  Posting an image needs media.write; re-check the app's User "
              "authentication settings if it is absent.")
    print("  access token   : expires in %ss (not stored; refreshed on demand)"
          % tok.get("expires_in"))
    print("\nDone. The bot can post from now on without you being present.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
