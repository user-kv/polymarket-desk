"""Harvest YouTube METADATA (title/channel/desc/chapters/links) for Polymarket videos.
Metadata is NOT throttled (only caption download is 429'd), so this works fully.
Writes a structured markdown file. Uses android player client to avoid blocks."""
import re
import subprocess
import sys
import json
import time
from pathlib import Path

OUT = Path(__file__).parent / "raw" / "youtube_metadata.md"

# curated, grouped (id, group)
VIDEOS = [
    # WEATHER
    ("hej22I5Sit4", "WEATHER"), ("UN4c_UwDKcM", "WEATHER"), ("86xl8sINErw", "WEATHER"),
    ("4JC0ZAv6qhQ", "WEATHER"), ("06g9UDv1IeU", "WEATHER"), ("qS-9cmgGctw", "WEATHER"),
    ("ZTr1qMtToFg", "WEATHER"), ("BiqG3it0gY0", "WEATHER"), ("ZpwnSn_TFio", "WEATHER"),
    ("npy1rzBOl6M", "WEATHER"), ("SGsNqudwel0", "WEATHER"),
    # COPY TRADING
    ("YqJxtqsBQTI", "COPY"), ("YN_wbR5g1S0", "COPY"), ("vphw2fFDiRU", "COPY"),
    ("Ee1jwQ7M7b0", "COPY"), ("WzE2A2W2G5c", "COPY"), ("djlq5UIhp4E", "COPY"),
    ("ByttzGVoj_Q", "COPY"), ("CABCnSUPA8U", "COPY"),
    # GENERAL / COURSE / TERMINALS
    ("bNUVAjbPMLE", "GENERAL"), ("BoJX4DfZs7s", "GENERAL"), ("VW1PpzauVzs", "GENERAL"),
    ("_HBFIN3nHJ0", "GENERAL"), ("7O93LhW8Gsc", "GENERAL"),
    # BTC (salvage)
    ("0YkolG5afrg", "BTC"), ("ZoY7ustjb-8", "BTC"),
]

URL_RE = re.compile(r"https?://[^\s)]+")

def dump(vid):
    r = subprocess.run(
        [sys.executable, "-m", "yt_dlp", "--dump-json", "--skip-download", "--no-warnings",
         "--extractor-args", "youtube:player_client=android",
         f"https://www.youtube.com/watch?v={vid}"],
        capture_output=True, text=True, timeout=60)
    if r.returncode != 0 or not r.stdout.strip():
        return None
    return json.loads(r.stdout)

blocks = []
for vid, grp in VIDEOS:
    try:
        d = dump(vid)
    except Exception as e:
        blocks.append(f"### [{grp}] {vid} — FETCH ERROR: {e}\n")
        print(f"ERR {vid}: {e}"); continue
    if not d:
        blocks.append(f"### [{grp}] {vid} — no metadata\n")
        print(f"MISS {vid}"); continue
    title = d.get("title") or ""
    chan = d.get("channel") or d.get("uploader") or ""
    dur = d.get("duration") or 0
    views = d.get("view_count")
    date = d.get("upload_date") or ""
    desc = (d.get("description") or "").strip()
    chapters = d.get("chapters") or []
    links = []
    for u in URL_RE.findall(desc):
        u = u.rstrip(".,")
        if u not in links:
            links.append(u)
    ch_txt = ""
    if chapters:
        ch_txt = "\n".join(f"  - {int(c.get('start_time',0)//60)}:{int(c.get('start_time',0)%60):02d} {c.get('title','')}" for c in chapters)
    b = [f"### [{grp}] {title}",
         f"- ID: {vid} | URL: https://www.youtube.com/watch?v={vid}",
         f"- Channel: {chan} | Duration: {dur//60}m{dur%60:02d}s | Views: {views} | Uploaded: {date}"]
    if links:
        b.append(f"- LINKS: {' , '.join(links[:12])}")
    if ch_txt:
        b.append(f"- CHAPTERS:\n{ch_txt}")
    b.append(f"- DESCRIPTION:\n{desc[:1800]}")
    blocks.append("\n".join(b) + "\n")
    print(f"OK {vid} ({len(desc)} desc chars, {len(links)} links)")
    time.sleep(1.5)

header = "# YouTube METADATA Harvest — Polymarket Research (RAW)\n\nCaptured: 2026-06-12 via yt-dlp --dump-json (captions are 429-blocked; this is descriptions+chapters+links, which carry the method).\n\n---\n\n"
OUT.write_text(header + "\n".join(blocks), encoding="utf-8")
print(f"\nWROTE {OUT} ({len(blocks)} videos)")
