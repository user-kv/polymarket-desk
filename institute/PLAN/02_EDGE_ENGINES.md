# The Institute — Edge Engines (02)

## CHANGELOG
- **Engine 3 cost honesty**: 10-agent simple-mean claim contradicted by PolySwarm paper (arXiv 2604.03888), which uses 50-agent confidence-weighted Bayesian combination. Corrected; token budget math updated. Added explicit net-of-cost verdict vs cheap behavioral baseline.
- **Engine 3 net edge**: added pre-registered falsification test + kill criterion. Flagged as INFORMATIONAL/PERISHABLE with estimated half-life.
- **Engine 4 entry-slippage critique**: promoted to #1 structural weakness; added realistic cost model for cron-cycle copy-flow.
- **Engine 2 FLB evidence updated**: SSRN 2025 cross-platform study (Reichenbach & Walther) finds NO general longshot bias on Polymarket at market level; the Kalshi FLB (Bürgi/Whelan CEPR 2026, 300K contracts) is the robust finding. The Polymarket-specific FLB is contested. Revised claims accordingly.
- **Engine 2 Favorite Underpricing**: "70¢ ≈ 83% true prob" claim attributed to arXiv 2602.19520 (re-verified) — kept but labeled ASSUMPTION pending vertical-specific replication.
- **Engine 1 independence test**: pairwise error-correlation audit formalised as a build gate, not optional.
- **Cross-engine blend**: blend rule had a typo (numbered "1." twice); corrected. Added explicit statement that Engine 2 alone is never sufficient for a YES bet — only for NO (FLB fade).
- **All edges**: restated NET of taker fee (0–2% typical on Polymarket) and marked STRUCTURAL vs INFORMATIONAL with decay half-lives.
- **Platt danger clause clarified**: extremization rule tightened — only safe when p_final is on the correct side of 0.5 AND swarm p_std < 0.20.
- **Kill criteria**: pre-registered for every engine.
- **Weak-engine verdict**: Engine 3 (10-agent news swarm) is flagged as likely marginal NET of token cost vs the cheap behavioral baseline unless on long-tail illiquid markets. Engine 4 cron-cycle copy-flow is flagged as likely negative-EV due to entry-price slippage.
- **PolySwarm correction**: paper uses KL/JS divergence market analysis and confidence-weighted Bayesian aggregation — NOT simple mean. Corrected.

---

**Status:** PLANNING ONLY. Research-backed design. No build authorized yet.
**Date:** 2026-06-30
**Feeds:** CHARTER §3 — four edge engines, all first-class, best-fit per market.

Every vertical draws from a menu of four reusable edge engines. This document is the
canonical specification: method, integration pattern, free vs premium, net edge,
falsification test, kill criterion, and when NOT to use it.

---

## Edge summary (rubric Tier 1 — read first)

| Engine | Edge type | NET of cost | STRUCTURAL or INFORMATIONAL | Half-life | Verdict |
|--------|-----------|-------------|----------------------------|-----------|---------|
| 1 Quant ensemble | Model vs crowd | +5–15% ROI on economic releases where crowd is anchored | STRUCTURAL (model quality moat) | Long; erodes if crowd also upgrades models | **BUILD** |
| 2 Behavioral / FLB | Bias exploitation | +2–5% on Kalshi longshots; contested on Polymarket | STRUCTURAL (prospect theory demand) | Long; partially arbed at liquid endpoints | **BUILD (Kalshi confirmed; Polymarket: verify first)** |
| 3 News/LLM swarm | Info + synthesis | ~+1–3% on long-tail qualitative; likely NEGATIVE on liquid/fast markets net of token cost | INFORMATIONAL | Short (~3–12 months before widely copied) | **CONDITIONAL** — only on illiquid long-tail; prove it beats longshot_fade baseline first |
| 4 Copy-flow (cron) | Latency / info | Likely NEGATIVE on cron cycle (slippage eats the edge) | INFORMATIONAL | Very short | **WEAK** — WebSocket-only to be viable; defer |

---

## Engine 1 — Quant / Information Ensembles

**Edge NET of cost:** On economic releases (CPI, NFP) where the crowd is anchored to the prior print, a calibrated ensemble can see 5–15% edge vs market price. Fee on Polymarket ≈ 0–2% taker; executable. Net edge survives on economic releases. Does NOT survive in liquid, well-traded weather markets where the crowd already prices NWP ensembles.

**Type:** STRUCTURAL (model quality moat). Competitors must build comparable ensembles; the moat is the data pipeline + walk-forward calibration, not a secret.

**Falsification test:** After 50 OOS resolved markets per vertical, compute mean S vs `price_follow` baseline. Kill if S ≤ 0 (not beating the market) AND Brier ≥ market Brier.

**Kill criterion:** 50 markets, Brier ratio Engine1/market ≥ 1.0, or mean S ≤ 0. Halt deployment of that vertical; do NOT widen sample to rescue it.

