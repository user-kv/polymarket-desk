# The Institute — Edge Engines (02)

**Status:** PLANNING ONLY. Research-backed design. No build authorized yet.
**Date:** 2026-06-30
**Feeds:** CHARTER §3 — four edge engines, all first-class, best-fit per market.

Every vertical draws from a menu of four reusable edge engines. This document is the
canonical specification of each: method, integration pattern, free vs premium, failure
modes, and when NOT to use it. Verticals mix and match; the weather bot is Engine 1 in
its purest form; the Institute's Alpha Engine adds Engine 3 on top.

---

## Engine 1 — Quant / Information Ensembles

### What it is
A numerical ensemble of INDEPENDENT models that each forecast a measurable quantity
(temperature, CPI MoM%, unemployment rate, election polling margin, crypto price), then
combine their predictive distributions into a single calibrated probability over market
buckets. This is the weather-bot pattern, generalized.

### The gold-standard pattern (weather bot / CPI)
```
HISTORY                 per-model historical data (BLS, Open-Meteo archive, FRED)
MODELS  M1 ... Mk       each returns (mu_i, sigma_i) — point + uncertainty
CALIBRATE               walk-forward OOS: compute per-model RMSE from history
WEIGHTS                 w_i = (1/RMSE_i) / sum(1/RMSE_j)  [inverse-RMSE]
COMBINE                 mu*    = sum(w_i * mu_i) - bias
                        sigma* = sqrt( sum(w_i * (sigma_i^2 + (mu_i - mu*)^2)) )
                        (mixture variance: within-model + across-model disagreement)
BUCKET                  p_model = Phi((hi - mu*)/sigma*) - Phi((lo - mu*)/sigma*)
                        clipped to (EPS, 1-EPS)
FREEZE                  p_model stored at snapshot time; never re-computed after
```
The mixture variance formula is load-bearing: when models disagree, sigma* widens,
which correctly shrinks p_model toward 0.5 — the ensemble auto-hedges its own confusion.

### Calibration: three distinct layers
1. **Per-model RMSE weights** (always on): fit from walk-forward OOS, weight better
   models more heavily. This is NOT the same as Platt scaling.
2. **Per-station/vertical bias correction** (always on, shrinkage-damped):
   `correction = (n/(n+K)) * raw_bias`. At n=4, K=10 → 29% of raw bias applied.
   Prevents overreaction to small samples.
3. **Platt/extremization calibration of p_model** (gated until n≥200 markets):
   `log(p̂/(1-p̂)) = alpha * log(p/(1-p))`, alpha≈1.73 (√3, Neyman & Roughgarden 2022).
   Undoes RLHF hedge-toward-0.5 bias when LLMs are in the ensemble.
   **Danger**: if raw forecast is on the wrong side of 0.5, extremization amplifies the
   error. Gate it.

### The CPI 3rd-model problem: how to get genuine independence cheaply
The CPI vertical's `nowcast` model (model 3) collapses to `random_walk` when Cleveland
Fed is absent, giving only ~2 effective models. This is the canonical model-diversity
failure: two models sharing a common data source or architecture correlate their errors.

**The independence principle** (arXiv 2509.21191): ensemble benefit comes from
*uncorrelated errors*, not individual accuracy. Models that share assumptions fail
simultaneously on identical scenarios — the cascade produces confidently wrong predictions
with narrow sigma*, the worst possible outcome.

**Cheap diversity strategies for quant verticals:**
```
LAYER 1 — different model families (highest bang/buck):
  Mechanistic (seasonal ARIMA, structural time-series)  vs
  Statistical (ridge regression, gradient boosting on lags)  vs
  External nowcast (3rd-party institutional, e.g. Cleveland Fed CPI, NOAA QPF for rain)

LAYER 2 — different training windows:
  Short window (6–12 months, recency-weighted)  vs
  Long window (5–10 years, captures cycles)
  → error correlation ≈ 0 across regimes

LAYER 3 — different data sources:
  Primary official series (BLS, NWS) vs
  Alternative proxy (Google Trends, satellite data, commodity futures strip)
  → correlated only when both right, independent when one sees something new

LAYER 4 — structural diversity:
  Temporal model (AR/SARIMA)  vs
  Cross-sectional model (uses correlated indicators: PPI→CPI, futures→temp)
  → orthogonal feature spaces → near-zero error correlation
```

