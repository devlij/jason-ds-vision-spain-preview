#!/usr/bin/env python3
"""Bake Spain 9:16 pack2 portraits from the final 16:9 masters.

Finished canvas is true 9:16: 1080×1920 = photo 1080×1730 + 190px label bar.
See tools/portrait_9x16.py. Do not scale the photo to 1080×1920 and then add
the bar — that yields 1080×2110, which is not 9:16.

Pack2 is the 30 masters on draft PR #32 (ES-01-036…078 except the cand-r1
portraits already on main). Crop is the centered 674px window. The label bar
is the sibling 16:9 artwork refit to 1080 wide, and it must match the bar
already on the previous 1080×2110 finish. ES-01-058's title is the one band
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
    "es-01-036-r1-9x16.png",
    "es-01-037-r1-9x16.png",
    "es-01-038-r2-9x16.png",
    "es-01-039-r1-9x16.png",
    "es-01-040-r1-9x16.png",
    "es-01-041-r2-9x16.png",
    "es-01-044-r1-9x16.png",
    "es-01-045-r1-9x16.png",
    "es-01-046-r1-9x16.png",
    "es-01-048-r1-9x16.png",
    "es-01-051-r1-9x16.png",
    "es-01-054-r1-9x16.png",
    "es-01-056-r1-9x16.png",
    "es-01-057-r1-9x16.png",
    "es-01-058-r1-9x16.png",
    "es-01-062-r1-9x16.png",
    "es-01-063-r1-9x16.png",
    "es-01-064-r1-9x16.png",
    "es-01-065-r1-9x16.png",
    "es-01-066-r1-9x16.png",
    "es-01-067-r1-9x16.png",
    "es-01-068-r1-9x16.png",
    "es-01-069-r1-9x16.png",
    "es-01-070-r1-9x16.png",
    "es-01-071-r1-9x16.png",
    "es-01-073-r1-9x16.png",
    "es-01-074-r1-9x16.png",
    "es-01-075-r1-9x16.png",
    "es-01-077-r1-9x16.png",
    "es-01-078-r1-9x16.png",
)


if __name__ == "__main__":
    if len(PACK) != 30:
        raise SystemExit(f"pack2 is 30 masters, got {len(PACK)}")
    reports = bake_named(PACK)
    verified = verify_ihdr(PACK)
    if len(verified) != 30 or any(row["ihdr"] != "1080x1920" for row in verified):
        raise SystemExit("IHDR verification failed")
    print(f"{len(reports)}/30 IHDR 1080x1920")
    for row in reports:
        print(f"{row['file']}\t{row['ihdr']}\t{row['source']}\t{row['comment']}")
