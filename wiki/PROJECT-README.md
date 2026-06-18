# Polymarket Project

Research + guides for trading prediction markets (Polymarket), focused on two durable,
human-accessible strategies: **Weather trading** and **Sports value-betting**.

> ⚠️ **Before risking real money, read this:** ~88% of users lose. The edge is real but thin.
> **Never bet money you can't afford to lose, and never your whole bankroll.** Paper-trade
> (fake money) and validate over 100+ logged trades first. Access note: Polymarket is blocked
> in Australia; Kavee plans to use a VPN — understand that this breaks platform ToS and offers
> no fund-recovery protection. Start tiny, prove it first.

---

## 📖 Start here — the guides (in `/`)
Read in this order:
1. **`Weather-and-Sports-Beginner-Guide.pdf`** ← START HERE. Explains everything from zero,
   every term in plain English. (Source: `GUIDE3.md`)
2. **`Weather-and-Sports-Value-Betting-Dense-Guide.pdf`** — the fast, information-dense version
   once you know the basics. (Source: `GUIDE2.md`)
3. **`Prediction-Markets-Complete-Guide.pdf`** — the original long beginner guide (covers
   weather + copy trading + why Bitcoin is out). (Source: `GUIDE.md`)

Each guide also has a `.html` version (opens in any browser; print-to-PDF if you want).

## 🔬 The research (in `raw/`)
Raw, sourced, unsorted research notes. Key files:
- `STRATEGY_SURVEY.md` — survey of ALL candidate strategies + why these 2 won + flaw audit.
- `weather_web.md`, `weather_tools_repos.md`, `weather_hermes_build.md` — weather deep-dives.
- `SPORTS_VALUE_BETTING.md` — sports deep-dive (Pinnacle, de-vig, CLV, tools).
- `copytrading_web.md`, `copytrading_wallets.md` — copy-trading research (secondary strategy).
- `youtube_findings.md` — extracted intelligence from ~130 YouTube videos.
- `youtube_metadata*.md` — raw video metadata harvests.
- `practical_blockers.md` — access (AU), fees, spreads, capital.
- `00_INDEX.md` — running index of the research.

## 🛠️ Scripts (in `/`)
All pure-Python; run from the project root (they use paths relative to themselves).
- `fetch_metadata.py`, `fetch_more.py`, `fetch_strat3.py` — harvest YouTube video metadata
  (titles/descriptions/links) via yt-dlp. The transcript *download* is IP-blocked, but
  metadata isn't — this is how the research got the substance.
- `fetch_transcripts.py` — attempt full transcripts via yt-dlp (needs Chrome closed / cookies).
- `make_pdf.py` / `make_pdf2.py` / `make_pdf3.py` — render `GUIDE.md` / `GUIDE2.md` / `GUIDE3.md`
  to PDF + HTML. Requires `pip install markdown xhtml2pdf`.
  - Regenerate a guide after editing: `python make_pdf3.py` (etc.)

## 🎯 The two strategies (one-line each)
Both are the same skill: **buy when Polymarket's price is below the true probability (from a
reliable source), then hold to resolution.**
- **Weather** → true probability from free pro forecast models (Open-Meteo, api.weather.gov);
  bet when model prob beats price by ≥8 pts; trade secondary cities; resolves on the official
  airport-station report next morning.
- **Sports value-betting** → true probability from de-vigged sharp odds (Pinnacle, r²=0.997 vs
  outcomes); bet when Polymarket is ≥5% cheaper than that; prove your edge via Closing Line Value.

## ✅ Next steps (the validation ladder)
1. Read the beginner guide. 2. Paper-trade (fake money) for weeks. 3. Tiny real bets ($1–5),
log everything (sports: track CLV). 4. 100+ trades → ahead after costs? → scale slowly.
Each step must work before the next. Optional later: build a weather bot with Claude Code
(template: `github.com/natestokens/polymarket-weather-bot`; see `weather_tools_repos.md`).

---
*Educational only — not financial advice.*