**CPI vertical fix** (concrete, free):
- Model 1: `seasonal_ar` (existing — mechanistic + calendar)
- Model 2: `random_walk` (existing — trailing base rate)
- Model 3 option A: **Cleveland Fed** (external nowcast, institutional, free, no-key v1)
- Model 3 option B (fallback): **PPI-based linear projection** — core PPI is a leading
  indicator of core CPI with ~1-month lag (FRED `PPIACO` or `PPIFID`, free CSV). Fit a
  rolling 36-month OLS: `CPI_MoM ~ alpha + beta * PPI_lag1_MoM`. This is structurally
  independent of both AR and random-walk because it uses a DIFFERENT INPUT VARIABLE, not
  just a different window over the same series.
- Model 3 option C: **Import price index** (FRED `IR`, free) — another orthogonal leading
  indicator of goods inflation.

**Effective model count** (AIA / PolySwarm finding): diminishing returns past ~10
independent models; 3–6 well-diversified models from different families beats 20
correlated ones. Don't add models for their own sake.

### How it plugs into a vertical
```python
# standard interface every quant model must implement:
def my_model(history, **context) -> dict:
    return {"name": str, "mu": float, "sigma": float}

# ensemble.py is generic — inject any list of model callables
# calibrate.py is generic — walk-forward RMSE on any (mu, actual) pairs
# bucket_prob() is universal — Normal CDF, works for any measurable quantity
```
A new vertical (e.g. jobs report, PCE deflator) only needs:
1. A `data.py` fetching its history
2. 3+ independent `models.py` functions returning (mu, sigma)
3. A `parse.py` mapping market question to (lo, hi) bucket
4. The existing `ensemble.py` + `calibrate.py` reused unchanged

### Free vs premium
| Component | Free | Premium |
|-----------|------|---------|
| BLS, FRED, Open-Meteo archive | Yes | — |
| Cleveland Fed nowcast | Yes (best-effort) | — |
| PPI, import prices (FRED) | Yes | — |
| ECMWF deterministic (full) | No | ~€60/yr academic |
| Bloomberg consensus forecasts | No | $$$$ |
| ADP payrolls early release | No | Paid |
| Refinitiv poll aggregator | No | $$$$ |

### Failure modes
- **Collapsed ensemble**: all models share the same data source or are mechanically
  related → sigma* narrows falsely → overconfident bucket probabilities.
  *Detection*: compute pairwise Pearson correlation of OOS errors; flag if any pair > 0.7.
- **Regime change blindness**: history-fitted RMSE weights are backward-looking; a new
  inflation regime can flip which model is best.
  *Mitigation*: exponentially decay historical errors (half-life 12 months) in RMSE fit.
- **Bucket mismatch**: market question says "≥0.3%" but the BLS rounds differently.
  *Mitigation*: conservative parse — abstain if bucket boundary ambiguous.
- **Small-n overfitting**: RMSE weights from 12 months of CPI history are noisy; one
  surprise month can dramatically shift weights.
  *Mitigation*: Bayesian shrinkage toward equal weights — `w_i ∝ 1/(RMSE_i + epsilon)`.

### When NOT to use Engine 1
- Market question is qualitative (who wins, will X happen by Y date) — no measurable
  quantity to fit a Normal to. Use Engine 3 (news+LLM) instead.
- Resolution criterion is ambiguous or subjective. Forecast error cannot be attributed
  to model quality if the outcome itself is uncertain.
- n < 6 historical outcomes for the specific bucket. Weights are noise; use equal
  weights and do not deploy Platt calibration.

---

## Engine 2 — Behavioral / Crowd-Bias

### What it is
Systematic exploitation of documented, persistent mispricings in prediction-market
prices that arise from crowd psychology, not information. These are structural biases,
not alpha from knowing something the crowd doesn't. They are the cheapest edge to deploy
(no data pipeline required) and the most robust across verticals.

### Bias 1: Favorite-Longshot Bias (FLB) — the most robust finding in PM research

**Evidence:**
- Kalshi (300K+ contracts, CEPR/GWU 2026): clear FLB across all market types. Takers
  lose 32% on average; makers lose 10%. Cheap contracts (5¢) win ~2% of the time —
  losng 60% of invested capital on expectation.
