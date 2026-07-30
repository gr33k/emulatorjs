#!/usr/bin/env python3
"""Fast concurrent source-media fetcher for the EmuHub V19 final video.

All hardware comes from Wikimedia Commons photographs. Gameplay is selected from
this repository's existing IPFS-backed EmulatorJS video metadata. Failed assets
are omitted; nothing is generated or approximated.
"""
from __future__ import annotations

import concurrent.futures as cf
import json
import re
import shutil
import time
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "v19_source_assets"
META = ROOT / "metadata"
UA = {"User-Agent": "EmuHub-V19-Final/1.0 authentic-media-fetch"}

HARDWARE = [
    # 1970s
    ("1970s","channelf","console","Fairchild Channel F console Evan-Amos"),
    ("1970s","atari2600","console","Atari 2600 console set Evan-Amos"),
    ("1970s","pet","computer","Commodore PET 2001 computer"),
    ("1970s","odyssey2","console","Magnavox Odyssey 2 console set Evan-Amos"),
    ("1970s","intv","console","Intellivision console set Evan-Amos"),
    # 1980s core consoles, computers and handhelds
    ("1980s","atari5200","console","Atari 5200 console set Evan-Amos"),
    ("1980s","colecovision","console","ColecoVision console set Evan-Amos"),
    ("1980s","nes","console","Nintendo Entertainment System console set Evan-Amos"),
    ("1980s","segaMS","console","Sega Master System console set Evan-Amos"),
    ("1980s","atari7800","console","Atari 7800 console set Evan-Amos"),
    ("1980s","pce","console","NEC PC Engine console set Evan-Amos"),
    ("1980s","pcecd","console","PC Engine CD ROM2 console set"),
    ("1980s","segaMD","console","Sega Genesis Mega Drive console set Evan-Amos"),
    ("1980s","gb","handheld","Nintendo Game Boy handheld Evan-Amos"),
    ("1980s","lynx","handheld","Atari Lynx handheld Evan-Amos"),
    ("1980s","c64","computer","Commodore 64 computer Evan-Amos"),
    ("1980s","zxspectrum","computer","ZX Spectrum 48K computer"),
    ("1980s","amstradcpc","computer","Amstrad CPC 464 computer"),
    ("1980s","amiga","computer","Amiga 500 computer Evan-Amos"),
    ("1980s","msx","computer","MSX computer system"),
    ("1980s","dos","computer","IBM PC 5150 computer Evan-Amos"),
    # 1990s hero systems
    ("1990s","segaGG","handheld","Sega Game Gear handheld Evan-Amos"),
    ("1990s","snes","console","Super Nintendo Entertainment System console set Evan-Amos"),
    ("1990s","segaCD","console","Sega CD model 1 console set Evan-Amos"),
    ("1990s","sega32x","console","Sega 32X console set Evan-Amos"),
    ("1990s","3do","console","Panasonic 3DO FZ-1 console set Evan-Amos"),
    ("1990s","jaguar","console","Atari Jaguar console set Evan-Amos"),
    ("1990s","segaSaturn","console","Sega Saturn console set Evan-Amos"),
    ("1990s","psx","console","Sony PlayStation console set Evan-Amos"),
    ("1990s","neocd","console","Neo Geo CD console set Evan-Amos"),
    ("1990s","pcfx","console","NEC PC-FX console"),
    ("1990s","vb","console","Nintendo Virtual Boy console controller Evan-Amos"),
    ("1990s","n64","console","Nintendo 64 console set Evan-Amos"),
    ("1990s","gbc","handheld","Nintendo Game Boy Color handheld Evan-Amos"),
    ("1990s","ngp","handheld","Neo Geo Pocket Color handheld Evan-Amos"),
    ("1990s","ws","handheld","WonderSwan Color handheld"),
]

