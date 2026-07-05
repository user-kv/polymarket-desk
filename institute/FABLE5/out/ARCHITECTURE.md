# The Institute — Converged Architecture (Fable 5)

**Version:** v4 — CONVERGED (red-team cycle 3: zero open BLOCKERs; 4 consistency fixes folded)
**Date:** 2026-07-04
**Mandate:** `../01_MISSION.md`. North star: a portfolio of forecasting cells, each clearing
the full 7-gate stack with positive NET-OF-FEE, out-of-sample, point-in-time-honest edge.
**Status of every number:** sourced (cited), derived (shown), or labeled ASSUMPTION.

---

## 0. The one-paragraph design

The Institute is a numeric-first **paper edge-proof machine** with one integrity spine
(7 gates, quarter-Kelly, cap cascade, append-only frozen-prior ledger) and a small stable of
cells; real-money deployment is blocked pending a human venue decision (O-F1/O6) that this
design does not assume away. For the 4-week proving window it fields exactly **one
graduation candidate** — the weather ensemble, the only cell with existing OOS evidence,
external ground truth, and daily cadence. **Honesty up front: whether C1 can actually reach
a powered graduation decision inside 4 weeks depends on its re-derived NET edge (W1 task,
branch pre-registered in §5); if that comes back small, the window's honest deliverable is
decisive study verdicts plus a running, correctly-powered pipeline — and zero graduations.
The design prefers that truth to a theatrical pass.** Alongside C1: **two pre-registered
decisive studies**
(C2: is the Kalshi longshot fade net-positive after fees AND a spread haircut, on a 10k+
market backtest? C3: does any price-only behavioral edge survive fees on Polymarket?) and
**two forward-only seeds** (geopolitics news at 0% fee; CPI macro). C2 additionally begins
forward paper accrual toward a properly-powered graduation at week ~10 (the payoff skew
demands ~600 forward bets, not 50 — see §5). Everything else is cut or backlogged. LLMs do
<5% of the work: news-cell forecasts, gate red-teams, weekly meta-learning.

**Venue reality (research pass, 2026-07-04): BOTH venues are geo-restricted for this AU
user.** Kalshi explicitly lists Australia as a restricted jurisdiction (gambling-law
grounds; account closure + plausible asset seizure for VPN circumvention — sourced to the
Kalshi Member Agreement plus a third-party aggregator list; **W1 task: confirm the
restricted-jurisdiction clause directly in the Member Agreement text before A2/A3 rely on
it** — red-team L1). Polymarket VPN detection = permanent
suspension + full forfeiture (PLAN/06). Therefore: the Institute proves edge on paper using
both venues' data first-class; REAL-money venue access is a human decision (O-F1/O6) that
no part of this design assumes away.

**The honesty spine is fixed. Everything else is replaceable.**

---

## 1. What the data actually supports (sampled 2026-07-04, sources verified)

| Holding | Size | Point-in-time honest? | Verdict |
|---|---|---|---|
| Polymarket resolved outcomes (Gamma+CLOB) | ~262k markets | Outcomes yes; final prices only | Ground truth for resolution; NOT sufficient for "would we have beaten the market" |
| Polymarket decision-time price series (from real trades) | 1,795 usable (≥10 trades) of 2,100 fetched | YES — each trade is a real (t, price, size) | The only honest PM backtest substrate we hold. THIN — must grow |
| Kalshi settled outcomes | 153,228 | Outcomes yes; **prices NULL in our pull** | Kalshi edges (incl. FLB) are UNBACKTESTABLE on current holdings — fetcher v2 is the unlock |
| Own live captures (weather scans 621, settled bets 26, crypto snapshots 698) | small | YES — the moat | Seed + forward-validation anchor; never sufficient alone |
| Open-Meteo forecast archive | years, free | YES (archived model runs) | Rich for FORECAST-SKILL backtests only. Net-of-fee EDGE requires decision-time market prices — for weather those exist solely in our own 621 frozen scans / 165-market ledger (small, honest) + 20 PM series. Weather's edge proof is therefore ledger-based + forward, not archive-scale (red-team c2-H3) |
| FRED/BLS vintage data | decades, free | YES (ALFRED vintages) | Macro backtestable but monthly — cannot graduate in 4 weeks |

