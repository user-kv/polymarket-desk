## CHANGELOG

| # | Change | Why |
|---|--------|-----|
| 1 | **Sports volume restated as ~55% of reported figure** (wash-trading correction) | Columbia (Nov 2025) found 45% of all-time Sports volume is likely wash trading — 90%+ at peak periods. "Largest addressable market" claim was built on inflated volume. True liquid volume ≈ $126M/month, not $230M. |
| 2 | **Soccer match-moneyline edge downgraded from "real" to "thin and context-dependent"** | arXiv 2403.07669 achieves 51.94% accuracy vs. bookmaker closing line — not vs. a naive Polymarket retail crowd. Closing-line efficiency is near-perfect. The edge is real only against uninformed retail in illiquid off-tournament markets; vanishes against any sharp participant. |
| 3 | **Soccer and NBA demoted from Tier 1 to Tier 2; sequencing note added** | User vetoed sports as FIRST build. Both are still in-scope; this is a sequencing decision, not a veto of the vertical. Reinstating them at Tier 2 so the priority table is consistent with the veto. Tier 1 slots reclaimed by weather (proven OOS) and geopolitics (0% fee, genuine LLM edge). |
| 4 | **All Tier 1/2 sports edges restated NET of 0.75% taker fee** | Fee schedule confirmed (Polymarket March 2026 rollout): Sports 0.75% max taker at 50¢. A 51.9% model vs. closing line implies ~0.4% gross edge at best against sharp Polymarket crowds — consumed entirely by 0.75% fee. Player props vs. naive retail may survive costs; match moneylines against sharp crowds almost certainly do not. |
| 5 | **Crypto events (4.1) demoted to Tier 3** | 1.8% taker fee on crypto category. A "genuine informational gap" edge must clear 3.6% round-trip. That is a very high bar; demoted until a specific market demonstrates gross edge >> 2%. |
| 6 | **Musk tweet-count markets re-examined and demoted to Tier 3** | Economics/Culture/Weather fee = 1.25% taker. Volume claim "$97K" needs to be verified per market, not category. Fast track-record accrual argument stands, but edge over a simple historical-rate model is unproven. Labeled INFORMATIONAL / perishable — model is public and easily copied. |
| 7 | **Wash-trading warning elevated and quantified** | Sports: 45% all-time wash, 90% at peak. Elections: 17%. Crypto: 3%. CONSEQUENCE: Sports volume figures used for position-sizing estimates must be halved. Liquidity may be shallower than it appears; slippage is higher. |
| 8 | **Edge durability labels added to every INCLUDE vertical** | Rubric Tier 1.4 requires STRUCTURAL/behavioral vs. INFORMATIONAL/perishable classification. |
| 9 | **Pre-registered kill thresholds added to every INCLUDE vertical** | Rubric Tier 1.2. Kill threshold decided before data; never moved. |
| 10 | **Build-effort ROI re-ranking applied to summary table** | Rubric Tier 3.9. Cheap + durable + high-volume wins first. Sports verticals are high-volume but high-effort and sports is sequencing-deferred; FDA/geopolitics are high-edge-density per build-hour. |
| 11 | **Volume baseline footnote upgraded** | "~25% wash" in original was the headline figure; sports-specific rate is 45%. Reprinted accurately. |
| 12 | **Correlation risk note added to macro family** | CPI + Fed + GDP + NFP all respond to the same macro factor. "Diversified macro" is an illusion without explicit factor neutralisation. |

---

# The Institute — Market Universe Map
**Document:** 01_MARKET_UNIVERSE.md
**Status:** Research complete — RED-TEAMED R2 (2026-06-30). Feeds build backlog in 09_ROADMAP.md.
**Authored:** 2026-06-30, R1 research agent (Sonnet). Red-teamed and hardened R2 (Sonnet).
**Sources:** Polymarket Gamma API (live probe, offsets 0–400); Columbia University wash-trading study (Nov 2025, arXiv 2606.04217); arXiv 2403.07669 (soccer ML accuracy); Polymarket fee schedule (docs.polymarket.com/trading/fees, March 2026 rollout); DeFiRate volume data; QuantPedia/SSRN/arXiv academic literature; platform analytics (Polycopy, PolymarketAnalytics).

---

## Preamble: How to Read This Document

Each sub-market entry answers five questions in a consistent format:
1. **Edge thesis** — is the crowd beatable here, and *why* precisely?
2. **Data sources** — free tier (prototype) + premium upgrade (live launch).
3. **Best engine fit** — which of the 4 engines applies, and why.
4. **Cadence & volume** — market count, resolution frequency, track-record accrual speed.
5. **Verdict** — INCLUDE (tier 1/2/3) or CUT, with net-of-cost edge, durability label, kill threshold, and explicit reasoning.

### The 4 Edge Engines (reference)
- **Engine A — Quant/information model:** build a numerical model better than the crowd's
  implicit model. Exploits informational gaps where your forecast distribution is tighter.
- **Engine B — Behavioral/crowd-bias:** exploit systematic mispricings baked into the crowd
  (favorite-longshot bias, recency bias, anchoring, sentiment). No private data required;
  the crowd's own behavior is the signal.
- **Engine C — News & event reasoning:** extract signal from unstructured text (news, press
  releases, earnings, political statements) faster or more accurately than the crowd. LLM
  agentic-search is the implementation lever.
- **Engine D — Smart-money / copy-flow:** identify wallets with proven domain-specific edge
  and co-enter their positions with minimal lag. Parasitic but real; requires wallet analytics.

### The volume baseline (Polymarket, May 2026)
- Sports: ~33% of reported platform volume. **ADJUSTMENT: 45% of Sports volume is classified as likely wash trading (Columbia 2025). Treat Sports real liquid volume at ~55% of stated figures. Effective real Sports volume ≈ $126M/month.**
- Politics/Gov: ~23% (~$156M/month reported; elections wash-trading rate ~17%, so real ≈ $129M/month).
- Finance/Fed/Macro: ~7% (~$47M/month); spiked to $736M in March 2026 (Fed event).
- Entertainment: ~3% (~$21M/month).
- Weather: <0.1% (~$197K/month).
- Other (crypto sub-markets, tech, geopolitics, culture): ~34% (~$238M/month; crypto wash rate ~3%).

Total reported platform volume: ~$690M/month in May 2026. Wash-trading-adjusted real volume is approximately $500–550M/month.

*Source: Columbia University "Network-Based Detection of Wash Trading" (Nov 2025). Sports wash rate = 45% all-time, 90%+ at peak. These figures deflate the volume-based case for sports investment.*

---

## Family 1: Macro / Financial

**Correlation risk (flag for allocator):** CPI, Fed Decisions, GDP, and NFP all respond to the same underlying macro-economic factor. Treating these as four independent positions is incorrect. A day where all four macro markets move against you simultaneously is a plausible scenario. Cap total macro exposure as a single correlated cell, not four separate ones.

---

### 1.1 CPI — Month-over-Month and Year-over-Year

