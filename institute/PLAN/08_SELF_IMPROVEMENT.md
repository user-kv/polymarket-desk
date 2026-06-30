# The Institute — Self-Improvement & Adaptation Engine
## Plan Document 08 · PLANNING ONLY · Not built

**Status:** research-backed design (2026-06-30). Extends AGENT_ORG_DESIGN.md §IMPROVE.
**Depends on:** 04_AGENT_ORG.md (control loop), 00_CHARTER.md (locked decisions §4 + §7).
**Purpose:** define exactly how the institute adapts over time — recalibration, strategy
lifecycle, vertical expansion, meta-learning, the overseer gate, and memory compounding —
so the improvement loop is as rigorous as the forecasting loop it improves.

---

## 0. Design Principle: Self-Improvement Only Works Where Outcomes Are Verifiable

From the 2026 self-evolving agent survey (arXiv 2507.21046) and o-mega.ai 2026 guide:

> "AI self-improvement only works reliably in domains where outcomes are objectively
> verifiable. Code either compiles or it does not."

Prediction markets are nearly ideal: every market resolves to 0 or 1. This is the
strongest possible feedback signal, and it is what makes the institute's self-improvement
loop sound rather than speculative. Every design here is grounded in that signal.

The corollary: **the institute can ONLY self-improve on what it can measure.** Any
self-modification proposal that cannot be back-tested against resolved markets must
route through the Overseer gate and requires explicit human review.

---

## 1. Recalibration Loops

### 1.1 Per-Model RMSE Weights (weather; extends to all quantitative verticals)

**Current state:** `lib/calibration.py:compute_model_weights()` fits per-city
GFS/ECMWF/ICON/GEM/UKMO/AIFS RMSE from 7-day archive, stored in calibration.json.

**Self-improvement extension:**
- Weekly recalibration run: new resolution data → re-fit RMSE weights → write calibration.json
- Trigger condition: at least 10 new resolutions in any vertical since last calibration
- Change gate: if any weight shifts > 20% vs prior, route to Overseer digest (anomaly flag)
- Back-fit window: rolling 90-day window (older data downweighted; markets change character)

### 1.2 Per-City / Per-Archetype Bias Correction

Each archetype (e.g., "Dallas rain > 0.1 inch") can have a systematic bias:
the model consistently over- or under-estimates. Track:
```
bias[archetype] = mean(p_model - outcome) over last N resolutions
```
Apply additive correction at blend step:
```
p_final_corrected = p_final - bias[archetype]
```
Minimum n = 20 resolved bets per archetype before applying bias correction (otherwise
regression to sample noise). Stored in calibration.json under `bias_corrections`.

### 1.3 Probability Calibration (Platt Scaling)

**The n >= 200 rule is non-negotiable.** At n < 200, Platt scaling hurts (Charter §M1).
- Track n_resolved globally and per vertical in cadence_state.json
- Platt is toggled ON automatically when n_resolved >= 200 for that vertical
- Re-fit Platt parameters monthly once active; use 60/40 train/val split on resolved rows
- The current `lib/prob_calibration.py` is correct; it just needs the auto-toggle trigger

### 1.4 The Blend Weight `w` (model vs. market)

The p_final blend: `p_final = w·p_model + (1-w)·q_market`

PolySwarm uses w=0.70 as a fixed prior. The AIA finding shows w should vary by market
liquidity and archetype. Self-improvement target:

- Start: w = 0.70 (PolySwarm default)
- After n >= 50 per archetype: fit w by minimising Brier score on held-out resolutions
- Per-archetype w stored in calibration.json; updated weekly alongside RMSE weights
- Constraint: w ∈ [0.50, 0.90] — never trust market entirely, never ignore it entirely

---

## 2. Strategy Lifecycle: Birth → Promotion → Decay → Retirement

### 2.1 Pattern Foundation

The EvolveR framework (arXiv 2510.16079) and HyperAgents (o-mega.ai 2026) both converge
on the same lifecycle architecture:

```
BIRTH (propose) → GATE (validate) → PAPER (observe) → PROMOTE (confirm) → LIVE
                                         ↑                   ↓
                                    (iterate)          DECAY DETECT
                                                            ↓
                                                       RETIRE (archive)
```

This mirrors Monte Carlo Tree Search: exploit confirmed strategies + explore candidates.

### 2.2 Birth: The Proposer

**Who:** a dedicated Sonnet agent (PROPOSER) that runs weekly.

**Inputs:**
- autopsy_log.jsonl (patterns in recent misses and wins)
- cadence_state.json (which archetypes have thin coverage)
- open market scan (what market families have new volume)
- meta-learning signals (see §4 below)

**What it proposes:**
- New baseline variants for existing archetypes (e.g., a tighter edge threshold)
- New archetypes within existing verticals (e.g., a new city, a new bucket boundary)
- New verticals (new market family; triggers a vertical-proposal review, see §3)

**Output format:**
```json
{
  "proposal_id": "P-2026-07-01-001",
  "type": "baseline_variant | new_archetype | new_vertical",
  "description": "...",
  "mechanism_hypothesis": "...",
  "required_data": ["..."],
  "expected_edge_basis": "...",
  "proposer_rationale": "..."
}
```

All proposals are written to `data/proposals/` — never auto-executed. The pipeline
picks them up for Gate 1 evaluation.

### 2.3 Gate Passage (the existing pipeline, now auto-triggered)

Proposals pass through the existing 7-gate pipeline (institute/pipeline.py):
- Gate 1 (statistical): back-test on resolved rows; must pass, not merely "insufficient"
- Gate 2 (mechanism): Opus judge finds flaw or clears; adversarial
- Gate 3 (red-team): Opus red-team constructs strongest attack; must survive
- Gate 4 (paper-forward): promotes to paper with frozen parameters
- Gates 5-7 (portfolio, capital, decay): at paper→live promotion only

The Proposer mints candidates; it cannot self-promote. The pipeline is the adversary.

### 2.4 Decay Detection: Welch-z Test

Already partially implemented (institute/gates/decay referenced in AGENT_ORG_DESIGN).

**Full specification:**
```
For each active strategy cell:
  brier_recent = Brier score over last 30 resolved bets
  brier_baseline = Brier score over first 30 resolved bets (or overall baseline)
  z_score = Welch-z(brier_recent, brier_baseline)
  p_value = two-tailed p for z_score

  if p_value < 0.05 AND brier_recent > brier_baseline:
    flag as DECAYING → route to Overseer digest
  if p_value < 0.01 AND brier_recent > brier_baseline + 0.05:
    auto-retire (suspend from book) + notify Overseer
```

Minimum n for decay detection: 30 resolved bets in each window. Below this threshold,
no decay verdict possible — the cell remains in "monitoring" status.

### 2.5 Retirement

Retired strategies are NOT deleted — they are archived in `data/archive/strategies/`
with:
- Full gate verdicts
- All autopsy records during their life
- The Welch-z signal that triggered retirement
- A brief epitaph (Sonnet-generated: "what we learned from this strategy")

The archive IS the long-term memory. A future Proposer can read it to avoid re-proposing
a known-dead idea, or to notice when market conditions change enough to resurrect one.

---

## 3. Proposing New Verticals

### 3.1 What Triggers a Vertical Proposal

The Proposer generates a vertical proposal when:
- A scan shows >20 open markets in a family with no current coverage
- An existing vertical's autopsy log shows systematic misses linked to a data gap
  (e.g., weather misses concentrated in non-NWP markets → triggers a sports proposal)
- The user explicitly requests it (always honoured, routed through gate)

### 3.2 Vertical Proposal Contents

A vertical proposal is a superset of a strategy proposal. It must include:
- The market family and sub-market description
- Edge thesis (which of the 4 engines fits: quant / behavioral / news / smart-money)
- Free data source(s) and their quality grade
- Premium data upgrade slot (what it would buy)
- Estimated market volume (how many bets/week at paper stage)
- Why this vertical is NOT efficiently priced (the edge case)
- Kill criterion: "if we can't achieve Brier < X after Y bets, we retire this vertical"

