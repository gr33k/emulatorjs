#!/usr/bin/env python3
"""Fetch authentic retro hardware photos and raw gameplay clips for EmuHub V19.

Sources:
- Wikimedia Commons for hardware photography and arcade environment photos.
- The repository's existing LinuxServer EmulatorJS metadata for IPFS video CIDs.

The script never generates hardware or game imagery. Missing assets are recorded and
omitted rather than replaced with approximations.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
import time
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "v19_source_assets"
HW = OUT / "hardware"
VID = OUT / "gameplay"
META = ROOT / "metadata"
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "EmuHub-V19-AssetBuilder/1.0 (GitHub Actions; archival media composition)"})

HARDWARE: list[dict[str, str]] = [
    # 1970s
    {"key":"channelf","era":"1970s","kind":"console","query":"Fairchild Channel F console Evan-Amos"},
    {"key":"atari2600","era":"1970s","kind":"console","query":"Atari 2600 console set Evan-Amos"},
    {"key":"pet","era":"1970s","kind":"computer","query":"Commodore PET 2001 computer Evan-Amos"},
    {"key":"odyssey2","era":"1970s","kind":"console","query":"Magnavox Odyssey 2 console set Evan-Amos"},
    {"key":"intv","era":"1970s","kind":"console","query":"Intellivision console set Evan-Amos"},
    # 1980s
    {"key":"gw","era":"1980s","kind":"handheld","query":"Nintendo Game & Watch handheld console"},
    {"key":"vic20","era":"1980s","kind":"computer","query":"Commodore VIC-20 computer Evan-Amos"},
    {"key":"zx81","era":"1980s","kind":"computer","query":"Sinclair ZX81 computer"},
    {"key":"p2000","era":"1980s","kind":"computer","query":"Philips P2000T computer"},
    {"key":"pc88","era":"1980s","kind":"computer","query":"NEC PC-8801 computer"},
    {"key":"atari5200","era":"1980s","kind":"console","query":"Atari 5200 console set Evan-Amos"},
    {"key":"c64","era":"1980s","kind":"computer","query":"Commodore 64 computer Evan-Amos"},
    {"key":"zxspectrum","era":"1980s","kind":"computer","query":"ZX Spectrum 48K computer"},
    {"key":"colecovision","era":"1980s","kind":"console","query":"ColecoVision console set Evan-Amos"},
    {"key":"segaSG","era":"1980s","kind":"console","query":"Sega SG-1000 console"},
    {"key":"nes","era":"1980s","kind":"console","query":"Nintendo Entertainment System console set Evan-Amos"},
    {"key":"msx","era":"1980s","kind":"computer","query":"MSX computer system"},
    {"key":"x1","era":"1980s","kind":"computer","query":"Sharp X1 computer"},
    {"key":"amstradcpc","era":"1980s","kind":"computer","query":"Amstrad CPC 464 computer"},
    {"key":"plus4","era":"1980s","kind":"computer","query":"Commodore Plus 4 computer"},
    {"key":"atari7800","era":"1980s","kind":"console","query":"Atari 7800 console set Evan-Amos"},
    {"key":"c128","era":"1980s","kind":"computer","query":"Commodore 128 computer Evan-Amos"},
    {"key":"amiga","era":"1980s","kind":"computer","query":"Amiga 500 computer Evan-Amos"},
    {"key":"msx2","era":"1980s","kind":"computer","query":"MSX2 computer"},
    {"key":"segaMS","era":"1980s","kind":"console","query":"Sega Master System console set Evan-Amos"},
    {"key":"pce","era":"1980s","kind":"console","query":"NEC PC Engine console set Evan-Amos"},
    {"key":"pcecd","era":"1980s","kind":"console","query":"PC Engine CD ROM2 console set"},
    {"key":"segaMD","era":"1980s","kind":"console","query":"Sega Genesis Mega Drive console set Evan-Amos"},
    {"key":"gb","era":"1980s","kind":"handheld","query":"Nintendo Game Boy handheld Evan-Amos"},
    {"key":"lynx","era":"1980s","kind":"handheld","query":"Atari Lynx handheld Evan-Amos"},
    {"key":"dos","era":"1980s","kind":"computer","query":"IBM PC 5150 computer Evan-Amos"},
    # 1990s
    {"key":"segaGG","era":"1990s","kind":"handheld","query":"Sega Game Gear handheld Evan-Amos"},
    {"key":"snes","era":"1990s","kind":"console","query":"Super Nintendo Entertainment System console set Evan-Amos"},
    {"key":"segaCD","era":"1990s","kind":"console","query":"Sega CD model 1 console set Evan-Amos"},
    {"key":"cdi","era":"1990s","kind":"console","query":"Philips CD-i console set Evan-Amos"},
    {"key":"3do","era":"1990s","kind":"console","query":"Panasonic 3DO FZ-1 console set Evan-Amos"},
    {"key":"jaguar","era":"1990s","kind":"console","query":"Atari Jaguar console set Evan-Amos"},
    {"key":"sega32x","era":"1990s","kind":"console","query":"Sega 32X console set Evan-Amos"},
    {"key":"segaSaturn","era":"1990s","kind":"console","query":"Sega Saturn console set Evan-Amos"},
    {"key":"psx","era":"1990s","kind":"console","query":"Sony PlayStation console set Evan-Amos"},
    {"key":"neocd","era":"1990s","kind":"console","query":"Neo Geo CD console set Evan-Amos"},
    {"key":"pcfx","era":"1990s","kind":"console","query":"NEC PC-FX console Evan-Amos"},
    {"key":"vb","era":"1990s","kind":"console","query":"Nintendo Virtual Boy console controller Evan-Amos"},
    {"key":"n64","era":"1990s","kind":"console","query":"Nintendo 64 console set Evan-Amos"},
    {"key":"tamagotchi","era":"1990s","kind":"handheld","query":"Tamagotchi P1 device"},
    {"key":"gbc","era":"1990s","kind":"handheld","query":"Nintendo Game Boy Color handheld Evan-Amos"},
    {"key":"ngp","era":"1990s","kind":"handheld","query":"Neo Geo Pocket Color handheld Evan-Amos"},
    {"key":"ws","era":"1990s","kind":"handheld","query":"WonderSwan Color handheld"},
]

GAMEPLAY: list[dict[str, Any]] = [
    {"system":"channelf","keywords":[]},
    {"system":"atari2600","keywords":["Pitfall", "River Raid", "Space Invaders", "Adventure"]},
    {"system":"odyssey2","keywords":["Munchkin", "Pick Axe Pete"]},
    {"system":"intv","keywords":["Astrosmash", "BurgerTime", "Burgertime"]},
    {"system":"arcade","keywords":["Pac-Man", "Donkey Kong", "Galaga"]},
    {"system":"nes","keywords":["Super Mario Bros", "Mega Man 2", "Castlevania"]},
    {"system":"segaMS","keywords":["Alex Kidd", "R-Type", "Wonder Boy"]},
    {"system":"c64","keywords":["Last Ninja", "Impossible Mission", "Turrican"]},
    {"system":"amiga","keywords":["Shadow of the Beast", "Turrican", "Lemmings"]},
    {"system":"pce","keywords":["Bonk", "R-Type", "Blazing Lazers"]},
    {"system":"segaMD","keywords":["Sonic the Hedgehog 2", "Streets of Rage 2", "Gunstar Heroes"]},
    {"system":"gb","keywords":["Super Mario Land", "Tetris", "Kirby"]},
    {"system":"arcade","keywords":["Street Fighter II", "Mortal Kombat", "Out Run"]},
    {"system":"snes","keywords":["Super Metroid", "Mega Man X", "F-Zero"]},
    {"system":"segaSaturn","keywords":["NiGHTS", "Virtua Fighter 2", "Daytona"]},
    {"system":"psx","keywords":["Crash Bandicoot", "Tekken 3", "Ridge Racer"]},
    {"system":"n64","keywords":["Super Mario 64", "Ocarina of Time", "F-Zero X"]},
    {"system":"doom","keywords":[]},
    {"system":"quake","keywords":[]},
    {"system":"quake2","keywords":[]},
    {"system":"scummvm","keywords":["Monkey Island", "Day of the Tentacle", "Sam & Max"]},
]

BAD_TITLE_WORDS = {
    "logo", "motherboard", "bottom", "underside", "inside", "teardown",
    "packaging", "box", "advertisement", "manual", "cartridge", "board",
    "rear", "back", "circuit", "prototype"
}


def safe_name(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", value).strip("_")


def get_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    for attempt in range(4):
        try:
            r = SESSION.get(url, params=params, timeout=35)
            r.raise_for_status()
            return r.json()
        except Exception as exc:
            if attempt == 3:
                raise
            print(f"retry JSON {url}: {exc}")
            time.sleep(2 + attempt * 2)
    raise RuntimeError("unreachable")


def download(url: str, dest: Path, min_bytes: int = 8000) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(4):
        try:
            with SESSION.get(url, timeout=75, stream=True, allow_redirects=True) as r:
                r.raise_for_status()
                tmp = dest.with_suffix(dest.suffix + ".part")
                with tmp.open("wb") as fh:
                    for chunk in r.iter_content(1024 * 256):
                        if chunk:
                            fh.write(chunk)
                if tmp.stat().st_size < min_bytes:
                    tmp.unlink(missing_ok=True)
                    raise RuntimeError(f"short response: {url}")
                tmp.replace(dest)
                return True
        except Exception as exc:
            print(f"download retry {attempt+1}: {url}: {exc}")
            time.sleep(2 + attempt * 2)
    return False


def commons_candidates(query: str) -> list[dict[str, Any]]:
    data = get_json(
        "https://commons.wikimedia.org/w/api.php",
        {
            "action": "query",
            "generator": "search",
            "gsrsearch": f"file:{query}",
            "gsrnamespace": 6,
            "gsrlimit": 15,
            "prop": "imageinfo",
            "iiprop": "url|size|mime|extmetadata",
            "iiurlwidth": 1600,
            "format": "json",
            "formatversion": 2,
        },
    )
    return data.get("query", {}).get("pages", [])


def score_commons(page: dict[str, Any], entry: dict[str, str]) -> float:
    title = page.get("title", "").lower()
    info = (page.get("imageinfo") or [{}])[0]
    meta = info.get("extmetadata") or {}
    description = " ".join(str((meta.get(k) or {}).get("value", "")) for k in ("ImageDescription", "Credit", "Artist"))
    haystack = (title + " " + re.sub("<[^>]+>", " ", description)).lower()
    score = 0.0
    query_words = [w.lower() for w in re.findall(r"[A-Za-z0-9]+", entry["query"]) if len(w) > 2 and w.lower() not in {"evan", "amos", "console", "computer", "set", "handheld"}]
    score += sum(4 for w in query_words if w in haystack)
    if "evan-amos" in haystack or "evan amos" in haystack or "vanamo" in haystack:
        score += 22
    kind = entry["kind"]
    if kind in title or kind in haystack:
        score += 8
    if "set" in title or "with controller" in haystack or "wcontroller" in title:
        score += 7
    if title.endswith(".png"):
        score += 4
    if any(word in title for word in BAD_TITLE_WORDS):
        score -= 35
    if kind != "handheld" and "controller" in title and "console" not in title and "set" not in title:
        score -= 30
    width = int(info.get("width") or 0)
    height = int(info.get("height") or 0)
    if width >= 1000 and height >= 600:
        score += 5
    if info.get("mime", "").startswith("image/"):
        score += 2
    return score


def fetch_hardware(entry: dict[str, str]) -> dict[str, Any]:
    record: dict[str, Any] = {**entry, "status": "missing"}
    try:
        pages = commons_candidates(entry["query"])
    except Exception as exc:
        record["error"] = str(exc)
        return record
    ranked = sorted(pages, key=lambda p: score_commons(p, entry), reverse=True)
    for page in ranked:
        info = (page.get("imageinfo") or [{}])[0]
        url = info.get("thumburl") or info.get("url")
        if not url:
            continue
        mime = info.get("mime", "image/png")
        ext = ".png" if "png" in mime else ".jpg" if "jpeg" in mime else ".webp"
        dest = HW / entry["era"] / f"{entry['key']}{ext}"
        if download(url, dest):
            meta = info.get("extmetadata") or {}
            record.update({
                "status": "ok",
                "file": str(dest.relative_to(OUT)),
                "commons_title": page.get("title"),
                "source_url": info.get("descriptionurl") or url,
                "download_url": url,
                "author": (meta.get("Artist") or {}).get("value", ""),
                "license": (meta.get("LicenseShortName") or {}).get("value", ""),
                "score": score_commons(page, entry),
                "width": info.get("thumbwidth") or info.get("width"),
                "height": info.get("thumbheight") or info.get("height"),
            })
            return record
    record["candidates"] = [p.get("title") for p in ranked[:5]]
    return record


def find_metadata(system: str) -> Path | None:
    candidates = [META / f"{system}.json"]
    aliases = {
        "segaSaturn": ["saturn"],
        "segaMD": ["genesis", "megadrive"],
        "segaMS": ["mastersystem"],
        "arcade": ["mame"],
    }
    for alias in aliases.get(system, []):
        candidates.append(META / f"{alias}.json")
    for path in candidates:
        if path.exists():
            return path
    lower = system.lower()
    for path in META.glob("*.json"):
        if path.stem.lower() == lower:
            return path
    return None


def choose_video_entry(system: str, keywords: list[str], already: set[str]) -> tuple[str, str, str] | None:
    path = find_metadata(system)
    if not path:
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    entries = [v for v in data.values() if isinstance(v, dict) and v.get("vid") and v.get("name")]
    for keyword in keywords:
        regex = re.compile(re.escape(keyword), re.I)
        for item in entries:
            cid = item["vid"]
            if cid not in already and regex.search(item["name"]):
                return item["name"], cid, path.name
    for item in entries:
        cid = item["vid"]
        if cid not in already:
            return item["name"], cid, path.name
    return None


def fetch_ipfs(cid: str, dest: Path) -> tuple[bool, str]:
    gateways = [
        f"https://dweb.link/ipfs/{cid}",
        f"https://w3s.link/ipfs/{cid}",
        f"https://ipfs.io/ipfs/{cid}",
        f"https://gateway.pinata.cloud/ipfs/{cid}",
        f"https://cloudflare-ipfs.com/ipfs/{cid}",
    ]
    for url in gateways:
        if download(url, dest, min_bytes=25000):
            return True, url
    return False, ""


def fetch_gameplay() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    used: set[str] = set()
    per_system_count: dict[str, int] = {}
    for spec in GAMEPLAY:
        system = spec["system"]
        selected = choose_video_entry(system, spec.get("keywords") or [], used)
        if not selected:
            records.append({"system": system, "status": "metadata-missing"})
            continue
        name, cid, metadata_file = selected
        used.add(cid)
        idx = per_system_count.get(system, 0)
        per_system_count[system] = idx + 1
        dest = VID / f"{safe_name(system)}_{idx:02d}_{safe_name(name)[:70]}.mp4"
        ok, url = fetch_ipfs(cid, dest)
        records.append({
            "system": system,
            "game": name,
            "cid": cid,
            "metadata_file": metadata_file,
            "file": str(dest.relative_to(OUT)) if ok else "",
            "status": "ok" if ok else "download-failed",
            "gateway": url,
        })
    return records


def fetch_arcade_photos() -> list[dict[str, Any]]:
    queries = [
        ("arcade_1970s", "1970s arcade cabinet video game museum"),
        ("arcade_1980s", "1980s video arcade cabinets row"),
        ("arcade_1990s", "1990s arcade cabinets fighting racing"),
    ]
    records = []
    for key, query in queries:
        entry = {"key": key, "era": "arcade", "kind": "cabinet", "query": query}
        records.append(fetch_hardware(entry))
    return records


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    HW.mkdir(parents=True)
    VID.mkdir(parents=True)
    print(f"Fetching {len(HARDWARE)} hardware assets")
    hardware_records = []
    for i, entry in enumerate(HARDWARE, 1):
        print(f"[{i}/{len(HARDWARE)}] {entry['key']}: {entry['query']}")
        hardware_records.append(fetch_hardware(entry))
        time.sleep(0.15)
    arcade_records = fetch_arcade_photos()
    print("Fetching gameplay from repository IPFS metadata")
    gameplay_records = fetch_gameplay()
    manifest = {
        "hardware": hardware_records,
        "arcade": arcade_records,
        "gameplay": gameplay_records,
        "summary": {
            "hardware_ok": sum(r.get("status") == "ok" for r in hardware_records),
            "hardware_total": len(hardware_records),
            "arcade_ok": sum(r.get("status") == "ok" for r in arcade_records),
            "gameplay_ok": sum(r.get("status") == "ok" for r in gameplay_records),
            "gameplay_total": len(gameplay_records),
        },
    }
    (OUT / "asset_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    (OUT / "README.txt").write_text(
        "Authentic source asset package for EmuHub V19. Hardware is from Wikimedia Commons; gameplay CIDs are from this repository's existing EmulatorJS metadata. See asset_manifest.json for exact attribution and source URLs.\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest["summary"], indent=2))
    # Never fail only because rare assets are missing; the compositor omits missing items.
    return 0 if manifest["summary"]["hardware_ok"] >= 20 else 2


if __name__ == "__main__":
    sys.exit(main())
