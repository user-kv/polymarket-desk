# The Institute — Master Charter (living document)

**Status:** PLANNING ONLY. No build authorized yet. Opus-owned; refined in a loop.
**Started:** 2026-06-30. This is the backbone the rest of the plan hangs off.

## Mission
Build a **personal, autonomous, self-improving prediction-market fund** that, after a
paper-validation run, goes **live on Polymarket (via VPN)** trading the user's own small
capital. Not a product to sell — a private edge, deployed. The institute forecasts the
long-tail of the entire prediction-market universe better than the crowd, bets only where
it has a proven edge, sizes with discipline, and compounds a track record no competitor
can back-fill.

## Locked decisions (user, 2026-06-30, rounds 1-2)
1. **Cost:** free prototype; **premium-data budget unlocked at live launch** (news,
   on-chain, smart-money, odds). Design every vertical with a free tier AND a premium
   upgrade slot.
2. **Market scope:** all four families IN — Macro/financial, Sports, Politics/geopolitics,
   Crypto/culture/science-tech. **Cut any sub-market judged un-edgeable, and say why.**
3. **Edge engines (all first-class, best-fit per market, cost-no-object to set up):**
   (a) Quant/information models, (b) Behavioral/crowd-bias, (c) News & event reasoning,
   (d) Smart-money / copy-flow.
4. **Autonomy:** autonomous + self-improving on paper (propose/retire verticals &
   strategies, recalibrate); **real money gated through the 7 gates + explicit user
   sign-off** at activation.
5. **Capital/venue:** small personal ($100s-low $1000s), Polymarket via VPN; impact
   negligible (no fund-scale capacity modeling needed yet).
6. **Runtime/agents:** "use the best available" — pick optimal agents/models/frameworks
   per job, justified in the plan. Build a real autonomous agent-org, not just cron.
7. **Moat (invest in ALL):** compounding data & track record; agent/model sophistication;
   breadth x speed; the integrated gate->allocate->settle->decay->self-improve machine.

## Non-negotiable principles (inherited + reaffirmed)
- **Point-in-time honesty law:** every forecast frozen at decision time from data
  available THEN; never sees the outcome; idempotent. This is the moat's foundation —
  a competitor cannot back-fill our frozen priors.
- **Adversarial gates before capital:** statistical -> mechanism -> red-team -> forward
  lockbox -> portfolio -> capital -> decay. Kill our own ideas cheaply.
- **Fake money until gated + signed-off.** Never auto-escalate to real.
- **Simplicity first, then depth where it pays.** Don't over-architect; deepen what earns.
- **Free now, premium-ready.** Every data path has a free default and a premium slot.
- **Deterministic, offline-testable seams.** All network/LLM behind injectable mocks.

## What already exists (do not re-plan; build ON it)
- Data plane, classifier, predictability map, 7-gate pipeline, allocator (quarter-Kelly,
  cap cascade, correlation clustering), decay (Welch-z), paper executor, settlement.
- Two live verticals: **weather** (6-model NWP ensemble, the gold standard) and
  **CPI/macro** (B1, first deep specialist; 3-model ensemble, ~2 effective until a 3rd
  free signal is added). Crypto sensor (A5) live but efficient/low-edge.
- A6 Alpha Engine (LLM forecast swarm) — built, gated off until a real model is wired.
- Runs autonomously on a GCP VM cron, pushing to origin.

## The plan's structure (documents this CHARTER spawns)
- `01_MARKET_UNIVERSE.md` — every candidate market family + sub-market: edge thesis,
  data sources (free + premium), which edge engine(s) fit, INCLUDE/CUT verdict + why,
  cadence/volume, priority. The "what to build" map.
- `02_EDGE_ENGINES.md` — the four reusable engines: best-in-class method per engine, how
  each plugs into a vertical, free vs premium implementation, failure modes.
- `03_VERTICAL_TEMPLATE.md` — the canonical anatomy of a deep vertical (the weather-bot
  blueprint generalized): data/models/ensemble/calibration/parse/sensor/baseline/adapter,
  plus per-market customization slots.
- `04_AGENT_ORG.md` — the autonomous runtime: agent roles, model routing, orchestration
  pattern, the self-improvement loop, frameworks ("best available"), guardrails.
- `05_RISK_AND_PORTFOLIO.md` — sizing, correlation, caps, drawdown halts, capital
  activation ladder for small personal capital; the real-money cord.
- `06_EXECUTION_VENUE.md` — Polymarket/Gamma + CLOB mechanics, order types, settlement,
  VPN/operational realities, what's automatable vs manual.
- `07_MOAT.md` — how each moat dimension is built and compounded; what makes replication
  genuinely hard.
- `08_SELF_IMPROVEMENT.md` — how the institute adapts: recalibration, strategy birth/death,
  proposing new verticals, the overseer gate, meta-learning across verticals.
- `09_ROADMAP.md` — sequenced, prioritized build backlog with milestones + kill criteria.
- `99_DECISIONS_LOG.md` — every judgment call + rationale (auditable; part of the moat).

## Research agenda (dispatched to parallel deep-research agents)
- **R1 Market universe:** per family/sub-market — edge, free+premium data, best engine
  fit, INCLUDE/CUT, cadence, priority. Feeds 01.
- **R2 Edge engines:** state-of-the-art for quant ensembles, behavioral/crowd-bias,
  news/agentic-search forecasting, smart-money/copy-flow tracking on Polymarket. Feeds 02.
- **R3 Agent-org + self-improvement:** best autonomous multi-agent architectures,
  frameworks/models to use, the adaptive self-improvement loop. Feeds 04 + 08.
- **R4 Venue + risk + moat:** Polymarket execution/settlement mechanics, risk for small
  capital, and how to make the whole thing hard to replicate. Feeds 05 + 06 + 07.

## Open judgment calls (to surface for user in the plan, not block on)
- Exact INCLUDE/CUT list per sub-market (research-driven; user reviews).
- Which premium feeds to budget for at launch (and rough cost).
- The self-improvement leash: how much strategy/code self-modification within guardrails.
