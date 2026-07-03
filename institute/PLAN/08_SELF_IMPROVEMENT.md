## CHANGELOG
- **2026-06-30 (red-team + harden pass):** Welch-z thresholds challenged and corrected — n=30 window is insufficient for reliable z-test power; minimum raised to n=50 per window; added explicit note on why 0.05/0.01 thresholds churn on noise at small n and what the correct alternative is. Added pre-registered kill criterion requirement (Rubric §2) — every strategy must declare its kill threshold BEFORE data, not after. Added meta-learning overfitting guard: meta_patterns must be validated OOS before being applied, not just distilled. Tightened autonomy tier definitions — prior Tier B "auto-proceeds" had a silent-approval problem with no audit trail. Added explicit falsifiability gate: any self-improvement that cannot be measured against resolved bets routes to Tier C, not Tier B. Corrected calibration_history.jsonl: must include the n_resolved count at time of change (needed to interpret parameter shifts later). Removed "resurrect dead strategies" language — this is a contamination risk; dead-strategy resurrection requires Tier C sign-off, not just Proposer read. Marked ASSUMPTIONS explicitly. Cross-doc fix: Rubric §10 requires decay detection that doesn't churn on variance — the Welch-z spec is now hardened against exactly that.

---

# The Institute — Self-Improvement & Adaptation Engine
## Plan Document 08 · PLANNING ONLY · Not built

**Status:** research-backed design (2026-06-30), hardened pass.
**Depends on:** 04_AGENT_ORG.md (control loop, autonomy tiers), 00_CHARTER.md (§4 locked decisions, §M1 Platt rule).
**Purpose:** define exactly how the institute adapts over time — what changes autonomously,
what requires human sign-off, and how we KNOW improvement is real and not noise.

---

## 0. The Governing Principle

> Self-improvement only works where outcomes are objectively verifiable. (arXiv 2507.21046)

Prediction markets resolve to 0 or 1. That is an unusually strong signal. But:

**The institute can only self-improve on what it can MEASURE, and measurements must
be falsifiable BEFORE the data arrives.** Any adaptation that cannot be validated
against resolved bets — or whose validation criterion was set AFTER seeing the data —
routes to the Overseer and requires human review. No exceptions.

This document is a contract: every loop defined here has a pre-registered success metric,
a minimum sample size, and a kill criterion written before the loop runs.

---

## 1. Recalibration Loops

### 1.1 Per-Model RMSE Weights

**Existing implementation:** `lib/calibration.py:compute_model_weights()` fits per-city
GFS/ECMWF/ICON/GEM/UKMO/AIFS RMSE from 7-day archive, stored in calibration.json.

**Self-improvement extension:**
- Weekly recalibration: new resolution data → re-fit RMSE weights → write calibration.json
- Trigger: ≥10 new resolutions in the vertical since last calibration run
- Anomaly flag: if any weight shifts > 20% vs prior → Overseer digest (Tier B)
- Rolling window: 90 days; older data downweighted linearly (ASSUMPTION: market character
  is roughly stationary within 90 days — if not, window shrinks; this is a parameter, not a law)
- Pre-registered kill criterion: if re-fit RMSE weights produce higher OOS RMSE than
  the simple-equal-weight baseline over the next 30 resolutions → revert to equal weights
  and route to Overseer. This is checked automatically; no manual comparison needed.

**Calibration logged in `calibration_history.jsonl`:**
```json
{
  "ts": "...", "parameter": "rmse_weight_ECMWF_KDAL",
  "old_value": 0.22, "new_value": 0.31,
  "trigger": "weekly_refit",
  "n_resolved_at_change": 47,
  "oos_rmse_before": 1.42, "oos_rmse_after": 1.31
}
```
The `n_resolved_at_change` field is mandatory — without it, parameter history is uninterpretable.

### 1.2 Per-Archetype Bias Correction

Track mean model error per archetype:
```
bias[archetype] = mean(p_model - outcome) over last N resolutions
```
Apply additive correction:
```
p_final_corrected = p_final - bias[archetype]
```