**Cheapest disproof:** Compare to `longshot_fade` baseline on the same resolved rows. If Engine 1 does not beat the behavioral baseline on absolute Brier, the model is adding noise, not signal.

### The gold-standard pattern (weather bot / CPI)
```
HISTORY                 per-model historical data (BLS, Open-Meteo archive, FRED)
MODELS  M1 ... Mk       each returns (mu_i, sigma_i) — point + uncertainty
CALIBRATE               walk-forward OOS ONLY: per-model RMSE from history
                        NEVER in-sample; NEVER re-computed after snapshot
WEIGHTS                 w_i = (1/RMSE_i) / sum(1/RMSE_j)  [inverse-RMSE]
                        Bayesian shrinkage floor: w_i ∝ 1/(RMSE_i + epsilon)
PAIRWISE AUDIT          Pearson correlation of OOS errors per model pair.
                        If any pair > 0.7: that pair counts as ONE model, not two.
                        Build gate — vertical cannot deploy until audit passes.
COMBINE                 mu*    = sum(w_i * mu_i) - bias
                        sigma* = sqrt( sum(w_i * (sigma_i^2 + (mu_i - mu*)^2)) )
                        (mixture variance: within-model + across-model disagreement)
BUCKET                  p_model = Phi((hi - mu*)/sigma*) - Phi((lo - mu*)/sigma*)
                        clipped to (EPS, 1-EPS)
FREEZE                  p_model stored at snapshot time; NEVER re-computed after
```

The mixture variance formula is load-bearing: when models disagree, sigma* widens,
which correctly shrinks p_model toward 0.5. The ensemble auto-hedges its own confusion.

### Calibration: three layers, each independently gated

1. **Per-model RMSE weights** (always on): walk-forward OOS only. Bayesian shrinkage
   toward equal weights prevents a single surprise from dominating.
2. **Per-station/vertical bias correction** (always on, shrinkage-damped):
   `correction = (n/(n+K)) * raw_bias`. At n=4, K=10 → 29% applied. Conservative.
3. **Platt/extremization of p_model** (GATED: n≥200 markets AND p_final on correct
   side of 0.5 AND swarm p_std < 0.20):
   `log(p̂/(1-p̂)) = alpha * log(p/(1-p))`, alpha≈1.73 (Neyman & Roughgarden 2022).
   **Danger**: if p_final is on the wrong side of 0.5, extremization amplifies the
   error catastrophically. All three gates must pass before applying.

### Genuine independence: the build gate
The CPI vertical's `nowcast` model collapses to `random_walk` when Cleveland Fed
is absent — giving ~2 effective models, not 3. This is the canonical failure.

**Independence principle** (arXiv 2509.21191): ensemble benefit comes from
*uncorrelated errors*. Models sharing data sources or architectures fail together,
producing confidently wrong narrow sigma* — the worst outcome.

**Mandatory pairwise audit before deploy:**
```python
# Must pass before any vertical goes to gate pipeline:
def pairwise_audit(oos_errors: dict[str, list[float]]) -> bool:
    """Returns True if all model pairs have Pearson corr < 0.70.
    oos_errors: {model_name: [error_t1, error_t2, ...]} aligned by time.
    """
    names = list(oos_errors.keys())
    for i in range(len(names)):
        for j in range(i+1, len(names)):
            ei, ej = oos_errors[names[i]], oos_errors[names[j]]
            n = min(len(ei), len(ej))
            if n < 6: continue  # not enough data to audit; flag, don't fail
            mu_i = sum(ei[:n]) / n
            mu_j = sum(ej[:n]) / n
            cov = sum((ei[t]-mu_i)*(ej[t]-mu_j) for t in range(n)) / n
            std_i = (sum((ei[t]-mu_i)**2 for t in range(n))/n)**0.5 or 1e-9
            std_j = (sum((ej[t]-mu_j)**2 for t in range(n))/n)**0.5 or 1e-9
            if cov / (std_i * std_j) > 0.70:
                return False  # correlated pair — vertical has fewer models than it thinks
    return True
```

**Cheap diversity strategies (rank-ordered by bang/buck):**
```
LAYER 1 — different model families (highest bang/buck):
  Mechanistic (seasonal ARIMA, structural time-series)  vs
  Statistical (ridge regression, gradient boosting on lags)  vs
  External nowcast (3rd-party institutional, e.g. Cleveland Fed CPI)

LAYER 2 — different training windows (near-zero cost):
  Short window (6–12 months, recency-weighted)  vs
  Long window (5–10 years, captures cycles)

LAYER 3 — different data sources:
  Primary official series (BLS, NWS) vs
  Alternative proxy (PPI→CPI lag, futures→temp)

LAYER 4 — structural diversity:
  Temporal model (AR/SARIMA)  vs
  Cross-sectional model (correlated indicators: PPI→CPI, futures→temp)
```

