#!/usr/bin/env python3
"""Spain gallery gate for genuine daylight as the card primary.

Matches Netherlands ``tools/gallery_phase1.py`` ``is_genuine_daylight``
(merged PR #74, squash 91e7a4b, still on main e868118):

  daylight_primary only when ``daylight_variant.provenance`` is exactly
  ``genuine-daylight`` AND ``file_16x9_day`` exists on disk.

The flag is computed here and is not written back onto scene JSON or
``data.json``. Night masters stay on ``file_16x9`` / ``file_4x5`` /
``file_9x16``. A ``daylight_interim`` plate does not qualify a card.

    python3 tools/daylight_primary.py
    python3 tools/daylight_primary.py --check
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data.json"
INDEX = ROOT / "index.html"
GENUINE = "genuine-daylight"

CARD_SPLIT = '<article class="card"'
ID_RE = re.compile(r'id="(ES-[^"]+)"')
SRC_RE = re.compile(r'<img\b[^>]*\ssrc="([^"]+)"')


def master_exists(rel: object) -> bool:
    if not isinstance(rel, str) or not rel or rel.startswith(("/", "\\")):
        return False
    path = (ROOT / rel).resolve()
    root = ROOT.resolve()
    if path != root and root not in path.parents:
        return False
    return path.is_file()


def is_genuine_daylight(scene: dict) -> bool:
    """True only for a genuine-daylight master that exists on disk.

    Interim and derivative daylight do not qualify. ``daylight_interim``
    is never a positive signal.
    """
    variant = scene.get("daylight_variant")
    if not isinstance(variant, dict) or variant.get("provenance") != GENUINE:
        return False
    return master_exists(scene.get("file_16x9_day"))


def load_manifests() -> list[dict]:
    scenes = []
    for path in sorted(ROOT.glob("ES-*.json")):
        data = json.loads(path.read_text())
        if isinstance(data, dict) and data.get("entry_id"):
            scenes.append(data)
    return scenes


def load_catalogue() -> list[dict]:
    payload = json.loads(DATA.read_text())
    scenes = payload.get("scenes")
    if not isinstance(scenes, list):
        raise SystemExit("data.json scenes is not a list")
    return [row for row in scenes if isinstance(row, dict)]


def parse_cards(html: str) -> list[dict]:
    cards = []
    for part in html.split(CARD_SPLIT)[1:]:
        id_match = ID_RE.search(part)
        src_match = SRC_RE.search(part)
        if not id_match or not src_match:
            raise SystemExit("gallery card is missing an id or image")
        cards.append(
            {
                "entry_id": id_match.group(1),
                "src": src_match.group(1),
                "sun_toggle": 'class="day-tab"' in part,
                "night_toggle": "night-tab" in part,
            }
        )
    return cards


def _self_test() -> None:
    sample = "es-01-001-daylight-r4-16x9.png"
    if not master_exists(sample):
        raise SystemExit("self-test sample master is missing")
    if is_genuine_daylight({"daylight_interim": True, "daylight_16x9": sample}):
        raise SystemExit("interim plate qualified as genuine daylight")
    if is_genuine_daylight(
        {
            "daylight_variant": {
                "provenance": None,
                "derivative_disclosure": "derived from the night interpretation",
            },
            "file_16x9_day": sample,
        }
    ):
        raise SystemExit("derivative daylight qualified as genuine")
    if is_genuine_daylight({"daylight_variant": {"provenance": GENUINE}}):
        raise SystemExit("genuine provenance without a day 16:9 file qualified")
    if is_genuine_daylight(
        {
            "daylight_variant": {"provenance": "Genuine-daylight"},
            "file_16x9_day": sample,
        }
    ):
        raise SystemExit("provenance match was not exact")
    if not is_genuine_daylight(
        {
            "daylight_variant": {"provenance": GENUINE},
            "file_16x9_day": sample,
            "daylight_interim": True,
        }
    ):
        raise SystemExit("exact genuine-daylight gate rejected an existing day 16:9")
    if is_genuine_daylight(
        {
            "daylight_variant": {"provenance": GENUINE},
            "file_16x9_day": "../" + sample,
        }
    ):
        raise SystemExit("day 16:9 path escaped the repository")


def check() -> dict:
    _self_test()
    manifests = load_manifests()
    catalogue = load_catalogue()
    html = INDEX.read_text()
    cards = parse_cards(html)
    errors: list[str] = []

    manifest_genuine = [s for s in manifests if is_genuine_daylight(s)]
    catalogue_genuine = [s for s in catalogue if is_genuine_daylight(s)]
    interim = [s for s in catalogue if s.get("daylight_interim") is True]
    interim_plates = {
        s["entry_id"]: s.get("daylight_16x9")
        for s in interim
        if s.get("entry_id") and s.get("daylight_16x9")
    }

    for scene in manifests + catalogue:
        if scene.get("daylight_primary") and not is_genuine_daylight(scene):
            errors.append(
                f"{scene.get('entry_id')} has daylight_primary without the genuine-daylight gate"
            )

    by_card = {card["entry_id"]: card for card in cards}
    if len(by_card) != len(cards):
        errors.append("gallery has duplicate card ids")

    for entry_id, plate in interim_plates.items():
        card = by_card.get(entry_id)
        if card and card["src"] == plate and not is_genuine_daylight(
            next(s for s in catalogue if s.get("entry_id") == entry_id)
        ):
            errors.append(f"{entry_id} interim daylight plate is the card primary")

    for card in cards:
        if card["night_toggle"]:
            errors.append(
                f"{card['entry_id']} has a nighttime toggle without a genuine-daylight card"
            )

    for scene in manifest_genuine:
        entry_id = scene.get("entry_id")
        card = by_card.get(entry_id)
        day = scene.get("file_16x9_day")
        if card is None:
            errors.append(f"{entry_id} genuine daylight has no gallery card")
            continue
        if card["src"] != day:
            errors.append(f"{entry_id} genuine daylight is not the card primary")
        if not card["night_toggle"]:
            errors.append(f"{entry_id} genuine daylight card has no nighttime toggle")

    if errors:
        raise SystemExit("\n".join(errors))

    return {
        "scenes": len(catalogue),
        "manifests": len(manifests),
        "genuine_daylight": len(manifest_genuine),
        "catalogue_genuine_daylight": len(catalogue_genuine),
        "daylight_interim": len(interim),
        "cards": len(cards),
        "sun_toggle": sum(1 for card in cards if card["sun_toggle"]),
        "night_toggle": sum(1 for card in cards if card["night_toggle"]),
        "interim_card_primary": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero when a card breaks the genuine-daylight gate.",
    )
    parser.parse_args()
    census = check()
    print(
        "scenes {scenes}, manifests {manifests}, "
        "genuine-daylight {genuine_daylight}, "
        "catalogue genuine-daylight {catalogue_genuine_daylight}, "
        "daylight_interim {daylight_interim}, "
        "cards {cards}, sun toggle {sun_toggle}, "
        "night toggle {night_toggle}, "
        "interim card primary {interim_card_primary}".format(**census)
    )
    if census["genuine_daylight"] or census["catalogue_genuine_daylight"]:
        print("genuine daylight cards follow file_16x9_day behind the nighttime toggle")
    else:
        print("no genuine-daylight master; interim plates were not made the card primary")


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        sys.exit(0)
