# The Institute — Agent Organisation & Autonomous Runtime
## Plan Document 04 · PLANNING ONLY · Not built

**Status:** research-backed design (2026-06-30). Build path: A6 SPEC → Sonnet impl.
**Depends on:** 00_CHARTER.md (mandate), AGENT_ORG_DESIGN.md (earlier pass, extended here).
**Purpose:** define the living agent-org that *runs* the institute — roles, model routing,
orchestration pattern, control loop, frameworks, and guardrails — so implementation has
a single authoritative spec to build against.

---

## 1. What the Runtime Must Do

The institute is a cron-driven, cost-conscious, offline-testable prediction-market fund
running on a single GCP VM. The runtime must, every cadence tick, close a complete loop:

```
PERCEIVE  → RESEARCH → FORECAST → GATE → ALLOCATE → EXECUTE
     ↑                                                   |
IMPROVE ← CRITIQUE ← SETTLE ←————————————————————————→ |
```

Critically, this is NOT a real-time reactive system. Markets resolve over days/weeks.
The loop runs on a cron schedule (hourly scan, daily settle, weekly calibrate) and must
be idempotent — re-running a tick on the same data produces the same output, no doubles.

---

## 2. The Research Baseline (what the literature says)

All design decisions below are grounded in three bodies of evidence:

**[a] The AIA Forecaster finding (arXiv 2511.07678):** LLM-based forecasters match human
superforecasters on long-tail/illiquid markets and lose to liquid consensus — the exact
regime we target. The ensemble of independent model + market always beats either alone.
This validates the p_final = w·p_model + (1-w)·q_market blend as our core architecture.

**[b] PolySwarm (arXiv 2604.03888):** 50-persona swarm, 25 sampled per scan, NO
inter-agent communication (to preserve independence), Bayesian aggregation, 70/30
model/market blend, quarter-Kelly sizing. The definitive production proof-of-concept
for our exact use case. Key guardrails: swarm_std > 30% → no trade; daily loss limit
auto-suspend; Brier tracking per cell.

**[c] Multi-agent failure modes (beam.ai, paiteq.com, 2025-2026):** 40%+ of multi-agent
pilots fail. The named failure modes are:
1. Token-budget runaway — supervisor context grows unboundedly; five-figure bills.
2. Role collision — overlapping prompts produce redundant, not additive, output.
3. Context-window OOM — silent truncation drops the original task instructions.
4. Untraceable tool calls — no audit trail; can't reconstruct what happened.
5. Coordination cost escalation — multi-agent costs 2–6× single-agent; grows with n.

Every design decision below is an explicit response to one of these failure modes.

---

## 3. Agent Roles & Org Chart

### 3.1 Role Definitions

```
┌─────────────────────────────────────────────────────────────────┐
│                        OVERSEER (Opus)                          │
│  - Reviews any self-modification proposal (strategy/code/param) │
│  - Holds the capital-activation cord (Gate 6, human co-sign)    │
│  - Weekly digest: drift, performance, budget, anomalies         │
│  - Runs on demand only; NOT in the hot path                     │
└─────────────────────────┬───────────────────────────────────────┘
                          │ escalates to / reports to
┌─────────────────────────▼───────────────────────────────────────┐
│                     CADENCE (Sonnet)                            │
│  Pure orchestrator. Reads cron tick, dispatches workers,        │
│  collects results, writes state. No LLM reasoning of its own.   │
│  Implements the perceive→...→improve loop. One instance.        │
└──┬──────────────┬───────────────┬──────────────┬───────────────┘
   │              │               │              │
   ▼              ▼               ▼              ▼
RESEARCHER    FORECASTER(S)   GATE/ALLOCATOR  SETTLE/MONITOR
(Sonnet)      (Haiku workers  (Opus judgment  (Haiku)
              + Opus super)   seats)
```

### 3.2 Agent Role Contracts

**RESEARCHER (Sonnet, 1–N workers, fan-out)**
- Input: open market question + archetype label + existing priors
- Job: agentic iterative search (2–3 rounds of follow-up queries), extract evidence,
  return structured evidence bundle {facts, sources, last_updated, confidence_note}