- Polymarket cross-platform study (SSRN 2025): Kalshi longshots overpriced; Polymarket
  favorites (>55% implied) SYSTEMATICALLY UNDERPRICED. Market design (CLOB vs. fee
  structure) moderates which tail is most exploitable.
- Academic consensus (Whelan 2024, Economica): FLB arises from probability
  misperception (prospect theory) plus trader disagreement + market-maker risk aversion.

**Quantitative form:**
```
FLB region:    q_yes ≤ 0.15 (and often up to 0.20)
True prob:     p_true ≈ q_yes * 0.65  (longshots win ~35% less than priced)
Edge per bet:  2–5% expected positive return on NO side
Signal:        fade_longshot(q) = "NO" if q ≤ 0.15
               Our longshot_fade baseline (cap=0.35, shrink=0.5) already implements this
```

**The institute's existing implementation**: `map/baselines.py::longshot_fade`. This
is live as a baseline. The upgrade path is to fit the shrink parameter per-vertical from
resolved bets rather than using a fixed 0.5.

**Why it persists**: lottery-ticket demand (agents overweight small probabilities per
prospect theory), poor calibration on rare events, and thin liquidity means no one
is large enough to fully arb it away.

### Bias 2: Favorite Underpricing (the other tail)

**Evidence** (Polymarket-specific from cross-platform study above):
- Favorites above 55% implied probability are SYSTEMATICALLY UNDERPRICED on Polymarket
  relative to their true frequency. The mechanism: CLOB structure means FOMO buyers
  push YES prices high but NO side (which funds the YES payoff) is provided by reluctant
  market-makers who demand extra margin.
- Practical edge: 70¢ Polymarket contract corresponds to ~83% true probability
  (13pp gap) one week before resolution, per calibration research (arXiv 2602.19520).

**Trading signal:**
```
Favorite_region:    q_yes ≥ 0.70 AND time_to_resolution ≤ 14 days
Edge:               buy YES; expected true prob ~10–15pp above q_yes near resolution
Gate:               requires corroborating evidence (Engine 3 search or Engine 1 model)
                    to confirm it isn't a genuine 70% event about to go wrong
```

### Bias 3: Anchoring / Round-Number Clustering

**Evidence (academic):**
- FRB FEDS 2007 + Hilary et al.: expert consensus forecasts anchor systematically to
  previous month's value. This means the consensus embedded in market prices INHERITS
  the previous print as an anchor.
- Round numbers (0.50, 0.25, 0.75) see excess order clustering — prices cluster at
  psychological anchors more than information warrants.
- Effect size: anchored forecasts deviate from true model by ~1–3pp on CPI, ~2pp on
  payrolls, systematic and persistent across forecasters.

**Detection:**
```python
def anchoring_signal(q_yes, prev_price=None, round_buckets=[0.25, 0.50, 0.75]):
    # Round-number clustering: check if q_yes is within 0.02 of a round number
    near_round = any(abs(q_yes - r) < 0.02 for r in round_buckets)
    # Prior-anchor: check if q_yes ≈ q_yes_yesterday (no update despite new data)
    stale = prev_price and abs(q_yes - prev_price) < 0.005
    return near_round or stale
```
**Exploit**: when Engine 1 model says p_model differs from q_yes AND q_yes is anchored
to a round number, confidence in the edge is HIGHER (the market is anchored, not informed).

### Bias 4: Overreaction to News / Recency Bias

**Evidence:**
- Prediction Market Analysis (3,587 markets): prices overreact to news in the first
  1–4 hours after a breaking story; 2–4 hour delay before entry is optimal.
- Nobel Peace Prize Oct 2025: probability surged 3%→73% in hours, then mean-reverted
  partially before resolution.
- Order Book Imbalance (OBI) explains ~65% of short-interval price variance; OBI > 0.65
  predicts price increase at 58% accuracy (vs 50% random) in 15–30 min window.

**Quantitative signal:**
```
Overreaction trigger:   abs(q_today - q_yesterday) > 0.15 (15pp single-day move)
Fade window:            t+2h to t+6h after the news spike
Expected mean reversion: 30–50% of the spike reverses within 48h
Entry rule:             only fade if Engine 3 (news) confirms the move was
                        priced in (not new fundamental information)
```

### Bias 5: Time-to-Resolution Effects

**Evidence** (prediction market calibration research, arXiv 2602.19520):
- Long-horizon compression: all markets underconfident at distant horizons; prices
  compressed toward 50% more than information warrants.