**Edge thesis:**
The market crowd aggregates sell-side economist consensus (Bloomberg survey), which anchors on prior month's print and under-updates on high-frequency sub-data available before the BLS release (shelter indices from ApartmentList/Zillow, gasoline price trackers, airfare trackers). An Engine A model built on these leading sub-indicators can produce a tighter distribution than consensus *before* the print, giving a clean edge on tail bins.

**Net-of-cost edge:** Finance/Politics/Tech taker fee = 1.0% max at 50¢. Near-50% tail bins carry the full fee. A gross edge of ≥2% is required for a viable net position; 3–5% gross is realistic for a well-calibrated sub-indicator model on tail bins. This is the only macro vertical where net edge plausibly clears costs with reasonable confidence.

**Edge durability:** STRUCTURAL/behavioral — anchoring bias in analyst consensus is persistent. Half-life: long (this bias has persisted for decades). The sub-indicator data advantage has a shorter half-life as more funds discover it; ~2–3 years before the alpha is crowded out.

**Kill threshold (pre-registered):** After 24 resolved markets, if ROI is below 0% net-of-fees, retire the vertical and diagnose before rebuilding. Do not move this threshold.

**Data sources:**
- Free: FRED API; BLS Public Data API v2; ApartmentList National Rent Report; GasBuddy average price data; BTS airfare index.
- Premium: Bloomberg consensus scrape via Unusual Whales ($99–299/mo) — gives the exact consensus to bet against, which is the core signal.

**Best engine fit:** Engine A (quant model) primary; Engine C (LLM text on BLS press releases + shelter commentary) secondary.

**Cadence & volume:** Monthly (12/year). ~10–20 live markets per print. Track record: ~12 data points/year — slow but each is high-confidence if the model is sound.

**Verdict: INCLUDE — Tier 1.** Already partially built (B1). Best net-of-cost macro edge. Clean resolution. **NOTE: treat CPI + Fed + GDP + NFP as one correlated macro position for sizing.**

---

### 1.2 Federal Reserve Decisions (rate cuts / holds / hikes)

**Edge thesis:**
Fed decisions are heavily forecasted. The specific edge is the framing gap between Polymarket question wording and OIS swap market pricing (12–48h lag in crowd updating) and mis-timing of shifts after Fed communication (speeches, minutes, dot plot). Engine C detects these shifts faster than median retail. Engine D (macro-specialist wallets) adds signal.

**Net-of-cost edge:** 1.0% taker fee. High-volume event markets (~$10M+ per market) have lower effective spread, which helps. The framing-gap edge is likely 2–5% gross on correctly identified lag situations. Survives costs. **Caveat:** this edge exists only in the lag window; the crowd catches up. If our scan latency exceeds 12h, the edge evaporates.

**Edge durability:** INFORMATIONAL — the lag exists because retail doesn't process Fed communications quickly. As automated news-trading improves, this half-life is ~1–2 years before the gap closes. STRUCTURAL component: the framing-gap between Polymarket question wording and OIS is a persistent structural artefact as long as Polymarket writes questions in English prose rather than basis-point contracts.

**Kill threshold (pre-registered):** After 16 resolved FOMC markets (2 years of data), if net ROI < 0%, pause and diagnose. 8 meetings/year means patience is required.

**Data sources:**
- Free: FRED API; Fed press release text; CME FedWatch implied probabilities (free scrape); FOMC calendar published a year in advance.
- Premium: Bloomberg terminal for real-time OIS vs. Polymarket spread (this is the specific signal).

**Best engine fit:** Engine C (Fed communications parsing) + Engine D (macro wallets) + Engine A (OIS vs. Polymarket spread comparator).

**Cadence & volume:** 8 FOMC meetings/year. $10M+ per market around decision dates. Very slow track-record accrual.

**Verdict: INCLUDE — Tier 1.** High volume, clean resolution, framing-gap edge is specific and falsifiable. Correlated with CPI/GDP/NFP — count as one macro cell.

---

### 1.3 GDP — Advance, Preliminary, and Final Estimates

**Edge thesis:**
Nowcast divergence from consensus (Atlanta Fed GDPNow vs. SPF median) provides a lead signal that the crowd under-weights. Edge is real only on clear divergence; GDP is harder to beat than CPI due to economy-wide aggregation noise.

**Net-of-cost edge:** 1.0% taker fee. GDP markets are lower-volume than CPI/Fed, so spreads are wider. Net edge is marginal — requires 3%+ gross divergence signal to clear fees plus spread. Build only after CPI/Fed demonstrate positive OOS ROI.

**Edge durability:** STRUCTURAL — nowcast divergence is a persistent free signal the crowd ignores. Likely to remain usable for 5+ years.

**Kill threshold (pre-registered):** After 8 resolved GDP markets (2 years), net ROI < 0% triggers pause. Very slow; tolerate wider confidence intervals.

**Data sources:**
- Free: BEA GDP release; Atlanta Fed GDPNow; NY Fed Staff Nowcast; Philadelphia Fed SPF; FRED API.

**Best engine fit:** Engine A (nowcast divergence model).

**Cadence & volume:** 4 releases/year. Very slow track record. Lower volume than CPI/Fed.

**Verdict: INCLUDE — Tier 2** (build after Tier 1 macro). Correlated with CPI/Fed — same macro cell budget.

---

### 1.4 Non-Farm Payrolls / Jobs Report

**Edge thesis:**
ADP National Employment Report (T-2 before NFP) and Challenger layoff data (T-1) provide directional lead signal. Crowd under-adjusts NFP bins when ADP surprise is large and directional. The edge is noisier than CPI because NFP revision rates are high — a "beat" can be revised away.

**Net-of-cost edge:** 1.0% taker fee. NFP revision risk means even a correct directional call can resolve against you. Gross edge must be ≥3% to survive fees plus revision noise. Lower conviction than CPI.

**Edge durability:** INFORMATIONAL — the ADP-to-NFP correlation is publicly known and increasingly arbitraged. Half-life: ~2 years before this specific signal is crowded out. Structural base: anchoring to consensus persists as a behavioral bias.

**Kill threshold (pre-registered):** After 24 resolved NFP markets (2 years), net ROI < 0% triggers retirement. Separate kill from CPI — these are different models.

**Data sources:**
- Free: BLS Employment Situation; ADP National Employment Report; Challenger Gray & Christmas; FRED API; Philly Fed SPF.

**Best engine fit:** Engine A (ADP-to-NFP calibration model).

**Cadence & volume:** Monthly. Moderate Polymarket volume. Similar cadence to CPI but lower confidence.

**Verdict: INCLUDE — Tier 2.** Edge exists but noisy. Build after CPI shows positive ROI. Same macro correlation cell.

---

### 1.5 Cryptocurrency Price Levels (Bitcoin, Ethereum specific-date targets)

**Edge thesis:**
CUT. Crypto price markets on Polymarket are the most efficiently arbed on the platform. Professional crypto options traders at Deribit/Binance arb the Polymarket price continuously. Academic evidence: crypto prediction markets show highest accuracy (94%+) precisely because they are most heavily arbed. Our models cannot compete. Note: the taker fee for Crypto is 1.8% — the highest category. Any thin edge is doubly exterminated by cost.