**Consequences (these drive the whole design):**
1. Any 4-week graduation must come from **weather** (external ground truth) or **price-only
   behavioral signals** (the price series *is* the point-in-time record).
2. News/sentiment edges (geopolitics, FDA, elections) **cannot be honestly backtested on free
   data** — retrospective news search leaks outcomes (AIA-measured contamination ~1.65%;
   phantom +20–30% backtest). They run forward-only and cannot graduate inside the window.
3. The **decision-time price fetcher (fetcher v2)** is the highest-leverage build item in the
   entire plan: it converts 153k Kalshi outcomes + 260k PM outcomes from "trivia" into
   backtest ground truth.

---

## 2. Market universe — in / cut, each with a net-of-fee reason

**Fee schedules (both sourced via 2026-07-04 Opus research pass):**
- **Polymarket** (dynamic model, rolled out ~Mar 30 2026, docs.polymarket.com/changelog):
  `fee = C·rate·p·(1−p)`; max taker per 100 shares: geopolitics **$0**, sports $0.75,
  politics/finance/tech $1.00, econ/culture/weather $1.25, crypto $1.80. Makers pay zero;
  20–25% of taker fees rebated to makers. **Applies only to markets deployed on/after
  activation** — pre-fee markets in our history are fee-free (backtests must be
  fee-regime-aware; forward edge must always assume the fee ON).
- **Kalshi** (kalshi.com/docs/kalshi-fee-schedule.pdf): taker
  `fee = ceil(0.07·C·P·(1−P))` per side (0.035 for S&P/Nasdaq index markets); maker fee
  = 25% of taker **since April 2025** (the "makers trade free" era is over — any evidence
  predating this is stale). Settlement itself is free, so positions held to expiry pay
  one-way only. **Side-specific consequence (derived):** the longshot BUYER (YES at 10¢)
  pays ~6.3% one-way — but the longshot FADER (NO at 90¢) pays 0.07·0.9·0.1/0.90 ≈ **0.7%
  one-way** (~0.3% at 95¢). Fading longshots sits in Kalshi's cheap-fee zone, exactly like
  the PM NO-side strategy.

### IN — the 4-week active set

| Cell | Venue routing + why | Edge, net-of-fee | Backtest substrate | Can graduate in window? |
|---|---|---|---|---|
| **C1 Weather ensemble** (existing). Evidence stated honestly: `yes_raw` **+21.9% GROSS ROI, 165 OOS mkts** (YES-side — the near-0-fee NO-longshot argument does NOT bless this number; W1 task: re-derive it net at actual entry prices/sides from the existing ledger, noting most were pre-fee-regime PM markets). NO-side longshot evidence is 8/8 wins, n=8 — anecdotal, not proof | **Both venues, paper** (Kalshi: 2,508 resolved weather mkts held; PM: 7,287 held, 1.25% cap, ~0 at price extremes). Real-money venue = O-F1/O6 human call | STRUCTURAL: NWP ensemble vs crowd + tail mispricing | Open-Meteo archive + Wunderground/NWS resolution + own 621 frozen scans (our captured decision-time prices) — no *fetched archive* venue price history needed | **Only capable candidate.** Graduation conditional on the W1 net re-derivation and its pre-registered branch (§5) — expected-n may exceed the window; n≥50 is Gate 4's floor, never the claimed proof |
| **C2 Kalshi longshot fade** (Engine B) — **demoted from graduation candidate to backtest-study + forward seed** (red-team B1: at a 93% win-rate target, n=50 forward has ~25% power vs the 90% breakeven; a real decision needs ~600 forward bets ≈ week 10) | **Kalshi data/paper only** (AU access unresolved — O-F1) — FLB bias robust there (Bürgi/Deng/Whelan CEPR DP20631, 300k+ contracts to Apr 2025: takers lose 32%; <10¢ contracts lose 60%+); CONTESTED on PM (Reichenbach & Walther SSRN 5910522) | Behavioral. **The BIAS is durable (prospect-theory demand); the FADER'S NET EDGE is perishable** — fee regimes and crowding compress it, and the cited data ends exactly where Kalshi's Apr-2025 maker fees begin. Net profitability is NOT established by any source; the backtest's job is to establish or kill it. Costs modeled: fee ≈0.3–0.7% one-way with `ceil()` rounding at real contract counts, **PLUS the per-market HISTORICAL spread measured from the candlesticks themselves** — Kalshi candles carry yes_bid/yes_ask, so the backtest fills at the measured ask side, with a 1¢ half-spread as the FLOOR only, never the estimate (red-team c2-H4: illiquid sub-10¢ books quote 3–5¢ wide; a flat 1¢ would flatter the verdict); fillability/depth remains an untested ASSUMPTION until F3 tape exists | Kalshi candlesticks — **confirmed publicly available for settled markets, no auth** (`GET /historical/markets/{ticker}/candlesticks`, 1m/1h/1d; docs.kalshi.com) via fetcher v2 | **NO.** In-window deliverable = the backtest VERDICT (≥10k mkts, ≥+2% net after fee+haircut) + forward seed start. Graduation ≈ week 10 via SPRT on net ROI (§5) |
| **C3 Polymarket behavioral validation STUDY** (not a betting cell) | Polymarket data only | Pre-registered study, no edge assumed. Decides J10/O6: does ANY price-only signal (longshot fade, favorite underpricing >55¢ per cross-platform study, horizon compression) clear its fee bucket on PM? | Our 1,795 price series now; +fetcher v2 expansion to ≥20k stratified markets | n/a — output is a GO/NO-GO for a future PM behavioral cell |
| **S1 Geopolitics news cell** (Engine C, seed) | **Polymarket** — 0% taker makes 1–2% edges viable; Kalshi has only 16 geopolitics mkts in our pull | INFORMATIONAL + base-rate STRUCTURAL. Cannot be backtested honestly (news look-ahead) — forward paper only | Forward captures only (becomes moat) | NO — seeds Gate-4 sample for a later window; graduation ≥8–12 weeks |
| **S2 CPI/macro cell** (Engine A, seed) | Polymarket (1.0% fee) and Kalshi macro (978 mkts) | STRUCTURAL anchoring vs consensus; 2–4% net est. (PLAN/01, ASSUMPTION until OOS) | ALFRED/BLS vintages — honest but monthly | NO — ~1 print in window. Keep running; do not count it |