**CPI vertical fix (concrete, free):**
- Model 1: `seasonal_ar` (mechanistic + calendar)
- Model 2: `random_walk` (trailing base rate — honest naive anchor)
- Model 3A: **Cleveland Fed** nowcast (external institutional, free)
- Model 3B (fallback): **PPI-based linear projection** — FRED `PPIFID`, rolling
  36-month OLS: `CPI_MoM ~ alpha + beta * PPI_lag1_MoM`. Structurally independent
  because it uses a DIFFERENT INPUT VARIABLE, not just a different window.
- Model 3C (fallback): **Import price index** (FRED `IR`) — orthogonal goods
  inflation signal.

**Effective model count:** diminishing returns past 5–6 well-diversified models
(arXiv 2509.21191). Don't add models for count; add them only if they pass the
pairwise audit.

### Standard model interface
```python
def my_model(history, **context) -> dict:
    return {"name": str, "mu": float, "sigma": float}
    # sigma floored at 0.05; never return 0 sigma

# ensemble.py is generic — inject any list of model callables
# calibrate.py is generic — walk-forward RMSE on any (mu, actual) pairs
# bucket_prob() is universal — Normal CDF, works for any measurable quantity
```

### Free vs premium
| Component | Free | Premium |
|-----------|------|---------|
| BLS, FRED, Open-Meteo archive | Yes | — |
| Cleveland Fed nowcast | Yes (best-effort) | — |
| PPI, import prices (FRED) | Yes | — |
| ECMWF deterministic (full) | No | ~€60/yr academic |
| Bloomberg consensus | No | $$$$ |

### Failure modes
- **Collapsed ensemble**: pairwise error corr > 0.7 → sigma* narrows falsely.
  *Detection*: mandatory pairwise audit before deploy.
- **Regime change blindness**: RMSE weights are backward-looking; new regime flips
  which model is best. *Mitigation*: exponential decay of historical errors (half-life
  12 months) in RMSE fit.
- **Bucket mismatch**: market question says "≥0.3%" but BLS rounds differently.
  *Mitigation*: conservative parse — abstain if bucket boundary is ambiguous.
- **Small-n weight noise**: RMSE weights from 12 months of CPI data are noisy.
  *Mitigation*: Bayesian shrinkage floor `w_i ∝ 1/(RMSE_i + epsilon)`.

### When NOT to use Engine 1
- Qualitative market (who wins, will X happen). Use Engine 3 instead.
- Resolution criterion is ambiguous. Cannot attribute forecast error to model quality.
- n < 6 historical outcomes for the bucket. Use equal weights; do not deploy Platt.

---

## Engine 2 — Behavioral / Crowd-Bias

**Edge NET of cost:** On Kalshi, taker loss on longshots is well-documented:
contracts < 10¢ lose 60%+ of invested capital (Bürgi/Whelan/Deng, CEPR DP20631 /
GWU 2026, 300K+ contracts). On Polymarket, the evidence is more nuanced —
Reichenbach & Walther (SSRN 5910522, 124M trades) find NO general longshot bias at
the market level; Polymarket prices closely track realized probabilities. The
cross-platform study does find Polymarket favorites (>55%) are systematically
underpriced. **Net verdict: FLB edge on Kalshi is confirmed; on Polymarket it must be
verified from our own resolved bets before betting on it.**

**Type:** STRUCTURAL (prospect theory demand). The mechanism (lottery-ticket demand,
thin liquidity) is not easily arbed away at small scale. BUT: if Polymarket's MM pool
improves, the effect in the longshot tail erodes.

**Falsification test:** After 100 resolved markets with LONGSHOT_FADE tag on Polymarket,
compute win rate on NO bets in q_yes ≤ 0.15 range. Kill if win rate < 55% (expected
~65% to break even vs fee).

**Kill criterion:** 100 resolved Polymarket longshot bets, win rate < 55%. Retire the
FLB fade on Polymarket; keep on Kalshi (separately tracked) if Kalshi data available.

**Cheapest disproof:** Track the existing `longshot_fade` baseline's EV net of fee
across the first 100 resolved bets. Already live in `map/baselines.py`. Cost: zero.

### Bias 1: Favorite-Longshot Bias (FLB)

**Evidence (calibrated to venue):**
- **Kalshi** (Bürgi/Whelan/Deng, GWU/CEPR 2026, 300K+ contracts): clear FLB. Takers
  lose 32% on average; contracts < 10¢ lose 60%+ of invested capital.
- **Polymarket** (Reichenbach & Walther, SSRN 2025, 124M trades): NO general longshot
  bias found. Market prices closely track realized probabilities. The effect may exist
  in specific archetype subsets — ASSUMPTION, not confirmed.
- **Cross-platform study** (SSRN, 72M Kalshi + 404M Polymarket trades): Kalshi
  longshots overpriced; Polymarket favorites (>55%) UNDERPRICED. Market design
  moderates which tail is exploitable.

