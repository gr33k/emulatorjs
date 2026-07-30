#!/usr/bin/env python3
"""Augment V19 assets with real console images from the NBBA theme and Infura IPFS videos."""
from __future__ import annotations
import concurrent.futures as cf
import json, re, shutil, subprocess
from pathlib import Path
import requests

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'v19_source_assets'; META=ROOT/'metadata'
UA={'User-Agent':'EmuHub-V19-Final/1.1 authentic-media-augmentation'}

MAP={
 '3do':'3do','amiga':'amiga','atari2600':'atari2600','atari5200':'atari5200','atari7800':'atari7800',
 'jaguar':'atarijaguar','lynx':'atarilynx','c64':'c64','segaGG':'gamegear','gb':'gb','gbc':'gbc',
 'intv':'intellivision','segaMS':'mastersystem','segaMD':'megadrive','n64':'n64','nes':'nes','ngp':'ngp',
 'pce':'pcengine','psx':'psx','segaSaturn':'saturn','sega32x':'sega32x','segaCD':'segacd','segaSG':'sg-1000',
 'snes':'snes','odyssey2':'videopac','vb':'virtualboy','zxspectrum':'zxspectrum','arcade':'mame'
}
ERAS={
 'atari2600':'1970s','intv':'1970s','odyssey2':'1970s',
 'atari5200':'1980s','atari7800':'1980s','c64':'1980s','segaMS':'1980s','segaMD':'1980s','pce':'1980s','gb':'1980s','lynx':'1980s','amiga':'1980s','zxspectrum':'1980s','nes':'1980s','segaSG':'1980s',
 '3do':'1990s','jaguar':'1990s','segaGG':'1990s','gbc':'1990s','n64':'1990s','ngp':'1990s','psx':'1990s','segaSaturn':'1990s','sega32x':'1990s','segaCD':'1990s','snes':'1990s','vb':'1990s',
 'arcade':'arcade'
}
VIDEOS=[
 ('atari2600',['Pitfall','River Raid']),('intv',['Astrosmash','BurgerTime']),('arcade',['Pac-Man','Donkey Kong','Galaga']),
 ('nes',['Super Mario Bros','Mega Man 2']),('segaMS',['Alex Kidd','R-Type']),('c64',['Last Ninja','Turrican']),
 ('amiga',['Shadow of the Beast','Turrican']),('pce',['Bonk','R-Type']),('segaMD',['Sonic the Hedgehog 2','Streets of Rage 2']),
 ('gb',['Super Mario Land','Tetris']),('arcade',['Street Fighter II','Mortal Kombat','Out Run']),
 ('snes',['Super Metroid','Mega Man X']),('segaSaturn',['NiGHTS','Virtua Fighter 2']),
 ('psx',['Crash Bandicoot','Tekken 3']),('n64',['Super Mario 64','Ocarina of Time']),
 ('doom',[]),('quake',[]),('quake2',[]),('scummvm',['Monkey Island','Day of the Tentacle'])
]
ALIASES={'segaSaturn':['saturn'],'segaMD':['genesis','megadrive'],'segaMS':['mastersystem'],'arcade':['mame']}

def safe(s): return re.sub(r'[^A-Za-z0-9._-]+','_',s).strip('_')
def dl(url,dest,minimum=20000,timeout=50):
 try:
  dest.parent.mkdir(parents=True,exist_ok=True)
  with requests.get(url,headers=UA,timeout=timeout,stream=True,allow_redirects=True) as r:
   r.raise_for_status(); tmp=dest.with_suffix(dest.suffix+'.part')
   with tmp.open('wb') as f:
    for c in r.iter_content(262144):
     if c: f.write(c)
   if tmp.stat().st_size<minimum: tmp.unlink(missing_ok=True); return False
   tmp.replace(dest); return True
 except Exception: return False

def mp(system):
 for stem in [system,*ALIASES.get(system,[])]:
  p=META/f'{stem}.json'
  if p.exists(): return p
 return None