### 3.3 Vertical Gate: Overseer Required

New vertical proposals do NOT auto-enter the pipeline. They route to the Overseer digest
for human review before Gate 1 is attempted. Rationale: verticals require data pipeline
work (new sensors, new parsers) that may involve real-money data subscriptions or
operational complexity. The Overseer — and ultimately the user — must sign off.

Existing vertical extensions (new archetype, new baseline) go straight to Gate 1.

---

## 4. Meta-Learning Across Verticals

### 4.1 The HyperAgents Finding

HyperAgents (2026, cited in o-mega.ai) trained on paper review and robotics and
transferred successfully to grading Olympiad math solutions. The emergent meta-skills
were NOT domain-specific — they were:
- Memory infrastructure patterns (what to track)
- Exploration-exploitation balancing heuristics
- Reusable prompt templates for evidence extraction
- Self-diagnosis routines for common failure modes
- Bias detection patterns

This is directly applicable: lessons from weather forecasting (NWP ensemble weighting,
per-bucket bias correction) transfer structurally to any quantitative vertical. The
principle is: **compress the METHOD, not the result.**

### 4.2 The Meta-Learning Layer

The institute maintains a `data/meta/` directory with:

**`meta_patterns.json`** — compressor of cross-vertical lessons:
```json
{
  "pattern_id": "MP-001",
  "discovered_vertical": "weather",
  "description": "RMSE-weighted ensemble outperforms simple mean when model errors are heteroscedastic",
  "transfer_hypothesis": "applies to any quantitative vertical with multiple signal sources",
  "gate_transferred_to": ["macro/CPI"],
  "brier_delta_after_transfer": -0.023,
  "status": "confirmed_transfer"
}
```

**`meta_failures.json`** — anti-pattern archive:
```json
{
  "failure_id": "MF-001",
  "vertical": "weather",
  "pattern": "Platt calibration at n<200 degrades performance",
  "mechanism": "overfits to noise; sign flip on small samples",
  "never_repeat": true
}
```

The PROPOSER reads `meta_patterns.json` before minting any new strategy proposal. If a
meta-pattern applies, it is cited in the proposal's `mechanism_hypothesis`. If a
`meta_failures.json` entry applies, the proposal must explain why this case is different
or it is rejected at intake.

### 4.3 Cross-Vertical Weight Sharing

When a new vertical (e.g., sports) has n < 30 resolved bets, it cannot self-calibrate.
The blend weight `w` defaults to:
1. The average w across all OTHER verticals with n >= 50 (Bayesian prior)
2. Shrinks toward vertical-specific estimate as vertical n grows
3. Full vertical-specific estimate at n >= 100

This is the Bayesian shrinkage / hierarchical estimation pattern: borrow strength from
related verticals until the local sample is sufficient.

---

## 5. The Overseer Gate: How Much Leash Is Safe

### 5.1 The Fundamental Tension

From arXiv 2507.21046 (self-evolving agents survey):
> "Human oversight remains essential in current systems — full autonomy represents an
> aspirational goal rather than the current norm."

The institute's answer: calibrate the leash to the reversibility and stakes of the
modification. Reversible changes with low capital stakes get more autonomy; irreversible
or high-stakes changes require human co-sign.

### 5.2 Autonomy Tiers

```
TIER A — Fully Autonomous (no human review)
  - Recalibrating RMSE weights within existing verticals
  - Updating per-archetype bias corrections
  - Adjusting blend weight w (within [0.50, 0.90] constraint)
  - Re-fitting Platt parameters (once n >= 200)
  - Retiring a strategy via Welch-z auto-retire (p < 0.01)
  Rationale: all are reversible; bounded by fixed constraints; track-record-driven

TIER B — Overseer Digest (Overseer reviews; human sees it; auto-proceeds if no veto in 24h)
  - Promoting a strategy from paper to live-micro (small capital)
  - Minting a new archetype within an existing vertical
  - Any weight shift > 20% vs prior calibration
  - Decay-flagging a strategy (not yet auto-retiring)
  - New version of a baseline (parameter change, not mechanism change)
  Rationale: consequential but reversible; Overseer digest is the human checkpoint

TIER C — Explicit User Sign-Off Required (blocks until acknowledged)
  - New vertical proposal (requires new data pipeline)
  - Activating real capital (Gate 6; the cord stays hand-pulled per Charter)
  - Any self-modification of code in the gate pipeline itself
  - Removing or relaxing a guardrail
  - Changing the blend weight constraint bounds [0.50, 0.90]
  Rationale: irreversible or high-stakes; Charter principle "fake money until gated + signed-off"
```

