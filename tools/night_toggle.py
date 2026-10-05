#!/usr/bin/env python3
"""Spain gallery Night button (moon), format by format.

Matches the France / Sweden / Greece / Denmark night-toggle gate:

  A format is a night master only when the manifest records that exact
  path as the scene's own master and the file is on disk.

  * ``daylight_variant.source_night`` names that path, or
  * the manifest lighting label is exactly Night (``time_of_day`` or the
    composition head) and ``file_16x9`` / ``file_4x5`` / ``file_9x16`` is
    that master.

Scenario hour is not used, so dusk and daylight plates stay without a
Night button. A missing 9:16 stays empty. A 16:9 file is never copied
into the 9:16 slot, and a ``source_night`` path that is not the scene's
own master is never shown.

The button, the ``data-src-*-night`` / ``data-dl-night`` attributes, and
the click handler are re-applied on every run, so a later rebuild of
``index.html`` keeps them. Approvals and status lines are not rewritten.

    python3 tools/night_toggle.py
    python3 tools/night_toggle.py --check
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"
APP = ROOT / "app.js"
CSS = ROOT / "style.css"

FORMATS = (("16x9", "file_16x9"), ("4x5", "file_4x5"), ("9x16", "file_9x16"))
NIGHT_ATTR = {
    "16x9": "data-src-16-night",
    "4x5": "data-src-45-night",
    "9x16": "data-src-916-night",
}
NIGHT_BUTTON = (
    '<button type="button" class="night-tab" aria-pressed="false" '
    'title="Show the night image">\U0001f319 Night</button>'
)
NIGHT_COMMENT = (
    "<!-- night-toggle: app.js owns the moon button. "
    "Night sources are data-src-*-night only. -->"
)
ARTICLE_RE = re.compile(r'<article class="card" .*?</article>', re.S)
IMG_RE = re.compile(r"<img\b[^>]*>", re.S)
DL_RE = re.compile(r'<a class="download"[^>]*>', re.S)
NIGHT_BTN_RE = re.compile(
    r'<button type="button" class="night-tab"[^>]*>.*?</button>',
    re.S,
)
NIGHT_SCRIPT_RE = re.compile(
    r"\n<script>\s*\(function\(\)\{\s*"
    r"document\.addEventListener\('click', function\(e\)\{\s*"
    r"var b = e\.target\.closest \? e\.target\.closest\('\.night-tab'\) : null;"
    r".*?</script>\n",
    re.S,
)
STATUS_RE = re.compile(r'<p class="status">.*?</p>', re.S)
APP_START = "/* SPAIN_NIGHT_TOGGLE START */"
APP_END = "/* SPAIN_NIGHT_TOGGLE END */"
OLD_APP_START = "/* Section 16: 16:9 / 4:5 format tab switching per card. */"
OLD_APP_END = "/* Word-of-day slim band rotation (2026-09-25, Jason directive) */"
MOTION_MARKER = "card.querySelectorAll('.night-tab.is-active, .day-tab.is-active, .pc-tab.is-active')"
MOTION_OLD = """        return;
      }
      // Stop any other playing videos
"""
MOTION_NEW = """        return;
      }
      card.querySelectorAll('.night-tab.is-active, .day-tab.is-active, .pc-tab.is-active').forEach(function(x){
        x.classList.remove('is-active');
        x.setAttribute('aria-pressed','false');
        if (x.classList.contains('pc-tab')) x.setAttribute('data-postcard','off');
        else if (x.classList.contains('day-tab')) x.setAttribute('data-daynight','night');
      });
      // Stop any other playing videos
