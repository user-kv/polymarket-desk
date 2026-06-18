# SYNTHESIS — What the research means + recommended path

Captured: 2026-06-12. My read of the raw files. Sort/argue with this later.

---

## THE ONE THING THAT CHANGES EVERYTHING
**Both Polymarket and Kalshi block Australia.** (Polymarket ISP-blocked by ACMA since
Aug 2025; Kalshi excludes AU/UK/CA.) For an AU-based user this is the **first decision**,
above any strategy. Until venue/jurisdiction is resolved, everything else is research-only.
→ See `practical_blockers.md`. Resolve this with Kavee before building anything.

## RANKING THE 3 STRATEGIES (after research)
1. **WEATHER — best edge, and it's automatable.** Real, documented, repeatable. Edge =
   ensemble-forecast prob vs market price, bet when EV ≥ 8–10%, fractional Kelly, many small
   bets across cities. Two ready open-source bots exist. Secondary cities (Buenos Aires,
   Cape Town, Dallas, Atlanta) still have hour-long edge windows; major cities are bot-owned.
2. **COPY TRADING — works only with hard filtering.** 14/20 top wallets are bots you CAN'T
   replicate (speed/MM edge). Copy only slow DISCRETIONARY humans (~100 trades/mo) in
   non-HFT niches (politics/sports). Theo4, beachboy4, HorizonSplendidView are real humans.
   Use PolySmartWallet to filter by category. Tools: Poly Syncer ($299–499/mo) or manual.
3. **BTC LATENCY — dead for non-bots.** Polymarket's dynamic fee (peaks ~3.15% at 50% odds)
   was engineered to eat exactly this edge. Park it. See `btc_latency_salvage.md`.

## RECOMMENDED PATH (if access is solved)
**Phase 0 — Access (BLOCKER):** decide venue + accept legal/funds risk. No code until done.

**Phase 1 — Learn weather by hand (no code, ~$50–100):** run the NO-CODE MANUAL PLAYBOOK
(`weather_web.md`): Windy "compare models" + Tropical Tidbits; when 3+ models (GFS/ECMWF/ICON)
agree on a range → true prob 70–90%; buy YES <$0.15 / NO >$0.45 on clear mispricings; bet
$1–3, 1–5/day, secondary cities; LIMIT orders (0 maker fee); log 100+ trades. Goal: feel the
edge, validate it's real for you, learn the resolution-station gotcha (KLGA not Midtown).

**Phase 2 — Automate (if Phase 1 win-rate holds 65%+):** run the **alteregoeth/weatherbot**
repo (simplest): Open-Meteo (free ECMWF/HRRR) + METAR + Gamma API; config min EV 0.05,
Kelly 0.25, max bet $20, scan hourly. Paper-trade first (`status`/`report`), then tiny live.

**Phase 3 — Optional agent layer:** wrap it in **Hermes Agent (+Claude)** for 24/7 autonomy,
self-improving skills, Telegram alerts. Nice-to-have, not required. Hermes has native Windows
support (matches Kavee's setup). The "$100→$5,000" claim is unproven marketing — ignore the number.

## 🔑 UPDATE — THE STRONGEST PRACTICAL PATH: BUILD IT WITH CLAUDE CODE (Kavee already has it)
The whole YouTube ecosystem converged on one thing: people build these bots with **Claude Code**,
and the sold bots/signals are mostly affiliate funnels (one is literally malware). Kavee has
Claude Code → he can build his own and skip all of it. Concrete, proven templates:
- **Weather bot:** clone `github.com/natestokens/polymarket-weather-bot` (173-member ensemble,
  honest +27.6% ROI, pure Python) — or have Claude Code rebuild/extend it.
- **Whale tracker / copy:** The Prediction Engineer's Flask+SQLite+HTML real-time tracker, built
  by prompting Claude Code (no code experience needed).
- **Execution layer:** `github.com/Polymarket/polymarket-cli` (OFFICIAL, `-o json` = agent-ready) —
  Claude Code drives it to read markets + place orders.
- **Validate first:** backtest on `github.com/jon-becker/prediction-market-analysis` (36GB real
  Polymarket+Kalshi history) BEFORE risking money.
- **Edge refinements found:** day-ahead ensemble mispricing (8–15pp thresholds, "stay out of the
  middle") + intraday **advection/nowcasting** via free METAR (api.weather.gov).
This collapses Phase 2–3 below: you don't need Hermes or a paid bot — Claude Code + polymarket-cli
+ the natestokens template is the lean build. (Hermes only adds 24/7 autonomy + Telegram later.)

## HARD TRUTHS / RISK LEDGER
- Only ~12.7% of users profitable; ~23% of 5+ trade wallets lifetime-positive.
- Weather edge is THIN: 1.25% taker fee + 5–10% spread on niche cities → net edge needed
  is well above headline 8%. Use limit orders; only trade when EV clears spread+fee.
- Bots compressed major-city windows to 5–15 min; you compete with 24/7 automation.
- Profit shows only over hundreds of trades; single freak weather event wipes a concentrated bet.
- "$819K / 99.3% win" type wallets are almost certainly arb/MM — not a template for you.

## OPEN QUESTIONS FOR KAVEE (when back)
1. How are you accessing given the AU block? (go/no-go)
2. Capital you'd commit to a learning phase?
3. Manual-first, or straight to the bot? (I recommend manual-first.)
4. Want the Hermes(+Claude) autonomous setup, or keep it a simple script?
5. Should I finish the YouTube transcripts (need Chrome closed or a cooldown)?