### 5.3 The Overseer Agent's Scope

The Overseer (Opus) does NOT have write access to strategy code or calibration files.
It can RECOMMEND; execution requires either auto-proceed (Tier A), digest-approval (Tier B),
or the user explicitly running a command (Tier C). This is the "frozen foundation model"
guardrail pattern from the self-evolving agents literature: weights never update
autonomously; only the wrapping context (calibration.json, proposal files) evolves.

### 5.4 Self-Modification of Strategy Code

The institute does NOT allow agents to modify gate logic, pipeline code, or LLM prompts
autonomously. This is a hard constraint, not a soft preference. Rationale:
- Point-in-time honesty law requires the pipeline to be stable across back-test periods
- A self-modifying pipeline destroys the integrity of the track record (moat §7)
- The risk of silent regression is not worth the automation benefit at this scale

The appropriate path: Overseer flags a systematic issue → proposes a code change in the
Overseer digest → user reviews → developer implements + commits → A/B test on paper first.

---

## 6. Memory & Track Record as a Compounding Asset

### 6.1 Why the Track Record Is the Moat

From the Charter: "a competitor cannot back-fill our frozen priors." Every bet frozen at
decision time — with the p_model, q_market, evidence_bundle, gate_verdicts — is an
irreproducible record of what the institute BELIEVED at that moment. Competitors can
clone our methods; they cannot clone our history.

This is the compounding asymmetry: the longer the institute runs honestly, the harder
it becomes to replicate, regardless of whether competitors adopt the same architecture.

### 6.2 Memory Architecture (Three Layers)

Adapted from o-mega.ai 2026 and arXiv 2507.21046:

**Layer 1 — Working Memory (ephemeral, per-cadence-pass)**
- The current evidence bundle, swarm outputs, gate verdicts for THIS tick
- Lives in-process; discarded after tick completes
- Never persisted directly — only the DECISION and its inputs are written to bets.csv

**Layer 2 — Episodic Memory (autopsy_log.jsonl, append-only)**
- One record per settled bet: {bet_id, p_model, q_market, actual, brier, autopsy}
- The "replay buffer" for recalibration and Welch-z
- Searchable by archetype, vertical, date range, baseline
- SimpleMem (2026) shows that semantic compression of episodic memory reduces token
  consumption by 30× while improving retrieval F1 by 26% — consider after n >= 500

**Layer 3 — Semantic Memory (meta_patterns.json, meta_failures.json)**
- Distilled cross-vertical lessons and anti-patterns
- Compressed from Layer 2 by the CRITIQUE agent (monthly distillation run)
- Read by the PROPOSER before every mint
- This is the "offline self-distillation" step in EvolveR (arXiv 2510.16079):
  trajectories → strategic principles → retrieved at proposal time

### 6.3 The Bet Autopsy (per-bet Reflexion)

After each settlement, CRITIQUE runs a structured autopsy:
```json
{
  "bet_id": "...",
  "vertical": "weather",
  "archetype": "KDAL_rain_bucket_3",
  "p_model": 0.72,
  "q_market": 0.61,
  "p_final": 0.69,
  "outcome": 1,
  "brier_this": 0.095,
  "brier_baseline_archetype": 0.142,
  "edge_claimed": 0.08,
  "edge_realised": 0.31,
  "what_worked": "ECMWF weight correctly elevated; supervisor targeted search resolved GFS outlier",
  "what_failed": null,
  "gate_that_should_have_caught": null,
  "meta_pattern_candidate": "Ensemble supervisor targeted search adds value when swarm_std > 25%"
}
```