def choose(system,keywords,index):
 p=mp(system)
 if not p:return None
 try:d=json.loads(p.read_text())
 except:return None
 es=[x for x in d.values() if isinstance(x,dict) and x.get('vid') and x.get('name')]
 for k in keywords:
  for x in es:
   if re.search(re.escape(k),x['name'],re.I): return p,x
 return (p,es[index%len(es)]) if es else None

def video_one(args):
 i,(system,keywords)=args; c=choose(system,keywords,i)
 if not c:return {'system':system,'status':'missing'}
 p,x=c; cid=x['vid']; name=x['name']; dest=OUT/'gameplay'/f'aug_{i:02d}_{safe(system)}_{safe(name)[:60]}.mp4'
 urls=[f'https://ipfs.infura.io/ipfs/{cid}',f'https://gateway.ipfs.io/ipfs/{cid}',f'https://nftstorage.link/ipfs/{cid}',f'https://gateway.lighthouse.storage/ipfs/{cid}']
 for u in urls:
  if dl(u,dest,25000,55): return {'system':system,'game':name,'cid':cid,'metadata_file':p.name,'file':str(dest.relative_to(OUT)),'status':'ok','gateway':u}
 return {'system':system,'game':name,'cid':cid,'metadata_file':p.name,'status':'download-failed'}

def main():
 manifest_path=OUT/'asset_manifest.json'; m=json.loads(manifest_path.read_text()) if manifest_path.exists() else {'hardware':[],'arcade':[],'gameplay':[]}
 repo=ROOT/'_nbba'
 if repo.exists(): shutil.rmtree(repo)
 subprocess.run(['git','clone','--depth','1','https://github.com/RetroPie/es-theme-nbba.git',str(repo)],check=True)
 bykey={r.get('key'):r for r in m.get('hardware',[]) if r.get('status')=='ok'}
 new=[]
 for key,folder in MAP.items():
  src=repo/folder/'gc.png'
  if not src.exists(): continue
  era=ERAS[key]; dest=OUT/'hardware'/era/f'{key}.png'; dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dest)
  rec={'era':era,'key':key,'kind':'cabinet' if key=='arcade' else ('computer' if key in {'amiga','c64','zxspectrum'} else ('handheld' if key in {'lynx','gb','gbc','segaGG','ngp'} else 'console')),
       'query':'NBBA verified system image','status':'ok','file':str(dest.relative_to(OUT)),'source_url':f'https://github.com/RetroPie/es-theme-nbba/tree/master/{folder}','commons_title':'NBBA gc.png','author':'NBBA theme contributors','license':'Repository theme asset'}
  if key=='arcade': m.setdefault('arcade',[]).append(rec)
  else: bykey[key]=rec
  new.append(key)
 m['hardware']=list(bykey.values())
 existing={(r.get('system'),r.get('game')) for r in m.get('gameplay',[]) if r.get('status')=='ok'}
 with cf.ThreadPoolExecutor(max_workers=8) as ex: aug=list(ex.map(video_one,list(enumerate(VIDEOS))))
 for r in aug:
  if r.get('status')=='ok' and (r.get('system'),r.get('game')) not in existing:
   m.setdefault('gameplay',[]).append(r); existing.add((r.get('system'),r.get('game')))
 m['summary']={'hardware_ok':sum(r.get('status')=='ok' for r in m.get('hardware',[])),'hardware_total':len(m.get('hardware',[])),
               'arcade_ok':sum(r.get('status')=='ok' for r in m.get('arcade',[])),
               'gameplay_ok':sum(r.get('status')=='ok' for r in m.get('gameplay',[])),'gameplay_total':len(m.get('gameplay',[])),
               'nbba_keys':new}
 manifest_path.write_text(json.dumps(m,indent=2))
 print(json.dumps(m['summary'],indent=2))
 shutil.rmtree(repo)
if __name__=='__main__': main()
