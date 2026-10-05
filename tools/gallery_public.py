#!/usr/bin/env python3
"""Public copy for the Spain gallery page.

index.html is the built page. tools/publish_descriptions.py and
build-image-sitemap.py rewrite that page in place; both call
apply_public_page() so a later rebuild keeps these visitor-facing rules:

  * no <p class="review-label"> element on a card
  * an approved status line is "Approved · <variant>" with the variant
    that card already had
  * header nav keeps Home, License, and the Greece switcher

The false "Cosmo QC" wording is removed from the built page, including
the embedded scene-data the page carries. No replacement review claim
is written. Scene manifests and approvals/ are not read or written.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"

REVIEW_LABEL = re.compile(r'<p class="review-label">.*?</p>', re.S)

# Exact approved-status claims. The last segment is the variant already
# on that card (Night, Daylight, Dusk, Morning daylight, Midday daylight).
APPROVED_STATUS = (
    ("Approved · Cosmo QC 5/5 · ", "Approved · "),
    ("Approved · internal editorial QC · ", "Approved · "),
    ("Awaiting Cosmo QC · ", "Awaiting · "),
)

DEAD_NAV = (
    '<a href="#library">Gallery</a>'
    '<a href="#pipeline">Pipeline</a>'
    '<a href="#coverage">Regions</a>'
)

# Delete the claim phrase only. Longer patterns run first so a score
# or a whole claim sentence goes with the name. Factual sentences stay.
# A replacement is either "" or punctuation needed so the remaining
# words still form the original sentence.
_CLAIM_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r"Approved following Cosmo QC 5/5, relayed by Jason on 23 September 2026\.\s*",
            re.I,
        ),
        "",
    ),
    (
        re.compile(
            r"Church proportions, sea-wall course and waterfront arrangement need Cosmo QC\.\s*",
            re.I,
        ),
        "",
    ),
    (re.compile(r"No new Cosmo QC is claimed\.\s*", re.I), ""),
    (re.compile(r"No Cosmo QC is claimed for these bytes\.\s*", re.I), ""),
    (re.compile(r"Cosmo QC 5/5,\s*approved 23 September 2026\.\s*", re.I), ""),
    (re.compile(r"by Cosmo QC APPROVED 5/5,", re.I), ","),
    (re.compile(r"Cosmo QC\s*:\s*5/5 approved,\s*", re.I), ""),
    (
        re.compile(
            r"Cosmo QC(?:\s+APPROVED)?\s+5/5(?:\s+approved)?(?:,\s*|\.\s*|\s+)",
            re.I,
        ),
        "",
    ),
    (re.compile(r"Cosmo QC approved\.\s*", re.I), ""),
    (re.compile(r"Cosmo QC approved;\s*", re.I), ""),
    (re.compile(r"Cosmo QC\s*[:;,]?\s*", re.I), ""),
)

_EMPTY_P = re.compile(r"<p>\s*</p>\n?")
_SCRIPT = re.compile(r"(<script\b[^>]*>)(.*?)(</script>)", re.S)
_TEXT_NODE = re.compile(r"(?<=>)[^<]*")


def _capitalize_if_claim_was_prefix(original: str, updated: str) -> str:
    """Capitalize a remainder that used to follow a leading claim sentence."""
    old = original.lstrip()
    new = updated.lstrip()
    if not old or not new or not old[0].isupper() or not new[0].islower():
        return updated
    pad = updated[: len(updated) - len(new)]
    return pad + new[0].upper() + new[1:]


def strip_cosmo_qc(text: str) -> str:
    """Remove Cosmo QC wording. Keep the surrounding factual words."""
    updated = text
    for old, new in APPROVED_STATUS:
        updated = updated.replace(old, new)
    for pattern, repl in _CLAIM_PATTERNS:
        updated = pattern.sub(repl, updated)
    if updated == text:
        return text
    updated = re.sub(r"[ \t]{2,}", " ", updated)
    updated = re.sub(r"\s+([,.;])", r"\1", updated)
    updated = updated.replace("—;", "—").replace("— ;", "—")
    updated = re.sub(r"—\s{2,}", "— ", updated)
    updated = updated.rstrip()
    return _capitalize_if_claim_was_prefix(text, updated)


def _clean_markup(html: str) -> str:
    return _TEXT_NODE.sub(lambda match: strip_cosmo_qc(match.group(0)), html)


def _clean_scene_data(body: str) -> str:
    import json

    data = json.loads(body)

    def walk(value):
        if isinstance(value, dict):
            return {key: walk(item) for key, item in value.items()}
        if isinstance(value, list):
            return [walk(item) for item in value]
        if isinstance(value, str):
            return strip_cosmo_qc(value)
        return value

    cleaned = walk(data)
    return json.dumps(cleaned, ensure_ascii=False, separators=(", ", ": "))


def apply_public_page(html: str) -> str:
    """Apply the visitor-facing label and nav rules. Idempotent."""
    updated = REVIEW_LABEL.sub("", html)
    if updated.count(DEAD_NAV) > 1:
        raise SystemExit("header nav appears more than once")
    updated = updated.replace(DEAD_NAV, "", 1)

    parts: list[str] = []
    pos = 0
    for match in _SCRIPT.finditer(updated):
        parts.append(_clean_markup(updated[pos : match.start()]))
        opener, body, closer = match.group(1), match.group(2), match.group(3)
        if 'id="scene-data"' in opener:
            body = _clean_scene_data(body)
        parts.append(opener + body + closer)
        pos = match.end()
    parts.append(_clean_markup(updated[pos:]))
    updated = _EMPTY_P.sub("", "".join(parts))
    if re.search(r"cosmo\s+qc", updated, re.I):
        raise SystemExit("public page still contains a Cosmo QC claim")
    if 'class="review-label"' in updated:
        raise SystemExit("public page still contains a review-label element")
    if DEAD_NAV in updated or 'href="#pipeline"' in updated or 'href="#coverage"' in updated:
        raise SystemExit("public page still contains a dead nav link")
    return updated


def _self_test() -> None:
    sample = (
        '<p class="review-label">APPROVED · COSMO QC 5/5</p>'
        '<p class="status">Approved · Cosmo QC 5/5 · Daylight</p>'
        '<p class="status">Approved · internal editorial QC · Midday daylight</p>'
        '<p class="status">Candidate · architectural rebuild · awaiting Cosmo re-audit · Night</p>'
        "<p>Cosmo QC 5/5, approved 23 September 2026.</p>"
        "<p>Cosmo QC approved; historical provenance and weather notes retained.</p>"
        "<p>pending — Cosmo QC; architecture and viewpoint to review</p>"
        "<p>Cosmo QC approved. Generated fine detail remains interpretive.</p>"
        '<nav aria-label="Main"><a class="home-link" href="https://jdvision.org/">&#8962; Home</a>'
        '<span class="sep" aria-hidden="true">|</span>'
        + DEAD_NAV
        + '<a href="#license">License</a><span class="sep" aria-hidden="true">|</span>'
        '<a href="https://greece.jdvision.org/">Greece</a></nav>'
    )
    out = apply_public_page(sample)
    if "review-label" in out or re.search(r"cosmo\s+qc", out, re.I):
        raise SystemExit("self-test left a review claim")
    if "Approved · Daylight" not in out or "Approved · Midday daylight" not in out:
        raise SystemExit("self-test dropped a variant suffix")
    if "awaiting Cosmo re-audit · Night" not in out:
        raise SystemExit("self-test rewrote a candidate status line")
    if "Generated fine detail remains interpretive." not in out:
        raise SystemExit("self-test dropped factual detail")
    if "approved 23 September 2026" in out:
        raise SystemExit("self-test left a claim sentence")
    if "Historical provenance and weather notes retained." not in out:
        raise SystemExit("self-test did not keep the provenance note")
    if "pending — architecture and viewpoint to review" not in out:
        raise SystemExit("self-test left broken claim punctuation")
    if 'href="#library"' in out or 'href="#pipeline"' in out or 'href="#coverage"' in out:
        raise SystemExit("self-test left a dead nav link")
    if 'href="#license"' not in out or "jdvision.org" not in out or "greece.jdvision.org" not in out:
        raise SystemExit("self-test dropped Home, License, or Greece")
    if apply_public_page(out) != out:
        raise SystemExit("self-test is not idempotent")


def main() -> None:
    _self_test()
    html = INDEX.read_text(encoding="utf-8")
    updated = apply_public_page(html)
    if updated != html:
        INDEX.write_text(updated, encoding="utf-8")
        print("updated index.html")
    else:
        print("index.html already matches the public copy")


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        sys.exit(0)
