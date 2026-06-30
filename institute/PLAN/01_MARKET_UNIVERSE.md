# The Institute — Market Universe Map
**Document:** 01_MARKET_UNIVERSE.md
**Status:** Research complete. Feeds build backlog in 09_ROADMAP.md.
**Authored:** 2026-06-30, R1 research agent (Sonnet). Reviewed by Opus before build.
**Sources:** Polymarket Gamma API (live probe, offsets 0–400), Defirate volume data, academic
literature (QuantPedia, SSRN, arXiv), platform analytics (Polycopy, PolymarketAnalytics),
DeFiRate category breakdown May 2026.

---

## Preamble: How to Read This Document

Each sub-market entry answers five questions in a consistent format:
1. **Edge thesis** — is the crowd beatable here, and *why* precisely?
2. **Data sources** — free tier (prototype) + premium upgrade (live launch).
3. **Best engine fit** — which of the 4 engines applies, and why.
4. **Cadence & volume** — market count, resolution frequency, track-record accrual speed.
5. **Verdict** — INCLUDE (tier 1/2/3) or CUT, with explicit reasoning.

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

### The volume baseline (Polymarket, May 2026, Defirate)
- Sports: ~33% of platform volume (~$230M/month)
- Politics/Gov: ~23% (~$156M/month)
- Finance/Fed/Macro: ~7% (~$47M/month); spiked to $736M in March 2026 (Fed event)
- Entertainment: ~3% (~$21M/month)
- Weather: <0.1% (~$197K/month)
- Other (crypto sub-markets, tech, geopolitics, culture): ~34% (~$238M/month)

Total platform volume: ~$690M/month in May 2026, up from ~$1B in peak months;
estimated $8–10B/month during high-volatility event periods (election, World Cup).

*Note: Columbia study estimates ~25% of historical Polymarket volume may be wash-trading.
Treat absolute dollar figures as directionally correct, not precise.*

---

## Family 1: Macro / Financial

### 1.1 CPI — Month-over-Month and Year-over-Year

**Edge thesis:**
The market crowd aggregates sell-side economist consensus (Bloomberg survey), which is
itself a diffuse average of models that vary primarily in how they weight shelter, energy,
and services components. Two systematic biases emerge: (a) analysts anchoring to the prior
month's print rather than re-weighting component trajectories, and (b) the crowd under-
updating on high-frequency sub-data available before the official BLS release (shelter
indices from ApartmentList/Zillow, gasoline price trackers, airfare trackers). An Engine A
model built on these leading sub-indicators can produce a tighter distribution than consensus
*before* the print, giving a clean edge on tail bins (e.g., "CPI MoM above 0.4%"). Academic
support: LLM-text-integration CPI models (arXiv 2506.09516) show untapped predictive signal
in news text; the B1 vertical we already have is the foundation of exactly this approach.

**Data sources:**
- Free: FRED API (free key; 800K+ series including CPI component history, PCE, PPI; Python
  `fredapi` library); BLS Public Data API v2 (CPI, PPI, employment costs; free, no key);
  ApartmentList National Rent Report (monthly, free); GasBuddy average price data (public);
  Bureau of Transportation Statistics airfare index (quarterly, free).
- Premium upgrade: Bloomberg consensus scrape via Unusual Whales or similar ($99–299/mo);
  Quandl/Nasdaq Data Link alternative data bundles (~$500/mo); point-in-time consensus
  vintages from MacroAxess (~$200/mo). These give us the exact consensus to bet against.

**Best engine fit:** Engine A (quant model) primary; Engine C (LLM text on BLS press
releases + shelter commentary) as a secondary signal to flag tail-event risk.

**Cadence & volume:** Monthly release (12/year); BLS releases CPI ~2 weeks after month-end.
Polymarket lists multiple bins per print (above/below X%, specific ranges). Approximately
10–20 live CPI markets visible at any time; resolves 12× per year. Track record: ~12 data
points/year — slow, but each is high-confidence if the model is good. The B1 vertical
already has this infrastructure started.

**Verdict: INCLUDE — Tier 1.** Already partially built (B1). Strongest quant edge in macro.
Resolution is clean, objective, public. Crowd beatable via sub-indicator models.

---

### 1.2 Federal Reserve Decisions (rate cuts / holds / hikes)

