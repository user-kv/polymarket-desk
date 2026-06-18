"""Fetch transcripts for Polymarket strategy videos via yt-dlp subtitle download.
Uses Chrome cookies (residential IP + auth) to bypass the youtube-transcript-api IP block.
Mirrors yt_pipeline/3_fetch_via_ytdlp.py. Resumable: skips existing .txt files."""
import re
import subprocess
import sys
import tempfile
from pathlib import Path

OUT = Path(__file__).parent / "raw" / "transcripts"
OUT.mkdir(parents=True, exist_ok=True)

VIDEOS = [
    # WEATHER
    ("06g9UDv1IeU", "weather_bot_tutorial_automate"),
    ("npy1rzBOl6M", "stormbot_ai_24-7"),
    ("TTc2ej05dOA", "weather_bot_2026_fast"),
    ("hej22I5Sit4", "weather_bot_claude_code"),
    ("u9k3M8Er_dc", "how_to_bet_weather_easy"),
    ("86xl8sINErw", "bots_10k_monthly_weather"),
    ("SGsNqudwel0", "high_winrate_ai_weather"),
    ("Rj6qAjNbUoc", "ai_weather_strategy_short"),
    # COPY TRADING
    ("gOgkoaRTq08", "polycule_copy_bot_tutorial"),
    # BTC (salvage)
    ("0YkolG5afrg", "btc_updown_2to2m_part2"),
]
for extra in sys.argv[1:]:
    VIDEOS.append((extra, "cli"))


def vtt_to_text(vtt: str) -> str:
    out, seen = [], set()
    for line in vtt.splitlines():
        line = line.strip()
        if not line or line.startswith(("WEBVTT", "NOTE", "Kind:", "Language:")) or "-->" in line:
            continue
        line = re.sub(r"<\d+:\d+:\d+\.\d+>", "", line)
        line = re.sub(r"<[^>]+>", "", line).strip()
        if line and line not in seen:
            seen.add(line)
            out.append(line)
    return " ".join(out)


ok = fail = 0
for vid, label in VIDEOS:
    out_file = OUT / f"{vid}__{label}.txt"
    if out_file.exists():
        print(f"SKIP exists: {vid} {label}"); ok += 1; continue
    print(f"FETCH {vid} {label}")
    with tempfile.TemporaryDirectory() as tmp:
        try:
            r = subprocess.run(
                [sys.executable, "-m", "yt_dlp", "--write-auto-subs", "--write-subs",
                 "--sub-lang", "en-orig,en,en-US", "--sub-format", "vtt", "--skip-download",
                 "--no-warnings", "--cookies-from-browser", "chrome",
                 "-o", str(Path(tmp) / "%(id)s.%(ext)s"),
                 f"https://www.youtube.com/watch?v={vid}"],
                capture_output=True, text=True, timeout=90)
        except subprocess.TimeoutExpired:
            print(f"  FAIL timeout"); fail += 1; continue
        vtts = list(Path(tmp).glob("*.vtt"))
        if not vtts:
            reason = (r.stderr.strip().splitlines() or ["no vtt"])[-1]
            print(f"  FAIL: {reason[-90:]}"); fail += 1; continue
        text = vtt_to_text(vtts[0].read_text(encoding="utf-8"))
        if len(text) < 100:
            print(f"  FAIL: too short ({len(text)})"); fail += 1; continue
        out_file.write_text(
            f"VIDEO_ID: {vid}\nLABEL: {label}\nURL: https://www.youtube.com/watch?v={vid}\n\n{text}",
            encoding="utf-8")
        print(f"  OK ({len(text)} chars)"); ok += 1

print(f"\nDONE. {ok} ok, {fail} failed. -> {OUT}")