- NEVER returns a probability — that is the forecaster's job
- Per-run token budget hard cap: 8K tokens/worker
- Failure mode defence: role-collision → explicit no-forecast output schema enforced

**FORECASTER SWARM (Haiku workers, Opus supervisor)**
- Workers: 10–25 independent Haiku instances, each with a distinct persona prompt
  (macro-economist, contrarian, base-rate statistician, domain specialist, etc.)
- NO inter-agent communication during individual inference (PolySwarm finding: anchoring
  from peer sharing worsens aggregate Brier vs. simple mean)
- Each worker outputs: {p_i, rationale_one_sentence, confidence_flag}
- Aggregation: simple mean of p_i (debate/LLM-judge aggregation is WORSE — it over-
  weights outliers and propagates sycophancy; PolySwarm, AGENT_ORG_DESIGN §3)
- Supervisor (Opus, 1 call): receives the distribution; if swarm_std > 30% OR any
  p_i is an outlier (>2σ), runs targeted search to resolve disagreement — does NOT
  re-weight by "judgment," only by new evidence. Returns p_model.
- Per-cycle budget: 25 Haiku workers × 2K tokens + 1 Opus call × 8K = ~58K tokens
  (Haiku portion ≈ $0.006; Opus portion dominates at ~$0.24 — acceptable per cycle)

**MECHANISM-JUDGE (Opus, 1 call, Gate 2)**
- Evaluates whether a proposed strategy has a plausible causal mechanism
- Adversarial: tasked to FIND the mechanism flaw, not confirm the strategy
- Structured output: {passed: bool, mechanism_flaw: str|null, required_fix: str|null}
- Runs only in the PIPELINE (new strategy proposals), not in the hot cadence path

**RED-TEAM (Opus, 1 call, Gate 3)**
- Tasked to construct the strongest possible counter-argument to the strategy surviving Gate 2
- Explicitly instructed: "You succeed if you kill this idea"
- Output: {survived: bool, strongest_attack: str, rebuttal_required: bool}
- Same as above — pipeline only, not hot path

**ALLOCATOR (Sonnet + deterministic rules)**
- Input: p_final per market, bankroll, existing positions, correlation clusters
- Runs quarter-Kelly + cap cascade (already built in institute/portfolio/book.py)
- The LLM role here is minimal: Sonnet checks for portfolio-level anomalies only
- Hard rules are deterministic (Kelly fraction, max-per-market cap, daily loss halt)
- Real-money guard: fake-paper mode vs live mode is a flag checked here and ONLY here

**SETTLER (Haiku, scheduled)**
- Polls Wunderground/venue for resolution of open bets
- Marks settled rows in bets.csv with outcome + timestamp
- Triggers CRITIQUE on each newly settled row
- Cheap, high-volume, no reasoning required → Haiku

**MONITOR (Haiku, always-on)**
- Tails cadence logs; alerts on: token spend > budget threshold, error rate spike,
  zero bets placed 3 consecutive cycles, settlement failures
- Pushes to a dead-simple alert file (monitor_alerts.json); Overseer reads it weekly
- NOT a real-time pager — this is a cron-driven fund, not HFT

**CRITIQUE / AUTOPSY (Sonnet)**
- Runs after each settlement batch
- For each settled bet: {predicted_p, actual_outcome, edge_claimed, gate_verdicts}
- Produces per-bet autopsy: what was right, what was wrong, which gate should have caught it
- Accumulates into autopsy_log.jsonl — feeds the self-improvement loop (see doc 08)
- Pattern: Reflexion (Shinn et al.) applied to bet-level feedback

---

## 4. Orchestration Pattern

### 4.1 Pattern Choice & Justification

The institute uses a **Hybrid: Orchestrator-Worker + Fan-Out/Fan-In + Sequential Pipeline**,
NOT a pure peer-swarm or hierarchical multi-supervisor design.

**Why Orchestrator-Worker at the top level:**
- Cadence is the single orchestrator; all agents are workers with defined input/output contracts
- This is the pattern the production literature (beam.ai, paiteq, 2025-2026) converges on
  for cron-driven, cost-budgeted, offline-testable systems
