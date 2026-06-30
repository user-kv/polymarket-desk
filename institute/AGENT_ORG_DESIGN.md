# Agent-Org Loop — research-backed design (the sensor -> fund step)

**Status:** design only (Opus, 2026-06-30). Not built. Build path = A6 SPEC -> Sonnet impl.
**Goal:** turn the institute from a thing that *records* market priors into a thing that
*forms its own* prior, compares it to the market, and bets the divergence through the gates.

## What the literature actually says (sources at bottom)

1. **The thesis is validated by the strongest forecaster on record.** The AIA Forecaster
   matches human superforecasters (Brier 0.1076 vs 0.1110) but **loses to market consensus
   on liquid markets and wins on easy/illiquid ones**; the *ensemble of model + market*
   always beats either alone. Our entire edge (illiquid long-tail + favorite-longshot bias)
   is precisely the regime where an independent model can dominate. We are aimed correctly.

2. **The single biggest lever is agentic search, not more models.** Iterative search with
   follow-up queries gives **3.6x** improvement in live markets (Brier 0.10 with search vs
   0.36 without). Reasoning grounded in fresh evidence >> raw model judgment.

3. **Ensemble of ~10 INDEPENDENT forecasters, simple-mean aggregated.** Diminishing returns
   past 10. Independence is load-bearing: PolySwarm runs persona-differentiated agents with
   **no inter-agent communication** to prevent anchoring. Debate/LLM-judge aggregation is
   *worse* than the raw mean (it overweights outliers + cascades sycophancy).

4. **A supervisor reconciles disagreement with TARGETED search** (not by "judging" outliers).
   Beats naive averaging (0.1125 vs 0.1199).

5. **Calibrate by extremizing toward the tails** (Platt, fixed alpha ~= 1.73) to undo the
   RLHF hedge-toward-0.5 bias. We already have `prob_calibration.py`. Caveat: calibration
   only helps once the raw judgment is on the correct side of 0.5, and our own rule says
   don't deploy it until n >= ~200.

6. **Sizing/risk that the field converged on = ours already.** PolySwarm: quarter-Kelly
   (we use KELLY_FRACTION=0.25), hard per-position caps, daily-loss auto-suspend, and trade
   only when EV>5% AND swarm-disagreement(std)<30%.

7. **Production reality: simplicity first.** Single agents match multi-agent on 64% of tasks
   at half the cost; multi-agent adds only ~2.1pp. **40% of multi-agent pilots fail** -- from
   wrong-pattern-selection and ignoring failure modes (context-overflow cost blowups,
   anchoring, infinite handoff loops), not from the idea being wrong. => build the *minimum*
   org that adds the proven lever, around the gates we already have.

## The design: a Cadence loop wrapping the existing 7-gate pipeline

Cron-driven on the VM (it already runs the sensor). One pass = perceive -> reason -> plan ->
act -> verify -> critique -> improve. Only ONE genuinely new subsystem (the Alpha Engine);
the rest is wiring around modules that already exist.

```
PERCEIVE  open markets (sensor) + newly-resolved (settle)            [built]
REASON    Alpha Engine  (NEW -- the lever):
            agentic search  (Sonnet workers, iterative)
            forecast swarm  (~10 independent personas, parallel, NO chat) -> p_i
            supervisor      (Opus: cluster disagreement, targeted search) -> p_model
            calibrate       (existing Platt extremize; gated at n>=200)
PLAN      blend   p_final = w*p_model + (1-w)*q_market   (w learned per-archetype, AIA-style;
                  PolySwarm 0.70/0.30 as the prior)
          trade-gate  |edge|>thr  AND  swarm_std<ceiling
          size    quarter-Kelly                                       [built: allocator]
GATE      cell walks Gates 1-7 unchanged (Gate-3 red-team exists)     [built]
ACT       paper executor records the bet                              [built]
VERIFY    settle from venue (two-phase honest sensor)                 [built]
CRITIQUE  autopsy + Welch-z decay + per-cell Brier                    [built: decay/gate4]
IMPROVE   recalibrate weights; proposer mints candidates; overseer    [partial]
```

### Model routing (institute standing rule, matches orchestrator-worker economics)
- **Opus** = judgment seats, few calls: supervisor reconciliation, Gate-3 red-team,
  allocator, overseer. (Capable orchestrator + cheap workers cuts cost 40-60%.)
- **Sonnet / Haiku** = the many cheap workers: agentic search, the forecast swarm, classify,
  settle.

### Pattern choice (mapped to the production decision-tree)
- Alpha Engine = **Fan-out/Fan-in** (independent swarm + statistical mean). Deliberately
  NOT Debate (sycophancy cascade; outlier overweighting).
- Whole loop = **Orchestrator-Worker** (Cadence orchestrates) + **Reflection** (supervisor)
  + the existing **Sequential pipeline** for the gates.

### Non-negotiable guardrails (because 40% of these fail)
- **Hard per-cycle token/cost budget** in the cron -- context overflow is the silent killer.
- **Look-ahead/foreknowledge defense is already structural** via the two-phase honest sensor
  (we capture q live, never reconstruct). Keep it; it is our backtest integrity.
- **Swarm independence** (no inter-agent messages) to kill anchoring.
- **Determinism seam**: every agent behind the injectable `agents/llm.py` mock -> the whole
  loop is testable fully offline (house rule).
- **Human-in-the-loop only at Gate 6** (real capital). Everything up to LIVE-MICRO may be
  autonomous; the cord to real money stays hand-pulled.

## Build order (smallest viable org first)
- **A6 (next):** Alpha Engine as a new cell baseline (`research`/swarm) + the Cadence loop
  wrapper, both behind the existing gates and the llm seam. One SPEC -> one Sonnet build.
- **Later:** persona library expansion (toward ~25-of-50 sampled), multi-archetype proposer,
  learned per-archetype blend weight w, self-mod overseer activation.

## Sources
- AIA Forecaster technical report (arXiv 2511.07678)
- PolySwarm: multi-agent LLM for prediction-market trading (arXiv 2604.03888)
- "6 Multi-Agent Orchestration Patterns for Production" (beam.ai)
- LLMs closing the gap on human superforecasters (Forecasting Research)
- TradingAgents / multi-agent LLM trading frameworks (arXiv 2412.20138)