- Near-resolution sharpening: prices improve dramatically in final 7–14 days as informed
  traders reduce information-leakage costs.
- Political markets: 70¢ contract 1 week before resolution ≈ 83% true probability.

**Trading signals:**
```
Far horizon (>60 days):     expect compression; q_yes biased toward 0.50.
                            If Engine 1 says p_model >> 0.50, the edge is REAL,
                            not just market inefficiency.
Near resolution (<14 days): watch for informed-flow signals (OBI spikes, large orders).
                            Late informed flow is predictive; follow it.
Gamma decay:                position size ∝ sqrt(T_remaining / T_initial).
                            Reduce exposure ~65% in final week to manage terminal
                            volatility risk (contract delta approaches 0 or 1).
```

### Venue-level detection scan
Run this on every new market batch to tag bias signals:
```python
def bias_tag(market):
    q = market["q_yes"]
    days = market["days_to_resolution"]
    tags = []
    if q <= 0.15:                          tags.append("LONGSHOT_FADE")
    if q >= 0.70 and days <= 14:           tags.append("FAVORITE_BUY")
    if near_round(q):                      tags.append("ANCHOR_CHECK")
    if big_move_today(market):             tags.append("OVERREACTION_WATCH")
    if days > 60 and abs(q - 0.5) < 0.15: tags.append("COMPRESSED_HORIZON")
    return tags
```
These tags flow into the gate pipeline as MECHANISM signals (Gate 2).

### How it plugs into a vertical
Engine 2 is vertical-agnostic. The LONGSHOT_FADE baseline is already live in
`map/baselines.py`. The upgrade path per vertical:
1. Fit the fade threshold (currently 0.15/0.35 fixed) per-archetype from resolved bets.
2. Track anchor patterns for that vertical's specific round numbers (CPI 0.3%, 0.5%;
   temperature 90°F, 100°F).
3. Add the time-horizon compression correction as a p_model adjustment for long-dated
   markets.

### Free vs premium
All Engine 2 signals are derived from market data that Polymarket exposes free:
- `q_yes` (current), historical prices (Data API), OBI (CLOB `/book`).
- No paid data required at any tier.
Premium upgrade: real-time OBI websocket monitoring (CLOB websocket, free) enables
the overreaction fade in near-real-time rather than on a cron cycle.

### Failure modes
- **Structural FLB disappears**: if Polymarket's market-maker pool improves, the FLB
  in the longshot tail may erode. Monitor with rolling Brier score per bias tag.
- **Overreaction fade enters BEFORE mean reversion**: the 2–4h delay rule is empirical,
  not guaranteed. In markets with true information (election leaks, sports injury),
  what looks like overreaction is a genuine price discovery. NEVER fade without
  Engine 3 confirmation that the news has been priced in.
- **Round numbers are sometimes correct**: 0.50 is the right price for a coin flip.
  The anchor signal only has value when combined with a model that says otherwise.

### When NOT to use Engine 2
- Liquid, heavily-traded markets with institutional participation (crypto top-50,
  major US elections close to resolution). The FLB is fully arbed out in these.
- Markets with mandatory maker activity (Kalshi treasury products). Makers absorb the
  bias on both sides; takers still lose but there's less pattern to exploit.

---

## Engine 3 — News & Event Reasoning (Agentic)

### What it is
An LLM-powered agentic forecasting system that, for qualitative market questions (will X
happen by Y), iteratively searches for evidence, synthesizes it into a probability, and
then combines a swarm of independent forecasters into a calibrated p_model. This is the
AIA Forecaster + PolySwarm architecture, adapted for the Institute's cost constraints.

### Architecture (the AIA/PolySwarm synthesis)

