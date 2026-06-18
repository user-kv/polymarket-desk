"""Harvest metadata for STRATEGY-survey videos (sports, arbitrage, favorites/calibration,
market-making, general 'best strategy'). Metadata route (not throttled). Auto-flags signal."""
import re, subprocess, sys, json, time
from pathlib import Path
try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except: pass
OUT = Path(__file__).parent / "raw" / "youtube_metadata_3_strategies.md"
QUERIES = [
    "polymarket sports trading strategy edge", "polymarket vs sportsbook arbitrage betting",
    "prediction market closing line value sharp odds", "polymarket favorite longshot bias",
    "polymarket buy favorites underpriced strategy", "polymarket politics trading edge",
    "polymarket market making liquidity rewards", "best prediction market strategy that works",
    "polymarket arbitrage logical correlated markets", "kalshi sports trading strategy",
    "polymarket calibration mispricing edge", "how professional polymarket traders make money",
]
URL_RE = re.compile(r"https?://[^\s)]+")
HIGH = ["sharp","pinnacle","betfair","de-vig","devig","closing line","clv","favorite","longshot",
        "calibrat","arbitrage","edge","model","kelly","de vig","oddsjam","sportsbook","backtest","api","github"]
def search_ids():
    ids={}
    for q in QUERIES:
        try:
            r=subprocess.run([sys.executable,"-m","yt_dlp",f"ytsearch8:{q}","--flat-playlist",
                "--dump-json","--no-warnings","--extractor-args","youtube:player_client=android"],
                capture_output=True,text=True,timeout=120)
            for line in r.stdout.splitlines():
                try:
                    d=json.loads(line); v=d.get("id")
                    if v and v not in ids: ids[v]=d.get("title","")
                except: pass
            print(f"  q: {q} (total {len(ids)})")
        except Exception as e: print(f"  qFAIL {q}: {e}")
        time.sleep(1)
    return ids
def dump(v):
    r=subprocess.run([sys.executable,"-m","yt_dlp","--dump-json","--skip-download","--no-warnings",
        "--extractor-args","youtube:player_client=android",f"https://www.youtube.com/watch?v={v}"],
        capture_output=True,text=True,timeout=60)
    return json.loads(r.stdout) if r.stdout.strip() else None
def flush(blocks):
    s=sorted(blocks,key=lambda b:(0 if "HIGH-SIGNAL" in b else (1 if "MID" in b else 2)))
    OUT.write_text(f"# STRATEGY-SURVEY YouTube Harvest — {len(blocks)} videos. 2026-06-12.\n\n---\n\n"+"\n".join(s),encoding="utf-8")
cands=search_ids(); print(f"\n{len(cands)} candidates harvesting...\n")
blocks=[]
for i,v in enumerate(cands,1):
    try:
        d=dump(v)
        if not d: continue
        t=d.get("title") or ""; ch=d.get("channel") or ""; dur=d.get("duration") or 0
        vw=d.get("view_count"); desc=(d.get("description") or "").strip(); chs=d.get("chapters") or []
        links=[]
        for u in URL_RE.findall(desc):
            u=u.rstrip(".,"); links.append(u) if u not in links else None
        score=sum(1 for k in HIGH if k in (t+desc).lower())
        flag="HIGH-SIGNAL" if score>=3 else ("MID" if score>=1 else "low")
        cc=" | CH: "+"; ".join(c.get("title","") for c in chs[:10]) if chs else ""
        b=[f"### [{flag}] (s{score}) — {t}",f"- ID:{v} | {ch} | {dur//60}m | {vw} views | https://youtube.com/watch?v={v}"]
        if links: b.append(f"- LINKS: {' , '.join(links[:8])}")
        if cc: b.append(f"-{cc}")
        b.append(f"- DESC: {desc[:600]}")
        blocks.append("\n".join(b)+"\n")
        print(f"[{i}/{len(cands)}] [{flag}] s{score} {v} {t[:46]}")
        if i%8==0: flush(blocks)
        time.sleep(1.0)
    except Exception as e: print(f"[{i}] {v} ERR {repr(e)[:60]}")
flush(blocks)
print(f"\nWROTE {OUT}: {len(blocks)} videos")
