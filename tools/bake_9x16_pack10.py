#!/usr/bin/env python3
"""Bake Spain 9:16 pack10 FINAL portraits from the final 16:9 masters.

Finished canvas is true 9:16: 1080×1920 = photo 1080×1730 + 190px label bar.
See tools/portrait_9x16.py. Do not scale the photo to 1080×1920 and then add
the bar — that yields 1080×2110, which is not 9:16, and this bake refuses it.

Pack10 is the 18 masters on draft PR #40 (ES-01-336…358). The photograph is
a full-height center crop (674×1080, left edge 623), Lanczos to 1080×1730.
The label bar is the previous finish on this draft, kept pixel for pixel.
Art. 50 chunks are copied from the source 16:9. Nothing here writes
approval_status.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from portrait_9x16 import (  # noqa: E402
    BAR_H,
    CANVAS_916,
    FORBIDDEN_CANVAS,
    PHOTO_916,
    bake_named,
    png_ihdr,
)

PACK = (
    "es-01-336-r1-9x16.png",
    "es-01-337-r1-9x16.png",
    "es-01-338-r1-9x16.png",
    "es-01-339-r1-9x16.png",
    "es-01-341-r1-9x16.png",
    "es-01-342-r1-9x16.png",
    "es-01-344-r1-9x16.png",
    "es-01-345-r1-9x16.png",
    "es-01-346-r1-9x16.png",
    "es-01-347-r1-9x16.png",
    "es-01-348-r1-9x16.png",
    "es-01-349-r1-9x16.png",
    "es-01-350-r1-9x16.png",
    "es-01-351-r1-9x16.png",
    "es-01-352-r1-9x16.png",
    "es-01-353-r1-9x16.png",
    "es-01-356-r1-9x16.png",
    "es-01-358-r1-9x16.png",
)


def main() -> None:
    if CANVAS_916 != (1080, 1920) or PHOTO_916 != (1080, 1730) or BAR_H != 190:
        raise SystemExit("refusing to emit a 9:16 canvas other than 1080x1920")
    if CANVAS_916 == FORBIDDEN_CANVAS or PHOTO_916[1] + BAR_H == FORBIDDEN_CANVAS[1]:
        raise SystemExit("refusing to emit 1080x2110")
    if len(PACK) != 18:
        raise SystemExit(f"pack10 is 18 masters, got {len(PACK)}")
    reports = bake_named(PACK)
    bad = []
    for name, row in zip(PACK, reports):
        width, height = png_ihdr(Path(__file__).resolve().parents[1] / name)
        if (width, height) != (1080, 1920) or row["ihdr"] != "1080x1920":
            bad.append(name)
    if bad or len(reports) != 18:
        raise SystemExit(f"IHDR verification failed: {bad}")
    print(f"{len(reports)}/18 IHDR 1080x1920")
    for row in reports:
        print(f"{row['file']}\t{row['ihdr']}\t{row['source']}\t{row['comment']}")


if __name__ == "__main__":
    main()