- Avoids the peer-handoff failure mode (infinite loops, untraceable tool calls)
- Cadence is stateless across calls; state lives in files (bets.csv, calibration.json,
  autopsy_log.jsonl) — session as ephemeral, files as source of truth

**Why Fan-Out/Fan-In for the forecast swarm:**
- Independent personas, parallel execution, statistical aggregation
- NOT Debate — PolySwarm and AGENT_ORG_DESIGN §3 both confirm debate degrades Brier
- NOT Hierarchical (supervisor-of-supervisors) — unnecessary indirection; one Opus
  supervisor call is sufficient for disagreement resolution

**Why Sequential Pipeline for the gates:**
- Gates 1-7 are already built as a strict sequential pipeline (institute/pipeline.py)
- Gate dependencies are causal: you cannot run Gate 3 (red-team) before Gate 1 (stat)
- This is the correct pattern for deterministic, ordered workflows

**Why NOT LangGraph (for now):**
- LangGraph adds a Postgres checkpointer, a graph-state store, and a deployment runtime
  on top of what we need. On a single GCP VM with cron + file-based state, this is
  infrastructure overhead without benefit.
- LangGraph 1.0 (stable) is the right upgrade path once the institute needs durable
  mid-run state recovery (i.e., when a 30-minute forecast run must survive a VM restart)
- For now: plain Python orchestration in cadence.py, with the llm.py seam providing
  the same abstraction LangGraph's model node would. Upgrade criteria: n_markets > 200
  AND any single cadence pass > 10 minutes

**Why NOT Google ADK (for now):**
- Google ADK (Cloud NEXT 2025) is GCP-native and attractive, but is opinionated about
  session management and adds vendor lock-in. The llm.py seam already provides the
  provider-agnostic interface; ADK would replace it rather than extend it.
- Revisit if Cadence needs to scale to parallel vertical runs on Cloud Run.

**Why NOT CrewAI / AutoGen:**
- CrewAI's role-based architecture suits enterprise workflow automation; it has no native
  support for the statistical aggregation pattern (mean-of-independent-forecasters) we need
- AutoGen's debate-style multi-agent rounds are explicitly contraindicated by PolySwarm

---

## 5. The Control Loop (Detailed)

### 5.1 Cadence Timing

```
Hourly:   PERCEIVE (open market scan, new questions)
          RESEARCH + FORECAST (for newly-opened or near-resolution markets)
          GATE + ALLOCATE (build_book over all open rows)
          EXECUTE (write paper bets / in future, live orders)

Daily:    SETTLE (resolve yesterday's closing markets)
          CRITIQUE (autopsy batch for all newly settled)
          MONITOR check (budget, error rate, alert flush)

Weekly:   CALIBRATE (refit per-model RMSE weights, Platt scaling if n>=200)
          OVERSEER digest (budget actuals, drift check, any self-mod proposals)
          PROPOSE (proposer scans for new market opportunities, mints candidates)
```

### 5.2 Idempotency Guarantee

Every cadence tick is keyed on (market_id, ts_decision). If a tick re-runs:
- Forecast already frozen → skip forecast, use stored p_model
- Bet already placed → skip execute, log "duplicate suppressed"
- Settlement already written → skip settle
- This is the "point-in-time honesty law" from the Charter, operationalised

### 5.3 State Storage (no database required at this scale)

```
data/
  bets.csv            — ledger (append-only)
  bankroll.json       — current paper capital
  calibration.json    — per-model RMSE weights, Platt params
  autopsy_log.jsonl   — per-bet critique records (append-only)
  monitor_alerts.json — rolling window of monitor events
  cadence_state.json  — last tick timestamps, budget counters
  scans/              — raw market snapshots (never re-read by cadence)
```

No Postgres, no Redis, no vector store at this stage. Files are the source of truth.
Upgrade to SQLite when cadence_state.json exceeds 1MB or query patterns emerge.

---

## 6. Model Routing (Institute Standing Rule)

Derived from the tiering finding: three-tier routing saves 51% vs uniform Opus deployment
(augmentcode.com, 2026). Rule: use the cheapest model whose error rate is acceptable.

