# The Two-Strategy Playbook
### Weather Trading + Sports Value-Betting on Prediction Markets — Dense Edition

*Information-dense. Every line is signal. Read top to bottom once, then use as a reference.*

---

## THE ONE SKILL (both strategies are this)
**Buy when the market price is below the true probability — measured against a reliable "answer key" — then hold to resolution.**
- Weather's answer key = **free professional forecast models**.
- Sports' answer key = **de-vigged sharp bookmaker odds (Pinnacle)**.
Everything below is how to (a) get a trustworthy true probability, (b) find where Polymarket disagrees, (c) size it, (d) prove your edge is real.

## BRUTAL TRUTHS (memorize)
- **~88% of users lose** (only ~12% net-positive; only ~3% are "skilled" at value betting). The edge is real but thin and statistical.
- **Never bet money you can't afford to lose. Never your whole bankroll. Not even close.** A normal 6-loss streak wipes out a big-bet account even with a *winning* system ("risk of ruin").
- **Access:** Polymarket **and** Kalshi both block **Australia** (ACMA ISP-block since Aug 2025). A VPN breaks ToS and gives zero fund-recovery protection. Solve "where can I legally trade" *before* funding. The skill below is portable; the access problem is separate.
- **Costs are real:** ~**2% winner fee** + **spread** (1–2¢ liquid, 5–10¢ niche). A 5% edge in a 6% spread is a *loser*. Always subtract costs first.
- **Validate before scaling.** Most strategies "fail" not because the logic is wrong but because the edge was never proven. Paper-trade, log everything, judge after 100+ trades.

---

# PART A — SHARED FOUNDATIONS

## A1. Price = probability
A share pays **$1 if right, $0 if wrong**. Price in cents = the crowd's implied probability (65¢ = 65%). "Yes" + "No" ≈ $1.

## A2. Expected Value (EV) — the only question that matters
**EV = (your true prob × amount won) − (lose prob × amount lost).** Positive EV = profitable on average → bet. Negative = skip, no matter how tempting.
*Example:* buy "Yes" at 40¢, you think true 65%. Win → +60¢ (65%); lose → −40¢ (35%). EV = 0.65×0.60 − 0.35×0.40 = **+$0.25/share**. **Then subtract costs** — if spread+fee = 6¢, real EV ≈ +19¢. Still a great bet.

## A3. Costs (and how to dodge them)
- **Taker fee** ~2% (weather ~1.25%), **highest near 50¢**, ~0 near 1¢/99¢.
- **Maker = 0 fee.** Post a **limit order** (offer to buy at your price, wait) instead of a market order → pay no fee. Use limit orders by default.
- **Spread** = hidden round-trip cost. Worst in niche markets (where the best edges live) → demand a bigger edge there.