```
PERCEIVE       fetch open markets needing forecast (already built: sensor)

SEARCH PHASE   For each question:
               1. Agentic search worker (Haiku/Sonnet):
                  - Issues 3–5 iterative search queries, conditions each on prior results
                  - Writes evidence summary (≤500 tokens)
                  - Flags "foreknowledge risk" if any result looks like post-event data
               2. POINT-IN-TIME CHECK: discard any evidence published AFTER t0.
                  (contamination rate ~1.65% — AIA found this via LLM-as-judge audit)

SWARM PHASE    ~10 independent forecaster agents (Haiku — cheap workers):
               - Each receives: question + evidence summary + its OWN persona prompt
               - Personas differentiated by analytical archetype (economist, political
                 scientist, domain expert, contrarian, base-rate statistician)
               - NO inter-agent communication. NO shared chain-of-thought.
               - Each returns: p_i ∈ (0,1) with one-sentence rationale
               AIA design: "Each forecasting agent operates independently, their paths
               can diverge significantly." Independence is the load-bearing property.

AGGREGATE      Simple mean of p_i values (PolySwarm: confidence-weighted; AIA: simple
               mean wins in practice — debate/LLM-judge aggregation is worse).
               p_swarm = mean(p_i) for i in 1..10

SUPERVISOR     Opus agent (1 call per question):
               - Detects outlier agents (|p_i - p_swarm| > 0.25)
               - For each major disagreement, runs 1–2 targeted SEARCH queries to
                 find resolving evidence. High-confidence updates replace mean.
               - AIA supervisor: Brier 0.1125 vs 0.1140 for simple mean (modest gain,
                 but worth 1 Opus call when swarm is genuinely split)
               - Returns: p_supervisor, confidence ("high"/"medium"/"low")

BLEND          p_final = w * p_supervisor + (1-w) * q_market
               AIA optimal weights on different benchmarks:
                 FB-7-21:     w=0.87 (model dominates)
                 MarketLiquid:w=0.33 (market dominates — liquid markets know more)
               Institute prior: w=0.70 (PolySwarm default; recalibrate per archetype
               as OOS data accumulates, per AIA methodology)
               Trade gate:   |p_final - q_yes| > edge_threshold (default 5%)
                             AND p_std < 0.30 (swarm not too divided)

CALIBRATE      Platt extremization: alpha≈1.73 (gated until n≥200 markets)
               log(p̂/(1-p̂)) = alpha * log(p_final/(1-p_final))
               DANGER: only apply if p_final > 0.5 (else extremization amplifies error)

FREEZE         p_final stored at snapshot time; idempotent; never re-computed
```

### Model routing (Institute standing rule)
- Opus: supervisor reconciliation (few calls, judgment seat)
- Sonnet: agentic search workers (iterative, ~5 calls per question)
- Haiku: forecaster swarm (10 parallel, cheap, volume work)
The AIA finding: **3.6x Brier improvement from agentic search vs no search**. This is
the single biggest lever — iterative evidence retrieval beats raw model judgment.

### Free vs premium news sources
```
FREE (default):
  NewsAPI (free tier, 100 req/day):     breaking news in English
  GNews API (free tier):                aggregated news headlines
  GDELT (free, no key):                 global events database, good for geopolitics
  Wikipedia API (free):                 background/context, not breaking
  RSS feeds (Reuters, BBC, AP):         parseable, no key, 15-min lag
  arXiv API (free):                     science/tech markets
  SEC EDGAR (free):                     earnings, filings (macro markets)
  Google Trends (free, unofficial API): sentiment proxy for consumer/cultural markets
  Reddit API (free tier):               community sentiment, crypto/culture

PREMIUM (activate at live launch):
  Bing News Search API (~$3/1000 calls): best coverage, good for recency
  Perplexity Sonar Pro ($5/1000 calls):  purpose-built agentic search endpoint
  Exa AI search (search-first API):      designed for LLM agent use, semantic search
  Polymarket-specific: none (CLOB data is free; on-chain is free)
```

### Point-in-time honesty (the structural moat)
The two-phase sensor is the defense:
1. **SNAPSHOT phase**: search runs now; evidence timestamped; p_final frozen.
2. **SETTLE phase**: outcome read AFTER resolution; never fed back into the snapshot.
3. **Foreknowledge audit**: every search result checked by LLM-as-judge: "Is this
   result available BEFORE the market's t0?" Contaminated results discarded.
   Rate: ~1.65% contamination in AIA's audit. The cost of not doing this is a phantom
   backtest that evaporates live.

A competitor running a backtester that queries live news will see a phantom 20–30%
performance improvement that disappears in production. Our frozen-prior architecture
means we can replay any historical scenario deterministically.