### CUT / DEFERRED (each with the one-line reason)

- **Crypto price levels (both venues):** options-market arb + PM 1.8% fee; Kalshi crypto is
  the same professional counterparty. No retail crowd to beat. (PLAN/01 J1.) The 697 crypto
  price series we hold serve C3 calibration research, not betting.
- **Sports models:** user sequencing veto + 45% wash-trading volume haircut (Columbia 2025)
  + closing-line efficiency. Note: C2 will mechanically trade Kalshi *sports* longshots as
  part of the venue-wide fade — that is a price-only behavioral position, not a sports model.
  Flagged to user in OPEN_DECISIONS (O-F2) rather than silently assumed.
- **Copy-flow as a directional engine:** cron-cycle entry slippage is likely negative-EV
  (PLAN/02 Engine 4); demoted to (a) confirmation signal, (b) **forward trade-tape capture
  on BOTH venues starting week 1** — capture is cheap, retroactively impossible for Kalshi
  (5c retrofit exception invoked: the tape cannot be back-filled later at any cost), and
  feeds a post-window copy/fade cell. Directional copy stays in BACKLOG until WebSocket.
- **FDA, elections, AI/tech milestones, esports, Musk tweets, IPO, recession, DeFi events:**
  real theses (PLAN/01) but all news-driven or slow-cadence → cannot graduate in-window.
  BACKLOG, ranked, with their PLAN/01 pre-registered kills intact.
- **FX/commodities/F1/celebrity/in-play:** CUT outright (PLAN/01) — efficient or unresolvable.

---

## 3. The edge engines (re-ranked by what is provable)

The 4-engine taxonomy survives, but the 4-week ranking is inverted from the original plan:

1. **Engine B — behavioral, price-only.** The workhorse for VALIDATION. It is the ONLY
   engine whose backtest is automatically point-in-time honest (the signal is the price
   itself). Durability stated precisely: **the underlying bias is durable; the fader's net
   edge is perishable** (crowding + fee-regime changes compress it) — so Engine B cells get
   decay monitoring sized for their payoff skew (Welch-z windows scaled so the test has
   ≥50% power against a 1pp win-rate drop, not a fixed n=50). Kalshi fade is its flagship
   hypothesis; PM deployment gated on C3. Standalone bets: NO-side fade only. Never YES on
   Engine B alone (PLAN/02 rule kept).
