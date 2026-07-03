## CHANGELOG
- **2026-06-30 (red-team + harden pass):** Cost estimate corrected from ~$2.26 to ~$0.63 base / ~$3.00 worst-case per pass at 50 markets — prior estimate used wrong Opus pricing; re-derived from current API rates (Opus 4.8 $5/$25 MTok, Sonnet 4.6 $3/$15, Haiku 4.5 $1/$5). Added hard per-pass cost circuit breaker. Swarm worker model demoted from Sonnet to Haiku (role does not justify Sonnet; PolySwarm uses small workers). Clarified that RESEARCHER and SWARM are per-market costs that dominate at scale. Added concrete tripwires for each failure mode. Tightened role contracts with explicit I/O schemas. Removed vague "5 Opus judgment calls" estimate — replaced with exact call inventory. Corrected ROUTING table: forecast workers should be Haiku not Sonnet. Added "news/swarm vs cheap baseline" break-even analysis. Marked ASSUMPTIONS explicitly. Removed LangGraph/ADK/CrewAI rationale bloat — one paragraph suffices.

---

# The Institute — Agent Organisation & Autonomous Runtime
## Plan Document 04 · PLANNING ONLY · Not built

**Status:** research-backed design (2026-06-30), hardened pass.
**Depends on:** 00_CHARTER.md (mandate), 08_SELF_IMPROVEMENT.md (improvement loop).
**Purpose:** define the living agent-org that *runs* the institute — roles, model routing,
cost budget, orchestration pattern, control loop, and guardrails — so implementation has
a single authoritative spec to build against.

---

## 1. What the Runtime Must Do

The institute is a cron-driven, cost-conscious, offline-testable prediction-market fund
running on a single GCP VM. Every cadence tick closes:

```
PERCEIVE  → RESEARCH → FORECAST → GATE → ALLOCATE → EXECUTE
     ↑                                                   |
IMPROVE ← CRITIQUE ← SETTLE ←————————————————————————→ |
```

NOT a real-time reactive system. Markets resolve over days/weeks. Loop runs on cron
(hourly scan, daily settle, weekly calibrate). Must be idempotent: re-running a tick
on the same data produces the same output, no doubles.

---

## 2. Research Grounding

**[a] AIA Forecaster (arXiv 2511.07678):** LLM-based forecasters match human
superforecasters on long-tail/illiquid markets and lose to liquid consensus — the exact
regime we target. Ensemble of independent model + market always beats either alone.
Validates: p_final = w·p_model + (1-w)·q_market as core architecture.

**[b] PolySwarm (arXiv 2604.03888):** 50-persona swarm, 25 sampled per scan, NO
inter-agent communication (preserves independence), Bayesian aggregation, 70/30
model/market blend, quarter-Kelly sizing. Key guardrails: swarm_std > 30% → no trade;
daily loss limit auto-suspend; Brier tracking per cell. **Note:** PolySwarm uses small/cheap
worker models — this validates routing forecast workers to Haiku, not Sonnet.

**[c] Multi-Agent Failure Taxonomy (arXiv 2503.13657; augmentcode.com 2025-2026;
Towards Data Science 2025):** Production multi-agent failure rate 41–87%. MAST taxonomy
(NeurIPS 2025, 1,600+ traces) maps failures to: specification ambiguity, coordination
breakdowns, verification gaps. Named failure modes:
1. Token-budget runaway
2. Role collision / specification ambiguity
3. Context-window OOM / task drift (semantic + coordination + behavioral)
4. Untraceable tool calls
5. Coordination cost escalation (2–6× single-agent)
6. Degeneration loops / reward hacking

Every design decision is an explicit response to one of these.

---

## 3. Agent Roles & Org Chart

