#!/usr/bin/env python3
"""Bake Spain 9:16 pack3 portraits from the final 16:9 masters.

Finished canvas is true 9:16: 1080×1920 = photo 1080×1730 + 190px label bar.
See tools/portrait_9x16.py. Do not scale the photo to 1080×1920 and then add
the bar — that yields 1080×2110, which is not 9:16.

Pack3 is the 30 masters on draft PR #33 (ES-01-079…115 except the cand-r1
portraits already on main). Crop is the centered 674px window. The label bar
is the sibling 16:9 artwork refit to 1080 wide, and it must match the bar
already on the previous 1080×2110 finish. ES-01-115's title is the one band
that is scaled horizontally; its scenario, disclosure, and signature stay.
Art. 50 chunks are copied from the source 16:9. Nothing here writes
approval_status.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from portrait_9x16 import bake_named, verify_ihdr

PACK = (
    "es-01-079-r1-9x16.png",
    "es-01-080-r1-9x16.png",
    "es-01-081-r1-9x16.png",
    "es-01-082-r1-9x16.png",
    "es-01-085-r1-9x16.png",
    "es-01-086-r2-9x16.png",
    "es-01-087-r1-9x16.png",
    "es-01-088-r1-9x16.png",
    "es-01-089-r1-9x16.png",
    "es-01-090-r1-9x16.png",
    "es-01-091-r1-9x16.png",
    "es-01-092-r1-9x16.png",
    "es-01-093-r1-9x16.png",
    "es-01-094-r1-9x16.png",
    "es-01-095-r1-9x16.png",
    "es-01-096-r1-9x16.png",
    "es-01-098-r1-9x16.png",
    "es-01-102-r1-9x16.png",
    "es-01-103-r1-9x16.png",
    "es-01-104-r1-9x16.png",
    "es-01-105-r1-9x16.png",
    "es-01-106-r1-9x16.png",
    "es-01-107-r1-9x16.png",
    "es-01-108-r1-9x16.png",
    "es-01-109-r1-9x16.png",
    "es-01-110-r1-9x16.png",
    "es-01-112-r1-9x16.png",
    "es-01-113-r1-9x16.png",
    "es-01-114-r1-9x16.png",
    "es-01-115-r1-9x16.png",
)


if __name__ == "__main__":
    if len(PACK) != 30:
        raise SystemExit(f"pack3 is 30 masters, got {len(PACK)}")
    reports = bake_named(PACK)
    verified = verify_ihdr(PACK)
    if len(verified) != 30 or any(row["ihdr"] != "1080x1920" for row in verified):
        raise SystemExit("IHDR verification failed")
    print(f"{len(reports)}/30 IHDR 1080x1920")
    for row in reports:
        print(f"{row['file']}\t{row['ihdr']}\t{row['source']}\t{row['comment']}")
