#!/usr/bin/env python3
"""Build image-sitemap.xml from live Spain scene records.

Approved scenes only, including ES-01-320 and above.
One <url> per scene: canonical page plus the copy-link fragment.
One <image:image> per existing canonical master (16:9, 4:5, and 9:16
when that file exists). Daylight day-toggle PNGs are not listed.
"""

from __future__ import annotations

import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "tools"))
from gallery_public import apply_public_page  # noqa: E402

ROOT = Path(__file__).resolve().parent
ORIGIN = "https://spain.jdvision.org"
CDN_BASE = "https://devlij.github.io/jason-ds-vision-spain-assets"
CDN_ASSETS = CDN_BASE + "/assets/"
CDN_AUDIO = CDN_BASE + "/audio/"
SITEMAP_NS = "http://www.sitemaps.org/schemas/sitemap/0.9"
IMAGE_NS = "http://www.google.com/schemas/sitemap-image/1.1"


def media_name(path: str) -> str:
    return path.split("?", 1)[0].rstrip("/").split("/")[-1]


def is_audio_ref(path: str) -> bool:
    return path.startswith("audio/") or "/audio/" in path


def cdn_url(path: str) -> str:
    """Public CDN URL for a scene media reference.

    Root PNGs and files under assets/ both live at /assets/<filename>.
    Narration lives at /audio/<filename>. Already-absolute CDN URLs pass through.
    """
    if path.startswith(CDN_BASE + "/"):
        return path
    name = media_name(path)
    if is_audio_ref(path):
        return CDN_AUDIO + name
    return CDN_ASSETS + name


def local_file(path: str | None) -> Path | None:
    """Map a relative path or CDN URL back to the media file in this repo."""
    if not path:
        return None
    if path.startswith(("http://", "https://")):
        if not path.startswith(CDN_BASE + "/"):
            return None
        name = media_name(path)
        if "/audio/" in path:
            cand = ROOT / "audio" / name
            return cand if cand.is_file() else None
        for cand in (ROOT / name, ROOT / "assets" / name):
            if cand.is_file():
                return cand
        return None
    rel = Path(path)
    if rel.is_absolute() or ".." in rel.parts:
        return None
    cand = (ROOT / rel).resolve()
    root = ROOT.resolve()
    if cand != root and root not in cand.parents:
        return None
    return cand if cand.is_file() else None


def site_name(caption: str, city: str, region: str) -> str:
    caption = caption.strip()
    city = city.strip()
    region = region.strip()
    if city and caption.endswith(", " + city):
        return caption[: -(len(city) + 2)].strip()
    if region and caption.endswith(", " + region):
        return caption[: -(len(region) + 2)].strip()
    if ", " in caption:
        return caption.split(", ", 1)[0].strip()
    return caption


def image_alt(caption: str, city: str, region: str) -> str:
    site = site_name(caption, city, region)
    return f"{caption.strip()} — {site}, {city.strip()}"


def load_scenes() -> dict[str, dict]:
    data = json.loads((ROOT / "data.json").read_text(encoding="utf-8"))
    scenes = {}
    for slim in data["scenes"]:
        entry_id = slim["entry_id"]
        full = json.loads((ROOT / f"{entry_id}.json").read_text(encoding="utf-8"))
        scenes[entry_id] = {"slim": slim, "full": full}
    return scenes


def gallery_order(html: str) -> list[str]:
    return re.findall(r'<article class="card"[^>]*\sid="(ES-[^"]+)"', html)


def master_path(full: dict, fmt: str) -> str | None:
    key = {"16x9": "file_16x9", "4x5": "file_4x5", "9x16": "file_9x16"}.get(fmt)
    if key and full.get(key):
        return full[key]
    masters = full.get("masters") or {}
    block = masters.get(fmt) if isinstance(masters, dict) else None
    if isinstance(block, dict):
        return block.get("file") or block.get("path")
    return None


def existing(path: str | None) -> str | None:
    if path and local_file(path):
        return path
    return None


def approved_images(full: dict) -> list[tuple[str, str]]:
    images: list[tuple[str, str]] = []
    seen = set()

    def add(fmt: str, path: str | None) -> None:
        path = existing(path)
        if not path or path in seen:
            return
        seen.add(path)
        images.append((fmt, path))

    for fmt in ("16x9", "4x5", "9x16"):
        add(fmt, master_path(full, fmt))
    return images


def card_slice(html: str, entry_id: str) -> tuple[int, int]:
    marker = f'id="{entry_id}"'
    start = html.find(marker)
    if start < 0:
        raise SystemExit(f"missing card {entry_id}")
    article = html.rfind("<article", 0, start)
    nxt = html.find("<article", start + len(marker))
    end = nxt if nxt >= 0 else len(html)
    return article, end


