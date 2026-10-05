#!/usr/bin/env python3
"""Publish Spain tourist descriptions into the gallery catalogue.

Source of truth for the 329 verbose texts is tools/tourist_descriptions.json
(byte-for-byte values from the supplied es_done map). This publisher projects
those strings onto:

  * ES-01-*.json  "description"     scene catalogue
  * data.json     scenes[].description
  * index.html    the description paragraph on each matching card

Scenes absent from the map are not modified. Re-running the publisher
rewrites the same three outputs, so a later rebuild keeps the texts.

    python3 tools/publish_descriptions.py
    python3 tools/publish_descriptions.py --check
    python3 tools/publish_descriptions.py --prove
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from html import escape, unescape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(__file__).resolve().parent / "tourist_descriptions.json"
INDEX = ROOT / "index.html"
DATA = ROOT / "data.json"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gallery_public import apply_public_page  # noqa: E402

DESC_KEY = re.compile(r'("description"\s*:\s*)"(?:\\.|[^"\\])*"')
ALT_LINE = re.compile(
    r'^([ \t]*)"alt_text": "(?:\\.|[^"\\])*",\n',
    re.M,
)


def load_source() -> dict[str, str]:
    raw = SOURCE.read_text(encoding="utf-8")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise SystemExit(f"{SOURCE.name} must be a JSON object")
    if len(data) != 329:
        raise SystemExit(f"{SOURCE.name} has {len(data)} keys, expected 329")
    if len(set(data)) != len(data):
        raise SystemExit("duplicate keys in tourist descriptions")
    for eid, text in data.items():
        if not isinstance(eid, str) or not re.fullmatch(r"ES-01-\d{3}", eid):
            raise SystemExit(f"unexpected entry id {eid!r}")
        if not isinstance(text, str) or text == "":
            raise SystemExit(f"empty description for {eid}")
        if text != text.strip() or "\n" in text:
            raise SystemExit(f"description for {eid} is not a single trimmed line")
    return data


def _set_description_value(raw: str, text: str) -> str:
    literal = json.dumps(text, ensure_ascii=False)
    out, n = DESC_KEY.subn(lambda m: m.group(1) + literal, raw, count=1)
    if n != 1:
        raise SystemExit(f"expected one description field, found {n}")
    return out


def write_scene(eid: str, text: str) -> bool:
    path = ROOT / f"{eid}.json"
    if not path.is_file():
        raise SystemExit(f"missing scene catalogue {path.name}")
    raw = path.read_text(encoding="utf-8")
    current = json.loads(raw).get("description")
    if current == text and raw.count('"description"') >= 1:
        # Still rewrite if the on-disk literal is not the canonical JSON string.
        literal = json.dumps(text, ensure_ascii=False)
        if re.search(r'"description"\s*:\s*' + re.escape(literal), raw):
            return False
    updated = _set_description_value(raw, text)
    parsed = json.loads(updated)
    if parsed.get("description") != text:
        raise SystemExit(f"{eid} description did not round-trip")
    original = json.loads(raw)
    original["description"] = text
    if parsed != original:
        raise SystemExit(f"{eid} catalogue changed beyond description")
    if updated != raw:
        path.write_text(updated, encoding="utf-8")
        return True
    return False


def _scenes_region(raw: str) -> tuple[int, int]:
    i = raw.find('\n  "scenes":')
    j = raw.find('\n  "starters":')
    if i < 0 or j < 0 or j <= i:
        raise SystemExit("data.json scenes catalogue markers missing")
    return i, j


def _scene_block(raw: str, eid: str) -> tuple[int, int]:
    region_start, region_end = _scenes_region(raw)
    catalogue = raw[region_start:region_end]
    marker = f'"entry_id": "{eid}"'
    local = catalogue.find(marker)
    if local < 0:
        raise SystemExit(f"{eid} missing from data.json scenes")
    if catalogue.find(marker, local + len(marker)) != -1:
        raise SystemExit(f"{eid} appears more than once in data.json scenes")
    i = region_start + local
    j = raw.find('"entry_id":', i + len(marker))
    if j < 0 or j > region_end:
        j = region_end
    return i, j


def write_data(descriptions: dict[str, str]) -> bool:
    raw = DATA.read_text(encoding="utf-8")
    original = raw
    for eid, text in descriptions.items():
        i, j = _scene_block(raw, eid)
        block = raw[i:j]
        literal = json.dumps(text, ensure_ascii=False)
        if re.search(r'"description"\s*:\s*' + re.escape(literal), block):
            continue
        if '"description"' in block:
            block = _set_description_value(block, text)
        else:
            m = ALT_LINE.search(block)
            if not m:
                raise SystemExit(f"{eid} has no alt_text line to insert description after")
            line = m.group(1) + '"description": ' + literal + ",\n"
            block = block[: m.end()] + line + block[m.end() :]
        raw = raw[:i] + block + raw[j:]
    if raw == original:
        return False
    parsed = json.loads(raw)
    by_id = {s["entry_id"]: s for s in parsed["scenes"]}
    for eid, text in descriptions.items():
        if by_id[eid].get("description") != text:
            raise SystemExit(f"data.json description mismatch for {eid}")
    before = json.loads(original)
    before_by = {s["entry_id"]: s for s in before["scenes"]}
    for eid, scene in by_id.items():
        prev = before_by[eid]
        if eid in descriptions:
            prev = dict(prev)
            prev["description"] = descriptions[eid]
        if scene != prev:
            raise SystemExit(f"data.json scene {eid} changed beyond description")
    DATA.write_text(raw, encoding="utf-8")
    return True


def _card_span(html: str, eid: str) -> tuple[int, int]:
    m = re.search(
        rf'<article class="card"[^>]*\bid="{re.escape(eid)}"[^>]*>',
        html,
    )
    if not m:
        raise SystemExit(f"missing gallery card {eid}")
    end = html.find("</article>", m.end())
    if end < 0:
        raise SystemExit(f"unclosed card {eid}")
    return m.start(), end + len("</article>")


def card_description(article: str) -> str:
    h3 = re.search(r"<h3>.*?</h3>", article, re.S)
    if not h3:
        raise SystemExit("card has no heading")
    paras = list(re.finditer(r"<p>(.*?)</p>", article[h3.end() :], re.S))
    if len(paras) < 2:
        raise SystemExit("card has no description paragraph")
    return unescape(paras[1].group(1))


def write_index(descriptions: dict[str, str]) -> bool:
    html = INDEX.read_text(encoding="utf-8")
    original = html
    for eid, text in descriptions.items():
        start, end = _card_span(html, eid)
        article = html[start:end]
        if card_description(article) == text:
            continue
        h3 = re.search(r"<h3>.*?</h3>", article, re.S)
        assert h3 is not None
        base = h3.end()
        paras = list(re.finditer(r"<p>.*?</p>", article[base:], re.S))
        if len(paras) < 2:
            raise SystemExit(f"{eid} card has no description paragraph")
        p = paras[1]
        p_start = base + p.start()
        p_end = base + p.end()
        replacement = "<p>" + escape(text, quote=False) + "</p>"
        article = article[:p_start] + replacement + article[p_end:]
        if card_description(article) != text:
            raise SystemExit(f"{eid} card text did not round-trip")
        html = html[:start] + article + html[end:]
    html = apply_public_page(html)
    if html != original:
        INDEX.write_text(html, encoding="utf-8")
        return True
    return False


def publish() -> dict[str, bool]:
    descriptions = load_source()
    scene_changes = 0
    for eid, text in descriptions.items():
        if write_scene(eid, text):
            scene_changes += 1
    return {
        "scenes": scene_changes > 0,
        "data": write_data(descriptions),
        "index": write_index(descriptions),
    }


def check() -> None:
    descriptions = load_source()
    html = INDEX.read_text(encoding="utf-8")
    data = json.loads(DATA.read_text(encoding="utf-8"))
    by_id = {s["entry_id"]: s for s in data["scenes"]}
    problems: list[str] = []
    for eid, text in descriptions.items():
        scene = json.loads((ROOT / f"{eid}.json").read_text(encoding="utf-8"))
        if scene.get("description") != text:
            problems.append(f"{eid} scene json")
        if by_id.get(eid, {}).get("description") != text:
            problems.append(f"{eid} data.json")
        start, end = _card_span(html, eid)
        if card_description(html[start:end]) != text:
            problems.append(f"{eid} card")
        # Exact text once on the built page and once in each catalogue file.
        if html.count(text) != 1:
            problems.append(f"{eid} index count {html.count(text)}")
        scene_raw = (ROOT / f"{eid}.json").read_text(encoding="utf-8")
        if scene_raw.count(text) != 1:
            problems.append(f"{eid} scene file count {scene_raw.count(text)}")
        data_raw = DATA.read_text(encoding="utf-8")
        if data_raw.count(text) != 1:
            problems.append(f"{eid} data.json count {data_raw.count(text)}")
    untouched = [s["entry_id"] for s in data["scenes"] if s["entry_id"] not in descriptions]
    empty_untouched = [
        eid for eid in untouched if not (by_id[eid].get("description") or "")
    ]
    if problems:
        raise SystemExit("check failed:\n" + "\n".join(problems[:30]))
    print(f"OK {len(descriptions)}/{len(descriptions)} exact")
    print(f"untouched scenes {len(untouched)}; still without a data.json description: {len(empty_untouched)}")


def prove() -> None:
    """Wipe published copy, regenerate from the catalogue, and require a byte match."""
    publish()
    descriptions = load_source()
    index_before = INDEX.read_bytes()
    data_before = DATA.read_bytes()
    scene_before = {
        eid: (ROOT / f"{eid}.json").read_bytes() for eid in descriptions
    }

    # Drop the rendered paragraphs and the catalogue fields, then rebuild.
    html = INDEX.read_text(encoding="utf-8")
    for eid in descriptions:
        start, end = _card_span(html, eid)
        article = html[start:end]
        h3 = re.search(r"<h3>.*?</h3>", article, re.S)
        assert h3 is not None
        base = h3.end()
        paras = list(re.finditer(r"<p>.*?</p>", article[base:], re.S))
        p = paras[1]
        article = (
            article[: base + p.start()]
            + "<p></p>"
            + article[base + p.end() :]
        )
        html = html[:start] + article + html[end:]
    INDEX.write_text(html, encoding="utf-8")

    desc_line = re.compile(r'^[ \t]*"description": "(?:\\.|[^"\\])*",\n', re.M)
    data_raw = DATA.read_text(encoding="utf-8")
    for eid in list(descriptions)[:3]:
        i, j = _scene_block(data_raw, eid)
        block = data_raw[i:j]
        block2, n = desc_line.subn("", block, count=1)
        if n != 1:
            raise SystemExit(f"could not strip data.json description for {eid}")
        data_raw = data_raw[:i] + block2 + data_raw[j:]
    DATA.write_text(data_raw, encoding="utf-8")

    sample = next(iter(descriptions))
    scene_path = ROOT / f"{sample}.json"
    scene_raw = scene_path.read_text(encoding="utf-8")
    scene_path.write_text(DESC_KEY.sub(r'\1""', scene_raw, count=1), encoding="utf-8")

    try:
        publish()
    except Exception:
        INDEX.write_bytes(index_before)
        DATA.write_bytes(data_before)
        for eid, blob in scene_before.items():
            (ROOT / f"{eid}.json").write_bytes(blob)
        raise
    if INDEX.read_bytes() != index_before:
        raise SystemExit("index.html did not regenerate byte-for-byte")
    if DATA.read_bytes() != data_before:
        raise SystemExit("data.json did not regenerate byte-for-byte")
    if scene_path.read_bytes() != scene_before[sample]:
        raise SystemExit(f"{sample}.json did not regenerate byte-for-byte")
    for eid, blob in scene_before.items():
        if (ROOT / f"{eid}.json").read_bytes() != blob:
            raise SystemExit(f"{eid}.json changed during prove")
    check()
    print("persistence OK: wiped index, data.json, and a scene file; publisher restored them")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify exact texts, do not write")
    parser.add_argument("--prove", action="store_true", help="wipe outputs and confirm a rebuild restores them")
    args = parser.parse_args()
    if args.check:
        check()
        return
    changed = publish()
    print(
        "published"
        + (" scenes" if changed["scenes"] else "")
        + (" data.json" if changed["data"] else "")
        + (" index.html" if changed["index"] else "")
    )
    if args.prove:
        prove()


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        sys.exit(0)