2. **Engine A — quant ensembles.** Weather (proven) + CPI (seed). Mixture-variance combine,
   inverse-RMSE walk-forward weights, pairwise error-correlation audit <0.7 as a build gate,
   Platt only at n≥200 — all inherited unchanged from PLAN/02; they survived their own red-team.
3. **Engine C — news/LLM.** Geopolitics seed only, 0-fee venue only, forward-only, token
   budget ≤$0.02/market, and the standing bar: must beat the cheap behavioral baseline on
   the same markets before it earns budget (PLAN/02 kill kept).
4. **Engine D — copy-flow.** Confirmation-only + tape capture. No directional trades.

Blend rule, threshold modifiers, and "Engine 2 fade is the only standalone" all carried
forward from PLAN/02 §Cross-Engine unchanged.

---

## 4. The risk & gate spine (fixed; never self-modified)

Inherited from PLAN/05 with its 2026-06-30 hardening, plus four amendments:

- 7 gates: statistical → mechanism → red-team → forward lockbox (n≥50 OOS, ≥4-week span,
  **net-of-fee EV**) → portfolio → capital → decay (Welch-z, n≥50 windows).
- Quarter-Kelly × calibration_quality; cap cascade CELL 10% / CLUSTER 25% / **MACRO 15%** /
  TOTAL 60%; book halt −15%; cell halt −20%; $5 min bet; no auto-reload.