```python
ROUTING = {
    # Judgment seats — few calls, high stakes, Opus non-negotiable
    "reason":    "claude-opus-4-8",   # strategy-gen, red-team, allocator anomaly
    "judge":     "claude-opus-4-8",   # mechanism gate (Gate 2)
    "supervise": "claude-opus-4-8",   # swarm supervisor (disagreement resolution)

    # Workers — many calls, structured output, Sonnet sufficient
    "forecast":  "claude-sonnet-4-6", # swarm worker instances
    "research":  "claude-sonnet-4-6", # agentic search workers
    "critique":  "claude-sonnet-4-6", # autopsy / reflexion

    # High-volume, low-reasoning — Haiku
    "classify":  "claude-haiku-4-5",  # market archetype classification
    "index":     "claude-haiku-4-5",  # evidence indexing
    "settle":    "claude-haiku-4-5",  # settlement parsing
    "monitor":   "claude-haiku-4-5",  # log tailing and alert detection
}
```

**Cost envelope per full cadence pass (estimated, 50 markets):**
- Haiku workers: ~500K tokens → ~$0.06
- Sonnet workers: ~200K tokens → ~$0.60
- Opus judgment calls (≤5): ~40K tokens → ~$1.60
- Total: ~$2.26/pass. Weekly: ~$15 at hourly cadence.
- Hard budget cap in cadence_state.json: $50/week; Overseer alert at 80%.

---

## 7. Guardrails (Failure Mode Defences)

| Failure Mode | Defence |
|---|---|
| Token-budget runaway | Per-agent token cap enforced in complete() wrapper; cadence_state tracks cumulative; hard stop at $50/week |
| Role collision | Each agent has a strict output schema; no agent role overlaps (researcher ≠ forecaster; supervisor ≠ judge) |
| Context-window OOM | Researcher summarises evidence to ≤2K tokens before returning; swarm workers ≤2K output each |
| Untraceable tool calls | All LLM calls log to cadence_state.json with role, model, token count, ts; autopsy_log links to source calls |
| Coordination cost escalation | Sequential gates and Orchestrator-Worker pattern; no peer-to-peer handoffs; cost/call logged always |
| Anchoring in swarm | No inter-agent communication during individual forecast inference (PolySwarm rule) |
| Real-money auto-escalation | `live_mode: false` flag in bankroll.json checked at ALLOCATOR before any execute; only Overseer can flip it with user co-sign |
| Foreknowledge violation | Point-in-time law: p_model frozen at decision time, never reconstructed post-resolution |
| Infinite loop | Cadence has a hard 90-minute wall clock limit per pass; incomplete ticks roll forward to next tick |

---

## 8. The Provider-Agnostic LLM Seam

`institute/agents/llm.py` is the ONLY place that touches model APIs. All agents call
`complete(prompt, role=..., mock=True)`. This means:
- Entire cadence loop is testable fully offline with `mock=True` (house rule from Charter)
- Swapping Anthropic → OpenAI → Ollama requires changing one file, not agent prompts
- Cost tracking lives in the seam — every real call logs {role, model, tokens_in, tokens_out}

TODO for A6: wire the real Anthropic client behind the `mock=False` path (stub shown in
current llm.py), then add the token logging and budget-halt guard there.

---

## Sources Consulted

- PolySwarm: arXiv 2604.03888 (multi-agent LLM prediction market trading, 2026)
- AIA Forecaster: arXiv 2511.07678 (LLM vs superforecasters on prediction markets)
- Multi-Agent Orchestration Patterns: paiteq.com/blog, digitalapplied.com (2025-2026)
- Claude Agent SDK production playbook: autoolize.com (2025)
- Model routing cost tradeoffs: augmentcode.com, ayautomate.com (2026)
- LangGraph vs alternatives: zenml.io, speakeasy.com (2025-2026)
- Google ADK announcement: langchain.com/resources/ai-agent-frameworks (2025)
- Self-Improving Agents survey: o-mega.ai (2026)
- Self-Evolving Agents survey: arXiv 2507.21046
- EvolveR lifecycle: arXiv 2510.16079