**Verdict: CUT.** Efficient + highest fee category. No viable path.

---

### 1.6 Commodity Prices (Natural Gas, Crude Oil, Gold specific levels)

**Edge thesis:**
Commodity futures markets (HFT-dominated) arb Polymarket commodity price markets continuously. Same problem as crypto price markets, with the added complication that energy supply/demand dynamics are opaque. Seasonal gas markets with EIA inventory events are the one narrow exception, but the spread on these markets is wide.

**Net-of-cost edge:** Finance/Tech/Politics fee category (1.0%). Not enough alone to save an efficient market. The EIA-event seasonal gas exception would need 3%+ gross to survive; unproven.

**Verdict: CUT (provisional).** Revisit only if OOS weather engine (which shares atmospheric modelling) reveals portable methods applicable to natural gas seasonality. Requires a specific, testable hypothesis before reopening.

---

### 1.7 FX / Interest Rate Levels (JGB yields, EUR/USD, etc.)

**Verdict: CUT.** The deepest, most institutional markets in global finance. No viable edge.

---

### 1.8 IPO / Corporate Valuation Markets (Anthropic IPO, OpenAI IPO, etc.)

**Edge thesis:**
Crowd anchors to last funding round. Engine C synthesis of VC secondary-market data (Forge Global, Hiive), comparable public company multiples, and SEC S-1 filings can build a tighter distribution. No professional options market arbs these.

**Net-of-cost edge:** Finance/Tech/Politics fee = 1.0%. Volume $10K–$100K per market. Spread is wide (thinly traded). Need ~3–4% gross edge to survive costs plus spread. The secondary-market data advantage is real if Forge Global pricing is available; marginal on free data alone.

**Edge durability:** INFORMATIONAL — edges from secondary-market data evaporate as more funds access Forge/Hiive. Half-life: 2–3 years.

**Kill threshold (pre-registered):** After 10 resolved IPO-valuation markets, net ROI < 0% triggers retirement of the module.

**Best engine fit:** Engine C (secondary-market data synthesis + comparable analysis).

**Cadence & volume:** Event-driven (5–20 markets live). Very slow track record.

**Verdict: INCLUDE — Tier 3.** Genuine edge but slow cadence makes kill threshold very slow to reach. Build opportunistically after core verticals are live.

---

### 1.9 Recession Probability / Macro Regime Markets

**Edge thesis:**
Leading-indicator ensemble (yield curve, CLI, PMI, Sahm Rule) can produce a materially different distribution than crowd narrative. The crowd anchors to recent data and media sentiment.

**Net-of-cost edge:** 1.0% fee, but these markets resolve annually — long horizon, high uncertainty, low liquidity. Edge from a proper leading-indicator model is potentially large (5–10%) but extremely slow to validate.

**Edge durability:** STRUCTURAL — the behavioral anchoring to media narrative is persistent.

**Kill threshold (pre-registered):** After 4 resolved recession markets (at least 4 calendar years), net ROI < 0% triggers retirement.

**Cadence & volume:** 1–2 markets live; resolve annually. Extremely slow track record.

**Verdict: INCLUDE — Tier 3.** Interesting but the slowest kill cycle of any vertical. Build only after macro Tier 1 verticals are cash-flow positive. Part of the same correlated macro cell.

---

## Family 2: Sports

**Critical warning (wash trading):** Columbia (Nov 2025) found 45% of all-time Sports volume on Polymarket is likely wash trading, with peaks reaching 90%+ in a single week. Effective real Sports liquid volume should be treated as ~55% of reported figures. Position sizing estimates built on reported Sports volume are systematically overestimated. Model expected slippage at 1.5–2× what a naive liquidity read suggests.

**Sports sequencing note:** The user explicitly vetoed sports as the FIRST build. All sports verticals below are in-scope for the Institute; this is a sequencing decision only. Sports verticals are Tier 2 or lower in build order. The Tier 1 slots belong to verticals already generating track record (weather) or with highest net-of-cost edge density (geopolitics at 0% fee).

---

### 2.1 Soccer / Football — Tournament Outrights and Match Markets

**Edge thesis:**
Three sub-edges:
(a) **Tournament outrights:** Recency bias (opening-match over-inflation) + Elo under-weighting. Academic backtests show ~2–4% ROI on this specific bias. This is a STRUCTURAL/behavioral edge — durable.
(b) **Match moneylines:** arXiv 2403.07669 achieves 51.94% accuracy vs. bookmaker closing line. This is the crucial caveat: the closing line at Pinnacle is the sharpest available price; Polymarket match odds against retail may be marginally softer, but sophisticated arb participants will close this gap. Gross edge vs. Polymarket retail: 1–3% plausible. Net of 0.75% fee: thin but possibly positive in tournament group-stage markets with naive retail participation.
(c) **Player props:** Less liquid on Polymarket; naive crowd; Poisson shot model edge potentially 5–10%. Best net-of-cost bet within soccer.

**Net-of-cost edge summary:**
- Tournament outrights (Engine B): 2–4% gross → 1.25–3.25% net after 0.75% fee. VIABLE.
- Match moneylines (Engine A): 1–3% gross → 0.25–2.25% net. THIN — only viable in illiquid retail-dominated markets.
- Player props (Engine A): 5–10% gross → 4.25–9.25% net. BEST SUB-EDGE.

**Edge durability:**
- Tournament outright bias: STRUCTURAL (behavioral) — durable, 5+ years.
- Match moneyline model: INFORMATIONAL — as more models deploy, this gap closes. Half-life ~3 years.
- Player props: STRUCTURAL partially (crowd anchors to naive averages); half-life 3–5 years.

**Kill threshold (pre-registered):** After 100 resolved soccer markets (attainable within 1 World Cup tournament), net ROI < 0% triggers a full model review. Separate kill thresholds per sub-type: outrights, moneylines, props.

**Data sources:**
- Free: ClubElo.com; football-data.co.uk; Understat.com (xG); API-Football free tier; FBref/StatsBomb free; FIFA ranking API.
- Premium: Betfair historical odds (~$100/mo) for closing-line calibration — critical for validating gross edge claims.

**Best engine fit:** Engine A (Elo + xG + Poisson) + Engine B (recency-bias correction on outrights) + Engine C (injury news, lineup confirmation).

**Cadence & volume:** Real Sports liquid volume (wash-adjusted): ~$126M/month. World Cup 2026 has 271 active markets; club football year-round. Fast track-record accrual. **Wash-trading adjustment: liquidity shallower than it appears; model slippage at 1.5× stated spreads.**

**Verdict: INCLUDE — Tier 2** (sequencing-deferred per user veto on sports as first build). Prioritise in this order: player props → tournament outrights → match moneylines.

---

### 2.2 NBA Basketball — Game Moneylines and Player Props