### How it plugs into a vertical
Engine 3 is the Alpha Engine (A6). It is market-agnostic but calibrates per archetype:
- Sports: evidence = injury reports, referee assignments, weather (outdoor events)
- Politics: evidence = polls, endorsements, prediction-market aggregators, betting trends
- Geopolitics: evidence = GDELT events, news agency wires, diplomatic signals
- Science/culture: evidence = arXiv, Wikipedia, domain-specific RSS
The swarm personas specialize to the archetype (a "sports statistician" persona for
sports markets; a "macroeconomist" persona for CPI). The search worker gets archetype-
specific query templates.

### Failure modes
- **Context overflow (silent cost killer)**: 10 agents × ~2000 tokens each = 20K tokens
  per question. At 100 open questions, this is 2M tokens per run. Budget hard caps:
  max 50 questions per A6 run; max 500 tokens per agent response.
- **Anchoring to market price**: if the forecaster swarm sees q_yes before forecasting,
  they anchor to it. NEVER show q_yes to swarm agents. Show it only at blend stage.
- **Sycophancy cascade in aggregation**: debate-style or LLM-judge aggregation causes
  outlier agents to be talked out of correct minority views. Use raw mean, not debate.
  PolySwarm's persona-differentiated swarm + no inter-agent communication is the fix.
- **Stale evidence**: news from 3 months ago is not stale for a long-horizon market but
  IS stale for a 2-day election market. Agent must assess evidence recency vs question
  horizon.
- **Calibration applied on wrong side**: Platt extremization with α=1.73 on a p_final=0.35
  pushes it to ~0.20 — correct direction. On a p_final=0.65 → ~0.80 — also correct.
  But on p_final=0.45 (wrong side of 0.5 for a truly ~0.60 event) → ~0.35 (disaster).
  Gate: only extremize when swarm p_std < 0.20 (high consensus).

### When NOT to use Engine 3
- Numerical quantity markets (CPI MoM%, temperature °F). Use Engine 1 instead — a
  numerical ensemble beats an LLM reasoning about whether inflation will be "high".
- Markets with <72h to resolution AND no breaking news. Market price already incorporates
  all available information; the search adds noise not signal.
- Markets where search is systematically contaminated (e.g., "will study X be replicated"
  — search will surface opinion pieces that anchor to the market price, not evidence).

---

## Engine 4 — Smart-Money / Copy-Flow

### What it is
Track which wallets on Polymarket have demonstrated edge (via on-chain history), monitor
their current positioning in real-time, and use their order flow as a leading signal —
either follow (for directional bets the swarm missed) or fade (when they appear to be
taking the other side of the FLB).

### The structural advantage: full transparency
Polymarket's on-chain settlement (Polygon / Bor) means EVERY trade is permanently public.
No hidden order flow. No dark pools. The smart-money signal is cleaner than equities.

```
Data sources (all free):
  Gamma API:       market metadata, no auth  (gamma-api.polymarket.com)
  CLOB API:        order book depth, no auth (/book?token_id=<id>)
  Data API:        wallet positions, trade history, P&L, no auth
                   /positions?user=<addr>, /trades?user=<addr>
  CLOB WebSocket:  real-time order book + last trade (wss, no auth for market channel)
  Polygon RPC:     raw on-chain events (OrderFilled, PositionsMerged, ConditionResolution)
                   via any public Polygon endpoint (e.g. polygon.llamarpc.com, free)

Premium upgrades:
  Polywhaler ($9/mo): pre-processed whale feed, insider risk scoring, Telegram alerts
  Chainstack dedicated Polygon RPC ($19/mo): lower latency than public endpoint
  Unusual Whales (Polymarket, Jan 2026, paid): insider-pattern detection
```

### The four archetypes of sharp wallets (from copy-trading research)
1. **Information arbitrageurs**: few but large bets, 60%+ win rate, research-driven.
   Signal: high conviction on illiquid long-tail markets (Engine 1+3 edge territory).
2. **Domain specialists**: 10–30 trades/year, one category, very deep.
   Signal: concentrated in one archetype (sports, political, scientific).
3. **Algo market-makers / arbitrageurs**: high frequency, both sides, spread capture.
   NOT useful to follow directionally — they hedge everything. Identify and EXCLUDE.
4. **Lucky streaks**: high all-time P&L from 1–2 massive bets.
   NOT useful to follow — survivor bias. Filter: require 50+ resolved trades,
   profit spread across ≥10 distinct markets.