**Edge thesis:**
Fed decisions are among the most-forecasted events in global finance, yet the prediction
market crowd often lags the bond futures market's implied probability by 12–48 hours. Edge
is real but narrow: it exists in the *exact framing* of Polymarket questions (e.g., "25 bps
cut at September meeting?" vs what the OIS swap market is pricing). The crowd occasionally
misprices the tail options (a 50 bps cut when 25 is expected) and mis-times shifts after
Fed communication (FOMC minutes, speeches). Engine C (LLM parsing of Fed communications,
dot plot changes, Fed-speak sentiment) can detect these shifts slightly faster than the
median retail crowd. Volume is substantial — Fed markets spike dramatically around meeting
dates (Finance/Fed category spiked to $736M in March 2026). Smart-money copy-flow (Engine D)
also works here: certain wallets specialize in macro and are worth tracking.

**Data sources:**
- Free: FRED API (fed funds rate history, dot plot releases); Fed press release text (public
  FederalReserve.gov); CME FedWatch implied probabilities (free scrape); FedSpeak NLP via
  public press releases; FOMC calendar is published a year in advance.
- Premium upgrade: Bloomberg terminal access for real-time OIS swap pricing vs Polymarket
  implied probability (the gap is the trade); Refinitiv Eikon text feed.

**Best engine fit:** Engine C (LLM parsing Fed communications, dot plot) + Engine D (follow
macro-specialist wallets); Engine A (OIS vs Polymarket spread model) as a signal comparator.

**Cadence & volume:** 8 FOMC meetings/year. Volume spikes to $10M+ per market around
decision dates. Track record accrues 8×/year. Low cadence but very high volume per event.

**Verdict: INCLUDE — Tier 1.** High volume, clean resolution, Engine C + D both apply.
Medium-difficulty crowd (it's a liquid, well-forecasted event), but the framing-gap between
Fed futures and Polymarket wording is the specific edge to exploit.

---

### 1.3 GDP — Advance, Preliminary, and Final Estimates

**Edge thesis:**
GDP advance estimates are released by BEA ~28 days after quarter-end. The crowd consensus
(SPF, Bloomberg) is fairly accurate — GDP is harder to beat than CPI because it aggregates
across the entire economy. However, Polymarket markets tend to bin GDP into coarse buckets
(e.g., "Q2 GDP growth between 1.5–2.0%") where the tails are mispriced. The Philadelphia
Fed Survey of Professional Forecasters (SPF) provides a free high-quality consensus to bet
against — and the Nowcast models (Atlanta Fed GDPNow, NY Fed Staff Nowcast) update daily.
Edge = monitoring the nowcast divergence from the consensus and betting when the gap exceeds
the market's priced probability. Not a high-frequency edge; profitable only on clear
divergence signals.

**Data sources:**
- Free: BEA GDP release (public); Atlanta Fed GDPNow (free, updates daily during quarter);
  NY Fed Staff Nowcast (free, updates weekly); Philadelphia Fed SPF (free, quarterly);
  FRED API (all GDP history).
- Premium: Oxford Economics or IHS Markit consensus services (~$500+/mo). Nice-to-have but
  the free nowcast models often embed equivalent or better signal.

**Best engine fit:** Engine A (nowcast model: GDPNow vs Polymarket gap). Engine C marginal
(GDP reports are long and complex; LLM adds less incremental value than for CPI).

**Cadence & volume:** 4 releases/year (advance); very slow track record accrual.
Market volume much lower than Fed or CPI markets — niche within macro.

**Verdict: INCLUDE — Tier 2.** Legitimate edge (free nowcast signal is excellent), but low
cadence and lower volume than CPI/Fed markets. Build after CPI and Fed verticals mature.

---

### 1.4 Non-Farm Payrolls / Jobs Report

**Edge thesis:**
NFP is the most-watched US economic release and is notoriously difficult to forecast — the
series has high revision rates and the BLS sampling methodology introduces substantial noise.
However, the ADP National Employment Report (released 2 days before NFP) and Challenger
layoff data (released day before) provide leading signal. The crowd's consensus anchor is
the Bloomberg economist median, and that median systematically under-reacts to the direction
of ADP surprises. Specific edge: when ADP is strongly directionally divergent from consensus,
the market crowd under-adjusts the NFP bins. Resolution: the "above/below Xk" binary bins
on Polymarket.

**Data sources:**
- Free: BLS Employment Situation (public press release); ADP National Employment Report
  (free, Adpemploymentreport.com); Challenger Gray & Christmas layoff data (public); FRED
  API; Philly Fed SPF (forecast consensus).
- Premium: Bloomberg consensus survey vintages (the real edge is knowing the exact consensus
  and how much the market has already moved to price in ADP surprises).

**Best engine fit:** Engine A (ADP-to-NFP calibration model). Engine C marginal (layoff
news, strike announcements can move the print).

**Cadence & volume:** Monthly; moderate Polymarket volume (less than Fed decisions or CPI).
Track record: 12×/year. Similar cadence to CPI but harder to forecast.

**Verdict: INCLUDE — Tier 2.** Edge exists (ADP signal) but the series is noisy and the
crowd has partially learned the ADP-NFP relationship. Lower conviction than CPI; build after
Tier 1 macro verticals show positive ROI.

---

### 1.5 Cryptocurrency Price Levels (Bitcoin, Ethereum specific-date targets)

**Edge thesis:**
THIS IS A TRAP. Crypto price markets on Polymarket ("Will BTC be above $X on date Y?") are
among the highest-volume markets on the platform and the most efficient. Price-level
forecasting for BTC/ETH at specific dates is essentially equivalent to predicting a random
walk with high volatility — and the implied volatility embedded in the Polymarket price
strongly reflects the options market's view. There are professional crypto options traders
who actively arb this directly. The crowd here is NOT naive retail; it is crypto-native with
access to Deribit/Binance options pricing. Any edge from our models would be smaller than
the bid-ask spread plus slippage. Academic evidence: crypto prediction markets show highest
accuracy (94%+) precisely because they are the most heavily arbed by sophisticated players.

**Data sources:** Irrelevant — see CUT verdict.

**Best engine fit:** None viable. Options market is the correct comparison universe and it
already prices the crowd's information.

**Cadence & volume:** Very high cadence and volume (dozens of markets daily). But
efficiency wipes out the edge.

**Verdict: CUT.** The market is too efficient. Professional crypto options traders arb
the Polymarket crypto price markets in near-real-time. Our models cannot compete without
quantitative speed infrastructure that contradicts the "simplicity first" principle. The
only potential exception: extremely short-window (24h) markets on minor altcoins where
options arb is absent — but these have negligible volume. Skip the entire crypto price
sub-family.

---

### 1.6 Commodity Prices (Natural Gas, Crude Oil, Gold specific levels)

**Edge thesis:**
Similar to crypto price markets, but somewhat less efficiently arbed. Natural Gas ("Will
Henry Hub hit $3.00 in June?") and WTI/Brent crude price markets list with $100K+ volumes.
However, the same problem applies: commodity futures markets are liquid, HFT-dominated,
and the Polymarket prices strongly reflect the futures strip. The crowd here includes energy
traders who understand supply/demand better than our LLM. Edge is marginally possible on
seasonal gas markets when the EIA inventory release creates a known weekly information event.
Crude oil is more subject to geopolitical surprises (Engine C opportunity, but low R²).

**Data sources:** EIA weekly inventory reports (free); NOAA weather for gas demand
seasonality (free).

**Best engine fit:** Engine C (geopolitical shocks on crude), but thin edge.

**Cadence & volume:** High volume ($100K+/market) but very efficient against futures strip.

**Verdict: CUT (provisional).** The commodity price markets behave like the commodity
futures markets — they are efficient. No sustainable edge without access to proprietary
supply-chain data. Exception: if we find a specific seasonal or structurally mispriced gas
market, revisit as a Tier 3 target. Set a reminder to re-evaluate if the engine achieves
+ROI on weather, which shares some atmospheric modelling.

---

### 1.7 FX / Interest Rate Levels (JGB yields, EUR/USD, etc.)

**Edge thesis:**
CUT outright. FX and sovereign rate markets are arguably the most efficient in the world.
The Polymarket crowd on "Will 10-year JGB yield be ≥3.0%?" is priced against the JGB
futures market and the OIS swap curve, both of which are multi-trillion-dollar markets with
institutional participation. There is zero informational edge possible for a personal fund.

**Verdict: CUT.** Efficient — no viable edge.

---

### 1.8 IPO / Corporate Valuation Markets (Anthropic IPO at $1.75–2T, OpenAI IPO, etc.)

**Edge thesis:**
This is the most interesting and overlooked sub-market in the macro/financial family.
Polymarket lists corporate IPO markets ("Will Anthropic's market cap be between $1.75T–$2.0T
at IPO close?"; "OpenAI IPO Market Cap $1.5T+?") with volumes in the $10K–$100K range. The
crowd here is guessing. No professional options market exists for these events. The edge is
Engine C: LLM-driven synthesis of VC secondary-market data (Forge Global, Hiive), disclosed
funding round valuations, comparable public company multiples, and analyst commentary.
This is an informational gap — the crowd is anchoring to the last funding round; a model
that tracks secondary-market prices and comparable revenue multiples can build a tighter
distribution. These markets resolve at IPO close — timing uncertainty is high (the IPO date
itself is uncertain), but the valuation bucket markets are genuinely forecasting a
quantitative outcome.

**Data sources:**
- Free: Public funding announcements (TechCrunch, Bloomberg); CB Insights free tier;
  SEC S-1 filings (free, EDGAR); comparable public company multiples (Yahoo Finance free).
- Premium: Forge Global secondary-market pricing API (~$500/mo); PitchBook subscription
  (~$1000/mo). These give actual secondary-market transaction prices — the real moat.

**Best engine fit:** Engine C (LLM synthesis of comparable analysis + secondary data).

**Cadence & volume:** Event-driven (5–20 such markets live at any time); each resolves once.
Low cadence but high volume per market (~$10K–$100K). Track record accrues slowly.

**Verdict: INCLUDE — Tier 3.** Genuine edge opportunity but irregular cadence and the
timing uncertainty (will the IPO even happen this year?) makes it hard to accrue track
record. Build as an opportunistic Engine C module after core verticals are live.

---

### 1.9 Recession Probability / Macro Regime Markets

**Edge thesis:**
"Will the US enter recession by Q4 2026?" type markets. These are low-cadence (resolve
annually at most), but the edge is potentially strong: the crowd anchors to media narrative
and recent data, while a proper leading-indicator model (yield curve inversion, CLI,
PMI trajectory, unemployment Sahm Rule) can produce a meaningfully different distribution.
Metaculus community accuracy on macro regime questions significantly exceeds naive consensus.

**Data sources:** FRED API (all recession indicators free); Conference Board CLI (free);
ISM PMI (public releases).

**Best engine fit:** Engine A (leading-indicator ensemble). Slow-moving but the edge is
structural.

**Cadence & volume:** Very low cadence (1–2 markets live at any time, resolve annually).
Volume moderate ($10K–$100K). Track record accrual: extremely slow.

**Verdict: INCLUDE — Tier 3.** Interesting but slow to accrue track record. Build as an
add-on to the macro quant stack after CPI/Fed are proven.

---

## Family 2: Sports

*Volume context: Sports is Polymarket's largest category by volume at ~33% of platform
total (~$230M/month as of May 2026). The 2026 FIFA World Cup alone generated $3.5B+ in
total volume. This is the single largest addressable market for the Institute.*

---

### 2.1 Soccer / Football — Tournament Outrights and Match Markets

**Edge thesis:**
Football is the most-modeled sport in academic prediction literature and the most-traded
on Polymarket. Three distinct sub-edges exist:

(a) **Outright tournament markets (e.g., World Cup Winner):** The crowd exhibits a recency
bias — teams that win their opening match see their probability over-inflated, and pre-
tournament rank (FIFA rankings, Elo) is under-weighted vs. narrative. A pre-tournament
ELO-based model outperforms the opening odds on tournament outrights by ~2–4% ROI in
academic backtests (ResearchGate, 2024).

(b) **Match moneylines:** Football match outcomes are the most-studied prediction problem
in sports analytics. Best ML approaches (Gradient-boosted trees with xG, shot metrics,
Elo, form) achieve ~51.9% accuracy vs. ~51.5% for bookmaker-implied (arXiv 2403.07669).
The gap is narrow but real; it widens for weaker leagues and tournament group-stage upsets.

(c) **Player props (goals, cards, shots):** Much less liquid on Polymarket, but the crowd
is naive and the edge from a Poisson-based shot model can be large (10–20%).

**Data sources:**
- Free: ClubElo.com (free Elo ratings for all European leagues); football-data.co.uk
  (free historical results + implied odds back to 1993); Understat.com (xG data, free);
  API-Football free tier (basic fixtures/results); open-source `soccerway` and `worldfootball`
  scrapers; FBref (StatsBomb-derived free data for major leagues); FIFA ranking API (free).
- Premium: StatsBomb API (~$2000+/mo for premium xG/tracking); OptaPro (enterprise);
  Betfair historical odds (~$100/mo). The free tier is sufficient for prototype.

**Best engine fit:** Engine A (Elo + xG + Poisson ensemble for match and tournament markets).
Engine B (recency-bias correction on tournament outrights post-result). Engine C (LLM for
pre-match injury news, lineup confirmation, coach press conference sentiment).

**Cadence & volume:**
- World Cup 2026: 271 active markets, $3.5B+ total volume, $66M/day at peak. Enormous
  volume, fast resolution (daily/every 3 days during group stage).
- Club football: ongoing all year (Premier League, Champions League, Euros, Copa, MLS, etc.)
  — hundreds of markets weekly. Among the fastest track-record accrual of any vertical.

**Verdict: INCLUDE — Tier 1.** Single largest volume opportunity on the platform. Multiple
edge mechanisms. Fast track-record accrual. The free data infrastructure is excellent.
Build a dedicated Football vertical (Engine A + B hybrid). Start with World Cup tournament
outrights, then match moneylines for top 5 European leagues.

---

### 2.2 NBA Basketball — Game Moneylines and Player Props

**Edge thesis:**
NBA markets are heavily traded on Polymarket (Tier 2 volume). The crowd incorporates Vegas
lines within minutes, but three edge pockets exist:

(a) **Game moneylines / totals:** The NBA is relatively efficient because line movement on
Vegas is fast. Edge narrows to line-shopping situations (Polymarket price vs Pinnacle
consensus) and games with significant injury news where Polymarket lags the sharps.
Academic work (arXiv 2512.08591, LSTM on multi-season data; NCBI, XGBoost + SHAP) shows
models achieving 56–58% accuracy on game outcomes — not enormous but real.

(b) **Player props (points, rebounds, assists, steals O/U):** This is the most promising
NBA edge. The crowd sets player prop prices based on recent averages, but a lineup-adjusted
Poisson model (adjusting for matchup, pace, usage rate, minutes forecast) can systematically
outperform the naive crowd average. The NBA Prop Edge academic tool showed consistent
statistical edge in 24–25 season backtests.

(c) **Season-long markets (MVP, scoring leader, team win totals):** Favorite-longshot bias
applies here — superstar narrative drives over-betting on popular players. The Engine B
longshot-bias correction (already in our arsenal from weather) applies cleanly.

**Data sources:**
- Free: NBA.com stats API (free, comprehensive); Basketball-Reference.com (full historical
  data, free); basketball-reference injury tracker (free scraping); rotowire.com (free
  player news tier); lineups.com (free starting lineup confirmations).
- Premium: PFF/PlayerProfiler advanced player tracking ($150/mo); Synergy Sports
  (play-type level data, used by NBA teams, ~$500/mo). Not needed for prototype.

**Best engine fit:** Engine A (Poisson player prop model + game total model). Engine B
(longshot bias correction on season outrights). Engine C (LLM for injury reports, lineup
news — the most time-sensitive signal).

**Cadence & volume:** NBA season runs Oct–June with 82 games/team; ~1,230 regular season
games total plus playoffs. Hundreds of markets weekly during the season.

**Verdict: INCLUDE — Tier 1.** High volume, multiple edge pockets, very fast track-record
accrual. Player props specifically are the highest-edge sub-family. Co-priority with soccer.

---

### 2.3 NFL American Football — Game Moneylines, Totals, Props, Season Markets

**Edge thesis:**
NFL is the single most-traded sport in US prediction markets overall (though soccer may
rival it on Polymarket due to World Cup volume). Three edge zones:

(a) **Game moneylines / spreads:** NFL lines are sharp; closing lines at Pinnacle/Circa are
among the most efficient in sports. Edge against Polymarket crowd exists *around injury and
weather news* in the 48h before kickoff. A model that updates faster than the crowd on
QB injury status (often disclosed Wed–Sat) can capture a real but narrow window.

(b) **Player props:** Same as NBA — volume of available props is high, naive crowd prices
on recent averages. A targets-adjusted receiving prop model (WR targets vs. cornerback
matchup) shows documented edge in betting markets.

(c) **Season markets (Super Bowl winner, division winners, MVP):** Polymarket lists the
Arizona Cardinals 2027 NFC Championship market with $983K volume — very deep. These are
high-volume with slow resolution. Elo-based power ratings updated weekly beat the naive
consensus. Favorite-longshot bias is very strong on Super Bowl futures (public bets on
Cowboys/Patriots inflate their prices).

**Data sources:**
- Free: Pro Football Reference (free, comprehensive history); NFL.com injury reports (free,
  published Wed/Thu/Fri/Sat per NFL schedule); ESPN API (free unofficial); `nflreadr`
  Python package (free, official NFL data including Next Gen Stats summaries); Weather.gov
  for game-day conditions (free — wind/cold materially affects totals).
- Premium: Pro Football Focus (PFF) grades ($99/mo); Next Gen Stats official API (limited
  free tier). Not critical for prototype.

**Best engine fit:** Engine A (Elo + injury-adjusted model for game markets). Engine B
(longshot bias on Super Bowl / season outrights). Engine C (LLM injury report parser, the
48h edge window).

**Cadence & volume:** 18-week regular season (Sep–Jan) + playoffs = ~270 games + post.
Moderate cadence; highest volume per market of any sport. Off-season (Feb–Aug): season
outright markets only — lower cadence.

**Verdict: INCLUDE — Tier 2.** High volume and clear edge pockets, but the core game
markets are more efficient than soccer due to sharper Vegas lines. Deprioritize game
moneylines; prioritize season outrights (longshot bias) and props. Build after soccer/NBA.

---

### 2.4 MLB Baseball — Game Moneylines, Pitcher Props, Season Markets

**Edge thesis:**
Baseball is the most statistically sophisticated sport — the sabermetrics revolution (xFIP,
SIERA, wOBA, sprint speed) has produced the richest public free dataset of any sport.
However, this sophistication means the baseball betting market is also the most quantitatively
competitive. Edges:

(a) **Starting pitcher props (strikeouts, innings):** The crowd prices on recent K-rate, but
a model incorporating batters-faced, matchup BvP, temperature, and home/away ballpark (park
factors affect K-rate) can produce tighter distributions.

(b) **Season leaders (stolen base leader, home run leader, ERA leader):** Polymarket markets
like "Carson Benge MLB Stolen Bases Leader 2026" ($98K volume) and "Ben Rice MLB Home Runs"
appear consistently. These are genuinely hard to beat — variance is high — but a Poisson
rate model outperforms the naive crowd on pace extrapolation.

(c) **Game totals (runs O/U):** Weather (wind, temperature) and umpire-specific effects
create non-obvious edges. Rain/wind models improve totals accuracy significantly.

**Data sources:**
- Free: Baseball-Reference.com (complete free data); Statcast (MLB's free public pitch
  tracking database via Baseball Savant / pybaseball library — outstanding); FanGraphs
  (park factors, Steamer/ZiPS projections — free tier very good); Retrosheet.org (historical
  game logs, free).
- Premium: Statcast bulk API access via MLB Advanced Media ($300+/mo for commercial use,
  but the free public Baseball Savant covers most use cases).

**Best engine fit:** Engine A (Statcast-based pitcher/batter prop model). Engine B (pace
extrapolation biases in season markets). Engine C (injury news, trade deadline impacts).

**Cadence & volume:** 162 games/team × 30 teams = ~2,430 regular season games. Very fast
track-record accrual. Volume per game is lower than NFL but cadence is 10× higher.

**Verdict: INCLUDE — Tier 2.** Outstanding free data (Statcast is elite-grade). The
sabermetrics community is large, so competition is real. Best edge in pitcher props and
ballpark/weather-affected totals — the intersection of our weather vertical's expertise.

---

### 2.5 Tennis — Match and Tournament Markets

**Edge thesis:**
Tennis is the most forecastable individual sport by pure model performance. Elo-based tennis
models (TennisAbstract.com methodology, Jeff Sackmann's work) routinely outperform the
public. Key edge mechanisms: (a) surface-specific Elo (clay vs hard vs grass — massive
performance splits the crowd ignores), (b) player-specific hot/cold streaks vs. their serve
accuracy statistics, (c) the crowd over-weights world ranking and under-weights recent
form. Grand Slam tournament outrights exhibit extreme favorite-longshot bias at the tail
(e.g., a 200th-ranked player gets correct odds but a 30th-ranked player is systematically
undervalued relative to Elo).

**Data sources:**
- Free: Jeff Sackmann's tennis GitHub repository (the most comprehensive free tennis dataset
  in existence; all ATP/WTA matches back to 1968 with Elo ratings; github.com/JeffSackmann);
  TennisAbstract.com (free Elo ratings and match stats); ATP/WTA official websites
  (draws, results); on-court stats via Tennis Explorer (free scraping).
- Premium: IBM SlamTracker (official Grand Slam analytics, limited API); Tennis24.com
  (live in-match stats). Premium rarely needed given Sackmann data quality.

**Best engine fit:** Engine A (surface-adjusted Elo model — extremely well-validated in
literature). Engine B (longshot bias on Grand Slam outrights). Engine C (LLM for
injury/withdrawal news before and during tournaments, which is very high-impact in tennis).

**Cadence & volume:** ~70 ATP + ~65 WTA tournaments/year; 4 Grand Slams. Polymarket saw
substantial volume on Joao Fonseca 2026 US Open ($98K). Very fast track-record accrual
during Grand Slams (7 rounds, quick resolution).

**Verdict: INCLUDE — Tier 2.** Strong free data (Sackmann repository is elite), well-
validated model methodology, clear Engine A + B edges. Build after soccer/NBA. Note that
the within-tournament in-play markets (live Set totals like Taylor Townsend vs. Swiatek)
are lower-edge due to thin liquidity and the in-play information advantage going to viewers.
Focus on pre-match and pre-tournament outright markets.

---

### 2.6 Esports — CS2, Dota 2, League of Legends

**Edge thesis:**
Esports markets are the most mispriced family on Polymarket (15–40 cent edges documented)
because so few sophisticated market makers cover them. The forecastability driver: (a) map
pool analysis in CS2 (which maps teams veto/play — partially predictable from team history);
(b) team strength model using recent match results and roster stability; (c) individual
player performance consistency (CS2 has detailed free match statistics). The crowd prices
on recency (last match result) rather than stable team strength. However, tier-2 and tier-3
tournaments have very low volume (single-digit thousands), making position sizing tiny.

**Data sources:**
- Free: HLTV.org (CS2/CS:GO complete match database, stats, team rankings — the definitive
  source; free to scrape); Liquipedia (all esports tournament results, free wiki with API);
  Dota2ProTracker (Dota2 pro match stats, free); OP.GG and poke statistical sites (League
  of Legends, free).
- Premium: HLTV Pro subscription (faster data access, ~$10/mo — worth it); PandaScore
  API (esports data API, ~$100/mo; provides pre-match odds for cross-reference).

**Best engine fit:** Engine A (team Elo + roster-quality model). Engine B (recency bias
correction). Engine C (LLM for lineup/roster change news — very impactful in esports where
"stand-in" players dramatically affect outcomes).

**Cadence & volume:** CS2 alone had 510 live markets on Polymarket as of June 2026.
Tournaments run year-round. But individual market volume is low ($1K–$10K typically).
Multiple markets resolve daily during major tournaments.

**Verdict: INCLUDE — Tier 3.** Highest per-dollar edge of any category, but lowest dollar
volume. Position sizes are tiny. The edge is real and documented; build as a low-capital-
intensity diversifier after Tier 1/2 verticals are operational. The edge window may also
close as the market matures — build before it does.

---

### 2.7 Other Sports (Golf, F1, Cricket, MMA/UFC, NHL)

**Golf (INCLUDE Tier 3):**
Golf outrights and tournament winner markets are deeply affected by the favorite-longshot
bias (field markets where 1 player wins → strong bias toward household names). Datagolf.com
provides the best free strokes-gained-based predictive model; their pre-tournament
probabilities consistently outperform the betting market. Volume on Polymarket is moderate
($10K–$100K per major). Engine A (Datagolf-based model) + Engine B (longshot correction).

**F1 (CUT):**
Race winner and constructor championship markets are dominated by mechanical/engineering
factors that are opaque to public models, and the crowd tracks qualifying very closely.
Thin edge, niche volume.

**Cricket (INCLUDE Tier 3 — deferred):**
Cricket match markets (IPL, Test series, World Cup) list on Polymarket with meaningful
volume. The public cricket analytics community is much less developed than football/basketball,
creating a genuine informational gap. The Cricsheet database (free, ball-by-ball data) +
DuckworthLewis models give a foundation. Deprioritize until Tier 1/2 verticals are proven;
return for a dedicated cricket vertical.

**MMA/UFC (INCLUDE Tier 3):**
Fight markets have documented longshot bias (underdogs are over-bet by casual fans).
FightMatrix.com provides free Elo-style rankings. Low liquidity per market but consistent
behavioral bias. Build as part of Engine B rollout.

**NHL (INCLUDE Tier 3 — conditional):**
Hockey models (MoneyPuck.com, Natural Stat Trick) are high quality and free. Edge vs.
crowd exists via expected goals (xG) models. Volume on Polymarket is lower than NBA/NFL.
Include when capacity allows.

---

## Family 3: Politics / Geopolitics

### 3.1 US Federal Elections (Presidential, Senate, House races)

**Edge thesis:**
The 2024 election proved that prediction markets (specifically Polymarket at $340M+ volume)
achieved a Brier score of 0.185 on the presidential race — better than polling aggregates —
but were also subject to manipulation by a single trader with $85M who pushed Trump odds
10–15 points above competing platforms. This duality is the key insight: the crowd is
*sometimes* well-calibrated and *sometimes* heavily distorted by whale concentration.
The edge here is not building a better model than 538 — it is Engine D (detecting when a
whale's position is distorting the market) combined with Engine C (LLM synthesis of fresh
polling data, fundraising FEC filings, and ground-game signals). For individual House and
Senate races, the crowd is thin (low volume, few sophisticated traders), creating a genuine
informational gap that Engine A (district-level fundamentals model) + Engine C can exploit.

**Data sources:**
- Free: FiveThirtyEight/ABC News poll database (free); RealClearPolitics averages (free);
  FEC campaign finance filings (free, real-time EDGAR-equivalent); Cook Political Report
  district ratings (free); Decision Desk HQ historical results (free tier); Metaculus
  community forecast (free, historically well-calibrated).
- Premium: Catalist/L2 voter file access (the real moat — ~$5000/mo for commercial; skip
  at prototype). The_Odds_API for cross-platform calibration (~$50/mo).

**Best engine fit:** Engine C (LLM synthesis of polling, finance, ground news) for federal
elections. Engine D (whale detection; follow sophisticated wallets that specialize in politics).
Engine A (district fundamentals model for House races).

**Cadence & volume:** Presidential elections every 4 years (massive volume: $340M+), midterms
every 2 years (~$50M+), special elections irregularly. Congressional primary season
(March–September in election years) produces dozens of markets with moderate volume.
Track record accrues slowly on federal elections — mainly midterm and special election cycles.

**Verdict: INCLUDE — Tier 1 (but with caveats).** Volume is enormous when live. Key caveat:
the track record accrual is very slow except in election years (2026 is a midterm year —
good timing). The whale manipulation risk is real; Engine D is essential to detect when the
market price is distorted vs. where we should actually set our prior.

---

### 3.2 International Elections (France, Spain, Germany, Italy, Peru, etc.)

**Edge thesis:**
International election markets (French presidential at $999, Spanish PM at $9.7K, Peruvian
election at $95K) have thin crowds — mostly driven by politically-interested speculators
without quantitative models. The informational edge is large: national polling aggregators
(France: BFM TV tracking; Spain: El País sondeos) update weekly, and the crowd is not
systematically aggregating them. Engine C (LLM synthesis of international polling, coalition
formation likelihood, political system knowledge) can produce significantly better priors
than the Polymarket crowd on non-US elections.

**Data sources:**
- Free: Wikipedia election pages (outstanding free aggregation of polling data); Politico.eu
  (European election tracking, free); Electoral-Calculus (UK elections, free); national
  statistical institutes (free for all OECD countries); The Guardian elections section;
  Manifold Markets (free calibration reference).
- Premium: Oxford Analytica election risk reports (~$200/report); national polling agency
  APIs. Not critical at prototype.

**Best engine fit:** Engine C (LLM synthesis of international political landscape, polling
aggregation, coalition math). Engine A (seats projection model for parliament elections).

**Cadence & volume:** International elections happen year-round across 195 countries.
At any given time, 20–50 election markets are live on Polymarket. Volume per market ranges
from $100 (low-tier) to $100K+ (major elections like France, UK, Germany). Track record
accrues consistently throughout the year.

**Verdict: INCLUDE — Tier 2.** Fast track-record accrual, thin crowds, clear LLM synthesis
edge. The free data (Wikipedia polling aggregation + LLM reasoning) is sufficient.

---

### 3.3 US Policy / Leadership Markets (Trump policy actions, Cabinet confirmations, etc.)

**Edge thesis:**
Markets like "Jay Clayton DNI Confirmation" ($972), "Trump Gold Card Sales" ($9.8K), and
"Dwayne Johnson Presidential Run" ($9.8K) are high-noise, low-information markets where
the crowd guesses based on media narrative. These are the most Engine C-friendly markets:
LLM synthesis of official statements, congressional vote counts, committee outcomes, and
political dynamics can produce much better priors than the speculative crowd. The Polymarket
volume on US policy markets is substantial — these are live year-round (not just election
years). Confirmation markets in particular have clear resolution (Senate roll-call vote)
and the crowd's price often diverges from the actual committee hearing dynamics.

**Data sources:**
- Free: GovTrack.us (congressional vote tracking, real-time, free); Congress.gov (bills,
  amendments, hearing schedules, free); Senate.gov live vote counts; White House press
  briefings (public); major news LLM synthesis.
- Premium: CQ Roll Call ($500+/mo); Bloomberg Government — useful for vote-counting but
  not essential at prototype when Engine C can synthesize public news.

**Best engine fit:** Engine C (LLM synthesis of political dynamics, vote counting, statement
parsing). Engine D (follow wallets with demonstrated edge on US policy markets).

**Cadence & volume:** Year-round, high volume during legislative sessions. Dozens of markets
live at any time. Very fast track-record accrual.

**Verdict: INCLUDE — Tier 2.** Year-round pipeline of markets, genuine crowd naivety,
clear Engine C edge. Build as part of the politics vertical alongside elections.

---

### 3.4 Geopolitics / Conflict / War Markets (Ukraine, Middle East, etc.)

**Edge thesis:**
Geopolitics markets ("Russia x Ukraine ceasefire by March 31?"; "Will France send warships
through Strait of Hormuz?") have enormous volume ($99K–$100K per market) and genuinely
uncertain outcomes. The crowd's prior is largely based on recent news — events in the last
48 hours dominate. The edge mechanism here is *not* superior geopolitical modeling (no one
can reliably predict geopolitical discontinuities), but rather: (a) **news latency** — we
process diplomatic signals, official statement changes, and second-order reporting faster
than the median trader; (b) **base-rate anchoring** — the crowd over-reacts to individual
news events relative to the unconditional base rate (ceasefires rarely hold; conflicts
outlast expectations). Engine C (LLM digest of geopolitical newswire + base-rate correction)
is the mechanism.

However, these markets also have a known failure mode: tail events (coups, assassinations,
escalations) are truly unforecastable, and our Engine C can get badly caught on wrong side
of a discontinuity. Risk management is essential (hard position limits, never build
conviction >55% on pure geopolitical bets).

**Data sources:**
- Free: GDELT Project (free, massive geopolitical event database, near-real-time);
  Uppsala Conflict Data Programme (UCDP, free historical conflict database); Global
  Conflict Tracker (CFR, free); Reuters world news RSS feeds (free); Wikipedia current
  events (surprisingly useful for breaking news timing).
- Premium: Stratfor or Oxford Analytica intelligence reports (~$300/mo each). Worth
  considering at live launch for conflict markets, as these services embed intelligence
  professionals.

**Best engine fit:** Engine C (LLM synthesis of geopolitical newswire + base-rate model).
Engine D (follow wallets with documented geopolitics edge).

**Cadence & volume:** 617 active geopolitics markets on Polymarket as of mid-2026. Very
high volume per market ($10K–$100K+). Fast resolution on some (weekly ceasefire markets)
and slow on others (annual conflict-end markers). Very fast track-record accrual.

**Verdict: INCLUDE — Tier 2.** High volume, genuine crowd naivety (crowd is reactive to
news not analytically grounded), clear Engine C opportunity. **Capital-risk caveat:** hard
limit to 5% of portfolio in geopolitics at any time; tail events can gap past any stop.

---

### 3.5 Crypto Regulation / Policy Markets

**Edge thesis:**
Markets like "Will SEC approve spot ETH ETF by Q3?" or crypto-specific regulatory questions.
The crowd here is crypto-native and heavily attuned to the regulatory newsflow. Engine C
can read regulatory filings and CFTC/SEC docket updates faster than the average participant,
but the sophisticated crypto community is also doing this. Moderate edge, not priority.

**Verdict: INCLUDE — Tier 3** (opportunistic; fold into Engine C policy module).

---

## Family 4: Crypto / Culture / Science-Tech

### 4.1 Crypto Token/Protocol Events (token launches, ETH burns, DeFi milestones)

**Edge thesis:**
Markets like "OpenSea Token Launch by Sep 30" ($96K volume) are information-gap markets:
the crowd doesn't track GitHub commit velocity, protocol governance forums, or developer
blog posts as closely as a dedicated crawler. Engine C (LLM synthesis of on-chain governance
votes, project Discord/GitHub signals, core team communications) can produce better priors
than the speculative crowd. These are different from price markets — they're binary event
markets (did X happen?) which are much less efficiently arbed than price levels.

**Data sources:**
- Free: Protocol GitHub repositories (public); DeFi project forums and governance portals
  (free); The Block (free tier for on-chain analytics); DeFiLlama (protocol TVL and event
  tracking, free); CoinGecko/CoinMarketCap (token launch calendars, free).
- Premium: The Block Pro ($80/mo); Nansen on-chain analytics ($150/mo). Premium is worth
  it for detecting smart-money wallet movements into a protocol pre-event.

**Best engine fit:** Engine C (LLM synthesis of on-chain signals, governance news, developer
activity). Engine D (on-chain whale flow into a protocol often precedes its governance events).

**Cadence & volume:** 10–30 such markets live at any time; each resolves on its specific
event date. Volume ranges from $10K to $100K. Track record accrual: moderate cadence.

**Verdict: INCLUDE — Tier 2.** Genuine informational gap (crowd is not tracking developer
signals). Scalable via Engine C with DeFi-specific news corpus.

---

### 4.2 AI / Tech Company Milestones (GPT-6 release, Starship launches, etc.)

**Edge thesis:**
Markets like "GPT-6 Released by July 31, 2026" ($9.5K), "SpaceX Starship Flight Test 13"
($9.6K), and "Waymo Launch Sacramento by Dec 31" ($96K) are information-gap markets where
the crowd guesses based on public announcements and hype cycles. Edge:
(a) For AI model releases: OpenAI/Anthropic/Google blog posts, SEC filings, and employee
LinkedIn activity patterns telegraph release timing better than the crowd's naive anchoring.
(b) For SpaceX launches: the FAA regulatory license database is public; orbital mechanic
constraints are known. An Engine C model monitoring FAA filings can significantly outperform
the crowd on launch date markets.
(c) For autonomous vehicles: the CPUC demopermit database tracks Waymo/Cruise commercial
permits — a direct leading indicator.

**Data sources:**
- Free: FAA launchsite license database (free, public); FCC filings (free); SEC EDGAR
  (free); Company blogs/X/GitHub (free LLM monitoring); CPUC permit database (free).
- Premium: None essential; quality of free data here is high.

**Best engine fit:** Engine C (LLM monitoring of regulatory filings, company announcements,
technical constraints). This is a pure news/event-reasoning play.

**Cadence & volume:** 20–50 tech milestone markets live at any time. Variable volume ($10K
to $100K). Track record accrual: moderate. Polymarket lists SpaceX with 37 active markets.

**Verdict: INCLUDE — Tier 2.** Clear Engine C informational gap. FAA data for SpaceX is
a specific structural alpha source. Build as part of the Engine C news-reasoning module.

---

### 4.3 Culture / Celebrity / Social Media Markets

**Edge thesis:**
Markets like "Phoebe Bridgers attend Taylor Swift's wedding?" ($99), "Elon Musk Tweet
Volume" ($97K–$97K weekly), and "Will Dwayne Johnson announce presidential run?" ($9.8K).
Volume varies enormously. The Elon Musk tweet-count markets specifically are fascinating:
the resolution is based on objective, verifiable data (X post count in a time window) and
the crowd misprices based on Musk's most recent activity rather than his base-rate posting
velocity. An Engine A model that tracks Musk's historical posting patterns (currently
averaging 15–20 tweets/day with high variance) can produce a better distribution for the
weekly bins than the crowd's naive reading of the current-week pace.

More broadly, celebrity event markets are low-volume and mostly noise. The Musk posting
markets are the exception — they are high-volume ($97K), resolve weekly, and have a
quantitative resolution criterion.

**Data sources:**
- Free: X API (limited free tier with tweet counts); social media scrapers; celebrity
  news aggregators.
- Premium: Twitter/X Developer API for full volume data ($100/mo basic).

**Best engine fit:** Engine A (Musk posting rate model — specific, quantitative, tractable).
Engine B (recency bias in celebrity event markets). For general celebrity markets: CUT.

**Cadence & volume:** Musk tweet markets resolve weekly (52×/year — fastest track-record
accrual of any non-sports vertical). High volume per market ($97K). Other celebrity
markets: low volume, low priority.

**Verdict: MIXED.** Musk tweet-count weekly markets: INCLUDE — Tier 2 (weekly resolution,
high volume, behavioral bias, trackable quantitative signal). General celebrity event
markets (weddings, announcements): CUT (too speculative, too low volume, no reliable
signal). The Musk posting model is an opportunistic early win with very fast track-record
accrual.

---

### 4.4 Science / Health / FDA Markets

**Edge thesis:**
FDA drug approval markets, vaccine effectiveness markets, and clinical trial outcome markets
are information-dense: the crowd guesses based on media coverage, while a model that reads
FDA advisory committee meeting documents, PduFACA hearing transcripts, and Phase 3 trial
endpoint pre-registrations on ClinicalTrials.gov can produce dramatically better priors.
Academic evidence: FDA advisory committee votes (ADCOM) are publicly streamed; in 2023–2024,
the ADCOM vote nearly always predicted the final FDA decision, but Polymarket crowds often
ignored ADCOM results entirely. This is a documented informational gap.

Similarly, science milestone markets ("Will JWST detect biosignatures?", "First artificial
womb approval?") are pure Engine C plays — the crowd's prior is heavily anchored to
media hype, while a structured science-reading model produces more accurate base rates.

**Data sources:**
- Free: FDA advisory committee calendars and meeting transcripts (FDA.gov, free);
  ClinicalTrials.gov (complete trial registry, free API); PubMed/bioRxiv (free preprint
  access); PDUFA action dates (free from FDA website — this is the resolution trigger).
- Premium: BioPharm Catalyst or Evaluate Pharma for commercial drug pipeline analytics
  (~$500+/mo). Not needed at prototype; free FDA sources are excellent.

**Best engine fit:** Engine C (LLM synthesis of FDA documents, ADCOM transcripts,
clinical trial pre-registrations). One of the strongest Engine C opportunities available.

**Cadence & volume:** FDA PDUFA dates are set a year in advance (predictable calendar);
~50 major PDUFA decisions/year. Polymarket science category has 20+ live markets.
Volume per market: $10K–$100K for major drug approvals.

**Verdict: INCLUDE — Tier 2.** Strong informational gap (FDA documents are public but
complex; the crowd doesn't read ADCOM transcripts). Clean resolution criterion. Build
as part of Engine C deployment.

---

### 4.5 Weather Markets (Existing Vertical — Context)

*Note: Weather is already the Institute's most mature vertical (M1–M4 complete, Engine A
with 6-model NWP ensemble + NO-side longshot correction). This section provides context
for positioning within the broader universe.*

Weather markets ($197K/month volume, <0.1% of platform) are the smallest category by
volume but the Institute's strongest demonstrated edge (+21.9% OOS ROI). The value is:

(a) This is the **calibration baseline** — 165 markets resolved with documented P&L, OOS
tested, making it the only vertical with genuine track record evidence.
(b) The skills transfer: temperature uncertainty quantification → probabilistic bins;
RMSE-weighted ensemble → how to handle ensemble disagreement in any domain; NO-side
favorite-longshot exploitation → applicable to all domains. Weather is the blueprint.
(c) Volume is low but growing as expansion cities add markets. Expansion path: add 10–15
more global cities to generate volume and track-record data faster.

**Verdict: CONTINUE and EXPAND.** Expand cities roster; the weather vertical is the proof
of concept that gates every other vertical. Fastest path to the 200-market n threshold
for Platt calibration deployment is to expand city coverage.

---

## Summary Tables

### INCLUDE List (Build Order)

| # | Vertical | Family | Engine(s) | Priority | Track-Record Speed | Notes |
|---|----------|--------|-----------|----------|--------------------|-------|
| 1 | CPI MoM/YoY | Macro | A + C | Tier 1 | Monthly (12/yr) | B1 already started |
| 2 | Fed Decisions | Macro | C + D | Tier 1 | 8×/yr | High per-event volume |
| 3 | Soccer/Football | Sports | A + B + C | Tier 1 | Daily (WC) / Weekly | Single largest volume opportunity |
| 4 | NBA Basketball | Sports | A + B + C | Tier 1 | Near-daily | Player props = highest edge density |
| 5 | US Elections | Politics | C + D | Tier 1 | Event-driven | 2026 = midterm year — good timing |
| 6 | International Elections | Politics | C + A | Tier 2 | Year-round | Thin crowds, big LLM edge |
| 7 | US Policy/Confirmations | Politics | C + D | Tier 2 | Year-round | Week-to-week Congress pipeline |
| 8 | Geopolitics/Conflict | Politics | C + D | Tier 2 | Year-round | Hard capital cap (5%) |
| 9 | NFL | Sports | A + B + C | Tier 2 | Sep–Jan | Season outrights + props |
| 10 | MLB Baseball | Sports | A + C | Tier 2 | Daily (Mar–Oct) | Statcast data is elite |
| 11 | Tennis | Sports | A + B + C | Tier 2 | Weekly (majors) | Sackmann dataset = gold standard |
| 12 | AI/Tech Milestones | Sci-Tech | C | Tier 2 | Event-driven | FAA/FDA data is structural alpha |
| 13 | DeFi/Crypto Events (non-price) | Crypto | C + D | Tier 2 | Event-driven | Not price markets — information gap |
| 14 | Musk Tweet Count (weekly) | Culture | A + B | Tier 2 | Weekly (52/yr) | High volume, fast track record |
| 15 | GDP / NFP | Macro | A | Tier 2 | Monthly/Quarterly | Nowcast model is the edge |
| 16 | IPO/Corporate Valuations | Macro | C | Tier 3 | Event-driven | Irregular cadence |
| 17 | Esports (CS2, Dota2, LoL) | Sports | A + B + C | Tier 3 | Daily | Highest per-dollar edge; tiny volume |
| 18 | Recession Probability | Macro | A | Tier 3 | Annual | Low cadence but structural signal |
| 19 | Golf Majors | Sports | A + B | Tier 3 | 4 majors/yr | Datagolf model is documented |
| 20 | Cricket (IPL, Test, WC) | Sports | A | Tier 3 | Event-driven | Emerging analytics, big AU interest |
| 21 | MMA/UFC | Sports | A + B | Tier 3 | Event-driven | Longshot bias + Elo model |
| 22 | FDA Drug Approvals | Science | C | Tier 2 | ~50 PDUFA/yr | ADCOM transcript gap is real |
| 23 | Crypto Regulation | Crypto | C | Tier 3 | Event-driven | Fold into C policy module |

---

### CUT List (with Reasons)

| Sub-Market | Reason for Cut |
|------------|----------------|
| BTC/ETH Price Levels | Crypto options market arbs the Polymarket price in real-time. No informational gap; no model edge possible at our scale. |
| Other Altcoin Price Levels | Same as BTC/ETH, with the added risk of worse liquidity and manipulation. |
| FX / Sovereign Rate Levels (JGB, EUR/USD, etc.) | The deepest, most efficient markets in finance. No possible edge. |
| Commodity Price Levels (Nat Gas, WTI, Gold targets) | Futures markets arb these continuously. Only exception: seasonal gas with EIA event — revisit as Tier 3 opportunistic. |
| F1 Race Winner Markets | Machine/team engineering opacity; crowd closely tracks qualifying. Thin edge, niche volume. |
| Celebrity Event Markets (general) | Pure speculation, near-zero reliable signal. Not worth model capacity except Musk tweet-count. |
| Live In-Play Sports (Set totals, in-game props) | Require real-time data feeds and sub-second latency; defeat the "simplicity first" principle. Crowd has information advantage from live viewing. |
| NHL (deferred, not cut) | Good models exist but Polymarket volume is lower priority. Revisit after Tier 1/2 are proven. |

---

## Judgment Calls to Flag for User

1. **Soccer vs. NBA priority sequencing:** Both are Tier 1 and co-priority. The World Cup
   (currently live on Polymarket with $3.5B+ volume and 271 markets) is a once-in-4-years
   volume event happening right now. Soccer should be the first sports vertical built;
   NBA follows for the regular season cycle beginning October.

2. **Engine D (smart money) deployment timing:** Wallet copy-flow tools (Poly Syncer, Wallet
   Master, PolymarketAnalytics leaderboard) are functional and free-to-cheap. However, the
   whale manipulation risk (single wallet pushing Trump odds 10–15 points) means Engine D
   should be used as a *counter-signal* (detect distorted markets, fade the whale) as much
   as a follow-signal. Design the Engine D module to flag high whale concentration before
   entering, not just after identifying a good wallet.

3. **Geopolitics capital cap:** Geopolitics markets ($97K–$100K volume) are tempting but
   carry genuine tail-event blowup risk. The recommended hard limit is 5% of portfolio in
   geopolitics at any time. This needs to be wired into the allocator, not just a soft rule.

4. **Weather vertical: expand or plateau?** The current weather vertical generates <0.1% of
   platform volume. The fastest path to the n≥200 Platt calibration threshold is expanding
   city coverage. However, expanding cities does not increase per-city depth, just breadth.
   Recommendation: expand to 20–25 global cities immediately; do not invest more model
   sophistication until the new cities contribute resolved markets.

5. **Track-record accrual bottleneck:** The 7-gate pipeline requires a statistical track
   record before going live. The fastest-accrual verticals are: weather (daily, expanding
   cities), Musk tweet markets (weekly), soccer match markets (multiple daily during World
   Cup). Prioritize these in Year 1 paper-run specifically to hit the n≥200 threshold per
   vertical faster.

6. **Favorite-longshot bias remains the Institute's most reliable edge:** This is confirmed
   across weather (NO-side, 8/8 wins), academic research (Kalshi, Polymarket structural
   evidence), and every sports domain studied. Engine B should be the first engine deployed
   in every new vertical as a baseline; Engine A models are refinements on top. Do not
   deprioritize the simple behavioral bias play in pursuit of sophisticated quant models.

7. **Premium data sequencing:** At live launch (real money), the highest-priority premium
   upgrades in ROI order are likely: (a) Pinnacle/Betfair historical odds for sports
   calibration (~$50–100/mo); (b) Bloomberg consensus scrape for CPI/NFP ($100–200/mo);
   (c) Nansen on-chain for DeFi events ($150/mo); (d) HLTV Pro for esports ($10/mo).
   All other premium feeds are optional or deferred to when the vertical demonstrates
   positive OOS ROI on the free tier first.

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
| Bloomberg consensus (premium) | Exact economist consensus | ~$100–200/mo | CPI, NFP |
| Nansen (premium) | On-chain wallet analytics | ~$150/mo | DeFi events |
| The Block Pro (premium) | On-chain analytics | ~$80/mo | DeFi events |
| Pinnacle historical odds (premium) | Sharp closing line reference | ~$50–100/mo | Sports all |
| Forge Global (premium) | VC secondary-market pricing | ~$500/mo | IPO markets |

---

*End of document. Feeds 02_EDGE_ENGINES.md (engine implementation per vertical),
09_ROADMAP.md (build sequencing), and 99_DECISIONS_LOG.md (judgment calls above).*