**Minimum n: 20 resolved bets per archetype.** Below this, bias estimate has SE > 0.10
(ASSUMPTION: binomial variance at p≈0.5) — larger than the correction itself. No correction
applied below threshold; cadence_state tracks n_per_archetype.

**Pre-registered kill criterion:** if bias-corrected Brier > uncorrected Brier over
30 subsequent resolutions (after correction activated) → disable bias correction for
that archetype and flag to Overseer. Applied per-archetype, not globally.

### 1.3 Probability Calibration (Platt Scaling)

**The n ≥ 200 rule is non-negotiable** (Charter §M1; OOS evidence shows it hurts at n < 200).

- Toggle ON automatically when n_resolved ≥ 200 for that vertical
- Re-fit monthly once active; 60/40 train/val split on resolved rows
- Train and val splits must be TIME-ordered (no shuffle — shuffle is lookahead)
- `lib/prob_calibration.py` is correct; needs auto-toggle trigger wired in cadence

### 1.4 Blend Weight w

`p_final = w·p_model + (1-w)·q_market`

- Start: w = 0.70 (PolySwarm default; ASSUMPTION — no institute-specific evidence yet)
- After n ≥ 50 per archetype: fit w by minimising Brier on time-ordered held-out resolutions
- Per-archetype w stored in calibration.json; updated weekly alongside RMSE weights
- Hard constraint: w ∈ [0.50, 0.90] — changing these bounds is Tier C
- **Pre-registered kill criterion:** if w-fitted Brier > w=0.70 fixed Brier over 30 subsequent
  resolutions → revert to fixed 0.70 for that archetype, flag to Overseer

---

## 2. Strategy Lifecycle: Birth → Promotion → Decay → Retirement

### 2.1 Pattern

```
BIRTH (Proposer) → GATE (pipeline 1-7) → PAPER (observe, freeze params)
                                                  ↓
                                          PROMOTE (Welch-z confirms edge)
                                                  ↓
                                            LIVE MICRO
                                                  ↓
                                          DECAY DETECT → RETIRE (archive)
```

### 2.2 Birth: The Proposer

**Who:** dedicated Sonnet agent, runs weekly.

**Inputs:**
- autopsy_log.jsonl (recent misses and wins)
- cadence_state.json (thin-coverage archetypes)
- open market scan (new volume families)
- meta_failures.json (REQUIRED READ — any proposal that matches a dead pattern must
  explicitly argue why this case is different, or is rejected at intake)

**Output format:**
```json
{
  "proposal_id": "P-YYYY-MM-DD-NNN",
  "type": "baseline_variant | new_archetype | new_vertical",
  "description": "...",
  "mechanism_hypothesis": "...",
  "required_data": ["..."],
  "expected_edge_basis": "...",
  "pre_registered_kill_criterion": "Brier > X after N resolved bets",
  "pre_registered_n_required": 50,
  "meta_failure_check": "no match | matched MF-NNN and differs because: ..."
}
```

**`pre_registered_kill_criterion` is MANDATORY.** A proposal without it is rejected
at intake. This implements Rubric §2 (falsifiability) at the proposal level. The kill
criterion cannot be revised once the strategy enters Gate 4 (paper stage).

All proposals written to `data/proposals/` — never auto-executed.

### 2.3 Gate Passage

Proposals pass through `institute/pipeline.py` (7 gates):
- Gate 1 (statistical): back-test on resolved rows; must pass, not merely "insufficient data"
- Gate 2 (mechanism): Opus judge finds flaw or clears; adversarial; **pipeline only, not hot path**
- Gate 3 (red-team): Opus red-team constructs strongest attack; must survive; **pipeline only**
- Gate 4 (paper-forward): promotes to paper with FROZEN parameters (parameters cannot change
  once a strategy is in paper stage — change requires a new proposal)
- Gates 5-7 (portfolio, capital, decay): at paper→live-micro promotion only

**The Proposer mints candidates; it cannot self-promote. The pipeline is the adversary.**