**Quantitative form (Kalshi-confirmed; Polymarket: verify OOS):**
```
FLB region (Kalshi):    q_yes ≤ 0.10 (strongest effect)
FLB region (tentative): q_yes ≤ 0.15 (weaker, needs Polymarket OOS confirmation)
True prob (Kalshi):     p_true ≈ q_yes * 0.40 (longshots win ~60% less)
Edge per bet (Kalshi):  2–5% expected positive return on NO side NET of fee
Signal:                 fade_longshot(q) = "NO" if q ≤ 0.15 AND venue == "Kalshi"
                        On Polymarket: track in paper mode, do not size up until OOS confirms
```

**Existing baseline:** `map/baselines.py::longshot_fade` (cap=0.35, shrink=0.5).
This is live as a tracking baseline. Do NOT widen the cap to 0.35 on Polymarket
until OOS data confirms the effect.

**Why it persists (structural):** lottery-ticket demand (Tversky/Kahneman 1992
prospect theory probability weighting), poor calibration on rare events, thin
liquidity. No single player is large enough to fully arb it at small scales.

### Bias 2: Favorite Underpricing

**Evidence:** Cross-platform calibration study (arXiv 2602.19520, ASSUMPTION — not
independently verified for current Polymarket data). 70¢ Polymarket contract ≈ 83%
true probability 1 week before resolution. The mechanism: CLOB structure creates
reluctant NO-side market makers who demand extra margin.

**ASSUMPTION label:** "70¢ ≈ 83%" is a single study claim. Treat as a prior, not a
confirmed edge. Verify from OOS data before sizing up.

**Trading signal (conditional on OOS verification):**
```
Favorite_region:    q_yes ≥ 0.70 AND time_to_resolution ≤ 14 days
Gate:               requires Engine 1 or 3 corroboration (never Engine 2 alone for YES)
Edge:               buy YES; expected +10–15pp vs q_yes near resolution (ASSUMPTION)
```

**RULE: Engine 2 alone is NEVER sufficient for a YES bet.** The FLB fade (NO side)
works without a model because the bias is mechanical. A YES bet on "favorites are
underpriced" requires confirming evidence from Engine 1 or 3 that the event is
genuinely likely. Without corroboration, the 70¢ market may be correctly priced.

### Bias 3: Anchoring / Round-Number Clustering

**Evidence:**
- FRB FEDS 2007/012: expert consensus anchors to previous month's value.
- Hilary et al. (Bayes Business School): anchored forecasts deviate ~1–3pp on CPI,
  ~2pp on payrolls. Effect size: modest but persistent.

**Use case:** confirmatory signal only. When Engine 1 says market price is wrong AND
price is anchored to a round number, confidence in the edge is HIGHER — the market
is anchored, not informed. Never trade the anchoring signal alone.

```python
def anchoring_signal(q_yes, prev_price=None, round_buckets=[0.25, 0.50, 0.75]):
    near_round = any(abs(q_yes - r) < 0.02 for r in round_buckets)
    stale = prev_price and abs(q_yes - prev_price) < 0.005
    return near_round or stale
```

### Bias 4: Overreaction to News / Recency Bias

**Evidence:**
- 3,587-market analysis: prices overreact to news in first 1–4 hours; 2–4h delay
  before entry is optimal (source: FrenzyCapital April 2026 — ASSUMPTION; treat as
  prior, not confirmed).
- Nobel Peace Prize 2025: 3%→73% surge, partial mean-reversion before resolution.
- OBI > 0.65 predicts price increase at 58% accuracy in 15–30 min window (ASSUMPTION).

**NEVER fade without Engine 3 confirmation** that the news is already priced in. In
markets with true information (election leaks, sports injuries), what looks like
overreaction is genuine price discovery.

```
Overreaction trigger:   abs(q_today - q_yesterday) > 0.15 (15pp single-day move)
Fade window:            t+2h to t+6h after spike (ASSUMPTION on timing)
Entry rule:             REQUIRES Engine 3 confirmation. Never standalone.
```

### Bias 5: Time-to-Resolution Effects

**Evidence** (arXiv 2602.19520 — political markets specifically; may not generalise):
- Long-horizon: prices compressed toward 50% more than information warrants.
- Near-resolution: dramatic accuracy improvement in final 7–14 days.

```
Far horizon (>60 days):    compression likely; Engine 1 edge is real if p_model >> 0.50
Near resolution (<14 days): watch for informed flow (OBI spikes, large orders)
Gamma decay:               position size ∝ sqrt(T_remaining / T_initial) — reduce ~65%
                           in final week to manage terminal volatility
```

