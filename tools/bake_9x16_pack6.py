#!/usr/bin/env python3
"""Bake Spain 9:16 pack6 portraits from the final 16:9 masters.

Finished canvas is true 9:16: 1080×1920 = photo 1080×1730 + 190px label bar.
See tools/portrait_9x16.py. Do not scale the photo to 1080×1920 and then add
the bar — that yields 1080×2110, which is not 9:16, and this bake refuses it.

Pack6 is the 30 masters on draft PR #36 (ES-01-194…229 except the scenes
that are not in this pack). The photograph is a full-height center crop
(674×1080, left edge 623), Lanczos to 1080×1730. The label bar is the
previous finish on this draft, kept pixel for pixel. ES-01-196, ES-01-211,
and ES-01-228 keep that previous title band: a fresh Lanczos of the same
band is not byte-identical, and the signature, scenario, and disclosure
already match. Art. 50 chunks are copied from the source 16:9. Nothing here
writes approval_status.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from portrait_9x16 import (
    BAR_H,
    CANVAS_16,
    CANVAS_916,
    FORBIDDEN_CANVAS,
    PHOTO_16,
    PHOTO_916,
    ROOT,
    art50_chunks,
    comment_of,
    content_columns,
    crop_photo,
    largest_gap,
    png_ihdr,
    refit_label_bar,
    source_for,
    write_with_chunks,
)
from PIL import Image

PACK = (
    "es-01-194-r1-9x16.png",
    "es-01-195-r1-9x16.png",
    "es-01-196-r1-9x16.png",
    "es-01-197-r1-9x16.png",
    "es-01-198-r1-9x16.png",
    "es-01-199-r1-9x16.png",
    "es-01-200-r1-9x16.png",
    "es-01-201-r1-9x16.png",
    "es-01-202-r1-9x16.png",
    "es-01-206-r1-9x16.png",
    "es-01-208-r1-9x16.png",
    "es-01-209-r1-9x16.png",
    "es-01-210-r1-9x16.png",
    "es-01-211-r1-9x16.png",
    "es-01-212-r1-9x16.png",
    "es-01-213-r1-9x16.png",
    "es-01-214-r1-9x16.png",
    "es-01-215-r1-9x16.png",
    "es-01-216-r1-9x16.png",
    "es-01-217-r1-9x16.png",
    "es-01-218-r1-9x16.png",
    "es-01-219-r1-9x16.png",
    "es-01-221-r1-9x16.png",
    "es-01-222-r1-9x16.png",
    "es-01-223-r1-9x16.png",
    "es-01-225-r1-9x16.png",
    "es-01-226-r1-9x16.png",
    "es-01-227-r1-9x16.png",
    "es-01-228-r1-9x16.png",
    "es-01-229-r1-9x16.png",
)

# Previous finish scaled only these title bands. Keep those pixels.
TITLE_BAND_KEEP = {
    "es-01-196-r1-9x16.png",
    "es-01-211-r1-9x16.png",
    "es-01-228-r1-9x16.png",
}


def _existing_bar(dest: Path) -> Image.Image:
    if not dest.is_file():
        raise SystemExit(f"{dest.name} has no previous finish to keep the label from")
    with Image.open(dest) as im:
        im.load()
        if im.size not in (CANVAS_916, FORBIDDEN_CANVAS):
            raise SystemExit(f"{dest.name} existing size {im.size}")
        bar = im.convert("RGB").crop((0, im.size[1] - BAR_H, im.size[0], im.size[1]))
    if bar.size != (PHOTO_916[0], BAR_H):
        raise SystemExit(f"{dest.name} label {bar.size}")
    return bar


def _assert_label(name: str, refit: Image.Image, existing: Image.Image) -> None:
    """The bar we write is the previous finish. A fresh refit must agree with it.

    The three long titles differ only inside the scaled title band. Everything
    to the right of the caption/signature gap, including the signature, must
    still be identical, and a mismatch anywhere else is a refused bake.
    """
    if refit.size != existing.size:
        raise SystemExit(f"{name} refit {refit.size} existing {existing.size}")
    if refit.tobytes() == existing.tobytes():
        if name in TITLE_BAND_KEEP:
            raise SystemExit(f"{name} was expected to keep a distinct title band")
        return
    if name not in TITLE_BAND_KEEP:
        raise SystemExit(f"{name} label bar does not match the existing finish")
    _gap_left, gap_right = largest_gap(content_columns(existing))
    refit_px = refit.load()
    existing_px = existing.load()
    width, height = existing.size
    mismatched_rows: set[int] = set()
    for y in range(height):
        for x in range(width):
            if refit_px[x, y] == existing_px[x, y]:
                continue
            if x >= gap_right:
                raise SystemExit(f"{name} label differs at x={x}, which is the signature side")
            mismatched_rows.add(y)
    if not mismatched_rows:
        raise SystemExit(f"{name} title band did not differ")
    if min(mismatched_rows) < 40 or max(mismatched_rows) > 90:
        raise SystemExit(
            f"{name} label differs on rows {min(mismatched_rows)}..{max(mismatched_rows)}"
        )


def bake_pack() -> list[dict]:
    if CANVAS_916 != (1080, 1920) or PHOTO_916 != (1080, 1730) or BAR_H != 190:
        raise SystemExit("refusing to emit a 9:16 canvas other than 1080x1920")
    if CANVAS_916 == FORBIDDEN_CANVAS or PHOTO_916[1] + BAR_H == FORBIDDEN_CANVAS[1]:
        raise SystemExit("refusing to emit 1080x2110")
    reports = []
    for name in PACK:
        src = ROOT / source_for(name)
        dest = ROOT / name
        if not src.is_file():
            raise SystemExit(f"missing {src.name}")
        label = _existing_bar(dest)
        raw = src.read_bytes()
        chunks = art50_chunks(raw)
        with Image.open(src) as im:
            if im.size != CANVAS_16:
                raise SystemExit(f"{src.name} size {im.size}, expected {CANVAS_16[0]}x{CANVAS_16[1]}")
            rgb = im.convert("RGB")
            photo = rgb.crop((0, 0, PHOTO_16[0], PHOTO_16[1]))
            bar = rgb.crop((0, PHOTO_16[1], CANVAS_16[0], CANVAS_16[1]))
        _assert_label(name, refit_label_bar(bar), label)
        portrait = crop_photo(photo)
        if portrait.size != PHOTO_916 or label.size != (PHOTO_916[0], BAR_H):
            raise SystemExit("photo or bar size drifted before composite")
        finished = Image.new("RGB", CANVAS_916, (0x0E, 0x0E, 0x12))
        finished.paste(portrait, (0, 0))
        finished.paste(label, (0, PHOTO_916[1]))
        if finished.size == FORBIDDEN_CANVAS:
            raise SystemExit(f"refusing to write {name} at 1080x2110")
        if finished.size != CANVAS_916:
            raise SystemExit(f"canvas {finished.size}")
        finished.save(dest, format="PNG", compress_level=9)
        write_with_chunks(dest, chunks)
        written = art50_chunks(dest.read_bytes())
        if written != chunks:
            raise SystemExit(f"{name} Art. 50 chunks do not match {src.name}")
        ihdr = png_ihdr(dest)
        if ihdr != CANVAS_916:
            raise SystemExit(f"{name} IHDR {ihdr[0]}x{ihdr[1]}")
        with Image.open(dest) as saved:
            saved.load()
            if saved.size != CANVAS_916:
                raise SystemExit(f"{name} saved {saved.size}")
            top = saved.crop((0, 0, PHOTO_916[0], PHOTO_916[1])).convert("RGB")
            bottom = saved.crop((0, PHOTO_916[1], PHOTO_916[0], CANVAS_916[1])).convert("RGB")
            if top.tobytes() != portrait.tobytes():
                raise SystemExit(f"{name} photo pixels changed on save")
            if bottom.tobytes() != label.tobytes():
                raise SystemExit(f"{name} label pixels changed on save")
        report = {
            "file": name,
            "source": src.name,
            "comment": comment_of(chunks),
            "ihdr": f"{ihdr[0]}x{ihdr[1]}",
        }
        reports.append(report)
        print(f"{name} {report['ihdr']} <= {src.name}", flush=True)
    return reports


if __name__ == "__main__":
    if len(PACK) != 30:
        raise SystemExit(f"pack6 is 30 masters, got {len(PACK)}")
    reports = bake_pack()
    bad = [row for row in reports if row["ihdr"] != "1080x1920"]
    if bad or len(reports) != 30:
        raise SystemExit(f"IHDR verification failed: {bad}")
    print(f"{len(reports)}/30 IHDR 1080x1920")
    for row in reports:
        print(f"{row['file']}\t{row['ihdr']}\t{row['source']}\t{row['comment']}")
