# The Institute — Build Roadmap (synthesized from 01-08)

**Status:** PLANNING. No build authorized. Sequenced backlog with kill criteria.
Synthesizes 01_MARKET_UNIVERSE, 02_EDGE_ENGINES, 03_VERTICAL_TEMPLATE, 04_AGENT_ORG,
05_RISK, 06_EXECUTION_VENUE, 07_MOAT, 08_SELF_IMPROVEMENT.

## Sequencing principles
1. **Sharpen what exists before spreading** — cheap wins compound.
2. **Volume + confirmed edge first** — fastest honest path to a track record (n>=200 for
   Platt; ~50 resolved for Gate-4 lockbox).
3. **Behavioral FLB is the baseline in EVERY vertical** — it is the most reliable confirmed
   edge; add quant/news/flow sophistication on top only where it earns.
4. **Respect the user's sports veto on SEQUENCING** — sports is in-scope (round 1) but not
   the immediate build; user chooses when it enters (see 99_DECISIONS_LOG open item).
5. **Reconcile edge vs FEES** — a sub-market's edge must clear its taker fee (0% geopolitics
   -> 1.8% crypto) net. Re-rank any market whose edge < fee.

---

## Phase 0 — Harden the foundation (cheap, high-value, build on live code)
**Goal:** tighten the two working verticals + ship the cheapest venue-wide edge.
- **B2 — CPI third-model fix.** Replace the collapsed `nowcast` fallback with a genuinely
  independent model (PPI-based OLS or import-price index — a different INPUT variable, not a
  window on CPI). Independence detector: pairwise error corr > 0.7 = fail. Restores real
  3-model diversity + honest sigma. (Ref 02 Engine 1, 03 anti-pattern "collapsed diversity".)
- **B3 — Weather city expansion.** Add cities to the weather ensemble to accelerate toward
  n>=200 (unlock Platt) and validate the calibration loop end-to-end. Weather is the
  calibration baseline (+21.9% OOS). Fastest route to the first fully-graduated cell.
- **B4 — Behavioral engine (FLB) as a venue-wide baseline.** A reusable `behavioral` engine
  (Engine B): fade longshots <=0.15, favorite-underpricing, round-number anchoring,
  news-overreaction, horizon-compression — all from FREE market data. Deploy as a baseline
  cell across every live archetype. Broad, cheap, confirmed edge.
**Kill/success:** B2 — 3 models with pairwise err-corr < 0.7; B3 — first cell reaches n>=200
and Platt improves OOS Brier; B4 — FLB cell clears Gate 1 on >=1 archetype.

## Phase 1 — The autonomous agent-org runtime (make it run itself)
**Goal:** turn cron+modules into the 7-role Cadence organization (04_AGENT_ORG).
- **B5 — Cadence org.** Plain-Python orchestrator (defer LangGraph per 04) running
  perceive->research->forecast->gate->allocate->execute(paper)->settle->critique->improve,
  with the seven roles, model routing (Opus judgment / Sonnet workers / Haiku volume),
  per-pass token/cost budget (~$2.26/50 mkts), and the five named failure-mode defences.
- **B6 — Real LLM provider behind the seam** (the shelved A7, now justified by Engine C).
  Wire "best available" (Haiku swarm + Sonnet agentic search + Opus supervisor) behind
  `agents/llm.complete`; keep the deterministic mock for tests; the INSTITUTE_LIVE_FORECAST
  cord stays until this is real (no placeholder burn).
**Kill/success:** a single `cycle` runs the full loop autonomously on the VM within budget,
fully observable, with paper-only output; no real-money path touched.

## Phase 2 — The four edge engines as reusable subsystems (02 + 03)
**Goal:** factor the edges into engines any vertical stamps in via the template's slots.
- **B7 — Engine A (quant ensemble)** generalized from weather/CPI (mixture-variance combine,
  walk-forward RMSE, gated Platt).
- **B8 — Engine C (news/agentic)** — AIA+PolySwarm: 10-agent Haiku swarm (no comms, q hidden),
  Sonnet 3-5 iterative searches, Opus supervisor, blend w=0.70, foreknowledge audit.
- **B9 — Engine D (copy-flow)** — free Polymarket APIs (Gamma/CLOB book/Data trades); wallet
  qualification (>=60% win, >=50 resolved); convergence signal (>=3 wallets, Copy Score>=70
  -> 67.7% win); **follow only if price <= whale entry + 5pp; use whale distortion as a FADE
  signal too** (the $85M election whale lesson).
(Engine B shipped in B4.)
**Kill/success:** each engine is a tested, offline-mockable subsystem with a clean vertical
slot; each demonstrates edge on >=1 live vertical before it is trusted.

## Phase 3 — Roll out verticals by priority (template x engines)
Build order from 01 (INCLUDE list), reconciled with fees + the sports-veto:
- **Tier 1 macro:** Fed decisions; CPI YoY + more CPI variants; jobs/NFP (Engine A + B + C).
- **Tier 1 news-driven:** select politics/geopolitics where Engine C + low/zero fees give
  edge (geopolitics taker fee ~0%).