VIDEOS = [
    ("atari2600", ["Pitfall", "River Raid", "Space Invaders"]),
    ("intv", ["Astrosmash", "BurgerTime"]),
    ("arcade", ["Pac-Man", "Donkey Kong", "Galaga"]),
    ("nes", ["Super Mario Bros", "Mega Man 2", "Castlevania"]),
    ("segaMS", ["Alex Kidd", "R-Type"]),
    ("c64", ["Last Ninja", "Impossible Mission", "Turrican"]),
    ("amiga", ["Shadow of the Beast", "Turrican", "Lemmings"]),
    ("pce", ["Bonk", "R-Type", "Blazing Lazers"]),
    ("segaMD", ["Sonic the Hedgehog 2", "Streets of Rage 2", "Gunstar Heroes"]),
    ("gb", ["Super Mario Land", "Tetris", "Kirby"]),
    ("arcade", ["Street Fighter II", "Mortal Kombat", "Out Run"]),
    ("snes", ["Super Metroid", "Mega Man X", "F-Zero"]),
    ("segaSaturn", ["NiGHTS", "Virtua Fighter 2", "Daytona"]),
    ("psx", ["Crash Bandicoot", "Tekken 3", "Ridge Racer"]),
    ("n64", ["Super Mario 64", "Ocarina of Time", "F-Zero X"]),
    ("doom", []), ("quake", []), ("quake2", []),
    ("scummvm", ["Monkey Island", "Day of the Tentacle", "Sam & Max"]),
]

BAD = {"motherboard","bottom","underside","teardown","packaging","manual","circuit","prototype","advertisement"}
ALIASES = {"segaSaturn":["saturn"],"segaMD":["genesis","megadrive"],"segaMS":["mastersystem"],"arcade":["mame"]}


def session() -> requests.Session:
    s = requests.Session(); s.headers.update(UA); return s