"""
CSS_RULE = (
    ".night-tab{display:inline-block;background:#243049;color:var(--ink);"
    "border-radius:8px;padding:.4rem .7rem;font-size:.85rem;border:1px solid var(--line);"
    "cursor:pointer}.night-tab:hover{border-color:var(--accent)}"
    ".night-tab.is-active{background:#1b2744;border-color:#9eb6e0;color:#e7eefc;font-weight:700}\n"
)

APP_BLOCK = r"""/* SPAIN_NIGHT_TOGGLE START */
/* Night / Daylight / Postcard / format. Night reads data-src-*-night only. */
function dlFormat(a){
  var f=a.getAttribute('data-dl');
  if(f==='16x9'||f==='4x5'||f==='9x16')return f;
  var blob=(a.getAttribute('href')||'')+' '+(a.textContent||'');
  if(/9x16|9:16/.test(blob))return '9x16';
  if(/4x5|4:5/.test(blob))return '4x5';
  return '16x9';
}
function modeOf(card){
  if(card.querySelector('.night-tab.is-active'))return 'night';
  if(card.querySelector('.pc-tab.is-active'))return 'postcard';
  var sun=card.querySelector('.day-tab:not(.pc-tab).is-active');
  if(sun&&sun.getAttribute('data-daynight')==='day')return 'day';
  return 'scene';
}
function srcFor(img,fmt,mode){
  if(!img)return '';
  if(mode==='night'){
    var nk=fmt==='9x16'?'data-src-916-night':fmt==='4x5'?'data-src-45-night':'data-src-16-night';
    return img.getAttribute(nk)||'';
  }
  if(mode==='postcard'){
    var pk=fmt==='9x16'?'data-src-916-pc':fmt==='4x5'?'data-src-45-pc':'data-src-16-pc';
    return img.getAttribute(pk)||'';
  }
  var sk=fmt==='9x16'?'data-src-916':fmt==='4x5'?'data-src-45':'data-src-16';
  if(mode==='day'){
    var dk=fmt==='9x16'?'data-src-916-day':fmt==='4x5'?'data-src-45-day':'data-src-16-day';
    var day=img.getAttribute(dk)||'';
    if(day)return day;
    if(fmt==='9x16')return '';
    return img.getAttribute(sk)||'';
  }
  return img.getAttribute(sk)||'';
}
function stopMotion(card){
  var preview=card.querySelector('.preview');
  var vid=preview&&preview.querySelector('video.motion-clip');
  if(vid)vid.remove();
  var img=card.querySelector('a.thumb img');
  if(img)img.style.display='';
  var btn=card.querySelector('.motion-btn.is-active');
  if(btn){
    btn.classList.remove('is-active');
    btn.innerHTML='\u25b6 360\u00b0';
    btn.setAttribute('title','Play the 360\u00b0 daylight motion clip');
  }
}
function clearModes(card,keep){
  var night=card.querySelector('.night-tab');
  if(night&&keep!=='night'){
    night.classList.remove('is-active');
    night.setAttribute('aria-pressed','false');
  }
  var sun=card.querySelector('.day-tab:not(.pc-tab)');
  if(sun&&keep!=='day'){
    sun.classList.remove('is-active');
    sun.setAttribute('aria-pressed','false');
    sun.setAttribute('data-daynight','night');
  }
  var pc=card.querySelector('.pc-tab');
  if(pc&&keep!=='postcard'){
    pc.classList.remove('is-active');
    pc.setAttribute('aria-pressed','false');
    pc.setAttribute('data-postcard','off');
  }
}
function rememberScenario(card){
  var sc=card.querySelector('p.scenario');
  if(!sc)return null;
  if(!sc.getAttribute('data-scenario')){
    var cur=sc.textContent||'';
    if(cur&&cur!=='Postcard collection'&&cur.indexOf('Daylight variant')<0)sc.setAttribute('data-scenario',cur);
  }
  return sc;
}
function showScenario(card,mode){
  var sc=rememberScenario(card);
  if(!sc)return;
  if(mode==='postcard')sc.textContent='Postcard collection';
  else if(mode==='day')sc.textContent='\u2600 Daylight variant \u00b7 derived from the night interpretation';
  else if(sc.getAttribute('data-scenario'))sc.textContent=sc.getAttribute('data-scenario');
}
function syncDownloads(card,img,mode){
  card.querySelectorAll('a.download').forEach(function(a){
    var u=srcFor(img,dlFormat(a),mode);
    if(u){a.hidden=false;a.href=u;a.setAttribute('download',u.split('/').pop());}
    else a.hidden=true;
  });
}
function applyPreview(card,img,link,fmt,mode){
  var next=srcFor(img,fmt,mode);
  if(!next)return;
  img.src=next;link.href=next;
  link.classList.toggle('tall',fmt==='4x5');
  link.classList.toggle('tall916',fmt==='9x16');
}
function sync916(card,img,mode){
  var t916=card.querySelector('.fmt-tab[data-format="9x16"]');
  if(!t916)return;
  var ok=!!srcFor(img,'9x16',mode);
  t916.disabled=!ok;
  t916.classList.toggle('is-disabled',!ok);
  if(!ok&&t916.classList.contains('is-active')){
    var t16=card.querySelector('.fmt-tab[data-format="16x9"]');
    if(t16)t16.click();
  }
}
document.querySelectorAll('.card').forEach(card=>{
  const tabs=card.querySelectorAll('.fmt-tab');
  const link=card.querySelector('a.thumb');
  const img=link&&link.querySelector('img');
  tabs.forEach(tab=>tab.addEventListener('click',e=>{
    e.preventDefault();
    if(tab.disabled||tab.classList.contains('is-disabled'))return;
    const fmt=tab.dataset.format;
    const prev=card.querySelector('.fmt-tab.is-active');
    tabs.forEach(t=>t.classList.toggle('is-active',t===tab));
    if(!img||!link)return;
    const mode=modeOf(card);
    const next=srcFor(img,fmt,mode);
    if(mode==='night'&&!next)return;
    if(mode==='scene'&&!card.querySelector('.pc-tab')&&fmt==='9x16'&&next&&!card.hasAttribute('data-916-ok')){
      const probe=new Image();
      probe.onload=function(){card.setAttribute('data-916-ok','1');applyPreview(card,img,link,fmt,mode);};
      probe.onerror=function(){
        card.setAttribute('data-916-missing','1');
        tab.remove();
        const dl=card.querySelector('a.download[data-dl="9x16"]');if(dl)dl.remove();
        tabs.forEach(t=>t.classList.toggle('is-active',t===prev));
        link.classList.remove('tall916');
      };
      probe.src=next;
      return;
    }
    if(next)applyPreview(card,img,link,fmt,mode);
  }));
});
document.querySelectorAll('.card .night-tab').forEach(ntab=>{
  ntab.addEventListener('click',e=>{
    e.preventDefault();
    const card=ntab.closest('.card');
    if(!card)return;
    stopMotion(card);
    clearModes(card,'night');
    ntab.classList.add('is-active');
    ntab.setAttribute('aria-pressed','true');
    const link=card.querySelector('a.thumb');
    const img=link&&link.querySelector('img');
    sync916(card,img,'night');
    const ftab=card.querySelector('.fmt-tab.is-active');
    const fmt=ftab?ftab.getAttribute('data-format'):'16x9';
    if(img&&link)applyPreview(card,img,link,fmt,'night');
    syncDownloads(card,img,'night');
    showScenario(card,'night');
  });
});
document.querySelectorAll('.card .pc-tab').forEach(ptab=>{
  ptab.addEventListener('click',e=>{
    e.preventDefault();
    const card=ptab.closest('.card');
    if(!card)return;
    stopMotion(card);
    const on=!ptab.classList.contains('is-active');
    if(on)clearModes(card,'postcard');
    ptab.classList.toggle('is-active',on);
    ptab.setAttribute('aria-pressed',on?'true':'false');
    ptab.setAttribute('data-postcard',on?'on':'off');
    const link=card.querySelector('a.thumb');
    const img=link&&link.querySelector('img');
    const mode=on?'postcard':'scene';
    sync916(card,img,mode);
    const ftab=card.querySelector('.fmt-tab.is-active');
    const fmt=ftab?ftab.getAttribute('data-format'):'16x9';
    if(img&&link)applyPreview(card,img,link,fmt,mode);
    syncDownloads(card,img,mode);
    showScenario(card,mode);
  });
});
document.querySelectorAll('.card').forEach(card=>{
  const dtab=card.querySelector('.day-tab:not(.pc-tab)');
  if(!dtab)return;
  dtab.addEventListener('click',e=>{
    e.preventDefault();
    stopMotion(card);
    const isDay=!dtab.classList.contains('is-active');
    if(isDay)clearModes(card,'day');
    dtab.classList.toggle('is-active',isDay);
    dtab.setAttribute('aria-pressed',isDay?'true':'false');
    dtab.setAttribute('data-daynight',isDay?'day':'night');
    const link=card.querySelector('a.thumb');
    const img=link&&link.querySelector('img');
    const mode=isDay?'day':'scene';
    sync916(card,img,mode);
    const ftab=card.querySelector('.fmt-tab.is-active');
    const fmt=ftab?ftab.getAttribute('data-format'):'16x9';
    if(img&&link)applyPreview(card,img,link,fmt,mode);
    syncDownloads(card,img,mode);
    showScenario(card,mode);
  });
});
/* SPAIN_NIGHT_TOGGLE END */
"""


def clean_path(value: object) -> str:
    if not isinstance(value, str):
        return ""
    text = value.split("?", 1)[0].strip()
    if not text or text.startswith(("/", "\\")) or ".." in text.replace("\\", "/"):
        return ""
    return text


def master_exists(rel: str) -> bool:
    if not rel:
        return False
    path = (ROOT / rel).resolve()
    root = ROOT.resolve()
    if path != root and root not in path.parents:
        return False
    return path.is_file()


def lighting_is_night(scene: dict) -> bool:
    """Manifest lighting label, not the scenario clock."""
    if str(scene.get("time_of_day") or "").strip() == "Night":
        return True
    head = str(scene.get("composition") or "").split("·", 1)[0].strip()
    return head in {"Night", "NIGHT"}


def night_urls(scene: dict, exists=master_exists) -> list[str]:
    """Return [16:9, 4:5, 9:16]. Empty string means that format has no night master."""
    variant = scene.get("daylight_variant")
    source = variant.get("source_night") if isinstance(variant, dict) else None
    if not isinstance(source, dict):
        source = {}
    scene_night = lighting_is_night(scene)
    found: list[str] = []
    for fmt, key in FORMATS:
        own = clean_path(scene.get(key))
        info = source.get(fmt)
        recorded = clean_path(info.get("path")) if isinstance(info, dict) else ""
        qualified = ""
        if own and exists(own):
            if recorded and recorded == own:
                qualified = own
            elif scene_night:
                qualified = own
        found.append(qualified)
    return found


def load_manifests() -> list[dict]:
    scenes = []
    for path in sorted(ROOT.glob("ES-*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and data.get("entry_id"):
            scenes.append(data)
    return scenes


def load_night_masters(scenes: list[dict] | None = None) -> dict[str, list[str]]:
    rows = scenes if scenes is not None else load_manifests()
    found: dict[str, list[str]] = {}
    for scene in rows:
        urls = night_urls(scene)
        if any(urls):
            found[str(scene["entry_id"])] = urls
    return found


def _rewrite_img(img: str, urls: list[str]) -> str:
    for attr in NIGHT_ATTR.values():
        img = re.sub(rf'\s{attr}="[^"]*"', "", img)
    extras = []
    for fmt, url in zip(("16x9", "4x5", "9x16"), urls):
        if url:
            extras.append(f' {NIGHT_ATTR[fmt]}="{url}"')
    if not extras:
        return img
    if img.endswith("/>"):
        return img[:-2] + "".join(extras) + "/>"
    if img.endswith(">"):
        return img[:-1] + "".join(extras) + ">"
    raise SystemExit("image tag is not closed")


def _infer_dl_format(tag: str) -> str:
    match = re.search(r'data-dl="(16x9|4x5|9x16)"', tag)
    if match:
        return match.group(1)
    if re.search(r"9x16|9:16", tag):
        return "9x16"
    if re.search(r"4x5|4:5", tag):
        return "4x5"
    return "16x9"


def _rewrite_download(tag: str, urls: list[str]) -> str:
    fmt = _infer_dl_format(tag)
    tag = re.sub(r'\sdata-dl-night="[^"]*"', "", tag)
    tag = re.sub(r'\sdata-dl="[^"]*"', "", tag)
    by_fmt = {"16x9": urls[0], "4x5": urls[1], "9x16": urls[2]}
    extra = f' data-dl="{fmt}"'
    if by_fmt[fmt]:
        extra += f' data-dl-night="{by_fmt[fmt]}"'
    return tag.replace('<a class="download"', "<a class=\"download\"" + extra, 1)


def _rewrite_article(article: str, urls: list[str]) -> str:
    img = IMG_RE.search(article)
    if not img:
        raise SystemExit("card is missing an image")
    article = article[: img.start()] + _rewrite_img(img.group(0), urls) + article[img.end() :]
    article = NIGHT_BTN_RE.sub("", article)
    if any(urls):
        daynight = re.search(r'<div class="daynight"[^>]*>', article)
        if daynight:
            article = article[: daynight.end()] + NIGHT_BUTTON + article[daynight.end() :]
        else:
            tabs = re.search(r'<div class="fmt-tabs"[^>]*>.*?</div>', article, re.S)
            if not tabs:
                raise SystemExit("card is missing format tabs")
            row = (
                '<div class="daynight" role="group" aria-label="Day or night">'
                + NIGHT_BUTTON
                + "</div>"
            )
            article = article[: tabs.end()] + row + article[tabs.end() :]
    return DL_RE.sub(lambda match: _rewrite_download(match.group(0), urls), article)


def apply_index_html(html: str, night: dict[str, list[str]] | None = None) -> str:
    """Insert the Night button and per-format night masters. Idempotent."""
    before_status = STATUS_RE.findall(html)
    before_cosmo = len(re.findall(r"cosmo\s+qc", html, re.I))
    masters = night if night is not None else load_night_masters()
    seen: set[str] = set()

    def rewrite(match: re.Match[str]) -> str:
        article = match.group(0)
        id_match = re.search(r'\bid="(ES-[^"]+)"', article)
        if not id_match:
            raise SystemExit("gallery card is missing an id")
        entry_id = id_match.group(1)
        if entry_id in seen:
            raise SystemExit(f"duplicate gallery card {entry_id}")
        seen.add(entry_id)
        return _rewrite_article(article, masters.get(entry_id, ["", "", ""]))

    updated = ARTICLE_RE.sub(rewrite, html)
    if NIGHT_SCRIPT_RE.search(updated):
        updated = NIGHT_SCRIPT_RE.sub("\n" + NIGHT_COMMENT + "\n", updated, count=1)
    elif NIGHT_COMMENT not in updated:
        raise SystemExit("night click script anchor missing; refusing to publish")
    if MOTION_MARKER not in updated:
        if updated.count(MOTION_OLD) != 1:
            raise SystemExit("360 click anchor missing; refusing to publish")
        updated = updated.replace(MOTION_OLD, MOTION_NEW, 1)
    if STATUS_RE.findall(updated) != before_status:
        raise SystemExit("night toggle rewrote a status line")
    if len(re.findall(r"cosmo\s+qc", updated, re.I)) != before_cosmo:
        raise SystemExit("night toggle changed a Cosmo QC claim")
    return updated


def apply_app_js(text: str) -> str:
    if APP_START in text and APP_END in text:
        start = text.find(APP_START)
        end = text.find(APP_END)
        if end < start:
            raise SystemExit("app.js night block is out of order")
        end = end + len(APP_END)
        # Keep the following newline that already sits after the end marker.
        if text[end : end + 1] == "\n":
            end += 1
        return text[:start] + APP_BLOCK + text[end:]
    start = text.find(OLD_APP_START)
    end = text.find(OLD_APP_END)
    if start < 0 or end < 0 or end < start:
        raise SystemExit("app.js format/daylight block missing; refusing to publish")
    return text[:start] + APP_BLOCK + "\n" + text[end:]


def apply_css(text: str) -> str:
    if ".night-tab.is-active" in text:
        return text
    if not text.endswith("\n"):
        text += "\n"
    return text + "\n" + CSS_RULE


def _self_test() -> None:
    files = {
        "es-01-018-16x9.png",
        "es-01-018-4x5.png",
        "es-01-016-cand-r1-16x9.png",
        "es-01-016-cand-r1-4x5.png",
        "es-01-016-cand-r1-9x16.png",
        "es-01-016-r2-16x9.png",
        "es-01-002-cand-r1-16x9.png",
        "es-01-002-cand-r1-4x5.png",
        "es-01-002-cand-r1-9x16.png",
        "es-01-001-daylight-r4-16x9.png",
        "es-01-001-daylight-r4-4x5.png",
        "es-01-009-r1-16x9.png",
        "es-01-009-r1-4x5.png",
    }

    def exists(rel: str) -> bool:
        return rel in files

    bridge = {
        "entry_id": "ES-01-018",
        "time_of_day": "Night",
        "composition": "Night · bridge",
        "file_16x9": "es-01-018-16x9.png",
        "file_4x5": "es-01-018-4x5.png",
        "daylight_variant": {
            "source_night": {
                "16x9": {"path": "es-01-018-16x9.png"},
                "4x5": {"path": "es-01-018-4x5.png"},
            }
        },
    }
    if night_urls(bridge, exists) != [
        "es-01-018-16x9.png",
        "es-01-018-4x5.png",
        "",
    ]:
        raise SystemExit("self-test invented a 9:16 night plate")
    missing = dict(bridge)
    missing["file_16x9"] = "es-01-018-missing-16x9.png"
    missing["daylight_variant"] = {
        "source_night": {
            "16x9": {"path": "es-01-018-missing-16x9.png"},
            "4x5": {"path": "es-01-018-4x5.png"},
        }
    }
    if night_urls(missing, exists)[0]:
        raise SystemExit("self-test accepted a night master that is not on disk")
    other = {
        "time_of_day": "Night",
        "composition": "Night · pool",
        "file_16x9": "es-01-016-cand-r1-16x9.png",
        "file_4x5": "es-01-016-cand-r1-4x5.png",
        "file_9x16": "es-01-016-cand-r1-9x16.png",
        "daylight_variant": {
            "source_night": {
                "16x9": {"path": "es-01-016-r2-16x9.png"},
                "4x5": {"path": "es-01-016-r2-4x5.png"},
            }
        },
    }
    got = night_urls(other, exists)
    if "r2" in " ".join(got) or got[2] != "es-01-016-cand-r1-9x16.png":
        raise SystemExit("self-test used a source_night path that is not the scene master")
    dusk = {
        "time_of_day": "DUSK twilight",
        "composition": "DUSK twilight · plaza",
        "file_16x9": "es-01-009-r1-16x9.png",
        "file_4x5": "es-01-009-r1-4x5.png",
    }
    if any(night_urls(dusk, exists)):
        raise SystemExit("self-test gave a dusk plate a Night button")
    morning = {
        "time_of_day": "Morning daylight",
        "composition": "Morning daylight · facade",
        "file_16x9": "es-01-001-daylight-r4-16x9.png",
        "file_4x5": "es-01-001-daylight-r4-4x5.png",
    }
    if any(night_urls(morning, exists)):
        raise SystemExit("self-test gave a daylight plate a Night button")
    escaped = dict(bridge)
    escaped["file_16x9"] = "../es-01-018-16x9.png"
    escaped["daylight_variant"] = {
        "source_night": {"16x9": {"path": "../es-01-018-16x9.png"}}
    }
    if night_urls(escaped, exists)[0]:
        raise SystemExit("self-test accepted a path outside the repository")
    portrait = {
        "time_of_day": "Night",
        "file_16x9": "es-01-002-cand-r1-16x9.png",
        "file_4x5": "es-01-002-cand-r1-4x5.png",
    }
    if night_urls(portrait, exists)[2]:
        raise SystemExit("self-test filled 9:16 from a 16:9 master")


def check_html(html: str, night: dict[str, list[str]]) -> dict:
    _self_test()
    cards = ARTICLE_RE.findall(html)
    if len(cards) != 365:
        raise SystemExit(f"expected 365 cards, found {len(cards)}")
    errors: list[str] = []
    buttons = 0
    portrait = 0
    for article in cards:
        id_match = re.search(r'\bid="(ES-[^"]+)"', article)
        if not id_match:
            errors.append("card missing id")
            continue
        entry_id = id_match.group(1)
        urls = night.get(entry_id, ["", "", ""])
        has = "night-tab" in article
        if has:
            buttons += 1
        if has != any(urls):
            errors.append(f"{entry_id} night button {has} does not match the night master")
        img = IMG_RE.search(article)
        if not img:
            errors.append(f"{entry_id} missing image")
            continue
        tag = img.group(0)
        for fmt, attr, url in (
            ("16x9", "data-src-16-night", urls[0]),
            ("4x5", "data-src-45-night", urls[1]),
            ("9x16", "data-src-916-night", urls[2]),
        ):
            found = re.search(rf'{attr}="([^"]*)"', tag)
            got = found.group(1) if found else ""
            if got != url:
                errors.append(f"{entry_id} {fmt} night attr {got!r} != {url!r}")
            if fmt == "9x16" and got:
                portrait += 1
                if not got.endswith("-9x16.png") and "9x16" not in got:
                    errors.append(f"{entry_id} 9:16 night plate does not look like a portrait")
                if got == urls[0]:
                    errors.append(f"{entry_id} 9:16 night plate repeats the 16:9 file")
        if "data-src-16" in tag and re.search(r'data-src-916-night="[^"]*16x9', tag):
            errors.append(f"{entry_id} 9:16 night attribute points at a 16:9 file")
    if "data-src-916') || i.getAttribute('data-src-16')" in html or "|| i.getAttribute('data-src-16')" in html:
        errors.append("night click handler still falls back to 16:9")
    if "closest('.night-tab')" not in APP.read_text(encoding="utf-8") and "night-tab" not in APP.read_text(encoding="utf-8"):
        errors.append("app.js is missing the night handler")
    app = APP.read_text(encoding="utf-8")
    if "data-src-916-night" not in app or "stopMotion" not in app:
        errors.append("app.js night handler is not format-aware")
    if errors:
        raise SystemExit("\n".join(errors[:30]))
    return {
        "cards": len(cards),
        "night_buttons": buttons,
        "night_16x9": sum(1 for urls in night.values() if urls[0]),
        "night_4x5": sum(1 for urls in night.values() if urls[1]),
        "night_9x16": portrait,
    }


def apply_behavior_files() -> None:
    app = apply_app_js(APP.read_text(encoding="utf-8"))
    if app != APP.read_text(encoding="utf-8"):
        APP.write_text(app, encoding="utf-8")
    css = apply_css(CSS.read_text(encoding="utf-8"))
    if css != CSS.read_text(encoding="utf-8"):
        CSS.write_text(css, encoding="utf-8")


def rebuild() -> dict:
    _self_test()
    night = load_night_masters()
    original = INDEX.read_text(encoding="utf-8")
    updated = apply_index_html(original, night)
    if apply_index_html(updated, night) != updated:
        raise SystemExit("night toggle rebuild is not idempotent")
    if updated != original:
        INDEX.write_text(updated, encoding="utf-8")
    apply_behavior_files()
    return check_html(updated, night)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero when the built page disagrees with the night-master gate.",
    )
    args = parser.parse_args()
    if args.check:
        census = check_html(INDEX.read_text(encoding="utf-8"), load_night_masters())
    else:
        census = rebuild()
    print(
        "cards {cards}, night buttons {night_buttons}, "
        "night 16:9 {night_16x9}, night 4:5 {night_4x5}, night 9:16 {night_9x16}".format(
            **census
        )
    )


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        sys.exit(0)