- **Amendment A1 — multiple-testing correction is a gate, not advice (family frozen at
  pre-registration):** the test family is enumerated and FROZEN before any result is seen —
  the 4 non-C3 cells/studies of §5 plus C3's k named buckets (C3 enters AS its buckets —
  no double-counting; k is named at the end-W1 freeze, and C3 buckets enter e-BH via a
  pre-registered p-to-e calibration since they are batch tests, not SPRTs), one flat
  family — corrected ONCE at
  the day-28 report using **e-BH (e-value Benjamini-Hochberg)**: SPRT likelihood ratios ARE
  e-values, so sequential members and batch members combine coherently in one anytime-valid
  FDR procedure (red-team c2-H5 — classical BY cannot mix a week-10 SPRT with day-28
  batch p-values; BY's advantage over BH is under negative/arbitrary dependence, c2-L10).
  Members with no in-window statistic (S1, S2) carry e-value 1 — counted, conservative,
  stated now so the family never unfreezes (c2-M9). An SPRT boundary hit BEFORE the day-28
  readout is provisional until the family correction; one hit at n far below expected-n
  triggers Tier-B review, not auto-accept (c2-M8). A C3 bucket that survives feeds a future
  cell WITHOUT re-testing against a second family. New cells born later start a new,
  separately pre-registered family (C2's ~week-10 decision belongs to that successor family
  and is corrected there).
- **Amendment A2 — venue forfeiture enters the sizing math, PER VENUE:** research confirms
  BOTH venues are restricted for AU (Kalshi lists Australia explicitly; PM VPN detection =
  permanent forfeiture). Each venue's real-money balance is capped:
  `VENUE_BALANCE_CAP[v] = min(0.30 × bankroll, $500)` [ASSUMPTION — user sets dollar caps
  at go-live]. The gating inequality — expected forfeiture loss (p_detect × balance) <
  expected cumulative net edge on that venue over the horizon — is **uncomputable while
  p_detect is unknown (red-team M1, accepted): A2 is a PLACEHOLDER mechanism whose gate
  output is "CANNOT CERTIFY", never "pass", until an empirical p_detect basis exists or the
  user supplies one and signs it.** Its real function today is to force the forfeiture term
  onto the go-live worksheet where the human must confront it (GO_LIVE_TRIGGER.md). No
  venue is treated as "safe."
- **Amendment A3 — correlated-venue shock:** cells on the same venue share forfeiture/oracle
  risk regardless of market family → venue is a factor in the correlation model, alongside
  archetype. UMA-dispute clusters (PLAN/06 §4.2) cap: no more than 10% of bankroll in PM
  markets sharing one resolution event.
- **Amendment A4 — ruin restatement at $500 (forfeiture modeled as an independent event,
  red-team M3):** forfeiture seizes the ENTIRE venue balance regardless of position P&L and
  can coincide with the worst correlated trading day on the other venue. Joint worst case:
  full venue balance (30% cap) + macro-cluster loss (15%) elsewhere = **−45%, requiring
  +82% to recover**; halts stop new bets but neither unwind exposure nor prevent seizure.
  Survivable exactly once; therefore the venue cap and the macro cap may never be raised in
  the same review cycle, and a second forfeiture-exposed venue is never funded while the
  first is live. [Derived from PLAN/05 §3.1 + A2.]

Gate code, ledger append-only-ness, and freeze semantics are Tier-0: no autonomous process
may modify them (3-tier leash, PLAN/08).

---

## 5. Pre-registered metrics, samples, kills (decided now, before results)

**Sample-size honesty (red-team B1, accepted):** heavily-skewed payoffs (−0.90/+0.10) make
win-rate tests at n=50 powerless (SE ≈ 3.8pp vs a 3pp effect; power ≈ 25%). Therefore all
skewed-payoff cells graduate via a **sequential net-ROI test (SPRT / always-valid CI)** with
H1 effect size taken from the backtest, and the pre-registration states the expected n to
decision. n=50 remains only the *minimum floor* Gate 4 inherits, never the claimed proof.

| Cell/Study | Success metric (net of fee + spread haircut) | Sample plan (with expected n to decision) | Kill threshold (never moved) |
|---|---|---|---|
| C1 weather | Forward net ROI > 0 AND mean_S > 0 vs price_follow baseline, SPRT-confirmed | **Powered off the W1 net re-derivation, not the gross number (red-team c2-B1).** SPRT pre-registered with H1 = re-derived net edge δ, σ measured from the ledger's actual entry-price payoff mix (≈1.0/stake at mid prices, ≈0.3 at tail fades — NOT assumed 0.5), and an effective-n discount for same-day cross-city error correlation (bets clustered by date; one day ≈ one effective observation across correlated cities). Expected n stated at freeze; **may be several hundred — C1 may NOT graduate in-window, and the design says so** (§0). Pre-registered branch on the re-derivation: δ_net ≥ +10% → graduation plausibly weeks 4–8; +3–10% → C1 is a seed, decision weeks 8–16; < +3% → C1 demoted, the window's deliverable is verdicts only, reported plainly | Rolling-60 net ROI < −5% → halt city expansion, diagnose; < −15% → retire cell |
| C2 Kalshi fade (study+seed) | **Backtest verdict:** net edge ≥ +2%/bet after fee (ceil-rounded at real contract counts) AND the per-market MEASURED half-spread from candle bid/ask (1¢ as floor only), across ≥10k stratified settled mkts, 4 time-ordered folds **each containing ≥30 YES-resolving sub-10¢ loss events** (else the fold test is theater — red-team M4) | Forward: SPRT on net ROI, expected n to decision ≈ 400–800 [derived: ROI SE over n bets ≈ 0.30/√n vs +2% mean] ≈ week 10 at daily cadence | Backtest < +1% after haircut → never deploys. Forward SPRT accepts H0 → retire; no sample-widening rescue |
| C3 PM study | Any pre-registered signal bucket (longshot fade; favorite >55¢ underpricing [ASSUMPTION — single cross-platform study, SSRN 72M/404M trades, unreplicated]; horizon compression) with net edge > 0 under the day-28 family correction (A1) | All available usable price series after the W1 coverage probe (target ≥20k; **bars re-anchored to measured availability before the pre-registration freeze — the probe result, not the target, is binding**), ≥500/bucket else bucket is dropped as untestable | No bucket survives → PM behavioral cell is DEAD; record and stop re-testing until a new data class exists |
| S1 geopolitics | Brier < market Brier AND net ROI > 0 | n≥50 forward (near-symmetric payoffs) | 50 mkts ROI < 0 → suspend Engine C for archetype (token budget dies with it) |
| S2 CPI | Beats consensus-anchor baseline on Brier | n≥12 prints (≈1 yr) | 24 prints net ROI < 0 → retire (PLAN/01 kill kept) |

Kill thresholds live in code (`gates/kills.py`), asserted by tests (5d), and are only
movable BEFORE a cell has data (Tier C, human).

**The bar LADDER (deliberate, not a contradiction — red-team c2-H6):** the §5 bars admit a
cell to *paper* forward seeding; GO_LIVE_TRIGGER's stricter bars (net edge ≥ 2× all-in
venue cost, per-venue-powered SPRT on the venue being funded — pooled graduation never
funds a venue by itself) admit *real money*. The paper stage exists precisely to refine the
edge estimate; a cell that passes §5 but never clears the go-live floor stays paper
indefinitely, and that is a correct outcome.

