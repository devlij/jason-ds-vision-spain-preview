#!/usr/bin/env python3
"""Bake Spain 9:16 portraits from the finished 16:9 masters.

True 9:16 at 1080 wide is 1080×1920. The label bar is 190px, so the photo
region is 1080×1730 and the bar is appended under it:

  finished 16:9 is 1920×1270 = photo 1920×1080 + 190px label bar
  9:16 photo is a full-height center crop of that photo, Lanczos to 1080×1730
  finished 9:16 is 1080×1920 (1080×1730 photo + the same 190px bar)

Scaling the photo to 1080×1920 and then adding the bar produces 1080×2110,
which is not 9:16. That was the Italy root cause. This module refuses that
canvas.

The label bar is the sibling 16:9 bar refit to 1080 wide: the left caption
block stays put, and the right signature block shifts left by 840px
(1920−1080) so its margin is unchanged. When that shift would cover the
caption (ES-01-058), only the title band is scaled horizontally so it
clears the signature by 32px. The scenario, disclosure, and signature stay
at the source pixels. Nothing here writes approval_status or the gallery
index.
"""

from __future__ import annotations

import struct
import sys
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]

PHOTO_16 = (1920, 1080)
PHOTO_916 = (1080, 1730)
BAR_H = 190
CANVAS_16 = (PHOTO_16[0], PHOTO_16[1] + BAR_H)
CANVAS_916 = (PHOTO_916[0], PHOTO_916[1] + BAR_H)
FORBIDDEN_CANVAS = (1080, 2110)
BAR_BG = (0x0E, 0x0E, 0x12)
# Source window that scales to the 1080×1730 photo. Full photo height, so the
# width is 1080 * 1080/1730, rounded.
CROP_W = int(round(PHOTO_16[1] * (PHOTO_916[0] / PHOTO_916[1])))
CENTER_LEFT = (PHOTO_16[0] - CROP_W) // 2
WIDTH_DELTA = PHOTO_16[0] - PHOTO_916[0]

PNG_SIG = b"\x89PNG\r\n\x1a\n"
ART50_KEYS = ("Title", "Description", "Copyright", "Software", "Comment")

if CANVAS_916 != (1080, 1920) or PHOTO_916 != (1080, 1730) or BAR_H != 190:
    raise SystemExit("9:16 canvas must be 1080x1920 = photo 1080x1730 + 190px bar")
if CANVAS_916 == FORBIDDEN_CANVAS or PHOTO_916[1] + BAR_H == FORBIDDEN_CANVAS[1]:
    raise SystemExit("refusing 1080x2110: do not scale the photo to 1080x1920 and then add the bar")
if CANVAS_916[0] * 16 != CANVAS_916[1] * 9:
    raise SystemExit(f"{CANVAS_916[0]}x{CANVAS_916[1]} is not exact 9:16")
if CROP_W != 674 or CENTER_LEFT != 623 or WIDTH_DELTA != 840:
    raise SystemExit(f"unexpected crop geometry {CROP_W} left {CENTER_LEFT} delta {WIDTH_DELTA}")


def _crop_width(height: int) -> int:
    return int(round(height * (PHOTO_916[0] / PHOTO_916[1])))


def crop_photo(photo: Image.Image, left: int | None = None) -> Image.Image:
    """Full-height 1080:1730 window, then Lanczos to 1080×1730."""
    photo = photo.convert("RGB")
    width, height = photo.size
    if (width, height) != PHOTO_16:
        raise SystemExit(f"photo {width}x{height}, expected {PHOTO_16[0]}x{PHOTO_16[1]}")
    crop_w = _crop_width(height)
    if crop_w != CROP_W:
        raise SystemExit(f"crop width {crop_w}, expected {CROP_W}")
    max_left = width - crop_w
    if left is None:
        left = max_left // 2
    if not 0 <= left <= max_left:
        raise SystemExit(f"crop left {left} outside 0..{max_left}")
    window = photo.crop((left, 0, left + crop_w, height))
    portrait = window.resize(PHOTO_916, Image.Resampling.LANCZOS)
    if portrait.size != PHOTO_916:
        raise SystemExit(f"portrait {portrait.size}")
    if portrait.size[1] + BAR_H == FORBIDDEN_CANVAS[1]:
        raise SystemExit("refusing a photo height that finishes at 1080x2110")
    return portrait