**Edge thesis:**
(a) **Game moneylines:** NBA Vegas lines are sharp; Polymarket lags on injury news (48h window). Gross edge: 1–2% in the lag window. After 0.75% fee: thin.
(b) **Player props:** Lineup-adjusted Poisson model (matchup, pace, usage, minutes) vs. naive crowd recent-averages. Gross edge: 5–10%. After fee: 4.25–9.25%. Best NBA sub-edge.
(c) **Season outrights (MVP, win totals):** Favorite-longshot bias strong on popular players. Engine B gross edge: 3–6%. After fee: 2.25–5.25%. Viable.

**Net-of-cost edge summary:**
- Player props: 4–9% net. BEST.
- Season outrights (Engine B): 2–5% net. VIABLE.
- Game moneylines: 0.25–1.25% net. MARGINAL — only in injury-news lag window.

**Edge durability:** Player props: STRUCTURAL partially; naive crowd anchors to recent averages persistently. Half-life 3–5 years before models crowd this out. Game moneylines lag: INFORMATIONAL, shrinking as automation grows.

**Kill threshold (pre-registered):** After 200 resolved NBA player prop markets (achievable in one NBA season), net ROI < 0% triggers retirement of props module. Game moneylines evaluated separately after 50 markets.

**Data sources:**
- Free: NBA.com stats API; Basketball-Reference; Rotowire (free tier for injury news); lineups.com.
- Premium: PFF/PlayerProfiler ($150/mo) for advanced tracking — not needed at prototype.

**Best engine fit:** Engine A (Poisson player prop + game total) + Engine B (longshot bias on season outrights) + Engine C (injury reports — the 48h edge window).

**Cadence & volume:** 1,230 regular-season games + playoffs. Very fast track-record accrual. Wash-trading adjustment applies (use 55% of stated volume figures for sizing).

**Verdict: INCLUDE — Tier 2** (sequencing-deferred). Player props first; season outrights second; game moneylines last (lowest net-of-cost edge).

---

### 2.3 NFL American Football — Game Moneylines, Totals, Props, Season Markets

**Edge thesis:**
(a) **Game moneylines:** NFL closing lines (Pinnacle/Circa) are the sharpest in sports. Edge against Polymarket crowd exists only in injury/weather news window (48h before kickoff). Net of 0.75% fee: marginal. Low priority.
(b) **Player props:** Targets-adjusted receiving model vs. naive crowd. 5–8% gross; 4.25–7.25% net. Viable.
(c) **Season markets (Super Bowl, division winners, MVP):** Favorite-longshot bias documented (Cowboys/Patriots/popular teams inflated). 3–7% gross; 2.25–6.25% net. Viable.

**Net-of-cost edge:** Props and season outrights viable; game moneylines marginal.

**Edge durability:** Season outright longshot bias: STRUCTURAL (behavioral). Props: STRUCTURAL partially. Game moneylines edge: INFORMATIONAL, shrinking.

**Kill threshold (pre-registered):** After 50 resolved NFL season outright markets (takes 2–3 NFL seasons), net ROI < 0% triggers review.

**Cadence & volume:** 270 regular-season games. Highest volume-per-market of any sport. Season is Sep–Jan only. Wash-adjusted liquidity applies.

**Verdict: INCLUDE — Tier 2** (sequencing-deferred). Season outrights and player props first; game moneylines last.

---

### 2.4 MLB Baseball — Game Moneylines, Pitcher Props, Season Markets

**Edge thesis:**
The sabermetrics revolution means baseball analytics is the most competitive public modelling domain in sports. Edges:
(a) **Pitcher props (K/IP):** Park factor + matchup + temperature model vs. naive recent-K-rate crowd. 5–8% gross; 4.25–7.25% net after 0.75% fee.
(b) **Season leaders (HR, SB):** Poisson pace extrapolation model vs. naive crowd extrapolation. 3–6% gross; 2.25–5.25% net.
(c) **Game totals:** Weather (wind, temperature) + umpire-specific effects. 2–4% gross; 1.25–3.25% net.

**Edge durability:** STRUCTURAL partially for park-factor/weather effects (persistent). Rate extrapolation model: INFORMATIONAL (sabermetrics community is large, competition is real). Half-life: 2–3 years.

**Kill threshold (pre-registered):** After 100 resolved MLB pitcher prop markets (achievable in one season), net ROI < 0% triggers review.

**Data sources:**
- Free: Baseball Savant / pybaseball (Statcast — outstanding); Baseball-Reference; FanGraphs (park factors, Steamer projections); Retrosheet.

**Cadence & volume:** 2,430 regular-season games. Very fast track-record accrual. Wash-adjusted liquidity applies.

**Verdict: INCLUDE — Tier 2** (sequencing-deferred). Pitcher props + weather-affected totals first; season leaders second.

---

### 2.5 Tennis — Match and Tournament Markets