---

## 6. Agent org (numeric-first, LLM surgical)

Inherited from PLAN/04 (Python CADENCE orchestrator, no reasoning coordinator; roles with
enforced I/O schemas; per-pass cost circuit breaker ~$0.63 base / $3 hard cap) with one
change: **the entire 4-week window runs with Engine C confined to S1**, so the standing
LLM bill is a single Haiku swarm on ≤20 geopolitics markets/day + weekly Opus red-team/
meta-learning calls. Arithmetic shown: 20 mkts × 10 Haiku workers × 1.5k tok ≈ 300k tok/day
≈ $0.30–0.40/day at Haiku $1/$5 per MTok (PLAN/04 rates) + ~2 Opus calls/week. All other
decisions (weather, fades, gates, sizing) are numeric with zero LLM calls — LLM-touched
markets ≈ 20 of ~500+ scanned daily, hence "<5% LLM work".

Build-phase routing (5b): Fable 5 architecture/integration; Opus 4.8 research + gate
red-teams + code verification; Sonnet fetchers/harness/adapters; Haiku bulk classification
(e.g., labeling 153k Kalshi markets into verticals — already partially done by
coverage_report.py).

---

## 7. The second brain (the moat's engine, designed to not overfit)

Purpose: the machine gets measurably smarter with age in ways a copyist cannot fast-forward.

- **Lesson ledger (append-only):** every settled bet writes
  `(frozen_prior, inputs_hash, venue, fee_paid, outcome, pnl, error_decomposition)`.
  Error decomposition separates model error vs calibration error vs execution slippage —
  so improvement targets the right layer.
- **Calibration state:** per-model RMSE weights, per-archetype bias (shrinkage-damped),
  per-archetype blend w ∈ [0.50, 0.90], Platt at n≥200 — all as PLAN/08, each with its
  pre-registered revert-to-baseline kill.
- **Meta-learning (weekly, Tier B):** Haiku labels settled bets; Sonnet distills candidate
  cross-vertical patterns; every pattern is a HYPOTHESIS that must validate on a held-out
  time-ordered slice before it may adjust any weight (PLAN/08 J15). Unvalidated patterns
  expire in 30 days.
- **What compounds and cannot be copied:** frozen forward captures (both venues), fee-paid
  actuals (true realized cost curves vs published schedules), decay baselines, and the
  negative results (killed strategies with their data) — a copyist must re-lose that money.
- **Leash:** Tier A (auto): recalibration within bounds. Tier B (digest + audit trail):
  weight changes >20%, new pattern activation. Tier C (human): new cells, kill-threshold
  changes (only allowed BEFORE a cell has data), venue changes, anything touching gates.

---

## 8. The free-data plan (fetchers → what graduates)

| # | Fetcher | What it pulls | Feeds | Week |
|---|---|---|---|---|
| F1 | **fetcher v2 (decision-time prices)** — THE unlock | Kalshi candlesticks (`GetMarketCandlesticks`, granularity 1h/1d) for settled markets, category-stratified: weather → sports → crypto → politics; PM `/trades` expansion 2.1k → ≥20k markets stratified by vertical; both append-only + point-in-time index `price_at(market_id, t)` with a no-look-ahead property test | C2 backtest, C3 study, all future venue routing | Build days 1–5 (Sonnet), verify (Opus), run continuously |
| F2 | Open-Meteo archived model runs, +20 cities | Historical per-model forecasts + observed | C1 expansion + calibration n≥200 | Days 1–3 (extends existing papertrader fetcher) |
| F3 | Trade-tape capture (forward, both venues) | PM Data-API trades + Kalshi public trades, hourly append | Copy/fade cell (post-window); moat | Day 5+, passive |
| F4 | ALFRED/BLS vintage puller | Point-in-time macro vintages | S2 | Week 2, low priority |

Graduation map (honest version): **only C1 can graduate inside the window.** C2 and C3
deliver decisive study verdicts; C2 additionally starts a forward seed whose SPRT decision
lands ≈ week 10. S1/S2 seed. Nothing else is claimed.