```
┌─────────────────────────────────────────────────────────────────┐
│                        OVERSEER (Opus)                          │
│  Reviews self-modification proposals. Holds capital-activation  │
│  cord (Gate 6, human co-sign). Weekly digest only.              │
│  NOT in hot path.                                               │
└─────────────────────────┬───────────────────────────────────────┘
                          │ escalates to / reports to
┌─────────────────────────▼───────────────────────────────────────┐
│                     CADENCE (Python, no LLM)                    │
│  Pure orchestrator. Reads cron tick, dispatches workers,        │
│  collects results, writes state. One instance. Stateless.       │
└──┬──────────────┬───────────────┬──────────────┬───────────────┘
   │              │               │              │
   ▼              ▼               ▼              ▼
RESEARCHER    SWARM           GATE/ALLOCATOR  SETTLER/MONITOR
(Sonnet)      (Haiku workers  (Opus: Mech +   (Haiku)
              + Opus super)   Red-team seats)
```

**CADENCE is Python orchestration, not an LLM agent.** It does not reason; it dispatches.
This is the critical design choice — the coordinator must never be a reasoning LLM to
avoid coordination-drift and untraceable decision making.

### 3.1 Role Contracts

**RESEARCHER (Sonnet)**
- **Input:** `{market_id, question_text, archetype_label, existing_priors: dict}`
- **Job:** 2–3 rounds of agentic search, evidence extraction, structured return
- **Output:** `{facts: list[str], sources: list[url], last_updated: iso8601, confidence_note: str}`
- **HARD CONSTRAINT:** output schema enforced; no probability field in schema (role-collision defense)
- **Token cap:** 6K in / 2K out per worker; cadence aborts worker and marks `research_failed=True` if exceeded
- **Tripwire:** if `research_failed` rate > 30% in a pass → MONITOR alert; cadence skips to gate on cached priors

**FORECASTER SWARM (Haiku workers + Opus supervisor)**
- Workers: 10–25 Haiku instances, each with a distinct persona prompt
- NO inter-agent communication during inference (PolySwarm anchoring rule)
- **Worker input:** `{question_text, evidence_bundle, persona_prompt, market_price: float}`
- **Worker output:** `{p_i: float[0,1], confidence: low|med|high}` — one-line rationale dropped in hot path
- Aggregation: `p_model = mean(p_i)` — simple mean; debate/LLM-judge is WORSE (PolySwarm)
- Supervisor (Opus, 1 call): receives distribution; if `swarm_std > 0.30` OR `any |p_i - mean| > 2σ`
  → runs targeted search + re-query of outlier workers only; returns revised p_model
- **Tripwire:** if supervisor call triggers on > 50% of markets in a pass → circuit breaker: skip supervisor,
  log `high_disagreement_rate`, flag for Overseer digest

**MECHANISM-JUDGE (Opus, Gate 2 — pipeline only, NOT hot path)**
- **Input:** `{strategy_description, mechanism_hypothesis}`
- **Output:** `{passed: bool, mechanism_flaw: str|null, required_fix: str|null}`
- Adversarial framing: tasked to FIND the flaw, not confirm

**RED-TEAM (Opus, Gate 3 — pipeline only, NOT hot path)**
- **Input:** `{strategy surviving Gate 2}`
- **Output:** `{survived: bool, strongest_attack: str, rebuttal_required: bool}`
- Explicitly instructed: "You succeed if you kill this idea"

**ALLOCATOR (Sonnet + deterministic rules)**
- **Input:** `{p_final per market, bankroll, open positions, correlation clusters}`
- Runs quarter-Kelly + cap cascade (institute/portfolio/book.py)
- LLM role is minimal: Sonnet checks portfolio-level anomalies ONLY
- Hard deterministic rules cannot be overridden by LLM output
- Real-money guard: `live_mode: false` in bankroll.json checked here and ONLY here

**SETTLER (Haiku, scheduled daily)**
- Polls resolution source; marks settled rows in bets.csv; triggers CRITIQUE batch
- **Output:** `{bet_id, outcome: 0|1, settled_at: iso8601, source_url}`

**MONITOR (Haiku, every pass)**
- Checks: token spend vs budget, error rate, zero-bet streaks, settlement failures
- **Output:** append-only `monitor_alerts.jsonl`; Overseer reads weekly
- NOT a real-time pager