### 2.4 Decay Detection: Welch-z — Corrected Specification

**The prior specification had a power problem.** Welch-z at n=30 per window has
statistical power ≈ 0.20–0.40 to detect a 0.05 Brier shift (ASSUMPTION: typical
Brier variance ~0.08). This means 60–80% of real decays go undetected, and the
false-positive rate at p=0.05 is high enough to churn good strategies on noise.

**Corrected specification:**

```python
# Minimum window: n=50 per window (not 30)
# Effect threshold: Brier shift > 0.05 (not arbitrary)
# Significance: p < 0.05 for FLAG; p < 0.01 AND shift > 0.05 for AUTO-RETIRE

For each active strategy cell with n_total >= 100 resolved bets:
  brier_recent  = Brier score over most recent 50 resolved bets
  brier_baseline = Brier score over first 50 resolved bets (frozen at n=50)
  
  # Only test if both windows are full — never extrapolate
  if len(recent_window) < 50 or len(baseline_window) < 50:
      status = "monitoring"  # no verdict
      continue
  
  welch_t, p_two_tailed = scipy.stats.ttest_ind(
      recent_briers,    # per-bet Brier scores, recent window
      baseline_briers,  # per-bet Brier scores, baseline window
      equal_var=False   # Welch, not Student's
  )
  
  if p_two_tailed < 0.05 AND brier_recent > brier_baseline + 0.05:
      flag as DECAYING → Overseer digest (Tier B)
  
  if p_two_tailed < 0.01 AND brier_recent > brier_baseline + 0.05:
      auto_retire()  # suspend from book immediately
      notify_overseer(reason="welch_z_auto_retire")
```

**Why n=50 per window:** power analysis at typical Brier variance gives ~0.65 power
at n=50 to detect a 0.05 shift at p=0.05 — acceptable; below that, the test churns.

**RAW Brier (pre-calibration):** Welch-z always runs on raw (uncalibrated) Brier to
detect true signal decay, not calibration artifact.

**The `brier_baseline` is frozen at n=50 and never updated.** If the baseline could
drift, decay detection becomes circular. ASSUMPTION: the first 50 bets are representative
of the strategy's true initial performance — if they are not, the strategy should not
have passed Gate 4.

### 2.5 Retirement

Retired strategies archived in `data/archive/strategies/` with:
- Full gate verdicts
- All autopsy records
- Welch-z signal
- Sonnet-generated epitaph: "what we learned"

**Dead strategies are NOT resurrectable autonomously.** The Proposer reads the archive
to avoid re-proposing dead ideas, but any resurrection requires a NEW proposal, a NEW
gate-1 back-test on fresh data, and Tier C user co-sign before re-entering paper stage.
Rationale: market conditions that would make a dead strategy live again cannot be verified
from the archive alone; human judgment required.

---

## 3. New Vertical Proposals

### 3.1 Triggers

Proposer generates a vertical proposal when:
- Scan shows > 20 open markets in a family with no current coverage
- Autopsy log shows systematic misses linked to a data gap

### 3.2 Required Contents

- Market family and sub-market description
- Edge thesis (which of the 4 engines: quant / behavioral / news / smart-money)
- Free data source(s) and quality grade
- Premium data upgrade slot (what it buys)
- Estimated market volume (bets/week at paper stage)
- Why this vertical is NOT efficiently priced
- **Pre-registered kill criterion** (mandatory, same as §2.2)
- Data pipeline complexity and cost estimate

### 3.3 Vertical Gate: Tier C (User Co-Sign Required)

New vertical proposals do NOT auto-enter the pipeline and do NOT auto-proceed from
Overseer digest. They require explicit user co-sign before Gate 1 is attempted.
Rationale: verticals require new data pipelines that may involve real-money subscriptions
or operational complexity outside the VM. Overseer can RECOMMEND; only the user can approve.

---

## 4. Meta-Learning (Cross-Vertical Transfer)

### 4.1 What the Literature Supports

