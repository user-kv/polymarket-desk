# STRATEGY SURVEY — Finding the Best 3 (RAW)

Captured 2026-06-12. Goal: broad survey of ALL candidate strategies, pick the best 3 for a
HUMAN seeking durable long-term results. Verified across academic + practitioner + traders.

## THE UNIFYING SKILL (why the top 3 are really one skill)
Every durable edge = **"buy when the market price is BELOW the true probability (from a more
reliable source), then hold to resolution."** The three best strategies are this same skill
applied in 3 domains, each with a different "source of truth" (answer key):
- Weather → answer key = free pro forecast models
- Sports → answer key = de-vigged sharp bookmaker odds (Pinnacle/Betfair)
- Favorites/Calibration → answer key = historical calibration + probability logic

Ranked by how ACTIVE they are: Sports (most active) → Weather (medium) → Calibration (most passive).

---

## FULL CANDIDATE EVALUATION (everything considered)

| Strategy | Durable? | Human-accessible? | Evidence | Verdict |
|---|---|---|---|---|
| **Weather info-edge** | ✅ high | ✅ (secondary cities) | gopfan2 $2M, ColdMath, natestokens +27% | **TOP 3** |
| **Sports value-betting vs sharp books** | ✅ high | ✅ (slower mkts/hold) | swisstony $3.7M; multi-source de-vig method | **TOP 3** |
| **Favorite-longshot / calibration** | ✅ high (behavioral) | ✅✅ (long horizon, passive) | QuantPedia (20 studies), CEPR, arxiv | **TOP 3** |
| Copy trading | ⚠️ medium | ✅ but needs constant vetting | 14/20 top = bots; 80% traps | Secondary |
| Market making / liquidity rewards | ✅ (yield) | ⚠️ capital-heavy, competitive | $30–80/day on $10k (was $200–300 in '24) | Honorable mention (income, not "edge") |
| Inter-exchange arb (Poly vs Kalshi) | ❌ low | ❌ bots, seconds | $40M extracted but 0.51% of users profit | Reject for human |
| Intra-market / logical arb | ❌ low | ❌ 4 sec / 200ms windows | 41% of conditions mispriced but bot-captured | Reject as primary |
| Mean reversion | ⚠️ | ❌ only works as maker (limit) | QuantPedia: alpha vanishes w/ market orders | Reject |
| News/event speed (latency) | ❌ | ❌ bot war | Polymarket fee-killed crypto latency | Reject |
| Economic-data modeling | ✅ | ✅ | subset of calibration/value betting | Folded into #3 |

---

## ⭐ THE BEST 3 (with verification + honest flaws)

### #1 — SPORTS VALUE BETTING vs SHARP BOOKS  (most active, highest ceiling)
**Idea:** The sharpest betting markets in the world (Pinnacle, Betfair exchange) have the most
accurate odds because they welcome winners and profit on volume. Polymarket's sports prices are
set by slower RETAIL money. **De-vig** the sharp odds → that's the "true probability." When
Polymarket's price is cheaper than that true probability by enough, buy that side; hold to result.
- **How (4 steps):** (1) get sharp odds (Pinnacle/PS3838/Betfair). (2) De-vig: strip the
  bookmaker margin so probabilities sum to 100% → true prob. (3) Compare to Polymarket price.
  (4) Bet the side where Polymarket price < true prob by ≥ your threshold (≥2–5% sports,
  ≥3–8% politics, AFTER fees/spread). Hold to resolution.
- **Why durable:** sharp books STAY efficient; Polymarket retail STAYS slow. Year-round (sports
  never stop), huge market count, scalable. The metric that proves you're +EV = **Closing Line
  Value** (you consistently got a better price than the final sharp line).
- **Verified:** "swisstony" ~**$3.7M** doing exactly this; de-vig method confirmed across
  multiple sportsbetting + prediction-market sources; QuantPedia favorite-longshot data.
- **⚠️ HONEST FLAW:** the *fastest/biggest* edges close in 15–60s and are bot-contested (pure
  ARBITRAGE = locking both sides instantly = partly a speed game). The DURABLE human version is
  **value betting** (buy one side, hold) in **less-liquid markets** where the lag is minutes–
  hours. Tools (OddsJam) flag edges but hit-rate is ~10–20% if you chase the fast ones. So:
  don't race bots — fish slower markets and hold to resolution. Needs sports knowledge + the
  de-vig habit. Also: Polymarket sports liquidity varies; and AU access issue applies.

### #2 — WEATHER INFO-EDGE  (most objective, proven, automatable)
(Full detail in weather_web.md / weather_tools_repos.md / GUIDE.md.)
- **Idea:** free pro ensemble forecasts (GFS/ECMWF) vs market price; bet when model prob beats
  price by ≥8pts; hold to next-morning resolution. Objective gov't resolution.
- **Why durable:** objective answer key, casual opponents, fast daily feedback, automatable.
- **Verified:** gopfan2 ~$2M, ColdMath ~$120k+, natestokens bot honest +27% ROI / 61% win.
- **⚠️ FLAW:** thin edge (clear costs!), bots own major cities → trade SECONDARY cities; needs
  the airport-station discipline (KLGA not Midtown).

### #3 — FAVORITE / CALIBRATION EDGE  (most passive, most academically bulletproof)
**Idea:** Two robust, documented biases you exploit by being patient, not fast:
- **Favorite-longshot bias:** cheap longshot contracts are OVERPRICED (a 5¢ contract that only
  wins 2% of the time loses ~60% of money); expensive FAVORITES are UNDERPRICED and yield small
  POSITIVE returns. → **Buy favorites, fade longshots.**
- **Politics underconfidence:** political prices are chronically compressed toward 50% — a "70¢"
  political contract has historically corresponded to a ~**83%** true chance. → buy underpriced
  political favorites and hold.
- **Why durable:** it's a HUMAN BEHAVIORAL bias (people overpay for the dream of a longshot) —
  it persists as long as casual money exists. Works at LONG horizons → **no bot speed war**,
  the most passive of the three.
- **Verified:** "single most robust finding in prediction-market research" — QuantPedia
  (synthesis of 20 studies, ~3.64% edge favoring favorites), CEPR economics column, arxiv
  calibration paper. Multiple independent academic sources. ✅✅
- **⚠️ FLAW:** edge per trade is small (~2–5%), so needs volume + discipline; some research
  found the bias WEAKER on Polymarket specifically (sophisticated traders) vs sportsbooks —
  strongest in CASUAL markets (sports, entertainment, novelty, politics). Don't blindly buy
  every favorite; target casual-heavy markets. Patience over excitement.

---

## WHY THESE 3 REPLACE THE OLD LINEUP
- Old lineup was Weather + Copy + Bitcoin. Bitcoin = dead (fee-killed, bots). Copy = real but
  DERIVATIVE/weakest (depends on others; 80% traps).
- New lineup (Sports value-bet + Weather + Calibration) = three INDEPENDENT, durable,
  academically/empirically backed edges that share ONE learnable skill. Copy trading kept as a
  SECONDARY option (lower effort, lower edge). Market-making noted as a passive INCOME play
  (yield, not edge) for when you have more capital.

## 🔬 FLAW AUDIT (stress-tested each — user wants the one whose flaw is hardest to find)

**#1 Sports value-betting — flaw is EXECUTION, not PREMISE (best).**
- Premise is near-unfalsifiable: Pinnacle/Betfair are among the most efficient forecasting
  mechanisms that exist (decades of evidence). Using them as "truth" vs slow Polymarket retail
  is structurally sound. **You cannot really argue the premise is wrong.**
- Real flaws (all execution, all manageable): rising efficiency; fragmented liquidity; bots take
  73% of the FAST arb; need ~2.2–3.0% min spread just to cover the 2% winner-fee + gas + slippage
  on small trades; a Feb-2026 quirk where a <$0.10 tx can wipe maker orders. Only 0.51% of wallets
  profit >$1k (but that includes all the gamblers).
- Mitigation: don't race bots on locked arbitrage — VALUE-bet slower/less-liquid markets and HOLD
  to resolution; require a bigger edge to clear costs; size up so fees matter less.
- **Verdict: the most logically bulletproof of the three. Flaw = how well you execute, not whether the idea works.**

**#2 Weather — flaw is THIN EDGE + bot-eroded major cities (known, manageable).**
- Premise solid (objective forecasts vs casuals). Flaw: edge is small and must clear costs; bots
  own NYC/London. Mitigation: secondary cities, limit orders, airport-station discipline.

**#3 Favorite/Calibration — flaw is CONTESTED EVIDENCE on Polymarket itself (most findable flaw).**
- ROBUST on traditional sportsbooks (QuantPedia, CEPR). But on POLYMARKET SPECIFICALLY the
  research CONTRADICTS itself: (a) some find classic bias (favorites underpriced → buy favorites);
  (b) one finds Polymarket UNDERESTIMATES low-prob events (sub-10% outcomes happen 14% of the time
  → longshots underpriced → opposite!); (c) others find prices well-calibrated (no edge).
- **So as a STANDALONE Polymarket strategy its flaw IS findable** (the edge may not exist there).
- Better use: as an OVERLAY/filter (lean toward favorites, be skeptical of <10¢ longshots) and on
  CASUAL-heavy markets (entertainment, novelty, lower-tier sports) where the bias is strongest —
  not as a mechanical "buy every favorite" on efficient Polymarket markets.

**BOTTOM LINE:** If you want the strategy whose core logic you CANNOT poke a hole in → **#1 Sports
value-betting vs sharp books.** Its only enemies are execution and access, both of which you
control. #2 Weather is the best OBJECTIVE + automatable one. #3 is real but contested on Polymarket
→ use as an overlay, not a standalone.

## SOURCES (multi-source verified)
- QuantPedia "Systematic Edges in Prediction Markets" + "Mean-Reversion... Polymarket"
- arxiv 2602.19520 (calibration), arxiv 2508.03474 & 2605.00864 (arbitrage analysis)
- CEPR "economics of Kalshi"; ResearchGate favorite-longshot overview
- Practitioner: clawarbs, oddspapi, predictengine, laikalabs, tradetheoutcome, startpolymarket
- Traders: swisstony (~$3.7M sports), gopfan2 (~$2M weather)
- (YouTube creator triangulation appending to youtube_metadata_3_strategies.md)