def content_columns(bar: Image.Image) -> list[int]:
    px = bar.load()
    width, height = bar.size
    columns = []
    for x in range(width):
        for y in range(height):
            if px[x, y][:3] != BAR_BG:
                columns.append(x)
                break
    return columns


def largest_gap(columns: list[int]) -> tuple[int, int]:
    """Return (last_left_content_x, first_right_content_x) for the widest gap."""
    if len(columns) < 2:
        raise SystemExit("label bar has no left/right split")
    best: tuple[int, int, int] | None = None
    for left_x, right_x in zip(columns, columns[1:]):
        gap = right_x - left_x
        if gap > 10 and (best is None or gap > best[0]):
            best = (gap, left_x, right_x)
    if best is None:
        raise SystemExit("label bar has no gap between caption and signature")
    return best[1], best[2]


def _empty_columns(bar: Image.Image) -> list[bool]:
    px = bar.load()
    width, height = bar.size
    empty = []
    for x in range(width):
        empty.append(all(px[x, y][:3] == BAR_BG for y in range(height)))
    return empty


def _column_runs(empty: list[bool]) -> list[tuple[int, int, int]]:
    runs: list[tuple[int, int, int]] = []
    in_run = False
    start = 0
    for i, is_empty in enumerate(empty):
        if is_empty and not in_run:
            start = i
            in_run = True
        elif not is_empty and in_run:
            runs.append((start, i - 1, i - start))
            in_run = False
    if in_run:
        runs.append((start, len(empty) - 1, len(empty) - start))
    return runs


def refit_tight_title(bar: Image.Image) -> Image.Image:
    """Scale only the wide title band. Signature, scenario, and disclosure stay.

    Used when the 840px signature shift would cover the caption. The right
    block is placed so its right margin is unchanged. Title rows are the
    ones whose ink reaches within 32px of that block. That band is Lanczos-
    scaled horizontally and pasted at its original left edge, leaving a 32px
    gap. Every other row left of the signature is copied unchanged.
    """
    bar = bar.convert("RGB")
    width, height = bar.size
    if (width, height) != (PHOTO_16[0], BAR_H):
        raise SystemExit(f"tight title bar {bar.size}")
    runs = _column_runs(_empty_columns(bar))
    interior = [run for run in runs if run[0] > 40 and run[1] < width - 40]
    if not interior:
        raise SystemExit("tight title bar has no interior gutter")
    g0, g1, glen = max(interior, key=lambda run: run[2])
    if glen >= WIDTH_DELTA:
        raise SystemExit(f"tight title path used on a {glen}px gutter")
    right = bar.crop((g1 + 1, 0, width, height))
    out = Image.new("RGB", (PHOTO_916[0], BAR_H), BAR_BG)
    rx = PHOTO_916[0] - right.width
    if rx < 0:
        raise SystemExit("signature block is wider than the 1080px bar")
    out.paste(right, (rx, 0))
    gap = 32
    src_px = bar.load()
    title_rows = []
    for y in range(height):
        last = None
        for x in range(g0):
            if src_px[x, y][:3] != BAR_BG:
                last = x
        if last is not None and last >= rx - gap:
            title_rows.append(y)
    if not title_rows:
        raise SystemExit("tight gutter but no title rows")
    y0, y1 = title_rows[0], title_rows[-1] + 1
    title_set = set(range(y0, y1))
    out_px = out.load()
    for y in range(height):
        if y not in title_set:
            for x in range(rx):
                out_px[x, y] = src_px[x, y]
    xs = [
        x
        for x in range(g0)
        if any(src_px[x, y][:3] != BAR_BG for y in range(y0, y1))
    ]
    if not xs:
        raise SystemExit("title band has no ink")
    x0, x1 = xs[0], xs[-1] + 1
    target_w = rx - gap - x0
    if target_w < 40:
        raise SystemExit("no room for title")
    sprite = bar.crop((x0, y0, x1, y1))
    scaled = sprite.resize((target_w, sprite.height), Image.Resampling.LANCZOS)
    out.paste(scaled, (x0, y0))
    if out.size != (PHOTO_916[0], BAR_H):
        raise SystemExit(f"tight title bar {out.size}")
    return out