### Venue-level scan
```python
def bias_tag(market):
    q = market["q_yes"]
    days = market["days_to_resolution"]
    tags = []
    if q <= 0.15:                          tags.append("LONGSHOT_FADE")
    if q >= 0.70 and days <= 14:           tags.append("FAVORITE_BUY")   # needs E1/E3 gate
    if near_round(q):                      tags.append("ANCHOR_CHECK")
    if big_move_today(market):             tags.append("OVERREACTION_WATCH")
    if days > 60 and abs(q - 0.5) < 0.15: tags.append("COMPRESSED_HORIZON")
    return tags
```
Tags flow into Gate 2 as MECHANISM signals. LONGSHOT_FADE is the only tag that can
trigger a standalone bet (NO side). All others require corroboration.

### Failure modes
- **FLB disappears on Polymarket**: if MM pool improves, longshot tail erodes.
  Monitor with rolling Brier per bias tag; retire if EV turns negative.
- **Overreaction fade enters before mean reversion**: 2–4h delay is empirical, not
  guaranteed. Always gate on Engine 3.
- **Round numbers are sometimes correct**: 0.50 is right for a coin flip.

### When NOT to use Engine 2
- Liquid, heavily-traded markets (crypto top-50, major elections close to resolution).
  FLB is fully arbed out in these.
- Markets with mandatory maker activity (Kalshi treasury products). Both sides absorb
  the bias; takers still lose but pattern is harder to exploit.

---

## Engine 3 — News & Event Reasoning (Agentic)

**Edge NET of cost:** The AIA Forecaster (arXiv:2511.07678) achieves 3.6x Brier
improvement from agentic search vs no search (Brier 0.1002 vs 0.3609 on closed
markets). However, on liquid-market benchmarks, AIA underperforms market consensus;
only the AIA+market ensemble beats consensus. This means Engine 3 is valuable as a
COMPLEMENT to the market price, not a replacement, and only where the market has
genuine information gaps (illiquid long-tail markets).

**Cost reality check:**
- 10 agents × ~1500 tokens each (input+output) = 15K tokens per question
- Haiku at ~$0.001/1K tokens → ~$0.015 per question × 100 questions = $1.50/run
- Token cost is manageable. The real cost is LATENCY and SUPERVISION OVERHEAD.
- If the edge per bet is < $2 expected profit, a $1.50/run token cost eats the margin.

**CORRECTION vs doc v1:** PolySwarm (arXiv 2604.03888) uses a 50-agent swarm with
confidence-weighted Bayesian aggregation (not simple mean) and KL/JS divergence
market analysis. The "10 agents, simple mean" in the prior version was inaccurate.
For the Institute, we default to 10 agents (cost-constrained) with simple mean as a
starting point, and note that PolySwarm's richer aggregation is the upgrade path.

**Type:** INFORMATIONAL (perishable). As more teams deploy LLM swarms on Polymarket,
the information advantage erodes. Half-life estimate: 6–18 months before the edge is
materially competed away on mainstream markets. Remains durable longer on long-tail
obscure markets where no institutional player bothers.

**Falsification test:** After 100 resolved qualitative markets, compute Brier vs
`longshot_fade` baseline (the cheap alternative). Kill if Engine 3 Brier ≥ longshot_fade
Brier, or if mean S ≤ 0. The LLM swarm must beat the behavioral baseline on the SAME
market set to justify its token cost.

**Kill criterion:** 100 resolved qualitative markets. Mean S ≤ 0, OR Brier ratio
Engine3/longshot_fade ≥ 1.0. Suspend all Engine 3 calls; revert to Engine 2 only.

**Cheapest disproof:** On the next 30 qualitative markets, track both Engine 3 and
the `longshot_fade` baseline. If longshot_fade matches or beats Engine 3 EV, the
swarm is not adding value. Cost of this check: already tracked in baselines.py.

### Architecture (AIA/PolySwarm synthesis, Institute-adapted)