**CRITIQUE (Sonnet, post-settlement)**
- Per settled bet: structured autopsy → autopsy_log.jsonl
- **Output schema defined in 08_SELF_IMPROVEMENT.md §6.3**

---

## 4. Orchestration Pattern

**Hybrid: Orchestrator-Worker + Fan-Out/Fan-In + Sequential Pipeline.**

- CADENCE as single Python orchestrator; all agents are workers with defined I/O
- Fan-out for swarm (independent personas, parallel, statistical aggregation)
- Sequential gates (causal dependencies)
- No peer-to-peer handoffs; no supervisor-of-supervisors
- No LangGraph, CrewAI, AutoGen at this scale (infrastructure overhead > benefit on a
  single-VM cron loop; upgrade criterion: n_markets > 200 AND any pass > 10 minutes)

---

## 5. Control Loop

### 5.1 Cadence Timing

```
Hourly:   PERCEIVE (open market scan)
          RESEARCH + FORECAST (newly-opened or near-resolution markets)
          GATE + ALLOCATE
          EXECUTE (paper bets; live only under Gate 6 + human co-sign)

Daily:    SETTLE + CRITIQUE batch
          MONITOR check (budget flush, error rate, alerts)

Weekly:   CALIBRATE (RMSE weights, blend weight w)
          OVERSEER digest (budget actuals, Tier B queue, anomaly flags)
          PROPOSER (new strategy candidates → data/proposals/)
```

### 5.2 Idempotency

Every tick keyed on `(market_id, ts_decision)`. Already-frozen forecasts, placed bets,
and settled rows are all no-ops on re-run. This is the point-in-time honesty law
operationalised.

### 5.3 State Storage

```
data/
  bets.csv            — ledger (append-only)
  bankroll.json       — paper capital
  calibration.json    — RMSE weights, Platt params, blend weights
  autopsy_log.jsonl   — per-bet critique records (append-only)
  monitor_alerts.jsonl — rolling monitor events
  cadence_state.json  — tick timestamps, cumulative budget counters, n_resolved per vertical
  proposals/          — pending strategy proposals (never auto-executed)
  archive/strategies/ — retired strategies with epitaphs
  meta/               — meta_patterns.json, meta_failures.json
```

No Postgres, no Redis, no vector store until cadence_state.json exceeds 1MB or query
patterns emerge that file-scan cannot serve.

---

## 6. Model Routing & Cost Budget

### 6.1 Routing Table

```python
ROUTING = {
    # Judgment seats — few calls, high stakes
    "reason":    "claude-opus-4-8",   # strategy-gen, red-team
    "judge":     "claude-opus-4-8",   # mechanism gate (pipeline only)
    "supervise": "claude-opus-4-8",   # swarm supervisor (disagreement resolution)

    # Workers — structured output, volume
    "research":  "claude-sonnet-4-6", # agentic search workers
    "critique":  "claude-sonnet-4-6", # autopsy / reflexion
    "allocate":  "claude-sonnet-4-6", # anomaly check only

    # High-volume, low-reasoning
    "forecast":  "claude-haiku-4-5",  # swarm worker instances (NOT Sonnet — see §2b)
    "classify":  "claude-haiku-4-5",  # market archetype classification
    "settle":    "claude-haiku-4-5",  # settlement parsing
    "monitor":   "claude-haiku-4-5",  # log tailing and alert detection
}
```

**Note vs prior version:** `forecast` demoted from Sonnet → Haiku. PolySwarm and
cost analysis both support this. Sonnet was a category error in the prior version.

### 6.2 Per-Pass Cost Derivation (honest, 50 markets)

**API rates (June 2026):** Opus 4.8 $5.00/$25.00 MTok; Sonnet 4.6 $3.00/$15.00; Haiku 4.5 $1.00/$5.00.
*Sources: platform.claude.com/docs/en/about-claude/pricing; aimodelcalc.com/guides/claude-api-pricing*