HyperAgents (2026, o-mega.ai) and EvolveR (arXiv 2510.16079) both show that cross-domain
transfer of METHOD (not result) is achievable. The transferable meta-skills are:
- Memory infrastructure patterns (what to track)
- Exploration-exploitation heuristics
- Evidence extraction prompt templates
- Self-diagnosis routines for common failure modes
- Bias detection patterns

**What does NOT transfer reliably:** calibrated probability estimates, market-specific
thresholds, archetype-specific edge sizes. Do not carry these across verticals.

### 4.2 Meta-Memory

`data/meta/meta_patterns.json` — cross-vertical lessons (compressed from autopsy_log):
```json
{
  "pattern_id": "MP-001",
  "discovered_vertical": "weather",
  "description": "RMSE-weighted ensemble outperforms equal-weight when model errors are heteroscedastic",
  "transfer_hypothesis": "applies to any vertical with multiple heterogeneous signal sources",
  "gate_transferred_to": ["macro/CPI"],
  "brier_delta_after_transfer": -0.023,
  "n_at_measurement": 62,
  "status": "confirmed_transfer | pending_validation | rejected"
}
```

`data/meta/meta_failures.json` — anti-pattern archive:
```json
{
  "failure_id": "MF-001",
  "vertical": "weather",
  "pattern": "Platt calibration at n<200 degrades performance",
  "mechanism": "overfits to noise; sign flip on small samples",
  "never_repeat": true
}
```

**Meta-pattern validation gate:** a pattern cannot have status `confirmed_transfer` until
it has been applied to ≥1 other vertical AND validated against ≥30 OOS resolved bets in
that vertical. Status starts as `pending_validation`. The CRITIQUE agent updates status
monthly. PROPOSER may cite `pending_validation` patterns as hypotheses but must flag them
as unconfirmed in the proposal's `mechanism_hypothesis`.

**This prevents meta-learning from overfitting its own distillations.** The prior version
had no validation gate — patterns flowed from distillation directly into proposals without
OOS confirmation. That is a second-order overfitting risk.

### 4.3 Cross-Vertical Weight Sharing (Bayesian Prior)

