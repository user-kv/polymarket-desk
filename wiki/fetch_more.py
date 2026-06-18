"""Autonomous wide harvest: search many queries, dedup vs already-harvested, dump metadata,
auto-flag high-signal videos (repos, ensembles, real method) vs referral shills.
Metadata route (not throttled). Appends concise entries to youtube_metadata_2.md."""
import re, subprocess, sys, json, time
from pathlib import Path
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

RAW = Path(__file__).parent / "raw"
DONE_FILE = RAW / "youtube_metadata.md"
OUT = RAW / "youtube_metadata_2.md"

QUERIES = [
    "polymarket weather strategy", "polymarket weather bot python", "kalshi weather trading strategy",
    "polymarket arbitrage bot", "polymarket edge prediction market", "claude code polymarket trading bot",
    "polymarket smart money wallets", "prediction market trading strategy 2026",
    "polymarket temperature trading", "polymarket bitcoin 15 minute strategy",
    "polymarket insider wallets copy trade", "moon dev polymarket bot",
    "polymarket python bot tutorial", "polymarket how to find edge", "kalshi vs polymarket strategy",
    "polymarket weather market explained", "polymarket automated trading", "polymarket whale tracking",
]

# already-harvested IDs
done = set(re.findall(r"ID: ([\w-]{11})", DONE_FILE.read_text(encoding="utf-8"))) if DONE_FILE.exists() else set()
# plus any already in OUT (resume)
if OUT.exists():
    done |= set(re.findall(r"ID: ([\w-]{11})", OUT.read_text(encoding="utf-8")))

URL_RE = re.compile(r"https?://[^\s)]+")
HIGH = ["github.com", "ensemble", "gfs", "ecmwf", "open-meteo", "kelly", "open meteo",
        ".py", "api", "noaa", "nws", "metar", "claude", "backtest", "edge", "kalshi"]

def search_ids():
    ids = {}
    for q in QUERIES:
        try:
            r = subprocess.run([sys.executable, "-m", "yt_dlp", f"ytsearch10:{q}",
                "--flat-playlist", "--dump-json", "--no-warnings",
                "--extractor-args", "youtube:player_client=android"],
                capture_output=True, text=True, timeout=120)
            for line in r.stdout.splitlines():
                try:
                    d = json.loads(line); vid = d.get("id")
                    if vid and vid not in done and vid not in ids:
                        ids[vid] = d.get("title", "")
                except: pass
            print(f"  searched: {q} (running total {len(ids)})")
        except Exception as e:
            print(f"  search FAIL {q}: {e}")
        time.sleep(1)
    return ids

def dump(vid):
    r = subprocess.run([sys.executable, "-m", "yt_dlp", "--dump-json", "--skip-download",
        "--no-warnings", "--extractor-args", "youtube:player_client=android",
        f"https://www.youtube.com/watch?v={vid}"], capture_output=True, text=True, timeout=60)
    return json.loads(r.stdout) if r.stdout.strip() else None

print("=== enumerating ===")
cands = search_ids()
print(f"\n{len(cands)} NEW candidates. Harvesting metadata...\n")

def flush(blocks, hi):
    s = sorted(blocks, key=lambda b: (0 if "HIGH-SIGNAL" in b else (1 if "MID" in b else 2)))
    hdr = f"# YouTube METADATA Harvest #2 (WIDE) — {len(blocks)} new videos, {hi} high-signal\nCaptured 2026-06-12. Sorted high-signal first.\n\n---\n\n"
    OUT.write_text(hdr + "\n".join(s), encoding="utf-8")

blocks, hi = [], 0
for i, vid in enumerate(cands, 1):
    try:
        d = dump(vid)
        if not d:
            print(f"[{i}] {vid} miss"); continue
        title = d.get("title") or ""; chan = d.get("channel") or d.get("uploader") or ""
        dur = d.get("duration") or 0; views = d.get("view_count"); desc = (d.get("description") or "").strip()
        chapters = d.get("chapters") or []
        links = []
        for u in URL_RE.findall(desc):
            u = u.rstrip(".,")
            if u not in links: links.append(u)
        score = sum(1 for k in HIGH if k in (title+desc).lower())
        flag = "HIGH-SIGNAL" if score >= 3 else ("MID" if score >= 1 else "low/shill")
        if score >= 3: hi += 1
        ch = " | CHAPTERS: " + "; ".join(c.get("title","") for c in chapters[:12]) if chapters else ""
        b = [f"### [{flag}] (score {score}) — {title}",
             f"- ID: {vid} | {chan} | {dur//60}m | {views} views | https://youtube.com/watch?v={vid}"]
        if links: b.append(f"- LINKS: {' , '.join(links[:10])}")
        if ch: b.append(f"-{ch}")
        b.append(f"- DESC: {desc[:700]}")
        blocks.append("\n".join(b) + "\n")
        print(f"[{i}/{len(cands)}] [{flag}] s{score} {vid} {title[:48]}")
        if i % 8 == 0: flush(blocks, hi)   # incremental save
        time.sleep(1.0)
    except Exception as e:
        print(f"[{i}] {vid} ERR {repr(e)[:80]}")

flush(blocks, hi)
print(f"\nWROTE {OUT}: {len(blocks)} videos, {hi} high-signal")