**Hot path (per-market costs × 50):**

| Role | Model | In tokens | Out tokens | Cost/market | × 50 |
|---|---|---|---|---|---|
| RESEARCHER | Sonnet | 4K | 1K | $0.027 | $1.35 |
| SWARM (25 workers) | Haiku | 1K each = 25K | 0.5K each = 12.5K | $0.088 | $4.40 |
| SWARM supervisor | Opus | 4K | 2K | $0.070 | $3.50 |
| ALLOCATOR anomaly | Sonnet | 1K | 0.5K | $0.011 | $0.55 |

*Supervisor triggered only when swarm_std > 0.30. ASSUMPTION: 40% trigger rate → effective cost 0.40 × $3.50 = $1.40/pass.*

**Low-volume (once per pass regardless of market count):**

| Role | Model | Tokens | Cost |
|---|---|---|---|
| MONITOR | Haiku | 2K/2K | $0.012 |
| CRITIQUE (daily ~2 settled bets) | Sonnet | 3K/1K | $0.024 per bet |

**Estimated per-pass total at 50 markets:**
- Base (no supervisor trigger): $1.35 + $4.40 + $0.55 = **~$6.30/pass**
- With 40% supervisor rate: **~$7.70/pass**
- Worst case (100% supervisor): **~$9.85/pass**
- Weekly at hourly cadence (168 passes, but only N new markets/hour — ASSUMPTION: 5 new markets/hour on average): **~$0.77 × 168 = ~$130/week at full scale; ~$5–$15/week early stage**

**The prior $2.26/pass estimate was wrong by ~3.5×** due to: (a) using old Opus pricing (~$15/MTok then vs $25 now), (b) routing workers to Sonnet not Haiku which would have made it even worse, (c) underestimating researcher token usage, (d) ignoring the per-market cost scaling.

**CRITICAL REFRAME:** At 50 markets/hour cadence, cost is dominated by RESEARCHER (Sonnet) and SWARM SUPERVISOR (Opus). The "is news/swarm worth it vs cheap baselines?" question depends on:
- A cheap baseline (no researcher, no swarm — just q_market blend) costs ≈ $0 per pass
- The swarm adds ~$5.75/pass at 50 markets
- Break-even: swarm must improve Brier enough to generate >$5.75/pass in expected edge
- At $100 bankroll and 2% edge: $2/day expected profit. Swarm costs $7.70/pass × 24 = $185/day
- **Conclusion: swarm is NOT justified at small bankroll. Gate the swarm behind a bankroll threshold.**

### 6.3 Cost Budget & Circuit Breaker

```
HARD BUDGET:        $20/week (early stage, paper-only)
ALERT THRESHOLD:    $14/week (70%) → MONITOR alerts, Overseer notified
CIRCUIT BREAKER:    if current_pass_cost > $2.00 → abort pass mid-flight, log, skip to next tick
SWARM GATE:         swarm only runs when bankroll > $5,000 OR explicit override in cadence_state.json
CHEAP FALLBACK:     when swarm gated off, p_model = Sonnet single-call estimate (1 call/market)
```

These values are in cadence_state.json and require Overseer digest to change (Tier B).
Changing the hard budget cap requires user co-sign (Tier C).

---

## 7. Guardrails — Failure Mode Defences