### Wallet qualification (the 4-dimension filter)
```python
def qualify_wallet(profile):
    """Returns True if wallet is worth tracking as a signal source."""
    return (
        profile["win_rate"] >= 0.60        # 60%+ win rate
        and profile["resolved_trades"] >= 50   # not luck — ≥50 markets
        and profile["profit_concentration"] < 0.50  # no single trade > 50% of P&L
        and profile["holding_period_median"] > 4    # not arbitrage bot (hours, not seconds)
        and not profile["is_market_maker"]  # exclude MM wallets
    )
```

### Order-flow signals and how to extract them

**1. Convergence signal (strongest):**
When ≥3 qualified wallets independently take the same directional position in the same
market within 48h, this is a strong directional signal. The basket approach from
copy-trading research: "when 80%+ of tracked wallets agree on the same outcome" —
empirical win rate 67.7% at Copy Score ≥70 (Polycopy data).
```python
def convergence_signal(market_id, tracked_wallets, window_hours=48):
    recent_positions = {w: get_recent_position(w, market_id, window_hours)
                        for w in tracked_wallets}
    long_wallets = [w for w, p in recent_positions.items() if p == "YES"]
    short_wallets = [w for w, p in recent_positions.items() if p == "NO"]
    n = len(recent_positions)
    if n == 0: return None
    if len(long_wallets) / n >= 0.80: return "YES_CONVERGENCE"
    if len(short_wallets) / n >= 0.80: return "NO_CONVERGENCE"
    return None
```

**2. Large-order signal:**
Single orders ≥$10K from a qualified wallet in a market with <$100K total volume is
a significant position. The Data API returns trade size and wallet address.
```
Threshold:    trade_size / market_volume > 0.10 (>10% of market depth)
Timing risk:  the entry price may already have moved by the time we see it
Mitigation:   only enter if q_yes has moved <5pp from when the whale entered
              (use CLOB historical prices — /book gives current book, trade history
              via /trades?user=<addr> gives their entry timestamp + price)
```

**3. Informed late flow:**
Final 60 minutes before resolution: large orders from historically-sharp wallets are
predictive of outcomes (2–5% edge from Frenzy Capital research). Not implementable on
a cron cycle — requires WebSocket monitoring.
```
Implementation: CLOB WebSocket market channel (free, no auth)
                Filter for trades > $1K in final hour from tracked wallet list
                Auto-follow with quarter-Kelly on the same side
```

**4. Position persistence signal (fade fakeouts):**
A qualified wallet entering a position and HOLDING through adverse price movement is a
strong conviction signal (Theo4 pattern — held through volatility). An arbitrage bot
would exit. Check via Data API `/positions?user=<addr>` — if the position is still open
2+ days after entry at a worse price, conviction is high.

### Follow vs fade logic
```
FOLLOW when:
  - 2+ qualified wallets converged on the same side in last 48h
  - Entry price within 5pp of their entry (not too late)
  - Market archetype matches their specialty
  - Engine 1 or 3 does NOT contradict (or is silent / abstaining)

FADE when:
  - Wallet is an algo market-maker (exclude from follow; fade their extreme positions)
  - Wallet is in the FLB longshot region (they may be the other side of the bias)
  - Engine 1 contradicts AND convergence is not overwhelming (< 80% agreement)
  - Price has already moved >15pp since their entry (cost basis too far gone)
```

### On-chain tracking implementation (free tier)
```
DAILY CRON:
  1. Pull leaderboard top 100 via Data API /positions + community sources
  2. For each, compute 30-day metrics: win_rate, resolved_trades, profit_concentration
  3. Qualify wallets into tracked set (target: 20–30 wallets)
  4. For each tracked wallet: /trades?user=<addr> -> recent activity
  5. Cross-reference against open markets: any tracked wallet in market X?
  6. Compute convergence signal per market
  7. Flag markets with YES_CONVERGENCE or NO_CONVERGENCE -> Gate 2 mechanism input

WEBSOCKET (future, premium-ready):
  Subscribe to CLOB market channels for top-20 markets
  On each large fill: check if wallet in tracked set -> fast-follow trigger
```

### Premium path
At live launch: Polywhaler ($9/mo) gives pre-processed whale alerts via Telegram,
insider risk scoring, and real-time feeds. This avoids having to maintain the wallet
qualification pipeline ourselves — a $9 outsourcing of ~40 hours of tracking work.

### Failure modes
- **Entry-price slippage**: the #1 copy-trading failure mode. Smart money enters at 35¢;
  by the time we see it, it's at 72¢. The edge has been captured. Hard rule:
  only follow if q_current ≤ q_entry + 0.05.