- **Sports (Tier 1 by volume — GATED on user go-ahead):** soccer/World Cup match markets,
  NBA player props (highest edge density). Engine A (ratings ensemble) + B.
- **Tier 2/3:** esports (CS2/Dota2/LoL — small volume, real edge), remaining INCLUDE list.
**Kill/success per vertical:** must clear Gates 1-3 on backtest/forward before paper capital;
CUT on Welch-z decay; never bet a market whose net edge < fee.

## Phase 4 — Self-improvement online + capital activation (08 + 05)
**Goal:** the institute adapts, and (only then) real money is considered.
- **B10 — Self-improvement loop live:** recalibration loops, strategy birth/decay (Welch-z;
  p<0.01 auto-retire, p<0.05 Overseer flag), meta-learning in `data/meta/`, the 3-tier leash
  (gate code NEVER self-modified).
- **B11 — Capital activation ladder + real-money cord:** paper -> forward-lockbox -> micro ->
  scale, quarter-Kelly + cap cascade + drawdown halts. Real money = hard manual gate + user
  co-sign, Polymarket via VPN, with the candid operational/legal caveats (06).
**Kill/success:** a cell only reaches micro-capital after the full gate ladder + explicit
user sign-off; book-level 15% drawdown halt is enforced.

---

## Dependency graph (high level)
Phase 0 (independent) -> Phase 1 (needs B4's engine pattern) -> Phase 2 (needs B5 org) ->
Phase 3 (needs engines + template) -> Phase 4 (needs a track record from Phase 3).

## Decision gates for the user (do not proceed past without sign-off)
- **G1:** approve Phase 1 scope + wiring a real (paid-per-call) LLM provider — first real spend.
- **G2:** approve sports sequencing (when/if soccer + NBA props enter).
- **G3:** approve the premium-data budget at launch (~$350-460/mo) and which feeds.
- **G4:** approve ANY real-money activation (hard gate, never automated).

## v2 — POST-HARDENING RECONCILIATION (2026-06-30, supersedes conflicts above)
The red-team pass changed several load-bearing assumptions. Where this section conflicts
with the phases above, THIS wins:
- **Favorite-longshot bias is CONTESTED on Polymarket** (SSRN 2025 finds no general
  market-level FLB here; the robust FLB is on Kalshi). So **B4 is reframed: VALIDATE the
  behavioral edge on Polymarket's own resolved data BEFORE deploying it venue-wide.** If the
  null holds, pivot to favorite-underpricing / round-number / overreaction sub-biases. FLB is
  no longer assumed — it is a hypothesis to test cheaply first. (This is the single biggest
  change: our presumed "most reliable edge" needs re-confirmation on THIS venue.)
- **New early verticals (best net-edge-per-build-hour):** GEOPOLITICS (0% taker fee makes
  thin edges viable) and FDA drug approvals (ADCOM->decision correlation, free, 4-14% net,
  domain-expertise barrier) move to Tier 1 / Phase 3 front. Macro (CPI/Fed) stays Tier 1.
- **Engines 3 & 4 DEMOTED, gated on beating cost:** Engine 3 (news swarm) is likely marginal
  net of token cost except on long-tail illiquid markets — enable per-vertical ONLY after an
  EV-vs-token-cost check passes. Engine 4 (copy-flow) is likely negative-EV on a cron due to
  entry slippage — relegate to CONFIRMATION-ONLY until a WebSocket feed exists. So Phase 2
  order = Engine 1 (quant) + behavioral-validation first; 3 & 4 are provisional.
- **Risk hardening (Phase 0/4):** add `MACRO_CAP = 0.15` (macro cells co-move; the 25%
  cluster cap still permits a 25% correlated drawdown and the book-halt fires AFTER the
  shock). Gate 4 now requires NET-OF-FEE positive EV. Welch-z decay window raised to n>=50.
- **Cost:** corrected to ~$0.63 base / ~$3 worst-case per 50-market pass; swarm workers =
  Haiku (not Sonnet); hard per-pass cost circuit breaker required in B5.
- **EXISTENTIAL pre-live checkpoint (before ANY real money):** AU-via-VPN detection = permanent
  suspension + FULL balance forfeiture, no appeal. At small bankroll this is a single-event
  total loss that can exceed all trading edge. The real-money cord (O4) must confront this
  explicitly — it may argue for staying paper-only, or a different venue/route entirely.
- **Context/memory (doc 11):** the runtime uses tiered memory (numeric state direct, per-task
  retrieval, GraphRAG only for periodic meta-learning) — build B5 against that, not naive
  context-stuffing.

## Token/continuation note
The full reasoning lives in 01-08. This roadmap + 99_DECISIONS_LOG are the entry points to
resume the BUILD. Each `Bn` is a milestone in the proven Opus-spec -> Sonnet-build ->
Opus-verify workflow.