### 4-week schedule
- **W1, day 1 — MINIMAL READ-ONLY PROBE SCRIPT first (breaks the c2-H7 circularity: the
  probe cannot depend on the day-5 fetcher):** ~100 lines, no indexing, no persistence
  guarantees — samples (a) PM long-tail trade counts (the 85% usable rate WILL fall as we
  go less liquid), (b) Kalshi candlestick rate limits + earliest retrievable candle date
  (the `/historical/` cutoff is undocumented) + bid/ask presence, (c) approximate count of
  YES-resolving sub-10¢ events per quarterly fold.
- **End-W1 — pre-registration FREEZE** (after both the probe and F1 have landed): §5's
  sample bars re-anchored to MEASURED availability and committed to git before any study
  result is computed. If Kalshi history is too shallow for 4 folds, C2 re-registers with
  the folds the data supports — before results are seen.
- **W1:** F1+F2 built & verified; C1 net re-derivation from the existing ledger (feeds the
  §5 branch); C1 city expansion live; S1 starts forward capture; F3 tape starts (validates
  the candle-measured spreads against live books and covers fillability forward).
- **W2:** C2 backtest on Kalshi candlesticks; verdict recorded either way. If ≥+2% net
  after fee+haircut → C2 forward paper seed goes live across daily-resolving Kalshi markets.
  C3 study executes.
- **W3–4:** forward lockbox accrual (C1 both venues; C2 seed); Gate 1–3 runs (Opus
  mechanism + red-team seats); day 28: portfolio report — which cells passed which gates
  under the frozen e-BH-corrected family (A1), with the go/no-go evidence bar per
  GO_LIVE_TRIGGER.md.

---

## 9. Venue routing summary (the standing rule)

```
route(market):                      # paper routing; real-money routing additionally gated by A2 + O-F1
  if family == weather:            trade BOTH (fader-side fees cheap on both; deepest sample fastest)
  elif signal == behavioral_fade:  Kalshi ONLY (FLB robust there; contested on PM until C3 says otherwise)
  elif family == geopolitics/news: Polymarket ONLY (0% taker; Kalshi coverage negligible: 16 mkts held)
  elif family == macro:            price-point fee comparison per bet: Kalshi 0.07·P·(1−P)/position
                                   vs PM 1.0% cap scaled by p(1−p) — computed, not assumed
  else:                            no route (not in the active set)
```
Real-money reality (research pass): **Kalshi lists Australia as restricted; PM requires VPN
in breach of ToS.** Neither venue is a safe home for real capital from AU. The design
therefore proves edge venue-accurately on paper, and the go-live decision (which venue, what
caps, whose account/jurisdiction) is escalated intact to the human — OPEN_DECISIONS O-F1/O6.
Nothing in this architecture depends on that answer.

---

## 10. The moat (what compounds)

PLAN/07's honest matrix stands. This design adds three compounding assets: (1) dual-venue
frozen forward captures incl. realized-fee actuals, (2) the C3 negative/positive result —
either way it is venue-specific calibration knowledge competitors must re-derive, (3) the
Kalshi trade tape from week 1 (cannot be back-filled). Model sophistication is treated as
an 8–12-week head start, not a moat.

---

## 11. What would falsify this design (standing red-team questions)

1. ~~Kalshi candlesticks unavailable~~ RESOLVED: confirmed public for settled markets
   (docs.kalshi.com, `/historical/` path). Residual risk: unstated rate limits and the
   exact historical-cutoff date — fetcher v2 must handle both defensively.
2. The fade's net edge fails the +2% backtest bar — plausible: literature documents only
   "small positive" high-price returns, and post-Apr-2025 maker fees make older maker-side
   evidence stale. If net < +1% → C2 never deploys; that outcome is a valid, valuable result.
2b. Fee-regime leakage: backtests spanning the 2026 fee activations must apply each
   market's actual fee regime at its deploy date, while FORWARD edge claims always assume
   fees ON. Asserted as a harness test, not prose.
3. C3 finds nothing on PM → PM carries only 0-fee news markets; fine — that is the answer,
   not a failure.
4. Weather edge was city-idiosyncratic → city expansion dilutes it; rolling kill catches
   this within the window.
5. Both venues inaccessible for real money (AU) → the Institute remains a paper edge-proof
   machine and O6 escalates: alternate venue or capital partner is a HUMAN decision.