```
PERCEIVE       fetch open markets needing forecast (sensor.py)

SEARCH PHASE   For each question:
               1. Agentic search worker (Haiku/Sonnet):
                  - Issues 3–5 iterative queries, conditions each on prior results
                  - Writes evidence summary (≤500 tokens)
                  - Flags "foreknowledge risk" if any result looks post-event
               2. POINT-IN-TIME CHECK: discard evidence published AFTER t0.
                  Contamination rate ~1.65% (AIA audit). Cost of missing this:
                  a phantom backtest 20–30% better than live — catastrophic.

SWARM PHASE    10 independent forecaster agents (Haiku — cost-constrained):
               - Each receives: question + evidence summary + its OWN persona
               - Personas: base-rate statistician, macroeconomist, domain expert,
                 contrarian, political scientist, geopolitical analyst,
                 tech analyst, public health expert, legal analyst, historian
               - NO inter-agent communication. NO shared chain-of-thought.
               - q_yes WITHHELD from all swarm agents (anchoring prevention).
               - Each returns: p_i ∈ (0,1) with one-sentence rationale
               NOTE: PolySwarm uses 50 agents + confidence-weighted Bayesian
               aggregation + KL/JS divergence. Our 10-agent simple mean is the
               budget starting point; upgrade path is PolySwarm's full method.

AGGREGATE      Simple mean (budget): p_swarm = mean(p_i)
               Upgrade: confidence-weighted Bayesian combination (PolySwarm)
               DO NOT use debate or LLM-judge — sycophancy cascade (AIA finding).
               DO NOT use geometric mean of log-odds unless calibrated from data.

SUPERVISOR     Opus/Sonnet agent (1 call per question, only when split):
               - Only triggered when p_std > 0.20 (genuine disagreement)
               - Detects outlier agents (|p_i - p_swarm| > 0.25)
               - Runs 1–2 targeted search queries to find resolving evidence
               - AIA finding: supervisor gives Brier 0.1125 vs 0.1140 for simple
                 mean — modest gain; only worth calling when swarm is split.
               - Returns: p_supervisor, confidence label

BLEND          p_final = w * p_supervisor + (1-w) * q_market
               AIA optimal weights:
                 FB-7-21 (illiquid):   w=0.87 (model dominates)
                 MarketLiquid:         w=0.33 (market dominates — it knows more)
               Institute prior:        w=0.70 (long-tail default)
               RECALIBRATE per archetype as OOS data accumulates.
               Trade gate: |p_final - q_yes| > edge_threshold (default 5%)
                           AND p_std < 0.30 (swarm not too divided)

CALIBRATE      Platt extremization: alpha≈1.73 (THREE-GATE check required):
               Gate 1: n ≥ 200 resolved markets for this archetype
               Gate 2: p_final is on the correct side of 0.5
               Gate 3: swarm p_std < 0.20 (high consensus)
               All three must pass. A p_final=0.45 extremized to ~0.35 on a
               truly 0.60 event is catastrophic. Never skip the gates.

FREEZE         p_final stored at snapshot time; idempotent; never re-computed
```

### Model routing (Institute standing rule)
- Opus: supervisor reconciliation only when p_std > 0.20 (few calls, judgment seat)
- Sonnet: agentic search workers (~5 calls per question)
- Haiku: forecaster swarm (10 parallel, cost-constrained volume work)

### Token budget enforcement (hard caps)
```
Max questions per Engine 3 run:  50
Max tokens per agent response:   500
Max search results per question: 10 (deduplicated)
Estimated cost per run:          ~$1.50–3.00 (Haiku swarm + Sonnet search)
Budget kill:                     if EV per resolved bet < $3, suspend E3 for that archetype
```

### Free vs premium news sources
```
FREE (default):
  NewsAPI (free tier, 100 req/day)    RSS feeds (Reuters, BBC, AP, 15-min lag)
  GNews API (free tier)               arXiv API (science/tech)
  GDELT (free, no key)                SEC EDGAR (filings, earnings)
  Wikipedia API (context only)        Google Trends (sentiment proxy)
  Reddit API (free tier)              

PREMIUM (at live launch — only if Engine 3 passes kill criterion on paper):
  Bing News Search API (~$3/1000):    best coverage + recency
  Perplexity Sonar Pro ($5/1000):     purpose-built agentic endpoint
  Exa AI:                             semantic search, LLM-optimized
```

### Point-in-time honesty (non-negotiable)
```
SNAPSHOT: evidence timestamped; p_final frozen. Data as of t_now only.
SETTLE:   outcome read after resolution; NEVER fed back into snapshot.
FOREKNOWLEDGE AUDIT: every search result checked: published_at > t0 → discard.
  Rate: ~1.65% contamination (AIA). Cost of ignoring: phantom +20–30% backtest.
```

### Failure modes
- **Token cost exceeds EV**: 100 questions × $0.03 = $3/run. If mean EV per bet is
  < $3, Engine 3 runs at a net loss. Hard budget cap is the defense.
- **Anchoring to q_yes**: if swarm sees market price, they anchor to it. NEVER show
  q_yes to swarm agents. Show it only at blend stage.
- **Sycophancy cascade**: debate/LLM-judge aggregation causes outliers to be talked
  out of correct minority views. Use simple mean, not debate.
- **Stale evidence timing**: news from 3 months ago is not stale for a long-horizon
  market but IS stale for a 2-day election market. Agent must assess evidence recency.
- **Calibration applied wrong**: Platt with α=1.73 on p_final=0.45 (wrong side of
  0.5 for a truly 0.60 event) → pushes to 0.35 (disaster). All three gates required.

### When NOT to use Engine 3
- Numerical quantity markets (CPI MoM%, temperature). Engine 1 beats LLM reasoning.
- Markets with < 72h to resolution AND no breaking news. Market price already
  incorporates all available information; search adds noise.