## A4. Sizing — fractional Kelly
- Kelly fraction: **f = (b·p − q) / b** — b = decimal odds − 1, p = your true prob, q = 1−p. f = % of bankroll.
- **Use Quarter Kelly (0.25×)** — full Kelly assumes you *know* the true prob (you don't); fractional cuts variance and protects against estimate error.
- **Hard caps:** ≤5% of bankroll per position; while learning, a flat tiny stake ($1–5).
- **Bankroll** = money you can fully afford to lose. Diversify across many small bets — the edge only shows over *hundreds* of independent trades.

## A5. Proof of edge (do this or you're guessing)
- **Log every trade:** date, market, your prob, price paid, size, result.
- For sports, also log **Closing Line Value (CLV)** — see C5. CLV proves edge *before* results catch up.
- Judge after **100+ trades**: are you positive *after costs*? If not, fix it before risking more.

---

# PART B — WEATHER TRADING

## B1. Why it's good
Objective government resolution (no rug-pulls), casual/emotional opponents, **free pro forecasts** they ignore, **daily** feedback (fast learning). The big winners: gopfan2 (~$2M), ColdMath (~$120k+ barbell). An honest public bot (natestokens) logged **+27% ROI, 61% win** — real, modest, repeatable.

## B2. How the markets work
- Question split into **temperature buckets** (e.g. ≤70, 71–72, 73–74, 75–76, 77+), each a Yes/No ticket; prices sum to ~100%.
- **Resolves on the official NWS Daily Climate Report (CLI) for ONE specific airport station**, listed in the market rules. Settles **8:00 AM ET next day**. ~212 weather markets; cities incl. NYC, London, Guangzhou, Beijing, Shanghai, Miami, Hong Kong, + secondary cities.
- **⚠️ The #1 beginner error:** analyzing the city, not the **airport**. NYC resolves at **LaGuardia (KLGA)** — can run **3–5°F cooler** than Midtown. Dallas = **Love Field (KDAL), not DFW**. Always analyze the exact station.

## B3. The data (all free)
- **Models:** GFS (US), ECMWF (Europe, sharpest), ICON (Germany), HRRR (US short-range).
- **Model runs (your timing edge):** GFS 00/06/12/18 UTC; ECMWF 00/12 UTC. When a new run shifts the forecast, the *price lags* → trade before it catches up.
- **Ensembles = probability:** run the model many times; if 25 of 31 members say "75°F+", that's ~**80%**. Best bots use 30–170+ members.
- **Sources:** **Open-Meteo** (free ensembles incl. 31-member GEFS & ECMWF), **api.weather.gov** (NWS forecasts + live **METAR** airport obs), **Windy** ("compare models" GFS/ECMWF/ICON), **Tropical Tidbits** (raw model output).

## B4. The edge & entry checklist
Edge = **your ensemble probability − market price.** Buy a bucket only if ALL hold:
1. Edge **≥ 8 percentage points** (asymmetric ok: ~5pt to fade an overpriced bucket "No", ~15pt to back "Yes").
2. Lead time **≤ 48 hours** (forecasts reliable).
3. **GFS & ECMWF ensembles agree within ~1.5°C** (if models fight, sit out).
4. Market volume **≥ ~$10k** (so you can enter/exit).
5. **Avoid the coin-flip middle** — leave a **3°F buffer** around the ensemble mean; trade buckets the models clearly favor/reject.
If one fails → **don't trade.** Skipping is a profitable action.

## B5. Advanced intraday edge — advection / nowcasting
**Advection** = a warm/cold air mass blowing in. The day-ahead forecast guessed; the **live METAR** airport readings show *reality*. If warm air is arriving faster than forecast, the high will likely beat it → trade before the market notices. "Nowcasting" = using current obs to refine the forecast. (Level-2 skill; free via api.weather.gov.)

## B6. Cities, tactics, sizing
- **Trade SECONDARY cities** (Buenos Aires, Cape Town, Dallas, Atlanta): fewer bots, edges last **hours** not 5–15 min. Avoid bot-saturated NYC/London/Hong Kong (edge gone in minutes) — but they have tighter spreads. Trade-off: secondary = bigger edge but wider spread (clear it).
- **Laddering:** buy several adjacent cheap buckets (5–15¢); one or two winners cover the rest.
- **Barbell (ColdMath):** many tiny long-shot buckets + occasional bigger high-conviction bets.
- **Sizing:** learning = flat $1–5; proven = Quarter Kelly, ≤5% bankroll, run **10–30+ city/date combos** small (variance demands volume).
- **Costs:** weather taker fee ~1.25%; use **limit orders (0 fee)**; ensure the ≥8pt edge clears fee + spread.

## B7. Automate it (you have Claude Code)
The bot = the manual routine, tireless, across 30 cities. Best open-source blueprints:
- **`natestokens/polymarket-weather-bot`** (Claude-Code-built, the gold standard): **173-member ensemble** (ECMWF IFS+AIFS, GEFS, ICON via Open-Meteo); **city bias-correction** vs historical ASOS airport data (NYC +1.4°F, Miami −2.2°F); edge = model prob − price, thresholds **5pt (No) / 15pt (Yes)**, "stay out of the middle"; pure Python, no deps; **verified +27% ROI / 61% win**.
- **`alteregoeth-ai/weatherbot`**: ECMWF+HRRR via Open-Meteo, METAR, Visual Crossing, Gamma API; config min EV 0.05, Kelly 0.25, max bet $20, scan hourly; has **simulation/paper mode**.
- Official plumbing: **`Polymarket/polymarket-cli`** (Rust, JSON for agents) or **`py-clob-client`** (Python). **Paper-trade for weeks first.**

## B8. Manual routine (no code) & realistic expectations
Daily: pick city → find its airport station → check Windy compare-models for tomorrow's high → if 3+ models cluster on a range (true prob 70–90%) → open the market → find a bucket the models favor selling cheap (or one they reject selling rich) → run the B4 checklist → place a small **limit** order → **log it** → repeat → review after 100 trades.
**Expect:** a small grinding edge (~25% ROI / ~60% win at small scale), not a jackpot. Losing days/weeks are normal at 60% win. The "$80k/month" videos are marketing.
**Common killer:** "had a theory, won a few weeks, called it an edge, then lost." Validate with logged data, not vibes.

# PART C — SPORTS VALUE-BETTING

## C1. Why it's the most logically bulletproof
**Pinnacle's closing line ≈ true probability.** Hard evidence: across **397,935 football games, r² = 0.997** between Pinnacle's closing line and actual outcomes; optimal prediction puts **95–100% weight on Pinnacle** over all other books. Why: Pinnacle's **"winner's welcome"** policy invites sharp bettors and uses their money to price lines (other books *ban* winners, so their lines are softer). **Polymarket sports prices are set by slow retail money.** The gap between de-vigged Pinnacle and Polymarket = your edge. Documented human: **"swisstony" ~$3.7M** doing exactly this. The premise is the hardest in this whole field to argue with — the only real flaws are *execution and access*, both of which you control.

## C2. The full mechanic
1. Get the **sharp line** (Pinnacle, or Betfair Exchange / PS3838) for the game.
2. **De-vig** it → true probability (C3).
3. Compare to the **Polymarket price**.
4. If Polymarket price < true prob by **≥ your threshold (after costs)** → buy that side, **HOLD TO RESOLUTION** (don't try to flip — exit liquidity is poor).
*Worked example:* Pinnacle implies Lakers 70% (de-vigged). Polymarket "Lakers win" = **62¢**. Edge = 70 − 62 = **+8 points** → buy at 62¢, hold. If your prob source is right, this is +EV; over hundreds of such bets you profit.

## C3. De-vig (strip the bookmaker margin)
Raw book odds include a margin ("vig") so implied probs sum to >100%. Remove it:
- **Multiplicative** (default, 2-way): each side's implied prob ÷ sum of all implied probs. *e.g. 0.55 & 0.50 sum 1.05 → 52.4% & 47.6%.*
- **Power:** exponent-based; handles favorite/longshot asymmetry; between multiplicative and Shin.
- **Shin** (most theoretically sound): assumes part of the vig is insider info; allocates more margin to longshots; iterative; **best for heavy favorites, player props, multi-way markets.**
- **Rule:** multiplicative for simple 2-way; Shin/power for heavy-favorite or multi-outcome. Free devig calculators: OddsJam, gamblingcalc, edgeslip.

## C4. Which markets (and the threshold)
- Polymarket sports: **NFL, NBA, MLB, NHL, soccer, UFC, boxing, tennis, F1, Olympics, World Cup**; markets = game winners, season/championship, MVP, some props.
- **Edge threshold: ≥5%** commonly cited; you need **~2.2–3.0% just to cover** the 2% winner fee + gas + slippage, so demand more than that.
- Best opportunities: **less-liquid / less-watched markets** where Polymarket lags **minutes–hours** after news (injuries, lineups). Avoid racing bots on the obvious 15–60s edges.

## C5. Closing Line Value (CLV) — your proof of edge
The **closing line** (final odds before kickoff) bakes in *all* info → the gold-standard "true probability." **If you consistently get a better price than the closing line, you are mathematically profitable long-term** (Law of Large Numbers) — *before* results even confirm it.
- **Beat it by:** (1) **line-shop** the best price, (2) **bet EARLY** (soft lines before sharp money moves them), (3) make genuine +EV bets.
- **Track:** log your entry price + the closing line for 100+ bets; compute % positive-CLV and average CLV.
- **Benchmarks:** any positive CLV = beating the market; **+5% avg CLV = excellent**; **60–65% of bets beating CLV over 200+** = a confirmed, durable edge. *This is how you KNOW you have an edge without waiting months for variance to resolve.*

## C6. Sizing & tools
- **Kelly:** f = (b·p − q)/b; use **Quarter Kelly**; ≤5% bankroll/bet; flat tiny stakes while learning.
- **Tools:** **OddsJam** (edge feed + devig + CLV + prediction-market trader tracker), **PredictEngine** (arb/value scanner), **Pinnacle Odds Dropper**, odds APIs (oddspapi). Trackers: polysight.app, polytraders.io. Repos: `Alirun/polymarket-trader`, `jon-becker/prediction-market-analysis` (36GB Polymarket+Kalshi history for **backtesting**).

## C7. Step-by-step workflow
1. Pick a sport/league you understand. 2. Pull Pinnacle (or Betfair) lines. 3. De-vig → true prob. 4. Scan Polymarket for the same games; find price < true prob by ≥5% (after costs). 5. Place a **limit** order (0 fee) and **hold to resolution**. 6. **Log entry price + closing line** → track CLV. 7. After 100–200 bets, check CLV%: beating it 60%+ → real edge, scale slowly with Quarter Kelly. Not beating it → fix your inputs before risking more.

## C8. Flaws & mitigations (honest)
- **Bots own the fast/big edges** (15–60s) → don't race them; value-bet slower markets and hold.
- **Liquidity:** fewer markets than a sportsbook; low-liquidity markets are easy to **buy, hard to sell** → hold to resolution, size to available depth.
- **Wash trading** inflates Polymarket volume (Columbia study) → don't trust volume blindly; check real two-sided depth.
- **Rising efficiency** = fewer easy edges over time; **costs** (2% fee + spread) must be cleared; value betting is the **highest skill bar** (~3% of accounts skilled).
- **Access:** Polymarket blocked in AU (same gate as weather).

---

# PART D — WEATHER vs SPORTS: WHICH, WHEN, HOW TOGETHER

| | **Weather** | **Sports value-betting** |
|---|---|---|
| Answer key | Free ensemble forecasts | De-vigged Pinnacle (r²=0.997) |
| Logic strength | Strong (objective) | **Strongest (near-unfalsifiable)** |
| Best for | Automating; objective resolution | Year-round; if you know sport |
| Feedback speed | **Daily** (fast learning) | Per-game |
| Main flaw | Thin edge; bots in big cities | Liquidity/exit; bots on fast edges |
| Mitigation | Secondary cities, limit orders | Less-liquid markets, hold to resolution |
| Proof metric | Logged win% after costs | **CLV** (beat closing line 60%+) |
| Automatable? | **Yes** (natestokens template) | Partly (scanners + manual judgment) |
| Edge size | ≥8 pts (model vs price) | ≥5% (true prob vs price) |

**Which to start with?**
- Want **objective, automatable, fast feedback** → **Weather** (and you have Claude Code to build the bot).
- **Know a sport deeply** and want the **most bulletproof logic** + year-round volume → **Sports**.
- Ideal: learn **both** — they share the one skill and diversify your edge across unrelated domains.

**The validation gate (same for both):**
1. **Paper-trade** (fake money) for weeks → prove you can spot edges. 2. **Tiny real money** ($1–5/bet, few-hundred-$ bankroll), **log everything** (sports: track CLV). 3. **100+ trades** → positive after costs / beating CLV 60%+? → scale slowly (Quarter Kelly, ≤5%/bet). 4. Only then **automate / size up.** Each phase must succeed before the next. **Never skip to big money.**

---

# PART E — QUICK REFERENCE

**Formulas:** EV = p·(win) − (1−p)·(loss). Kelly f = (b·p − q)/b, use 0.25×. De-vig (mult.) = implied_prob ÷ Σ implied_probs.
**Edge thresholds:** Weather ≥8 pts; Sports ≥5% (clear ~2.5% costs first).
**CLV benchmarks:** +5% avg = excellent; 60–65% of bets beating close over 200+ = durable edge.
**Weather data:** Open-Meteo (ensembles), api.weather.gov (NWS + METAR), Windy (compare models), Tropical Tidbits. Runs: GFS 00/06/12/18 UTC, ECMWF 00/12 UTC. Stations: KLGA (NYC), KDAL (Dallas). Secondary cities: Buenos Aires, Cape Town, Dallas, Atlanta.
**Sports data:** Pinnacle / Betfair / PS3838 (sharp lines); OddsJam, PredictEngine, Pinnacle Odds Dropper, oddspapi (APIs); devig calcs (oddsjam/gamblingcalc/edgeslip).
**Repos:** natestokens/polymarket-weather-bot, alteregoeth-ai/weatherbot, Polymarket/polymarket-cli, Polymarket/py-clob-client, Alirun/polymarket-trader, jon-becker/prediction-market-analysis (backtest data).
**Rules of survival:** bet small (≤5%), limit orders (0 fee), hold to resolution, log everything, validate 100+ trades, never bet what you can't lose, never all-in.
**Access gate:** Polymarket + Kalshi block Australia — solve venue/legality before funding.
**Scam watch:** never run commands like `powershell irm <site> | iex` ("install a bot" = malware); guard your wallet private key; assume "$X/day bot" promos are paid affiliate funnels.

*Educational only — not financial advice. Prediction-market trading is risky, zero-sum, and legally restricted in many places including Australia. Never trade money you cannot afford to lose.*

