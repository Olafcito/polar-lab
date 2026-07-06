"""Probe the unofficial Polar Flow web login (email/password session).

    uv run python -m polar_lab.flow_probe

Reports whether flow.polar.com accepts POLAR_MAIL/POLAR_PASSWORD and whether
known export endpoints answer. Fragile by design (no API contract) — the
official AccessLink path is preferred; this exists to know what's possible.
"""

from __future__ import annotations

import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

LOGIN_URL = "https://flow.polar.com/login"


def main() -> None:
    email = os.environ.get("POLAR_MAIL") or os.environ.get("POLAR_EMAIL")
    password = os.environ.get("POLAR_PASSWORD")
    if not (email and password):
        raise SystemExit("POLAR_MAIL/POLAR_PASSWORD missing in .env")

    s = requests.Session()
    s.headers["User-Agent"] = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                               "AppleWebKit/537.36 Chrome/126 Safari/537.36")
    r = s.post(LOGIN_URL, data={"email": email, "password": password,
                                "returnUrl": "/"}, timeout=30,
               allow_redirects=True)
    print("login status:", r.status_code, "final url:", r.url)
    logged_in = r.status_code == 200 and "login" not in r.url
    print("session looks", "VALID" if logged_in else "INVALID")
    if not logged_in:
        return

    for name, url in [
        ("activity timeline", "https://flow.polar.com/api/activity-timeline/latest?_=1"),
        ("training history", "https://flow.polar.com/api/training/history"),
    ]:
        try:
            resp = s.get(url, timeout=30)
            body = resp.text[:120].replace("\n", " ")
            print(f"{name}: {resp.status_code} {body}")
        except Exception as e:  # noqa: BLE001 — probe reports, never crashes
            print(f"{name}: error {e}")


if __name__ == "__main__":
    main()
