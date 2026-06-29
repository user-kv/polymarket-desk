# Layer 2 — Architecture

*Serves [CONSTITUTION.md](CONSTITUTION.md). Defines the agent org, data plane, the cell lifecycle through the 7 gates, the build/verify loop, the first archetypes, and what we reuse. Models routed per owner: **Opus 4.8** for reasoning/judgement; **Sonnet 4.6 / Haiku** for scanning, classification, implementation, indexing.*

## 1. Agent org (each = a role, not a server)

| Agent | Model | Job |
|---|---|---|
| **Scout** | Haiku | Pull market universe (Gamma + Data API), snapshot context at `t₀`, dedupe → sensor stream |
| **Classifier** | Haiku | Tag each market: archetype + factor loadings + tradeability/integrity precheck (§4) |
| **Toxicity screen** | Sonnet | Counterparty-toxicity score (Seam 1); also emits smart-money-convergence signal |
| **Strategy-gen (Quant)** | **Opus** | Propose predictor hypotheses **with mechanism** (Gate 2); reads autopsy lessons; budgeted (§11C) |
| **Backtester** | Sonnet + deterministic engine | Purged/embargoed walk-forward, book-walking fills, `EV_net` + market-relative log-score; logs every trial |
| **Stat gate** | deterministic | DSR + PBO + permutation-null + SPRT (Gate 1) |
| **Red-team** | **Opus** | Adversarially break each surviving cell (Gate 3) |
| **Allocator** | **Opus** + deterministic | Portfolio-margin via factor model (Gate 5), Kelly sizing, drawdown halts |
| **Paper executor** | Haiku + deterministic ledger | Place/settle paper bets (reuse papertrader ledger/settlement) |
| **Overseer** | **Opus**, independent | Kernel-hash check, gate-order enforcement, veto (reuse desk overseer) |
| **Autopsy/Memory** | Opus reason / Haiku index | Loss autopsy → lessons → knowledge (reuse desk) |

## 2. Data plane

- **Sensor:** Polymarket Gamma (metadata) + Data API (`/trades`,`/activity`,`/positions`,`/holders`) — public, no key. Venue-agnostic seam for Kalshi later.
- **Corpus:** append-only resolved-markets store = `(context@t₀ → resolution)`, the compounding asset. Plus calibration history + **trial registry** (every hypothesis, incl. failures — §5).
- **Feature store:** per-archetype features knowable at `t₀` (weather=ensemble NWP; sports=power ratings/odds; crypto=price/vol).
- **Resolution pipeline:** per-archetype ground-truth source, integrity-checked (the §4.1 non-negotiable).

## 3. Cell lifecycle (state machine)

`PROPOSED → BACKTEST(Gate1) → MECHANISM(Gate2) → REDTEAM(Gate3) → PAPER-FORWARD(Gate4: ≥~50 resolved + ~4–6wk) → ALLOC(Gate5/6) → LIVE-MICRO → SCALE` — with **DECAY(Gate7)** able to demote any LIVE cell to paper/retired. Capital activates per cell; most stay PAPER forever (working as intended).

## 4. Build + verify loop (the autonomous cycle)

`perceive (Scout/Classifier) → propose (Strategy-gen) → backtest+gate → justify → attack → paper-forward → allocate → monitor/decay → autopsy → improve`.
**Verify discipline (carried over):** no behavioural change ships without a passing test or a clean backtest delta; Overseer + kernel hash guard each iteration. Loop runs unattended on the existing scheduler.

## 5. First archetypes (fast-resolving, for statistical power)

1. **weather-daily** — exists (papertrader = "expert #1"); migrate in as the reference cell.
2. **sports-game-winner** — schedules + power ratings/market odds; high daily volume = fast power.
3. **crypto-daily-close** — price/vol models; abundant, fast-resolving.
4. (next) **econ-release** — calendar-driven, scheduled.

## 6. Reuse vs new

- **Reuse:** desk kernel (invariants + hash), memory (store/knowledge/write-gate), autopsy, overseer, papertrader ledger/settlement/backtest harness, GCP scheduler + watchdog.
- **New:** multi-archetype sensor, classifier + factor model, toxicity screen, trial registry, the 7-gate stack, allocator, capital-activation ladder.

## 7. Build milestones (Layer 2 deliverables)

- **A1 — Data plane + predictability-map skeleton.** Sensor + Classifier + Corpus + resolution. Cheapest, highest leverage: produces the first *map* (where edge plausibly lives) before any predictor is built.
- **A2 — Evidence machine.** Backtester + Gate 1 (DSR/PBO/permutation/SPRT) + trial registry.
- **A3 — Close the loop on archetype #1+#2.** Strategy-gen + mechanism + red-team + paper executor; migrate weather, add sports.
- **A4 — Portfolio brain.** Allocator + factor model + decay gate + capital-activation ladder.

*Open: build location (extend `desk/` vs new `institute/` module) — pending owner.*