def refit_label_bar(bar: Image.Image) -> Image.Image:
    """Slide the 16:9 signature block left by 840px. Caption pixels stay put."""
    bar = bar.convert("RGB")
    if bar.size != (PHOTO_16[0], BAR_H):
        raise SystemExit(f"label bar {bar.size}, expected {PHOTO_16[0]}x{BAR_H}")
    if bar.getpixel((2, BAR_H - 1))[:3] != BAR_BG:
        raise SystemExit("label bar background is not #0e0e12")
    gap_left, gap_right = largest_gap(content_columns(bar))
    left_end = gap_left + 1
    dest_x0 = gap_right - WIDTH_DELTA
    if dest_x0 < left_end:
        return refit_tight_title(bar)
    if dest_x0 < 0 or dest_x0 + (PHOTO_16[0] - gap_right) != PHOTO_916[0]:
        raise SystemExit(f"label refit does not land on a {PHOTO_916[0]}px bar")
    dest = Image.new("RGB", (PHOTO_916[0], BAR_H), BAR_BG)
    dest.paste(bar.crop((0, 0, left_end, BAR_H)), (0, 0))
    dest.paste(bar.crop((gap_right, 0, PHOTO_16[0], BAR_H)), (dest_x0, 0))
    if dest.size != (PHOTO_916[0], BAR_H):
        raise SystemExit(f"refit bar {dest.size}")
    return dest


def art50_chunks(data: bytes) -> list[bytes]:
    """Raw PNG chunks for the five Art. 50 keys, in file order."""
    if data[:8] != PNG_SIG:
        raise SystemExit("not a png")
    found: list[bytes] = []
    keys: list[str] = []
    i = 8
    while i + 12 <= len(data):
        length = struct.unpack(">I", data[i : i + 4])[0]
        ctype = data[i + 4 : i + 8]
        end = i + 12 + length
        payload = data[i + 8 : i + 8 + length]
        if ctype in (b"tEXt", b"iTXt", b"zTXt"):
            key = payload.split(b"\x00", 1)[0].decode("latin-1")
            if key in ART50_KEYS:
                found.append(data[i:end])
                keys.append(key)
        i = end
        if ctype == b"IEND":
            break
    if keys != list(ART50_KEYS):
        raise SystemExit(f"Art. 50 keys {keys}, expected {list(ART50_KEYS)}")
    return found


def comment_of(chunks: list[bytes]) -> str:
    for chunk in chunks:
        length = struct.unpack(">I", chunk[:4])[0]
        ctype = chunk[4:8]
        payload = chunk[8 : 8 + length]
        if ctype != b"tEXt":
            continue
        key, value = payload.split(b"\x00", 1)
        if key == b"Comment":
            return value.decode("latin-1")
    raise SystemExit("Comment chunk missing")


def write_with_chunks(path: Path, chunks: list[bytes]) -> None:
    data = path.read_bytes()
    if data[:8] != PNG_SIG:
        raise SystemExit(f"not a png: {path}")
    out = [data[:8]]
    i = 8
    inserted = False
    while i + 12 <= len(data):
        length = struct.unpack(">I", data[i : i + 4])[0]
        ctype = data[i + 4 : i + 8]
        end = i + 12 + length
        payload = data[i + 8 : i + 8 + length]
        if ctype in (b"tEXt", b"iTXt", b"zTXt"):
            key = payload.split(b"\x00", 1)[0].decode("latin-1")
            if key in ART50_KEYS:
                i = end
                continue
        if ctype == b"IEND":
            out.extend(chunks)
            out.append(data[i:end])
            inserted = True
            i = end
            break
        out.append(data[i:end])
        i = end
    if not inserted:
        raise SystemExit(f"IEND missing: {path}")
    path.write_bytes(b"".join(out))


def png_ihdr(path: Path) -> tuple[int, int]:
    """Width and height from the PNG IHDR chunk, not from a decoder guess."""
    data = path.read_bytes()
    if data[:8] != PNG_SIG or data[12:16] != b"IHDR":
        raise SystemExit(f"{path.name} has no IHDR")
    width, height = struct.unpack(">II", data[16:24])
    if (width, height) == FORBIDDEN_CANVAS:
        raise SystemExit(f"{path.name} IHDR is 1080x2110")
    return width, height


def _existing_bar(dest: Path) -> Image.Image | None:
    if not dest.is_file():
        return None
    with Image.open(dest) as im:
        im.load()
        if im.size not in (CANVAS_916, FORBIDDEN_CANVAS):
            raise SystemExit(f"{dest.name} existing size {im.size}")
        return im.convert("RGB").crop((0, im.size[1] - BAR_H, im.size[0], im.size[1]))