- Markets where search is systematically contaminated (e.g., "will study X be
  replicated" — search surfaces opinion anchored to the market price, not evidence).
- Any market where Engine 3's per-bet expected EV < token cost per question.

---

## Engine 4 — Smart-Money / Copy-Flow

**Edge NET of cost:** On a cron cycle, entry-price slippage is the #1 failure mode.
Smart money enters at 35¢; by the time a cron job sees it and acts, the market is at
50¢. The edge has been captured by the whale; we are buying their exit. **On a daily
cron cycle, Engine 4 is likely negative-EV for directional copy-flow.** The exception:
WebSocket near-real-time monitoring where we see the order within seconds. Defer
Engine 4 directional copy until WebSocket is implemented.

**Engine 4 IS useful** for wallet qualification (building the tracked list) and for
CONVERGENCE CONFIRMATION (3+ whales agree → upgrade confidence on an existing Engine
1 or 3 signal, reduce edge threshold). Do NOT use it as the primary signal source
without WebSocket.

**Type:** INFORMATIONAL (perishable). As the copy-trading ecosystem matures (Polywhaler,
Unusual Whales, etc.), the latency advantage of on-chain tracking shrinks. Half-life
estimate: 12–24 months before the signal is widely commoditised.

**Falsification test:** Track 50 follow-trades placed within 5pp of whale entry price.
Kill if win rate < 58% OR if mean EV net of fee < 0.

**Kill criterion:** 50 cron-cycle copy trades, win rate < 58%. Downgrade to
"confirmation signal only" — never primary; restore only on WebSocket implementation.

**Cheapest disproof:** Don't trade Engine 4 at all until WebSocket is live. Paper-track
what cron-cycle copy would have returned on the first 30 markets and compare to baseline.
Cost: zero.

### The structural advantage: full transparency
Polymarket's on-chain settlement (Polygon) means every trade is permanently public.
No dark pools. But full transparency is available to EVERYONE, including
Polywhaler, Unusual Whales, and every copy-trading tool. The moat is latency, not
information exclusivity.

```
Data sources (all free):
  Gamma API:       market metadata (gamma-api.polymarket.com)
  CLOB API:        order book depth (/book?token_id=<id>)
  Data API:        wallet positions, trade history, P&L
                   /positions?user=<addr>, /trades?user=<addr>
  CLOB WebSocket:  real-time order book + last trade (wss, no auth)
  Polygon RPC:     raw on-chain events via public endpoint (polygon.llamarpc.com)

Premium:
  Polywhaler ($9/mo): pre-processed whale feed + Telegram alerts
  Chainstack dedicated RPC ($19/mo): lower latency than public endpoint
  Unusual Whales (paid, Jan 2026): insider-pattern detection
```

### The four archetypes of sharp wallets
1. **Information arbitrageurs**: few, large bets, 60%+ win rate, research-driven.
2. **Domain specialists**: 10–30 trades/year, one category, very deep.
3. **Algo market-makers**: high frequency, both sides, spread capture. EXCLUDE from
   follow — they hedge everything. Identify: holding_period_median < 30 min +
   simultaneous YES+NO positions.
4. **Lucky streaks**: 1–2 massive bets → high all-time P&L. EXCLUDE — survivor bias.
   Filter: require 50+ resolved trades, profit across ≥10 distinct markets.

### Wallet qualification
```python
def qualify_wallet(profile):
    return (
        profile["win_rate"] >= 0.60
        and profile["resolved_trades"] >= 50
        and profile["profit_concentration"] < 0.50   # no single trade > 50% of P&L
        and profile["holding_period_median"] > 4     # hours; not an arb bot
        and not profile["is_market_maker"]
    )
```

### Signals (in priority order)

**1. Convergence signal (primary use case — confirmation, not primary):**
When ≥3 qualified wallets independently take the same side in the same market within
48h, use as CONFIRMATION of an existing Engine 1 or 3 signal (reduces edge threshold
from 5% to 3%). Do NOT use as standalone primary signal.
```python
def convergence_signal(market_id, tracked_wallets, window_hours=48):
    recent = {w: get_recent_position(w, market_id, window_hours) for w in tracked_wallets}
    long_count = sum(1 for p in recent.values() if p == "YES")
    n = len(recent)
    if n == 0: return None
    if long_count / n >= 0.80: return "YES_CONVERGENCE"
    if (n - long_count) / n >= 0.80: return "NO_CONVERGENCE"
    return None
```

**2. Large-order signal (WebSocket only — NOT viable on cron):**
Single orders ≥$10K from a qualified wallet in market with <$100K volume.
```
Threshold:    trade_size / market_volume > 0.10
TIMING RULE:  only follow if q_yes has moved <5pp from whale's entry price.
              q_yes moved >5pp → edge already captured → DO NOT follow.
```

**3. Position persistence (conviction filter):**
Qualified wallet holding through 2+ days of adverse price movement = high conviction.
Use to upgrade a convergence signal from "WATCH" to "BET". Check via `/positions`.

### Follow vs fade logic
```
FOLLOW only when:
  - 2+ qualified wallets converged on same side in last 48h (confirmation only)
  - q_current ≤ q_entry + 0.05 (within 5pp of their entry — no slippage gap)
  - Engine 1 or 3 DOES NOT contradict (or is silent / abstaining)
  - WebSocket mode: q_current ≤ q_entry + 0.02

NEVER follow on cron alone when:
  - Entry slippage > 5pp vs whale's fill
  - Market < $10K volume (whale impact contaminates the copy signal)
  - Within 2h of resolution (terminal volatility)
  - Ultra-liquid markets (US election, large crypto): algo shops dominate
```

### Failure modes
- **Entry-price slippage**: #1 failure mode. Hard 5pp rule; no exceptions.
- **Arb bot misidentification**: algo MMs have high win rates but hedge both sides.
  Following only their YES side creates asymmetric risk.
- **Survivor-bias wallet selection**: 5 massive wins from 5 trades looks amazing.
  50+ resolved trades + profit across ≥10 markets is the floor.
- **Signal correlation to Engine 3**: if the whale is following the same news we are,
  convergence and Engine 3 are correlated, not independent. Log for audit.
- **Late exit mimicry**: when the whale exits at a loss, exit immediately. You are now
  trading without a thesis.

### When NOT to use Engine 4
- Markets with < $10K volume: whale impact contaminates their own signal.
- Within 2h of resolution: terminal volatility + entry slippage kill the trade.
- Ultra-liquid markets: professional algo shops dominate; wallet tracking has no
  advantage over the aggregate order book.
- Any cron-only deployment without WebSocket: likely negative-EV on directional bets.

---

## Cross-Engine Integration: the blend

```
p_engine1  = quant ensemble (or None)
p_engine3  = LLM swarm (or None)
copy_signal = Engine 4 convergence tag (YES/NO/None) — CONFIRMATION ONLY
bias_tags   = Engine 2 structural tags

BLEND RULE (per vertical, in order):
  1. p_base:
     If p_engine1 is not None: use as p_base (highest precision)
     Else if p_engine3 is not None: use as p_base
     Else: abstain — never bet without a model

  2. Apply Engine 2 bias correction to p_base:
     LONGSHOT_FADE in bias_tags AND p_base < q_yes → amplify NO signal
     FAVORITE_BUY in bias_tags AND p_base > q_yes → amplify YES (requires E1/E3)
     ANCHOR_CHECK in bias_tags → widen edge threshold (0.08 vs 0.05)

  3. Incorporate Engine 4 convergence:
     copy_signal agrees with p_base direction → REDUCE threshold (0.03 vs 0.05)
     copy_signal contradicts p_base → WIDEN threshold (0.10); log contradiction

  4. Final gate:
     |p_final - q_yes| > edge_threshold
     AND (p_engine3 is None OR p_std < 0.30)
     AND slippage_ok (q_current ≤ entry_price + 0.05 for copy signals)
     → place bet at quarter-Kelly via gate pipeline
```

**Engine 2 (LONGSHOT_FADE) is the ONLY engine that can trigger a standalone NO bet.**
All other engines require either Engine 1 or 3 as the primary signal source.

---

## Sources

- AIA Forecaster Technical Report — arXiv:2511.07678 (verified: 3.6x search improvement confirmed)
- PolySwarm: Multi-Agent LLM Framework for PM Trading — arXiv:2604.03888
  (CORRECTION: 50-agent swarm, confidence-weighted Bayesian aggregation, not 10-agent simple mean)
- Makers and Takers: Economics of the Kalshi Prediction Market — Bürgi/Whelan/Deng, CEPR DP20631 / GWU 2026
  (verified: takers lose 32%; contracts <10¢ lose 60%+)
- Exploring Decentralized Prediction Markets: Accuracy, Skill, and Bias on Polymarket —
  Reichenbach & Walther, SSRN 5910522 (verified: NO general longshot bias on Polymarket at market level)
- Cross-platform FLB study (Kalshi + Polymarket, 72M + 404M trades): Favorites >55% underpriced on Polymarket
- Not All Accuracy Is Equal: Prioritizing Independence in Ensemble Forecasting — arXiv:2509.21191
- Decomposing Crowd Wisdom: Domain-Specific Calibration Dynamics — arXiv:2602.19520
- Neyman & Roughgarden (2022) — extremization / Platt equivalence, alpha=√3
- Prospect theory (Tversky & Kahneman 1992) — probability weighting, FLB mechanism
- FRB FEDS 2007/012 + Hilary et al. — anchoring bias in economic consensus forecasts
- Copy Trading Masterclass — wiki/copy-trading-masterclass.md
- FrenzyCapital, Medium Apr 2026 — 2–4h overreaction delay (ASSUMPTION; treat as prior)
- Polymarket API Guide — pm.wiki/learn/polymarket-api; chainstack.com/polymarket-api-for-developers/
