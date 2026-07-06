# polar-lab

Experiments for getting Polar data (H10 chest strap) into the Tallyday
ecosystem. Sibling of [tallyday-garmin](https://github.com/Olafcito/tallyday-garmin)
— once a data path proves out, its output joins that repo's SQLite DB by
timestamp.

## The three data paths (research 2026-07-06)

| Path | Auth | What you get | Status |
|---|---|---|---|
| **H10 direct over BLE** (`h10_recorder.py`) | none — just the strap | Live HR + RR intervals (ECG-quality), second-by-second, recorded to CSV | ✅ Code ready; needs the strap powered on nearby to test |
| **AccessLink API** (`accesslink.py`) | OAuth2 — one-time app registration at [admin.polaraccesslink.com](https://admin.polaraccesslink.com) (email/password alone is NOT enough) | Training sessions w/ HR samples (≤30 days back), daily activity, sleep, nightly recharge | ⏳ Client ready; blocked on Simon registering an app → `POLAR_CLIENT_ID`/`SECRET` in `.env` |
| **Polar Flow unofficial** (`flow_probe.py`) | email+password (web session) | Whatever flow.polar.com serves (session exports, TCX) | 🧪 Probe script — fragile by nature, use as fallback only |

**Recommendation:** H10-over-BLE is the unique win (kickboxing HR where wrist
optical fails — pads/gloves) and needs no account plumbing. AccessLink is the
clean long-term sync path; register the app when you have 5 minutes.

## Quickstart

```bash
uv sync --extra dev
cp .env.example .env

# record a session from the H10 (wear the strap, moisten electrodes):
uv run python -m polar_lab.h10_recorder --out data/session.csv

# probe the unofficial Flow login:
uv run python -m polar_lab.flow_probe
```

## AccessLink registration (one-time, Simon)

1. Log in at https://admin.polaraccesslink.com with the Polar account.
2. Create a client → set redirect URI to `http://localhost:8080/callback`.
3. Put `POLAR_CLIENT_ID` + `POLAR_CLIENT_SECRET` in `.env`.
4. `uv run python -m polar_lab.accesslink --authorize` → browser consent →
   token is cached in `data/accesslink_token.json`; then
   `uv run python -m polar_lab.accesslink --exercises`.