When a new vertical has n < 50 resolved bets:
1. Blend weight w defaults to mean w across all verticals with n ≥ 50 (ASSUMPTION: verticals
   are related enough to share a prior — if not, default to PolySwarm's 0.70 instead)
2. Shrinks toward vertical-specific estimate as n grows
3. Full vertical-specific estimate at n ≥ 100

---

## 5. The Overseer Gate: 3-Tier Leash

### 5.1 Design Principle

Calibrate leash to reversibility and stakes. Reversible changes with measurable outcomes
and low capital at risk get more autonomy. Irreversible or unverifiable changes require
human review.

**Key addition vs prior version:** any self-improvement whose outcome cannot be validated
against resolved bets is treated as Tier C by default, regardless of perceived stakes.
Unverifiable autonomy is the primary self-deception risk.

### 5.2 Autonomy Tiers

```
TIER A — Fully Autonomous (no human review; weekly digest sees all changes)
  - Recalibrating RMSE weights (within existing verticals, <20% shift, n≥10)
  - Updating bias corrections (n≥20 per archetype)
  - Adjusting blend weight w (within [0.50, 0.90], n≥50 per archetype)
  - Re-fitting Platt (n≥200, time-ordered split)
  - Welch-z auto-retire (p<0.01, n≥100, shift>0.05)
  Constraint: all must log to calibration_history.jsonl with n_resolved_at_change

TIER B — Overseer Digest (Overseer sees item; auto-proceeds after 24h IF no veto)
  - Promoting strategy paper→live-micro (small capital)
  - New archetype within an existing vertical
  - Any Tier A parameter shift >20% vs prior
  - Welch-z DECAY FLAG (not yet auto-retire)
  - New baseline variant (parameter change, not mechanism)
  Requirement: Overseer digest item must include the pre-registered kill criterion
  and current n_resolved; Overseer cannot approve without these fields present.
  The 24h auto-proceed only triggers if Overseer is online and has read the digest
  (read-receipt required). If Overseer is not online, item BLOCKS until next weekly digest.

TIER C — Explicit User Co-Sign (BLOCKS; does not auto-proceed)
  - New vertical (new data pipeline)
  - Activating real capital
  - Any change to gate pipeline code, LLM prompts, or guardrail parameters
  - Dead-strategy resurrection
  - Changing blend weight constraint bounds [0.50, 0.90]
  - Changing hard budget cap
  System does NOT proceed until user runs an explicit sign-off command.
```

### 5.3 What the Overseer Can and Cannot Do

The Overseer (Opus) **can:** recommend; flag; veto within the 24h Tier B window; write
to Overseer digest; surface anomalies.

The Overseer **cannot:** write to calibration.json, bets.csv, or any strategy code.
It has no write access to any file except its own digest output. Execution of any
recommendation requires either auto-proceed (Tier A), digest approval (Tier B), or the
user running a command (Tier C).

### 5.4 Hard Constraint: No Autonomous Code Modification

Gate pipeline code (institute/pipeline.py, gate modules), LLM prompts, and llm.py
are NEVER modified by any agent autonomously. This is a hard constraint, not a preference.

Rationale:
- Point-in-time honesty requires a stable pipeline across back-test periods
- Self-modifying pipeline destroys track record integrity
- Silent regression risk is not worth the automation benefit at this scale

Correct path: Overseer flags systematic issue → proposes change in digest → user reviews →
developer implements + commits → A/B test on paper (new proposal ID) before any promotion.

---

## 6. Memory Architecture

### 6.1 Three Layers

**Layer 1 — Working Memory (ephemeral, per-pass)**
In-process only; discarded after tick. Only the DECISION and its frozen inputs are
written to bets.csv.

**Layer 2 — Episodic Memory (autopsy_log.jsonl, append-only)**
One record per settled bet. The replay buffer for recalibration and Welch-z.

**Layer 3 — Semantic Memory (meta_patterns.json, meta_failures.json)**
Monthly distillation of Layer 2 by CRITIQUE. Read by PROPOSER at every mint.
Patterns require OOS validation before `confirmed_transfer` status.

SimpleMem (2026) shows semantic compression of episodic memory reduces token cost 30×
while improving retrieval F1 26%. Consider after n ≥ 500 resolved bets — not before.

### 6.2 Per-Bet Autopsy (Reflexion, Shinn et al. NeurIPS 2023)

```json
{
  "bet_id": "...",
  "vertical": "weather",
  "archetype": "KDAL_rain_bucket_3",
  "p_model": 0.72, "q_market": 0.61, "p_final": 0.69,
  "outcome": 1,
  "brier_this": 0.095,
  "brier_baseline_archetype": 0.142,
  "edge_claimed": 0.08, "edge_realised": 0.31,
  "calibration_version_at_decision": "2026-06-15T00:00:00Z",
  "what_worked": "...", "what_failed": null,
  "gate_that_should_have_caught": null,
  "meta_pattern_candidate": "...",
  "meta_pattern_status": "pending_validation"
}
```

**`calibration_version_at_decision` is mandatory.** Without it, we cannot distinguish
calibration artifact from true edge/decay when reviewing the autopsy log later.

### 6.3 Track Record Integrity Rules

- **Never amend a frozen bet.** bets.csv is append-only. Wrong settlement → correction
  row with `correction_of: bet_id`. Never overwrite.
- **Never back-fill calibration.** calibration.json changes only prospectively; the
  version in effect when a bet was placed is archived alongside the bet (via timestamp
  link into calibration_history.jsonl).
- **Every self-improvement logged with n_resolved.** calibration_history.jsonl requires
  `n_resolved_at_change` on every entry — this field was missing in the prior version.

---

## 7. Failure Modes of Self-Improvement

| Risk | Defence | Tripwire |
|---|---|---|
| Overfitting to noise (small n) | Hard n thresholds: bias n≥20, Platt n≥200, Welch-z n≥50 per window, n≥100 total; no exceptions | cadence refuses Tier A changes below threshold; logs attempted-but-blocked |
| Decay detection churning on variance | Welch-z corrected: n=50 windows, shift>0.05 AND p<0.01 required for auto-retire | Monitor tracks retirement rate; >2 auto-retires/month → alert (may indicate threshold too sensitive) |
| Meta-learning overfitting distillations | Pattern status: pending_validation until ≥30 OOS bets confirm transfer; Proposer must flag unconfirmed patterns | CRITIQUE checks status before monthly distillation; no confirmed_transfer without OOS record |
| Catastrophic forgetting | Archive + epitaph on retirement; meta_failures.json blocks re-proposal; resurrection requires Tier C | Proposer must output `meta_failure_check` field; missing field → proposal rejected at intake |
| Self-modification destroying track record | Hard constraint: no autonomous code changes to pipeline; Tier C only | Any attempt to write to pipeline.py or gate modules logged as CRITICAL alert and cadence halted |
| Calibration drift masking decay | Welch-z on RAW Brier (pre-calibration) always | If calibrated and raw Brier diverge >0.05 → MONITOR alert, route to Overseer |
| Silent approval (Tier B auto-proceed without oversight) | Overseer read-receipt required; if not online, item blocks | cadence_state tracks digest_read status; unread Tier B items > 48h → escalate to Tier C |
| Leash too long (Tier A runs away) | All Tier A changes bounded by hard constraints; weekly digest sees ALL changes | If n_tier_a_changes_this_week > 10 → alert; may indicate runaway recalibration |
| Track record gaming | bets.csv checked into git; every push auditable; correction rows only, no overwrites | Any row with an updated timestamp on a non-correction field → CRITICAL alert |

---

## 8. Self-Improvement Schedule

```
EVERY TICK (hourly):
  - CRITIQUE: autopsy newly settled bets → autopsy_log.jsonl

DAILY:
  - bias_corrections: update archetypes with n≥20 new resolutions
  - cadence_state: check n_resolved per vertical; toggle Platt if n crosses 200

WEEKLY (Sunday 00:00 UTC):
  - CALIBRATE: refit RMSE weights (n≥10 trigger), blend weight w (n≥50 trigger)
  - PROPOSER: scan for new strategy/archetype proposals → data/proposals/
  - PIPELINE: run pending proposals through Gates 1-3
  - OVERSEER digest: budget actuals, Tier B queue, anomaly flags, retirement rate

MONTHLY (1st of month):
  - CRITIQUE (meta-distillation): compress autopsy_log → meta_patterns + meta_failures
  - Platt re-fit (if n≥200, time-ordered 60/40 split)
  - calibration_history.jsonl: append full parameter snapshot
  - PROPOSER: scan meta_patterns (pending_validation only) for transfer candidates

TRIGGERED (Tier B/C events):
  - OVERSEER: 24h veto window for Tier B (read-receipt required)
  - USER: co-sign for Tier C (capital, new vertical, code change, guardrail change)
```

---

## Sources

- EvolveR (experience-driven strategy lifecycle): arXiv 2510.16079
- Self-Evolving Agents survey: arXiv 2507.21046
- Self-Improving Agents 2026 guide: o-mega.ai/articles/self-improving-ai-agents-the-2026-guide
- HyperAgents meta-learning transfer: o-mega.ai 2026 guide
- Reflexion (Shinn et al.): NeurIPS 2023 / arXiv 2303.11366
- SimpleMem memory compression: o-mega.ai 2026 guide
- PolySwarm calibration + Brier tracking: arXiv 2604.03888
- AIA Forecaster blend weight: arXiv 2511.07678
- Continual Learning survey (LLMs): github.com/Wang-ML-Lab/llm-continual-learning-survey (CSUR 2025)
- FOREVER memory replay: arXiv 2601.03938
- Institute Charter §4 (autonomy), §7 (moat), §M1 (Platt n>=200): 00_CHARTER.md
- Improvement Rubric: 10_IMPROVEMENT_RUBRIC.md