def safe(v: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", v).strip("_")


def download(url: str, dest: Path, minimum: int, timeout: int = 20) -> bool:
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with session().get(url, timeout=timeout, stream=True, allow_redirects=True) as r:
            r.raise_for_status()
            tmp = dest.with_suffix(dest.suffix + ".part")
            with tmp.open("wb") as f:
                for chunk in r.iter_content(262144):
                    if chunk: f.write(chunk)
            if tmp.stat().st_size < minimum:
                tmp.unlink(missing_ok=True); return False
            tmp.replace(dest); return True
    except Exception:
        return False


def hardware_one(item: tuple[str,str,str,str]) -> dict[str, Any]:
    era,key,kind,query = item
    rec: dict[str,Any] = {"era":era,"key":key,"kind":kind,"query":query,"status":"missing"}
    try:
        s=session()
        r=s.get("https://commons.wikimedia.org/w/api.php", params={
            "action":"query","generator":"search","gsrsearch":f"file:{query}","gsrnamespace":6,"gsrlimit":12,
            "prop":"imageinfo","iiprop":"url|size|mime|extmetadata","iiurlwidth":1800,
            "format":"json","formatversion":2}, timeout=18)
        r.raise_for_status(); pages=r.json().get("query",{}).get("pages",[])
        def score(p: dict[str,Any]) -> float:
            title=p.get("title","").lower(); info=(p.get("imageinfo") or [{}])[0]
            meta=info.get("extmetadata") or {}; desc=" ".join(str((meta.get(k) or {}).get("value","")) for k in ("ImageDescription","Artist","Credit"))
            hay=(title+" "+re.sub("<[^>]+>"," ",desc)).lower(); sc=0
            words=[w.lower() for w in re.findall(r"[A-Za-z0-9]+",query) if len(w)>2 and w.lower() not in {"evan","amos","console","computer","set","handheld"}]
            sc += sum(4 for w in words if w in hay)
            if "evan-amos" in hay or "evan amos" in hay or "vanamo" in hay: sc += 24
            if kind in hay: sc += 7
            if "set" in title or "with controller" in hay: sc += 8
            if title.endswith(".png"): sc += 5
            if any(x in title for x in BAD): sc -= 40
            if kind != "handheld" and "controller" in title and "console" not in title and "set" not in title: sc -= 35
            if int(info.get("width") or 0) >= 1000: sc += 4
            return sc
        for page in sorted(pages,key=score,reverse=True):
            info=(page.get("imageinfo") or [{}])[0]; url=info.get("thumburl") or info.get("url")
            if not url: continue
            mime=info.get("mime",""); ext=".png" if "png" in mime else ".jpg"
            dest=OUT/"hardware"/era/f"{key}{ext}"
            if download(url,dest,7000,25):
                meta=info.get("extmetadata") or {}
                rec.update(status="ok",file=str(dest.relative_to(OUT)),source_url=info.get("descriptionurl") or url,
                           commons_title=page.get("title"),author=(meta.get("Artist") or {}).get("value",""),
                           license=(meta.get("LicenseShortName") or {}).get("value",""),score=score(page))
                return rec
    except Exception as exc:
        rec["error"]=str(exc)
    return rec


def metadata_path(system: str) -> Path | None:
    for stem in [system,*ALIASES.get(system,[])]:
        p=META/f"{stem}.json"
        if p.exists(): return p
    for p in META.glob("*.json"):
        if p.stem.lower()==system.lower(): return p
    return None


def video_spec(spec: tuple[str,list[str]], index: int) -> dict[str,Any]:
    system,keywords=spec; rec: dict[str,Any]={"system":system,"status":"missing"}
    p=metadata_path(system)
    if not p: return rec
    try: data=json.loads(p.read_text(encoding="utf-8"))
    except Exception: return rec
    entries=[x for x in data.values() if isinstance(x,dict) and x.get("vid") and x.get("name")]
    chosen=None
    for word in keywords:
        chosen=next((x for x in entries if re.search(re.escape(word),x["name"],re.I)),None)
        if chosen: break
    if not chosen and entries: chosen=entries[index % len(entries)]
    if not chosen: return rec
    cid=chosen["vid"]; name=chosen["name"]
    dest=OUT/"gameplay"/f"{index:02d}_{safe(system)}_{safe(name)[:64]}.mp4"
    gateways=[f"https://dweb.link/ipfs/{cid}",f"https://w3s.link/ipfs/{cid}",f"https://ipfs.io/ipfs/{cid}"]
    for url in gateways:
        if download(url,dest,25000,22):
            rec.update(status="ok",file=str(dest.relative_to(OUT)),game=name,cid=cid,gateway=url,metadata_file=p.name)
            return rec
    rec.update(status="download-failed",game=name,cid=cid,metadata_file=p.name)
    return rec


def arcade_one(item: tuple[str,str]) -> dict[str,Any]:
    key,query=item
    return hardware_one(("arcade",key,"cabinet",query))


def main() -> int:
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    with cf.ThreadPoolExecutor(max_workers=10) as ex:
        hardware=list(ex.map(hardware_one,HARDWARE))
    arcade_queries=[("arcade_1970s","1970s video arcade cabinets museum"),("arcade_1980s","1980s video arcade cabinets row"),("arcade_1990s","1990s arcade fighting racing cabinets")]
    with cf.ThreadPoolExecutor(max_workers=3) as ex:
        arcade=list(ex.map(arcade_one,arcade_queries))
    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        futures=[ex.submit(video_spec,spec,i) for i,spec in enumerate(VIDEOS)]
        gameplay=[f.result() for f in futures]
    summary={"hardware_ok":sum(r["status"]=="ok" for r in hardware),"hardware_total":len(hardware),
             "arcade_ok":sum(r["status"]=="ok" for r in arcade),"gameplay_ok":sum(r["status"]=="ok" for r in gameplay),"gameplay_total":len(gameplay)}
    manifest={"hardware":hardware,"arcade":arcade,"gameplay":gameplay,"summary":summary}
    (OUT/"asset_manifest.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    (OUT/"README.txt").write_text("Authentic source assets only. See asset_manifest.json for attribution and URLs. Missing items were omitted, never generated.\n",encoding="utf-8")
    print(json.dumps(summary,indent=2))
    return 0

if __name__=="__main__": raise SystemExit(main())
