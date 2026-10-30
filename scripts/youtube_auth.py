#!/usr/bin/env python3
"""Get a YouTube refresh token for the uploader. Run this ONCE on YOUR computer (it needs a browser).

    python3 scripts/youtube_auth.py path/to/client_secret.json

`client_secret.json` is the OAuth client of type "Desktop app" you download from Google Cloud Console
(APIs & Services > Credentials). The YouTube Data API v3 must be enabled in that project.

It opens Google's consent page, you pick the channel, and it prints three values. Store them as secrets in the
Claude Code environment settings (never paste them into a chat): YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN.
Standard library only.
"""
import http.server
import json
import secrets
import sys
import urllib.parse
import urllib.request
import webbrowser

SCOPES = "https://www.googleapis.com/auth/youtube.upload https://www.googleapis.com/auth/youtube.force-ssl"


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    cfg = json.load(open(sys.argv[1]))
    cfg = cfg.get("installed") or cfg.get("web") or cfg
    cid, csec = cfg["client_id"], cfg["client_secret"]
    state = secrets.token_urlsafe(16)
    got = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            got.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("Xong. Quay lại cửa sổ terminal.".encode())

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    redirect = f"http://127.0.0.1:{srv.server_port}"
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": cid, "redirect_uri": redirect, "response_type": "code", "scope": SCOPES,
        "access_type": "offline", "prompt": "consent", "state": state})
    print("Opening the consent page. If no browser opens, visit:\n" + url)
    webbrowser.open(url)
    while "code" not in got and "error" not in got:
        srv.handle_request()
    if got.get("state") != state or "code" not in got:
        sys.exit(f"Authorisation failed: {got.get('error', 'state mismatch')}")
    body = urllib.parse.urlencode({"code": got["code"], "client_id": cid, "client_secret": csec,
                                   "redirect_uri": redirect, "grant_type": "authorization_code"}).encode()
    tok = json.load(urllib.request.urlopen("https://oauth2.googleapis.com/token", body))
    if "refresh_token" not in tok:
        sys.exit("Google returned no refresh token; remove the app's access at myaccount.google.com/permissions and retry.")
    print("\nStore these three as environment secrets (not in chat):")
    print("YT_CLIENT_ID=" + cid)
    print("YT_CLIENT_SECRET=" + csec)
    print("YT_REFRESH_TOKEN=" + tok["refresh_token"])


if __name__ == "__main__":
    main()
