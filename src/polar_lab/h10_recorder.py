"""Record HR + RR intervals from a Polar H10 over BLE to CSV.

Uses the standard GATT Heart Rate Measurement characteristic (0x2A37), which
the H10 broadcasts without any pairing ceremony — wear the strap (moisten the
electrodes), then:

    uv run python -m polar_lab.h10_recorder --out data/session.csv

Stop with Ctrl+C. Output columns: iso_ts, bpm, rr_ms (one row per RR interval
when present, else one per notification). RR intervals are the gold dust —
they enable HRV analysis (RMSSD) per session, not just averaged nightly.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

from bleak import BleakClient, BleakScanner

HR_MEASUREMENT = "00002a37-0000-1000-8000-00805f9b34fb"


def parse_hr(data: bytearray) -> tuple[int, list[float]]:
    """Parse a Heart Rate Measurement packet -> (bpm, [rr_ms...]).

    Flags bit0: 16-bit HR; bit4: RR intervals present (1/1024 s units).
    """
    flags = data[0]
    if flags & 0x01:
        bpm = int.from_bytes(data[1:3], "little")
        i = 3
    else:
        bpm = data[1]
        i = 2
    if flags & 0x08:  # energy expended field present — skip 2 bytes
        i += 2
    rrs: list[float] = []
    if flags & 0x10:
        while i + 1 < len(data):
            rr = int.from_bytes(data[i:i + 2], "little")
            rrs.append(rr / 1024.0 * 1000.0)
            i += 2
    return bpm, rrs


async def record(out: Path, name_filter: str = "Polar H10") -> None:
    print(f"Scanning for '{name_filter}'... (strap on, electrodes moist)")
    device = await BleakScanner.find_device_by_filter(
        lambda d, ad: (d.name or "").startswith(name_filter), timeout=20.0)
    if device is None:
        print("No Polar H10 found. Is it worn and in range?")
        sys.exit(1)
    print(f"Found {device.name} [{device.address}] — connecting...")

    out.parent.mkdir(parents=True, exist_ok=True)
    f = open(out, "w", newline="", encoding="utf-8")
    writer = csv.writer(f)
    writer.writerow(["iso_ts", "bpm", "rr_ms"])
    n = 0

    def on_data(_, data: bytearray) -> None:
        nonlocal n
        ts = datetime.now(timezone.utc).isoformat()
        bpm, rrs = parse_hr(data)
        if rrs:
            for rr in rrs:
                writer.writerow([ts, bpm, round(rr, 1)])
        else:
            writer.writerow([ts, bpm, ""])
        n += 1
        if n % 30 == 0:
            print(f"  {ts}  {bpm} bpm  ({n} notifications)")
            f.flush()

    async with BleakClient(device) as client:
        await client.start_notify(HR_MEASUREMENT, on_data)
        print(f"Recording to {out} — Ctrl+C to stop.")
        try:
            while True:
                await asyncio.sleep(1)
        except (KeyboardInterrupt, asyncio.CancelledError):
            pass
        finally:
            await client.stop_notify(HR_MEASUREMENT)
            f.close()
            print(f"Saved {out} ({n} notifications).")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="data/session.csv")
    ap.add_argument("--name", default="Polar H10", help="BLE name prefix")
    args = ap.parse_args()
    try:
        asyncio.run(record(Path(args.out), args.name))
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