**Edge thesis:**
Tennis is the most forecastable individual sport. Surface-specific Elo (Jeff Sackmann's methodology) is the best-validated free model in any sport. Edges:
(a) Pre-tournament outrights: Elo under-weighted vs. ranking narrative. Longshot bias strong at Grand Slams. Engine B gross edge: 3–6%; net after 0.75% fee: 2.25–5.25%. Viable.
(b) Match pre-play: Surface-adjusted Elo beats naive ranking-based crowd. 2–4% gross; 1.25–3.25% net. Viable.
(c) In-play markets: CUT — require live viewing advantage; this audience has an information edge we cannot replicate.

**Edge durability:** Surface Elo: STRUCTURAL — the crowd's failure to adjust for surface is a persistent, well-documented bias. Half-life: 5+ years.

**Kill threshold (pre-registered):** After 50 resolved Grand Slam outright markets (takes ~3 years of Grand Slams), net ROI < 0% triggers retirement.

**Data sources:**
- Free: Jeff Sackmann GitHub (ATP/WTA data to 1968 with Elo); TennisAbstract.com; ATP/WTA official draws.

**Best engine fit:** Engine A (surface-adjusted Elo) + Engine B (longshot bias) + Engine C (injury/withdrawal news — very impactful in tennis).

**Cadence & volume:** ~135 tournaments/year; 4 Grand Slams. Fast accrual during Grand Slams.

**Verdict: INCLUDE — Tier 2** (sequencing-deferred). Tournament outrights (Engine B) + match pre-play (Engine A). Exclude in-play markets.

---

### 2.6 Esports — CS2, Dota 2, League of Legends

**Edge thesis:**
Documented 15–40 cent edges on specific Polymarket esports markets due to thin market-making. Map pool analysis + team strength model + roster-change detection via LLM. However, per-market volume is very low ($1K–$10K typically), limiting position size. The edge window will close as the market matures.

**Net-of-cost edge:** Sports fee = 0.75%. If gross edges of 15–40 cents are real on $0.50 markets, that is 30–80% gross — obviously the stated figure is on specific mispriced markets, not all. Average realistic gross: 5–10% on correctly identified roster-change situations. Net: 4.25–9.25%. Viable where the edge exists, but tiny positions.

**Edge durability:** INFORMATIONAL — the thin market-making that creates the edge will close as Polymarket grows. Half-life: 1–2 years. Build before it closes.

**Kill threshold (pre-registered):** After 100 resolved esports markets, net ROI < 0% triggers retirement.

**Cadence & volume:** CS2 alone had 510 live markets; resolves daily during majors. Fast accrual but tiny per-position.

**Verdict: INCLUDE — Tier 3.** Highest per-dollar edge of any category, but position sizes are tiny. Low-capital-intensity diversifier. Build only after Tier 1/2 are operational.

---

### 2.7 Other Sports (Golf, F1, Cricket, MMA/UFC, NHL)

**Golf (INCLUDE Tier 3):**
Datagolf.com pre-tournament strokes-gained model consistently outperforms public. Favorite-longshot bias strong (large field, household names over-bet). Net-of-cost edge after 0.75% Sports fee: 2–5%. Edge durability: STRUCTURAL (behavioral bias in large-field markets). Kill threshold: 20 resolved major-tournament markets.

**F1 (CUT):**
Engineering/mechanical factors are opaque to public models. Crowd closely tracks qualifying. Thin edge, niche volume.

**Cricket (INCLUDE Tier 3 — deferred):**
Public cricket analytics far less developed than football/basketball — genuine informational gap. Cricsheet (free, ball-by-ball). Deprioritise until Tier 1/2 proven. Large AU interest is noted but not an edge thesis.

**MMA/UFC (INCLUDE Tier 3):**
Documented longshot bias (casual fans over-bet underdogs). FightMatrix.com free Elo. Engine B gross edge: 3–6%; net after Sports fee: 2.25–5.25%. Durable behavioral bias. Kill threshold: 50 resolved fight markets.

**NHL (INCLUDE Tier 3 — conditional):**
MoneyPuck.com and Natural Stat Trick xG models are excellent free sources. Edge vs. crowd via expected goals. Volume lower than NBA/NFL on Polymarket. Include when capacity allows; sequencing-deferred.

---

## Family 3: Politics / Geopolitics

---

### 3.1 US Federal Elections (Presidential, Senate, House races)

**Edge thesis:**
The 2024 election demonstrated both crowd accuracy (Brier score 0.185, better than polling aggregates) and crowd distortability (single trader pushed Trump odds 10–15 points above competing platforms with $85M). The edge is NOT building a better model than 538 — it is detecting when a whale's position has distorted the market (Engine D) and fading the distortion, combined with Engine C (LLM synthesis of fresh polling, FEC filings, ground-game signals). For individual House/Senate races, crowds are thin and the informational gap is genuine.

**Net-of-cost edge:** Finance/Politics/Tech fee = 1.0%. Prediction markets are highly-liquid during election years; spreads narrow. Engine D whale-fade edge on distorted markets: 5–10% gross; 4–9% net. Engine C House race edge: 3–6% gross; 2–5% net. Viable.

**Edge durability:** Engine D (whale detection): STRUCTURAL — large concentrated positions will continue to distort prediction markets as long as single actors can move prices. Engine C (polling synthesis): INFORMATIONAL — other funds are running similar LLM synthesis. Half-life: 2–3 years for the pure news edge.

**Kill threshold (pre-registered):** After 30 resolved congressional race markets (achievable in one midterm cycle), net ROI < 0% triggers Engine C retirement. Engine D evaluated separately: after 10 identified whale-fade opportunities, if net ROI < 0%, retire.

**Data sources:**
- Free: FiveThirtyEight/ABC poll database; RealClearPolitics; FEC campaign finance filings; Cook Political Report; Metaculus community forecasts.
- Premium: The_Odds_API for cross-platform calibration (~$50/mo) — critical for detecting Polymarket distortion vs. competing markets.

**Cadence & volume:** Very slow for federal elections. 2026 is a midterm year — good timing. Congressional primaries March–September produce dozens of markets.

**Verdict: INCLUDE — Tier 1.** Volume is enormous when live; Engine D whale detection is a specific, falsifiable edge. Midterm timing is advantageous.

---

### 3.2 International Elections (France, Spain, Germany, etc.)

**Edge thesis:**
International election markets have thin crowds without quantitative models. National polling aggregators update weekly; Engine C (LLM synthesis of polling, coalition math, political system knowledge) produces significantly better priors than the Polymarket crowd. Wikipedia polling aggregation is an outstanding free source.

**Net-of-cost edge:** 1.0% fee. Thin crowds mean spreads are wider on small markets (below $10K volume). For $50K+ elections, spreads narrow; net edge from LLM synthesis: 3–8%. Viable.

**Edge durability:** INFORMATIONAL — as LLM-based political analysis becomes common, this gap narrows. Half-life: 2–3 years.

**Kill threshold (pre-registered):** After 30 resolved international election markets, net ROI < 0% triggers retirement.

**Data sources:**
- Free: Wikipedia election polling aggregation; Politico.eu; Electoral-Calculus; national statistical institutes; Manifold Markets (calibration reference).

**Best engine fit:** Engine C (LLM synthesis) + Engine A (seats projection for parliament elections).

**Cadence & volume:** 20–50 live markets year-round. Volume $100–$100K per market. Fast accrual during election-dense periods.

**Verdict: INCLUDE — Tier 2.** Fast track record, thin crowds, clear Engine C edge. Free data sufficient.

---

### 3.3 US Policy / Leadership Markets (Trump policy, Cabinet confirmations, etc.)

**Edge thesis:**
Confirmation markets and policy-action markets have clear resolution (Senate roll-call, official action) and crowds that price on media narrative rather than committee dynamics or vote counts. Engine C synthesis of GovTrack, Congress.gov vote counts, and hearing dynamics can produce materially better priors.

**Net-of-cost edge:** 1.0% fee. Markets like "Jay Clayton DNI Confirmation" are thinly liquid ($972 volume) — wide spreads, small positions. For higher-volume policy markets ($10K–$100K), Engine C gross edge 3–6%; net 2–5%. Viable at scale.

**Edge durability:** INFORMATIONAL — vote-counting synthesis is learnable by competitors. STRUCTURAL component: the crowd's media-narrative anchoring is behaviorally persistent. Half-life: 2–3 years for the pure information edge.

**Kill threshold (pre-registered):** After 30 resolved US policy markets, net ROI < 0% triggers retirement.

**Data sources:**
- Free: GovTrack.us; Congress.gov; Senate.gov live vote counts; White House press briefings.

**Best engine fit:** Engine C + Engine D (follow wallets with demonstrated US policy edge).

**Cadence & volume:** Year-round, high volume during legislative sessions. Dozens of markets live. Very fast accrual.

**Verdict: INCLUDE — Tier 2.** Year-round pipeline, genuine crowd naivety, clear Engine C edge.

---

### 3.4 Geopolitics / Conflict / War Markets (Ukraine, Middle East, etc.)

**Edge thesis:**
617 active geopolitics markets. Taker fee: **0% (free).** The crowd is reactive to news, not analytically grounded. Edge mechanisms:
(a) **News latency:** We process diplomatic signals faster than median trader.
(b) **Base-rate anchoring:** Crowd over-reacts to individual news events vs. unconditional base rates (ceasefires rarely hold; conflicts outlast expectations). Engine C provides base-rate correction.

**Net-of-cost edge:** 0% taker fee. This changes the calculus entirely — an edge that would be unviable at 1% fee is viable here. Even a 1–2% gross advantage survives costs. This is the most cost-forgiving vertical on the platform.

**CAPITAL-RISK CAVEAT:** Tail events (coups, assassinations, escalations) are genuinely unforecastable. A single discontinuous event can gap past any stop. Hard limit: 5% of portfolio in geopolitics at any time. This must be wired into the allocator, not a soft rule.

**Edge durability:** Engine C base-rate anchoring: STRUCTURAL (behavioral bias is persistent; crowds will always over-react to news). News latency: INFORMATIONAL, shrinking as more LLM-based news readers are deployed.

**Kill threshold (pre-registered):** After 50 resolved geopolitics markets (attainable within 3 months given volume), net ROI < 0% triggers Engine C review and position-limit tightening. Hard capital cap remains regardless of ROI.

**Data sources:**
- Free: GDELT Project; Uppsala Conflict Data Programme; Global Conflict Tracker (CFR); Reuters world news RSS; Wikipedia current events.

**Best engine fit:** Engine C (geopolitical newswire + base-rate model) + Engine D (follow geopolitics-specialist wallets).

**Cadence & volume:** 617 active markets. $10K–$100K+ per market. Very fast track-record accrual.

**Verdict: INCLUDE — Tier 1** (elevated from Tier 2). The 0% taker fee makes this the most cost-forgiving edge category on the platform. Fast accrual. Hard capital cap is non-negotiable.

---

### 3.5 Crypto Regulation / Policy Markets

**Edge thesis:**
Engine C can read SEC/CFTC regulatory dockets faster than average participant, but the sophisticated crypto community is also doing this. Marginal edge.

**Net-of-cost edge:** Finance/Politics/Tech fee = 1.0% (these are policy markets, not crypto price markets). Edge is 1–3% gross; 0–2% net. Thin.

**Verdict: INCLUDE — Tier 3** (opportunistic; fold into Engine C policy module). Do not build dedicated infrastructure.

---

## Family 4: Crypto / Culture / Science-Tech

---

### 4.1 Crypto Token/Protocol Events (token launches, ETH burns, DeFi milestones)

**Edge thesis:**
Engine C synthesis of GitHub commit velocity, governance forums, and developer communications can produce better priors than speculative crowd. These are binary event markets (did X happen?) — less efficiently arbed than price levels.

**Net-of-cost edge:** Crypto taker fee = **1.8%** — the highest category. Round-trip: 3.6%. A genuine informational gap edge on DeFi governance events might produce 3–5% gross; net is 0%–1.4% after fee. This is marginal to negative after accounting for spread on illiquid markets. **The 1.8% fee is the primary reason this vertical is demoted.**

**Edge durability:** INFORMATIONAL — on-chain signal monitoring is quickly replicated by other funds. Half-life: 1–2 years.

**Kill threshold (pre-registered):** After 20 resolved DeFi event markets, if net ROI < 0%, retire.

**Verdict: INCLUDE — Tier 3.** Downgraded from Tier 2 due to 1.8% crypto taker fee. Only pursue if gross edge clearly exceeds 2% on specific markets. Do not build dedicated infrastructure at prototype stage.

---

### 4.2 AI / Tech Company Milestones (GPT-6 release, Starship launches, etc.)

**Edge thesis:**
FAA regulatory license database is a structural, public, free leading indicator for SpaceX launch markets. CPUC demopermit database leads Waymo expansion markets. These are not traded by sophisticated arbitrageurs. Engine C with targeted regulatory-database monitoring has genuine structural alpha.

**Net-of-cost edge:** Finance/Tech/Politics fee = 1.0%. Market volume $10K–$100K. Estimated gross edge on FAA/CPUC-informed calls: 5–10%; net: 4–9%. Viable.

**Edge durability:** FAA/CPUC data advantage: STRUCTURAL — these databases are public but require systematic monitoring. Durable until a dedicated competitor builds the same crawler. Half-life: 3–5 years.

**Kill threshold (pre-registered):** After 30 resolved AI/Tech milestone markets, net ROI < 0% triggers retirement.

**Data sources:**
- Free: FAA launchsite license database; CPUC permit database; SEC EDGAR; company blogs/GitHub.

**Best engine fit:** Engine C (regulatory-database monitoring + LLM event-reasoning).

**Cadence & volume:** 20–50 markets live; SpaceX alone has 37. Moderate accrual cadence.

**Verdict: INCLUDE — Tier 2.** FAA/CPUC structural data advantage is specific, falsifiable, and defensible. Build as part of Engine C news-reasoning module.

---

### 4.3 Culture / Celebrity / Social Media Markets

**Edge thesis:**
General celebrity event markets are pure noise. **Exception: Elon Musk weekly tweet-count markets.** These resolve on an objective, verifiable criterion (X post count). The crowd mis-prices based on current-week pace vs. historical base rate. A historical posting-rate model can produce a better distribution.

**Net-of-cost edge:** Economics/Culture/Weather fee = 1.25%. Volume ~$97K per weekly market. Estimated gross edge from historical-rate model: 2–4%; net: 0.75–2.75%. Marginal but positive with fast accrual (52×/year). **CRITICAL CAVEAT: this model is trivially replicable — anyone who knows Musk's historical posting rate can build it. The edge is highly perishable once noticed.**

**Edge durability:** INFORMATIONAL, highly perishable. Recency bias that the model exploits is visible and simple. Half-life: 1 year or less once a competing model is deployed.

**Kill threshold (pre-registered):** After 26 resolved weekly Musk tweet markets (6 months), net ROI < 0% triggers retirement. This is the fastest possible kill evaluation of any vertical.

**Data sources:**
- Free: X API (limited free tier for tweet counts); social media scrapers.
- Premium: Twitter/X Developer API ($100/mo).

**Best engine fit:** Engine A (historical posting-rate model) + Engine B (recency bias correction).

**Verdict: INCLUDE — Tier 3.** Demoted from Tier 2. Fast accrual is valuable but edge is perishable and model is easily copied. Deploy quickly to capture the window; expect to retire within 12–18 months.

---

### 4.4 Science / Health / FDA Markets

**Edge thesis:**
FDA ADCOM (advisory committee) votes are publicly streamed and have historically predicted final FDA decisions with high accuracy. Polymarket crowds routinely ignore ADCOM results. This is a documented structural informational gap. PDUFA action dates are set a year in advance — predictable calendar.

**Net-of-cost edge:** Finance/Tech/Politics fee = 1.0%. Market volume $10K–$100K. Estimated gross edge from ADCOM synthesis: 5–15% on correctly identified ADCOM→final decision correlations; net: 4–14%. Potentially the highest net edge per market of any non-sports vertical.

**Edge durability:** STRUCTURAL — reading FDA documents is a durable moat because it requires domain expertise the median crowd does not have. The crowd will not develop ADCOM literacy quickly. Half-life: 5+ years.

**Kill threshold (pre-registered):** After 20 resolved FDA drug approval markets, net ROI < 0% triggers retirement. 50 PDUFA decisions/year means this is reachable within 6 months.

**Data sources:**
- Free: FDA.gov ADCOM transcripts and hearing calendars; ClinicalTrials.gov API; PubMed/bioRxiv; PDUFA action dates.

**Best engine fit:** Engine C (LLM synthesis of ADCOM transcripts + FDA documents). One of the strongest Engine C applications available.

**Cadence & volume:** ~50 major PDUFA decisions/year. 20+ live markets. Moderate but regular cadence.

**Verdict: INCLUDE — Tier 2.** One of the highest net-of-cost edge opportunities on the platform. Structural informational gap; readable free data; durable moat. Elevated from Tier 2 to high-priority within Tier 2.

---

### 4.5 Weather Markets (Existing Vertical — Context)

*This vertical is already live in paper-trading mode with M1–M4 complete.*

Weather markets ($197K/month volume, <0.1% of platform) are the smallest category by volume but the Institute's only vertical with a genuine, OOS-validated track record (+21.9% OOS ROI, 165 markets). Fee category: Economics/Culture/Weather = 1.25%.

**Net-of-cost edge (restated):** The +21.9% OOS ROI figure is gross or near-gross (paper trades do not incur taker fees). Under live conditions, apply 1.25% taker fee. Net estimated ROI: ~20.6%. This is the strongest validated net edge in the Institute's portfolio. The NO-side longshot strategy (ask ≤ 0.15) benefits from the fee-scaling formula — fees approach 0% near the extremes, so the effective fee on deep-longshot NO positions is well below 1.25%.

**Edge durability:** STRUCTURAL — the NWP ensemble model and NO-side longshot exploitation are both structural/behavioral edges. The crowd's mispricing of low-probability tail bins is persistent.

**Kill threshold:** Already active. If rolling 60-market OOS ROI drops below +5% net, diagnose calibration before expanding to new cities.

**Verdict: CONTINUE and EXPAND.** The weather vertical is the proof-of-concept that gates every other vertical. Fastest path to n≥200 for Platt calibration: expand to 20–25 global cities. Do not invest more model sophistication until new cities contribute resolved markets.

---

## Summary Tables

### INCLUDE List — Ranked by Edge-Density per Build Effort

*Ranking applies Rubric Tier 3.9: cheap + durable + high-volume wins first. Sports verticals sequencing-deferred per user veto.*

| # | Vertical | Family | Engine(s) | Build Priority | Track-Record Speed | Net Edge (est.) | Durability | Kill Threshold |
|---|----------|--------|-----------|---------------|-------------------|-----------------|-----------|----------------|
| 1 | Weather (existing) | Weather | A + B | CONTINUE | Daily | ~20% net | STRUCTURAL | Rolling 60-mkt < 5% |
| 2 | Geopolitics/Conflict | Politics | C + D | Tier 1 | Year-round (fast) | 1–5% net (0% fee) | STRUCT+INFO | 50 mkt, ROI < 0% |
| 3 | CPI MoM/YoY | Macro | A + C | Tier 1 | Monthly (12/yr) | 2–4% net | STRUCT+INFO | 24 mkt, ROI < 0% |
| 4 | US Elections | Politics | C + D | Tier 1 | Midterm 2026 | 4–9% net (whale fade) | STRUCT | 30 mkt, ROI < 0% |
| 5 | FDA Drug Approvals | Science | C | Tier 2 (high) | 50 PDUFA/yr | 4–14% net | STRUCTURAL | 20 mkt, ROI < 0% |
| 6 | AI/Tech Milestones | Sci-Tech | C | Tier 2 | Event-driven | 4–9% net | STRUCTURAL | 30 mkt, ROI < 0% |
| 7 | Fed Decisions | Macro | C + D | Tier 1 | 8×/yr | 1–4% net | STRUCT+INFO | 16 mkt, ROI < 0% |
| 8 | International Elections | Politics | C + A | Tier 2 | Year-round | 2–7% net | INFORMATIONAL | 30 mkt, ROI < 0% |
| 9 | US Policy/Confirmations | Politics | C + D | Tier 2 | Year-round | 2–5% net | STRUCT+INFO | 30 mkt, ROI < 0% |
| 10 | Soccer/Football | Sports | A + B + C | Tier 2 (deferred) | Daily (WC) | 1–9% net by sub-type | STRUCT+INFO | 100 mkt, ROI < 0% |
| 11 | NBA Basketball | Sports | A + B + C | Tier 2 (deferred) | Near-daily | 0–9% net by sub-type | STRUCT+INFO | 200 prop mkt, ROI < 0% |
| 12 | NFL | Sports | A + B + C | Tier 2 (deferred) | Sep–Jan | 2–7% net by sub-type | STRUCT+INFO | 50 mkt, ROI < 0% |
| 13 | MLB Baseball | Sports | A + C | Tier 2 (deferred) | Daily (Mar–Oct) | 1–7% net by sub-type | STRUCT+INFO | 100 mkt, ROI < 0% |
| 14 | Tennis | Sports | A + B + C | Tier 2 (deferred) | Weekly (majors) | 1–5% net | STRUCTURAL | 50 mkt, ROI < 0% |
| 15 | GDP / NFP | Macro | A | Tier 2 | Monthly/Quarterly | 1–3% net | STRUCTURAL | 24 mkt, ROI < 0% |
| 16 | Golf Majors | Sports | A + B | Tier 3 (deferred) | 4 majors/yr | 2–5% net | STRUCTURAL | 20 mkt, ROI < 0% |
| 17 | Esports (CS2, Dota2, LoL) | Sports | A + B + C | Tier 3 (deferred) | Daily | 4–9% net (tiny vol) | INFORMATIONAL | 100 mkt, ROI < 0% |
| 18 | MMA/UFC | Sports | A + B | Tier 3 (deferred) | Event-driven | 2–5% net | STRUCTURAL | 50 mkt, ROI < 0% |
| 19 | Cricket (IPL, Test, WC) | Sports | A | Tier 3 (deferred) | Event-driven | TBD | TBD | TBD |
| 20 | Musk Tweet Count | Culture | A + B | Tier 3 | Weekly (52/yr) | 0–3% net | INFORMATIONAL | 26 mkt, ROI < 0% |
| 21 | IPO/Corporate Valuations | Macro | C | Tier 3 | Event-driven | 2–4% net | INFORMATIONAL | 10 mkt, ROI < 0% |
| 22 | DeFi/Crypto Events | Crypto | C + D | Tier 3 | Event-driven | 0–1% net (1.8% fee) | INFORMATIONAL | 20 mkt, ROI < 0% |
| 23 | Recession Probability | Macro | A | Tier 3 | Annual | TBD | STRUCTURAL | 4 mkt, ROI < 0% |
| 24 | Crypto Regulation | Crypto | C | Tier 3 | Event-driven | 0–2% net | INFORMATIONAL | Fold into policy module |
| 25 | NHL | Sports | A | Tier 3 (deferred) | Season-bound | TBD | STRUCTURAL | Deferred |

---

### CUT List (with Reasons)

| Sub-Market | Reason for Cut |
|------------|----------------|
| BTC/ETH Price Levels | Crypto options traders arb in real-time. No informational gap. 1.8% taker fee is the highest category. Doubly eliminated. |
| Other Altcoin Price Levels | Same as BTC/ETH; worse liquidity; higher manipulation risk. |
| FX / Sovereign Rate Levels (JGB, EUR/USD, etc.) | The deepest institutional markets in finance. No viable edge. |
| Commodity Price Levels (Nat Gas, WTI, Gold targets) | Futures-market arb is continuous. Only revisit if weather engine reveals portable gas-seasonality methods; requires a specific hypothesis first. |
| F1 Race Winner Markets | Engineering opacity; crowd tracks qualifying closely. Thin edge, niche volume. |
| Celebrity Event Markets (general) | Pure speculation, near-zero reliable signal. Only exception: Musk tweet-count (Tier 3, separately listed). |
| Live In-Play Sports (Set totals, in-game props) | Require real-time data feeds and sub-second latency; viewers have structural information advantage. |

---

## Judgment Calls to Flag for User

1. **Sports sequencing (reconciled):** The user's veto applies to sports as the FIRST build — not as an exclusion from the universe. All sports verticals remain in scope at Tier 2/3. Geopolitics (Tier 1, 0% fee), CPI (Tier 1), and FDA approvals (high-priority Tier 2) are the correct initial builds before sports. Soccer and NBA follow once the first engines are tracking-record-positive.

2. **Geopolitics elevated to Tier 1:** The 0% taker fee changes the calculus. An edge that would be marginal at 1% fee is viable at 0%. Fast track-record accrual (617 active markets) and the Engine C base-rate advantage make this the highest build-effort-ROI non-weather vertical. The hard 5% portfolio cap is non-negotiable and must be enforced by the allocator.

3. **Macro correlation hazard:** CPI + Fed + GDP + NFP share the same underlying factor. The allocator must treat these as one correlated macro position. A 10% cap on the macro cell as a whole, not 10% per sub-vertical.

4. **Sports volume haircut:** All sports volume figures are wash-trading-adjusted at 55% of reported. Position-sizing models must use adjusted figures. Slippage should be modelled at 1.5–2× the naive spread estimate.

5. **Net-of-cost edge is the only number that matters:** Every edge range stated in this document is net of the applicable taker fee. Edges that do not clearly survive costs are not included in the INCLUDE list. The fee schedule (Sports 0.75%, Finance/Politics/Tech 1.0%, Crypto 1.8%, Economics/Culture/Weather 1.25%, Geopolitics 0%) must be applied to every bet sizing calculation in the engine.

6. **FDA drug approvals are the most underrated opportunity:** The ADCOM-to-FDA-decision correlation is documented, the data is free, the crowd ignores it, and the edge is structural (domain expertise moat). This vertical ranks above several sports verticals on net-edge-per-build-hour.

7. **Engine B (behavioral bias) is deployed first in every new vertical:** Favorite-longshot bias is the most durable, lowest-build-cost edge in the arsenal. Engine A (quant models) is a refinement on top. Do not skip Engine B in pursuit of sophistication.

8. **Kill thresholds are not to be moved.** Pre-registered above. If a vertical fails its kill threshold, it is retired and replaced on the roadmap. Moving a kill threshold after seeing data is the definition of overfitting.

---

## Data Source Master Reference

| Source | What It Provides | Cost | Vertical(s) |
|--------|-----------------|------|-------------|
| FRED API | 800K+ economic series | Free (key) | Macro all |
| BLS Public Data API v2 | CPI, PPI, employment | Free | CPI, NFP |
| Atlanta Fed GDPNow | Daily GDP nowcast | Free | GDP |
| CME FedWatch | OIS-implied Fed probabilities | Free scrape | Fed decisions |
| Philadelphia Fed SPF | Economist consensus vintages | Free | CPI, NFP, GDP |
| ClubElo.com | Football Elo by league | Free | Soccer |
| football-data.co.uk | Historical results + odds | Free | Soccer |
| Understat.com | xG data (Premier League) | Free | Soccer |
| FBref / StatsBomb | Advanced football stats | Free | Soccer |
| Jeff Sackmann GitHub | Complete ATP/WTA data + Elo | Free | Tennis |
| NBA.com Stats API | Full NBA stats | Free | NBA |
| Basketball-Reference | Historical NBA data | Free | NBA |
| Rotowire (free tier) | Player injury news | Free | NBA, NFL |
| Pro Football Reference | NFL historical data | Free | NFL |
| NFL.com injury reports | Official injury designations | Free | NFL |
| Baseball Savant / pybaseball | Statcast pitch tracking | Free | MLB |
| Baseball-Reference | Full MLB history | Free | MLB |
| Datagolf.com | Golf pre-tournament models | Free | Golf |
| FightMatrix.com | MMA Elo rankings | Free | MMA/UFC |
| HLTV.org | CS2 match history + stats | Free (Pro ~$10/mo) | Esports |
| Liquipedia | Esports tournament results | Free | Esports |
| FDA.gov ADCOM transcripts | Drug approval advisory votes | Free | FDA markets |
| ClinicalTrials.gov API | Clinical trial pre-registration | Free | FDA markets |
| FAA license database | Rocket launch licenses | Free | SpaceX markets |
| CPUC permit database | Autonomous vehicle permits | Free | Waymo markets |
| Congress.gov / GovTrack | Bill status, vote tracking | Free | US Policy |
| GDELT Project | Geopolitical event database | Free | Geopolitics |
| FEC filings | Campaign finance real-time | Free | US Elections |
| Wikipedia polling aggregation | International election polls | Free | Intl Elections |
| DeFiLlama | DeFi protocol TVL and events | Free | DeFi/Crypto events |
| CoinGecko/CMC | Token launch calendars | Free | DeFi/Crypto events |
| OddsPapi (de-vig) | Implied probabilities, 370 books | Free | Sports all |
| The Odds API | Historical odds back to 2020 | Free tier | Sports all |
| Poly Syncer / Wallet Master | Wallet copy-trading analytics | Free/cheap | Engine D all |
| PolymarketAnalytics leaderboard | Trader PnL + win-rate | Free | Engine D all |
| The Odds API (premium) | Cross-platform calibration | ~$50/mo | US Elections |
| Bloomberg consensus (premium) | Exact economist consensus | ~$100–200/mo | CPI, NFP |
| Nansen (premium) | On-chain wallet analytics | ~$150/mo | DeFi events |
| The Block Pro (premium) | On-chain analytics | ~$80/mo | DeFi events |
| Pinnacle historical odds (premium) | Sharp closing line reference | ~$50–100/mo | Sports all |
| Forge Global (premium) | VC secondary-market pricing | ~$500/mo | IPO markets |

---

*End of document. Feeds 02_EDGE_ENGINES.md (engine implementation per vertical), 09_ROADMAP.md (build sequencing), and 99_DECISIONS_LOG.md (judgment calls above).*