def retarget_stale_masters(html: str, scenes: dict[str, dict], order: list[str]) -> tuple[str, list[str]]:
    notes = []
    for entry_id in order:
        full = scenes[entry_id]["full"]
        article_start, article_end = card_slice(html, entry_id)
        article = html[article_start:article_end]
        img = re.search(r"<img\b[^>]*>", article)
        if not img:
            continue
        tag = img.group(0)

        def attr(name: str) -> str | None:
            match = re.search(rf'{name}="([^"]*)"', tag)
            return match.group(1) if match else None

        replacements = []
        for fmt, attr_name, file_key in (
            ("16x9", "data-src-16", "file_16x9"),
            ("4x5", "data-src-45", "file_4x5"),
        ):
            served = attr(attr_name)
            approved = full.get(file_key)
            if served and approved and served != approved and existing(approved):
                replacements.append((served, approved, fmt))
        approved_16 = full.get("file_16x9") or ""
        served_916 = attr("data-src-916")
        if approved_16.endswith("-16x9.png") and served_916:
            expected_916 = approved_16[: -len("-16x9.png")] + "-9x16.png"
            if served_916 != expected_916:
                replacements.append((served_916, expected_916, "9x16-ref"))
        if not replacements:
            continue
        updated = article
        for old, new, fmt in replacements:
            count = updated.count(old)
            if count == 0:
                continue
            updated = updated.replace(old, new)
            notes.append(f"{entry_id} {fmt}: gallery {old} -> approved master {new} ({count} refs)")
        html = html[:article_start] + updated + html[article_end:]
    return html, notes


def rewrite_alts(html: str, scenes: dict[str, dict]) -> str:
    for entry_id, scene in scenes.items():
        full = scene["full"]
        alt = image_alt(full["caption"], full["city"], full.get("region") or "")
        article_start, article_end = card_slice(html, entry_id)
        article = html[article_start:article_end]

        def repl(match: re.Match[str]) -> str:
            return match.group(1) + alt + match.group(2)

        updated, count = re.subn(r'(<img\b[^>]*\balt=")[^"]*(")', repl, article, count=1)
        if count != 1:
            raise SystemExit(f"alt rewrite failed for {entry_id}")
        html = html[:article_start] + updated + html[article_end:]
    return html


def build_sitemap(scenes: dict[str, dict], order: list[str]) -> tuple[ET.Element, dict]:
    ET.register_namespace("", SITEMAP_NS)
    ET.register_namespace("image", IMAGE_NS)
    urlset = ET.Element(f"{{{SITEMAP_NS}}}urlset")
    stats = {
        "scenes": 0,
        "formats": {},
        "missing_masters": [],
        "internal_editorial": [],
    }
    for entry_id in order:
        full = scenes[entry_id]["full"]
        state = (full.get("approval_state") or "").strip().lower()
        if state != "approved":
            stats.setdefault("skipped_not_approved", []).append(entry_id)
            continue
        images = approved_images(full)
        if not images:
            stats["missing_masters"].append(entry_id)
            continue
        if "internal editorial" in (full.get("status") or "").lower():
            stats["internal_editorial"].append(entry_id)
        url = ET.SubElement(urlset, f"{{{SITEMAP_NS}}}url")
        loc = ET.SubElement(url, f"{{{SITEMAP_NS}}}loc")
        loc.text = f"{ORIGIN}/#{entry_id}"
        alt = image_alt(full["caption"], full["city"], full.get("region") or "")
        for fmt, path in images:
            image = ET.SubElement(url, f"{{{IMAGE_NS}}}image")
            image_loc = ET.SubElement(image, f"{{{IMAGE_NS}}}loc")
            image_loc.text = cdn_url(path)
            title = ET.SubElement(image, f"{{{IMAGE_NS}}}title")
            title.text = alt
            stats["formats"][fmt] = stats["formats"].get(fmt, 0) + 1
        stats["scenes"] += 1
    return urlset, stats


def main() -> None:
    scenes = load_scenes()
    html = (ROOT / "index.html").read_text(encoding="utf-8")
    order = gallery_order(html)
    if len(order) != len(scenes):
        raise SystemExit(f"gallery cards {len(order)} != scene records {len(scenes)}")
    html, retargets = retarget_stale_masters(html, scenes, order)
    html = rewrite_alts(html, scenes)
    html = apply_public_page(html)
    (ROOT / "index.html").write_text(html, encoding="utf-8")

    app = (ROOT / "app.js").read_text(encoding="utf-8")
    for note in list(retargets):
        old = note.split(" gallery ", 1)[1].split(" -> ", 1)[0]
        new = note.split("approved master ", 1)[1].split(" (", 1)[0]
        if old in app:
            app = app.replace(old, new)
            retargets.append(f"app.js {old} -> {new}")
    (ROOT / "app.js").write_text(app, encoding="utf-8")

    # Rebuild image list from scene data after retarget. Retarget does not change JSON.
    urlset, stats = build_sitemap(scenes, order)
    tree = ET.ElementTree(urlset)
    ET.indent(tree, space="  ")
    xml_path = ROOT / "image-sitemap.xml"
    tree.write(xml_path, encoding="UTF-8", xml_declaration=True)
    # ElementTree writes a single-quoted declaration; normalize to the sitemap.xml style.
    text = xml_path.read_text(encoding="utf-8")
    if text.startswith("<?xml version='1.0' encoding='UTF-8'?>"):
        text = text.replace(
            "<?xml version='1.0' encoding='UTF-8'?>",
            '<?xml version="1.0" encoding="UTF-8"?>',
            1,
        )
        xml_path.write_text(text, encoding="utf-8")

    stats["retargets"] = retargets
    print(json.dumps(stats, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
