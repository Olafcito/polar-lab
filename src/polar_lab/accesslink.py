"""Minimal Polar AccessLink v3 client (official OAuth2 API).

One-time setup: register a client at https://admin.polaraccesslink.com,
put POLAR_CLIENT_ID/POLAR_CLIENT_SECRET in .env, then:

    uv run python -m polar_lab.accesslink --authorize   # browser consent
    uv run python -m polar_lab.accesslink --exercises   # list w/ HR data
    uv run python -m polar_lab.accesslink --sleep

Tokens cache in data/accesslink_token.json. HR samples reach back max 30
days (API limit) — sync regularly once this graduates into tallyday-garmin.
"""

from __future__ import annotations

import argparse
import json
import os
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

AUTH_URL = "https://flow.polar.com/oauth2/authorization"
TOKEN_URL = "https://polarremote.com/v2/oauth2/token"
API = "https://www.polaraccesslink.com/v3"
TOKEN_FILE = Path(__file__).resolve().parents[2] / "data" / "accesslink_token.json"
REDIRECT = "http://localhost:8080/callback"


def _client_creds() -> tuple[str, str]:
    cid = os.environ.get("POLAR_CLIENT_ID")
    secret = os.environ.get("POLAR_CLIENT_SECRET")
    if not (cid and secret):
        raise SystemExit(
            "POLAR_CLIENT_ID/POLAR_CLIENT_SECRET missing — register a client at "
            "https://admin.polaraccesslink.com first (see README).")
    return cid, secret


def authorize() -> None:
    cid, secret = _client_creds()
    code_holder: dict = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 — BaseHTTPRequestHandler API
            qs = parse_qs(urlparse(self.path).query)
            code_holder["code"] = (qs.get("code") or [None])[0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK - you can close this tab.")

        def log_message(self, *a):
            pass

    url = f"{AUTH_URL}?response_type=code&client_id={cid}"
    print("Opening browser for Polar consent:", url)
    webbrowser.open(url)
    server = HTTPServer(("localhost", 8080), Handler)
    while "code" not in code_holder:
        server.handle_request()

    resp = requests.post(TOKEN_URL, auth=(cid, secret), data={
        "grant_type": "authorization_code", "code": code_holder["code"],
        "redirect_uri": REDIRECT}, timeout=30)
    resp.raise_for_status()
    tok = resp.json()
    # Register the user against the client (required once by AccessLink).
    requests.post(f"{API}/users", json={"member-id": "simon"},
                  headers=_h(tok["access_token"]), timeout=30)
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(json.dumps(tok))
    print("Token saved to", TOKEN_FILE)


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Accept": "application/json"}


def _token() -> dict:
    if not TOKEN_FILE.exists():
        raise SystemExit("No token — run with --authorize first.")
    return json.loads(TOKEN_FILE.read_text())


def get(path: str) -> dict | list | None:
    tok = _token()
    r = requests.get(f"{API}{path}", headers=_h(tok["access_token"]), timeout=30)
    if r.status_code == 204:
        return None
    r.raise_for_status()
    return r.json()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--authorize", action="store_true")
    ap.add_argument("--exercises", action="store_true")
    ap.add_argument("--sleep", action="store_true")
    ap.add_argument("--recharge", action="store_true")
    args = ap.parse_args()
    if args.authorize:
        authorize()
    elif args.exercises:
        print(json.dumps(get(f"/users/{_token()['x_user_id']}/exercise-transactions")
                         or get("/exercises"), indent=2))
    elif args.sleep:
        print(json.dumps(get("/users/sleep"), indent=2))
    elif args.recharge:
        print(json.dumps(get("/users/nightly-recharge"), indent=2))
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
