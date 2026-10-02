#!/usr/bin/env python3
"""Bake Spain 9:16 pack1 portraits from the final 16:9 masters.

Finished canvas is true 9:16: 1080×1920 = photo 1080×1730 + 190px label bar.
See tools/portrait_9x16.py. Do not scale the photo to 1080×1920 and then add
the bar — that yields 1080×2110, which is not 9:16.

Pack1 is the 30 masters on draft PR #31 (ES-01-001…035 except the five
cand-r1 portraits already on main). Crop is the centered 674px window.
The label bar is the sibling 16:9 artwork refit to 1080 wide. Art. 50 chunks
are copied from the source 16:9. Nothing here writes approval_status.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from portrait_9x16 import bake_named, verify_ihdr

PACK = (
    "es-01-001-daylight-r4-9x16.png",
    "es-01-003-9x16.png",
    "es-01-004-r2-9x16.png",
    "es-01-005-r3-9x16.png",
    "es-01-006-r2-9x16.png",
    "es-01-009-r1-9x16.png",
    "es-01-010-r2-9x16.png",
    "es-01-011-r2-9x16.png",
    "es-01-012-r1-9x16.png",
    "es-01-013-r1-9x16.png",
    "es-01-014-r1-9x16.png",
    "es-01-015-r1-9x16.png",
    "es-01-018-9x16.png",
    "es-01-019-r2-9x16.png",
    "es-01-020-r1-9x16.png",
    "es-01-021-r3-9x16.png",
    "es-01-022-r1-9x16.png",
    "es-01-023-r1-9x16.png",
    "es-01-024-r1-9x16.png",
    "es-01-025-r1-9x16.png",
    "es-01-026-r2-9x16.png",
    "es-01-027-r1-9x16.png",
    "es-01-028-r1-9x16.png",
    "es-01-029-r3-9x16.png",
    "es-01-030-r1-9x16.png",
    "es-01-031-r1-9x16.png",
    "es-01-032-r1-9x16.png",
    "es-01-033-r1-9x16.png",
    "es-01-034-r1-9x16.png",
    "es-01-035-r1-9x16.png",
)


if __name__ == "__main__":
    if len(PACK) != 30:
        raise SystemExit(f"pack1 is 30 masters, got {len(PACK)}")
    reports = bake_named(PACK)
    verified = verify_ihdr(PACK)
    if len(verified) != 30 or any(row["ihdr"] != "1080x1920" for row in verified):
        raise SystemExit("IHDR verification failed")
    print(f"{len(reports)}/30 IHDR 1080x1920")
