# Weather — YouTube Transcript Notes (RAW)

Captured: 2026-06-12.

## ✅ RESOLVED via METADATA route (transcripts stayed 429-blocked, but we got the substance)
The caption *download* is throttled on every IP (local + Anthropic WebFetch), BUT yt-dlp
`--dump-json` METADATA is NOT throttled. Harvested titles + full descriptions + chapters +
links for 26 videos → extracted intelligence in **youtube_findings.md**, raw dump in
**youtube_metadata.md**. Best weather find: github.com/natestokens/polymarket-weather-bot
(Claude Code-built, 173-member ensemble, honest +27.6% ROI). See those files; transcript
verbatim text is the only thing still missing and is low-value.

---
ORIGINAL BLOCKED-STATUS NOTES BELOW (kept for reference):

## ⚠️ YOUTUBE FETCH STATUS = BLOCKED on this machine (every route tested 2026-06-12)
- `youtube-transcript-api` → IP-blocked (RequestBlocked).
- `yt-dlp --cookies-from-browser chrome` → "could not copy Chrome cookie database" (issue 7271)
  = Chrome STILL RUNNING in background (closing the window isn't enough on Windows; Chrome keeps
  background processes — must Exit via system tray / Task Manager).
- `yt-dlp --cookies-from-browser edge` → "Failed to decrypt with DPAPI" (issue 10927) =
  Chromium app-bound cookie encryption; yt-dlp can't read it.
- `yt-dlp --cookies-from-browser firefox` → Firefox not installed.
- `yt-dlp` no cookies → **HTTP 429 Too Many Requests** (IP throttled; needs HOURS to clear).

### WAYS TO FORCE IT (if a specific video is actually wanted)
1. **Fully quit Chrome** (Task Manager → end all Chrome processes, or tray → Exit), then
   `python polymarket_research/fetch_transcripts.py`. (May still hit DPAPI app-bound enc.)
2. **Export cookies to file**: use a "Get cookies.txt" browser extension on a YouTube tab,
   save as cookies.txt, then run yt-dlp with `--cookies cookies.txt` instead of --cookies-from-browser.
3. **Wait out the 429** (a few hours) and re-run the no-cookie path.

### HONEST NOTE ON VALUE
These queued videos are mostly "build a weather bot" / "bet on weather" tutorials that ECHO
content already captured from articles + the alteregoeth/Hermes repos. Marginal value is LOW.
Not worth heavy effort unless a specific video (e.g. hej22I5Sit4 "weather bot with Claude Code")
is wanted verbatim.

## Candidate videos queued (IDs in fetch_transcripts.py)
WEATHER:
- 06g9UDv1IeU — Polymarket Weather Trading Bot Tutorial | Automate Weather Markets
- npy1rzBOl6M — StormBot.Ai Trades Weather Markets 24/7
- TTc2ej05dOA — Weather Trading Bot Tutorial 2026 (Automate FAST)
- hej22I5Sit4 — Weather Trading Bot Built With Claude Code (Full Strategy)  ← relevant to Kavee
- u9k3M8Er_dc — How To Bet on the Weather (Easy Guide) Polymarket
- 86xl8sINErw — How Trading Bots Make $10K+ Monthly Predicting Weather
- SGsNqudwel0 — High Win Rate AI Weather Market Strategy
- Rj6qAjNbUoc — AI Weather Strategy Full Tutorial (Short)
- 22uqy6GdVus — BTC 5min Up/Down 2026 → REMOVED by uploader (dead)

(Transcript extraction notes will be appended here once fetch succeeds.)