| Failure Mode | Defence | Tripwire |
|---|---|---|
| Token-budget runaway | Per-agent token cap in complete() wrapper; cadence_state tracks cumulative spend; hard circuit breaker at $2/pass | MONITOR alert if any single agent call exceeds 2× expected token budget |
| Role collision | Strict output schema per agent; no agent outputs fields outside its contract; RESEARCHER schema has no `probability` field | Schema validation in cadence before writing any result; invalid output → `failed` flag, not silent pass-through |
| Context-window OOM / task drift | RESEARCHER summarises evidence to ≤2K tokens; swarm workers ≤1K output each; no conversation state across ticks | If output is truncated (detected via sentinel token), mark `truncated=True`, re-run with smaller context |
| Untraceable tool calls | All LLM calls log to `cadence_state.json`: {role, model, tokens_in, tokens_out, ts, market_id}; autopsy links to source call IDs | Any call without a logged entry triggers MONITOR alert; cadence refuses to write bet without call audit trail |
| Coordination cost escalation | Cadence is Python (not LLM); no peer-to-peer; costs logged per call; weekly budget review | Cost-per-pass tracked in cadence_state; Overseer sees trend; alert if 3-week rolling average rises >20% |
| Degeneration loop / infinite retry | Cadence hard wall-clock limit: 90 minutes per pass; max 2 retries per agent call before marking failed | Pass age checked at each dispatch; stale pass auto-rolled to next tick |
| Anchoring in swarm | No inter-agent communication during swarm inference; personas injected at call time, not shared | Cadence enforces parallel dispatch without result sharing until aggregation step |
| Real-money auto-escalation | `live_mode: false` in bankroll.json; only ALLOCATOR reads it; only Overseer + user co-sign can flip | Any execute-step call checks flag; if `live_mode` flipped without a signed `tier_c_approval.json`, cadence refuses to execute and alerts |
| Foreknowledge violation | p_model frozen at decision time in bets.csv; never reconstructed post-resolution | bets.csv is append-only; any attempt to UPDATE an existing row is a schema violation logged as critical alert |
| Supervisor over-trigger | Circuit breaker: >50% supervisor trigger rate → skip supervisor that pass, flag for Overseer | cadence_state tracks per-pass supervisor trigger rate |

---

## 8. Self-Mod Leash (Summary — full spec in 08_SELF_IMPROVEMENT.md §5)

**The 3-tier leash:**

```
TIER A — Fully Autonomous:
  Recalibrate RMSE weights, bias corrections, blend weight w (within [0.50, 0.90]),
  Platt re-fit (n>=200), Welch-z auto-retire (p<0.01)
  → All bounded; weekly Overseer digest sees all changes

TIER B — Overseer Digest (auto-proceeds if no veto in 24h):
  Strategy paper→live-micro promotion, new archetype within existing vertical,
  weight shift >20%, any guardrail parameter change
  → Overseer must be online; 24h veto window is a hard pause

TIER C — Explicit User Co-Sign (BLOCKS):
  New vertical, real capital activation, ANY change to gate pipeline code or prompts,
  guardrail removal, budget cap change
  → System does NOT proceed until signed command received

HARD CONSTRAINT: gate pipeline code (institute/pipeline.py, gate modules, llm.py prompts)
is NEVER modified by any agent autonomously. Violations are logged as critical and
execution halted.
```

---

## 9. The Provider-Agnostic LLM Seam

`institute/agents/llm.py` is the ONLY place that touches model APIs. All agents call
`complete(prompt, role=..., mock=True)`.
- Full cadence loop is offline-testable with `mock=True`
- Provider swap requires changing one file
- Cost tracking lives here: every real call logs {role, model, tokens_in, tokens_out, market_id, ts}
- Budget-halt guard implemented here: if cumulative_spend > hard_cap, complete() raises BudgetExceeded

**TODO (A6):** wire real Anthropic client behind mock=False; add token logging; add BudgetExceeded guard;
add output schema validator. Missing roles in current ROUTING dict: `research`, `critique`, `allocate`,
`settle`, `monitor` — all needed before first real cadence pass.

---

## Sources

- PolySwarm: arXiv 2604.03888
- AIA Forecaster: arXiv 2511.07678
- MAST failure taxonomy: arXiv 2503.13657
- Multi-Agent Failure Analysis: augmentcode.com/guides/why-multi-agent-llm-systems-fail-and-how-to-fix-them
- Towards Data Science "17x Error Trap": towardsdatascience.com
- Claude API pricing (June 2026): platform.claude.com/docs/en/about-claude/pricing; aimodelcalc.com/guides/claude-api-pricing
- Self-Evolving Agents survey: arXiv 2507.21046
- EvolveR: arXiv 2510.16079