- **Arbitrage bot misidentification**: algo MM wallets have high win rates but hedge both
  sides. Following only their YES side creates asymmetric risk. Identify by:
  holding_period_median < 30 minutes AND simultaneous YES+NO positions.
- **Survivor-bias wallet selection**: a wallet with 3 massive wins from 5 trades looks
  amazing. Require 50+ resolved trades AND profit across ≥10 markets.
- **Late exit mimicry**: when the wallet exits at a loss, exit immediately. Never hold
  after they leave — you're now trading without a thesis.
- **Correlation to Engine 3**: if the sharp wallet is following the same news we are,
  follow and Engine 3 will be correlated signals. Use them as confirmation, not
  independent sources.

### When NOT to use Engine 4
- Thin/illiquid markets with <$10K volume. Whales can move the market themselves;
  following them means buying into their own impact.
- Markets within 2 hours of resolution. Entry slippage + terminal volatility makes
  copy-flow dangerous at this stage.
- Ultra-liquid markets (US election, major crypto, large sports). Professional algo
  shops dominate; individual wallet tracking has no information advantage over the
  aggregate order book.

---

## Cross-Engine Integration: the blend

Each engine produces a signal. The vertical combines them:

```
p_engine1  = quant ensemble (or None if not a measurable-quantity market)
p_engine3  = LLM swarm (or None if market type doesn't fit)
copy_signal = Engine 4 directional tag (YES/NO/None)
bias_tags   = Engine 2 structural tags (LONGSHOT_FADE, ANCHOR_CHECK, etc.)

BLEND RULE (per vertical):
  1. If p_engine1 is not None: use as p_base (highest precision)
  2. Else if p_engine3 is not None: use as p_base
  3. Else: p_base = q_yes (abstain from directional bet)

  2. Apply Engine 2 bias correction to p_base:
     if LONGSHOT_FADE in bias_tags and p_base < q_yes: amplify the NO signal
     if FAVORITE_BUY in bias_tags and p_base > q_yes: amplify the YES signal
     if ANCHOR_CHECK in bias_tags: widen the edge threshold (0.08 vs 0.05)

  3. Incorporate Engine 4 convergence:
     if copy_signal agrees with p_base direction: reduce edge threshold (0.03 vs 0.05)
     if copy_signal contradicts p_base: widen threshold (0.10); log contradiction

  4. Final gate:
     |p_final - q_yes| > edge_threshold  AND  (p_engine3 is None OR p_std < 0.30)
     → place bet at quarter-Kelly
```

This means a market can qualify on Engine 2 alone (FLB fade), or on Engine 1 alone
(CPI nowcast divergence), or on the combination of Engine 1 + Engine 4 (model says YES,
whale convergence confirms YES → reduce threshold, size up slightly).

---

## Sources

- AIA Forecaster Technical Report — arXiv:2511.07678
- PolySwarm: Multi-Agent LLM Framework for PM Trading — arXiv:2604.03888
- Makers and Takers: Economics of the Kalshi Prediction Market — Whelan et al., GWU/CEPR 2026
- Not All Accuracy Is Equal: Prioritizing Independence in Ensemble Forecasting — arXiv:2509.21191
- Decomposing Crowd Wisdom: Domain-Specific Calibration Dynamics — arXiv:2602.19520
- PolyBench: Benchmarking LLM Forecasting on Live PM Data — arXiv:2604.14199
- Consistency Checks for Language Model Forecasters — arXiv:2412.18544
- Copy Trading Masterclass — wiki/copy-trading-masterclass.md (Institute research)
- Mathematical Execution Behind Prediction Market Alpha — navnoorbawa.substack.com
- Trading Strategies for Prediction Markets — FrenzyCapital, Medium Apr 2026
- Polymarket API for Developers — chainstack.com/polymarket-api-for-developers/
- Polymarket API Guide 2026 — pm.wiki/learn/polymarket-api
- Neyman & Roughgarden (2022) — extremization / Platt equivalence, alpha=√3
- Hilary et al., Bayes Business School — anchoring bias in consensus forecasts
- FRB FEDS 2007/012 — anchoring bias in economic consensus forecasts
- Prospect theory (Tversky & Kahneman 1992) — probability weighting, FLB mechanism