def bake_one(src: Path, dest: Path, left: int | None = None) -> dict:
    if CANVAS_916 != (1080, 1920):
        raise SystemExit("refusing to emit a 9:16 canvas other than 1080x1920")
    if CANVAS_916 == FORBIDDEN_CANVAS:
        raise SystemExit("refusing to emit 1080x2110")
    raw = src.read_bytes()
    chunks = art50_chunks(raw)
    previous_bar = _existing_bar(dest)
    with Image.open(src) as im:
        if im.size != CANVAS_16:
            raise SystemExit(f"{src.name} size {im.size}, expected {CANVAS_16[0]}x{CANVAS_16[1]}")
        rgb = im.convert("RGB")
        photo = rgb.crop((0, 0, PHOTO_16[0], PHOTO_16[1]))
        bar = rgb.crop((0, PHOTO_16[1], CANVAS_16[0], CANVAS_16[1]))
    portrait = crop_photo(photo, left)
    label = refit_label_bar(bar)
    if previous_bar is not None and label.tobytes() != previous_bar.tobytes():
        raise SystemExit(f"{dest.name} label bar does not match the existing finish")
    if portrait.size != PHOTO_916 or label.size != (PHOTO_916[0], BAR_H):
        raise SystemExit("photo or bar size drifted before composite")
    finished = Image.new("RGB", CANVAS_916, BAR_BG)
    finished.paste(portrait, (0, 0))
    finished.paste(label, (0, PHOTO_916[1]))
    if finished.size == FORBIDDEN_CANVAS:
        raise SystemExit(f"refusing to write {dest.name} at 1080x2110")
    if finished.size != CANVAS_916:
        raise SystemExit(f"canvas {finished.size}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    finished.save(dest, format="PNG", compress_level=9)
    write_with_chunks(dest, chunks)
    written = art50_chunks(dest.read_bytes())
    if written != chunks:
        raise SystemExit(f"{dest.name} Art. 50 chunks do not match {src.name}")
    ihdr = png_ihdr(dest)
    if ihdr != CANVAS_916:
        raise SystemExit(f"{dest.name} IHDR {ihdr[0]}x{ihdr[1]}")
    with Image.open(dest) as saved:
        saved.load()
        if saved.size != CANVAS_916:
            raise SystemExit(f"{dest.name} saved {saved.size}")
        top = saved.crop((0, 0, PHOTO_916[0], PHOTO_916[1])).convert("RGB")
        bottom = saved.crop((0, PHOTO_916[1], PHOTO_916[0], CANVAS_916[1])).convert("RGB")
        if top.tobytes() != portrait.tobytes():
            raise SystemExit(f"{dest.name} photo pixels changed on save")
        if bottom.tobytes() != label.tobytes():
            raise SystemExit(f"{dest.name} label pixels changed on save")
        if saved.getpixel((2, saved.height - 1))[:3] != BAR_BG:
            raise SystemExit(f"{dest.name} bar")
    return {
        "file": dest.name,
        "source": src.name,
        "left": CENTER_LEFT if left is None else left,
        "comment": comment_of(chunks),
        "ihdr": f"{ihdr[0]}x{ihdr[1]}",
    }


def source_for(dest_name: str) -> str:
    if not dest_name.endswith("-9x16.png") and not dest_name.endswith("9x16.png"):
        raise SystemExit(f"not a 9:16 master name: {dest_name}")
    return dest_name.replace("9x16.png", "16x9.png")


def bake_named(names: tuple[str, ...] | list[str]) -> list[dict]:
    reports = []
    for name in names:
        src = ROOT / source_for(name)
        dest = ROOT / name
        if not src.is_file():
            raise SystemExit(f"missing {src.name}")
        report = bake_one(src, dest)
        reports.append(report)
        print(f"{report['file']} {report['ihdr']} <= {report['source']}", flush=True)
    heights = {row["ihdr"] for row in reports}
    if heights != {"1080x1920"}:
        raise SystemExit(f"bake produced {heights}")
    return reports


def verify_ihdr(names: tuple[str, ...] | list[str]) -> list[dict]:
    rows = []
    for name in names:
        path = ROOT / name
        if not path.is_file():
            raise SystemExit(f"missing {name}")
        width, height = png_ihdr(path)
        if (width, height) != CANVAS_916:
            raise SystemExit(f"{name} IHDR {width}x{height}")
        rows.append({"file": name, "ihdr": f"{width}x{height}"})
    return rows