Monthly, CRITIQUE distills autopsy_log.jsonl → meta_patterns.json and meta_failures.json.
This is the Reflexion loop (Shinn et al., NeurIPS 2023) applied to the bet level:
generate → evaluate → reflect → improve prompt/strategy → repeat.

### 6.4 Track Record Integrity Rules

- **Never restate or amend a frozen bet.** bets.csv is append-only. If a settlement was
  wrong, add a correction row with `correction_of: bet_id` — never overwrite.
- **Never back-fill calibration.** Calibration.json changes only prospectively; the
  version in effect when a bet was placed is archived alongside the bet.
- **Every self-improvement applied is logged with a timestamp.** calibration_history.jsonl
  tracks every parameter change: {ts, parameter, old_value, new_value, trigger, n_resolved}

---

## 7. Failure Modes of Self-Improvement (Defences)

| Risk | Defence |
|---|---|
| Overfitting to noise (small n) | Hard n thresholds: bias at n>=20, Platt at n>=200, Welch-z at n>=30; no exceptions |
| Catastrophic forgetting of working strategies | Archive + epitaph on retirement; meta_failures.json blocks re-proposal |
| Self-modification destroying track record integrity | Hard constraint: no autonomous code changes to gate pipeline; Tier C only |
| Calibration drift masking decay | Welch-z runs on RAW Brier (pre-calibration) to detect true signal decay, not calibration artifact |
| Proposer proposing the same dead idea | meta_failures.json is a required read at proposal time; must explicitly argue why this is different |
| Leash too long (Tier A autonomy runs away) | All Tier A changes bounded by hard constraints ([0.50,0.90], ±20% change flag); weekly Overseer digest sees all changes |
| Track record gaming (cherry-pick reported bets) | bets.csv is the single source of truth, checked into git; every push is auditable |

---

## 8. The Self-Improvement Schedule

```
EVERY TICK (hourly):
  - CRITIQUE: autopsy any newly settled bets → autopsy_log.jsonl

DAILY:
  - bias_corrections: update if n_archetype >= 20
  - cadence_state: check n_resolved per vertical; toggle Platt if n crosses 200

WEEKLY (Sunday 00:00 UTC):
  - CALIBRATE: refit RMSE weights, blend weight w per archetype
  - PROPOSER: scan for new strategy/archetype proposals → data/proposals/
  - OVERSEER digest: budget actuals, Tier B pending items, anomaly flags
  - PIPELINE: run pending proposals through Gates 1-3

MONTHLY (1st of month):
  - CRITIQUE (meta-distillation): compress autopsy_log → meta_patterns + meta_failures
  - Platt re-fit (if n >= 200)
  - calibration_history.jsonl: append snapshot of all parameters
  - PROPOSER: scan meta_patterns for transfer candidates to new verticals

TRIGGERED (on Tier B/C events):
  - OVERSEER: review and respond to Tier B proposals (24h window)
  - USER: co-sign for Tier C (capital activation, new vertical, guardrail change)
```

---

## Sources Consulted

- EvolveR (experience-driven strategy lifecycle): arXiv 2510.16079
- Self-Evolving Agents survey (what/when/how/where to evolve): arXiv 2507.21046
- Self-Improving Agents 2026 guide: o-mega.ai/articles/self-improving-ai-agents-the-2026-guide
- HyperAgents meta-learning transfer: cited in o-mega.ai 2026 guide
- Reflexion (Shinn et al.): NeurIPS 2023 / arXiv 2303.11366
- SimpleMem memory compression: cited in o-mega.ai 2026 guide
- PolySwarm calibration + Brier tracking: arXiv 2604.03888
- AIA Forecaster blend weight: arXiv 2511.07678
- Institute Charter §4 (autonomy), §7 (moat), §M1 (Platt n>=200): 00_CHARTER.md
- Institute prior design: AGENT_ORG_DESIGN.md §CRITIQUE/IMPROVE
- Metacognitive self-improvement position paper: arXiv 2506.05109
