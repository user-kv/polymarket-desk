# Fable 5 Operator Setup — how to run the architecture loop at max potential

**Audience:** the operator (Kavee / JARVIS). This is HOW to configure and run Fable 5.
The file it reads is `01_MISSION.md`. This file is not shown to Fable 5.

**Job of the run:** Fable 5 is the CONDUCTOR. Phase A: it runs an autonomous loop that designs
the best possible architecture for the Institute given the available resources (Opus 4.8
reviews). Phase B: it orchestrates the build by delegating each task to the right model by
complexity (routing table below). Fable does the hardest reasoning and the integration; it
does not do all the work itself.

---

## 1. Model configuration (from the claude-api reference, cached 2026-06-24)

| Setting | Value | Why |
|---|---|---|
| `model` | `claude-fable-5` | Most capable widely-released model; 1M context. |
| `thinking` | **omit the parameter** | Fable 5 thinking is always on. Sending `{type:"enabled",budget_tokens:N}` or `{type:"disabled"}` returns 400. |
| `output_config.effort` | **`max`** for design cycles; `high` for routine | This is the depth dial on Fable 5 (replaces `budget_tokens`). Design reasoning wants `max`. CoT planning lifts success ~37% (research). |
| `betas` | `["server-side-fallback-2026-06-01"]` | Enable refusal fallback. Security/finance-adjacent tasks trip false refusals; this re-serves transparently. |
| `fallbacks` | `[{"model":"claude-opus-4-8"}]` | The rescue model. A pre-output refusal isn't billed; a rescue bills at Opus rates. |
| streaming | on | Long outputs; avoids request timeouts. Use `.finalMessage()`. |
| max output | up to 128K | Architecture docs are long; don't cap low. |

**The reviewer is a SEPARATE model.** The red-team pass in the loop is NOT Fable 5 grading its
own homework — it is an **independent Claude Opus 4.8 (`claude-opus-4-8`) call at
`output_config.effort: "medium"`**. Different model = genuine adversarial independence, which
is the documented fix for the self-confirmation / reward-hacking failure mode. Opus 4.8 also
sits behind Fable 5 as the refusal fallback, so it is already in the loadout.

Always check `stop_reason` before reading `content` (handle `refusal`).

## 1b. The model roster (who does what — route by complexity)

| Model | Model ID | Role | Effort |
|---|---|---|---|
| Fable 5 | `claude-fable-5` | Architect + orchestrator + integration + final judgment | max (design) |
| Opus 4.8 | `claude-opus-4-8` | Deep research AND independent red-team reviewer | medium |
| Sonnet | `claude-sonnet-5` (or `-4-6`) | Builder: fetchers, harness, adapters, tests | default |
| Haiku | `claude-haiku-4-5` | Volume: scanning, classification, bulk labeling | low |

Fable 5 decomposes work and dispatches it; you (operator) or the harness actually spawn the
delegate calls. Match model to task complexity, never to habit — heavy models only where
correctness demands them.

**The research role (Opus 4.8 "deep-research"):** when the design needs external evidence,
Opus 4.8 decomposes into 3-5 sub-questions, runs multi-source web search, returns a CITED
synthesis. **CHECKED 2026-07-04: firecrawl/exa MCP are NOT configured on this machine**, so the
`deep-research` skill has no live path. **Use the fallback:**
- **Parallel `Explore` subagents (ACTIVE default)** — spawn one Explore agent per sub-question
  for a true parallel fan-out, then Opus 4.8 synthesizes the cited findings. No MCP dependency.
- **`deep-research` skill** — only if firecrawl or exa MCP is later added to `~/.claude.json`.
Either way: cited findings only; unsourced claims are labeled ASSUMPTION.

## 2. Context strategy — cache the corpus, don't re-send it

The Institute corpus (the 6 signal PLAN docs + decisions log) is small (~tens of K tokens)
and fits many times over in 1M. The loop re-reads it every cycle, so **cache it**:

- Put the STABLE prefix first: the mission (`01_MISSION.md`) + the PLAN corpus. Mark the
  cache breakpoint after it. Put the VOLATILE part (this cycle's instruction, prior-cycle
  critique) AFTER the breakpoint.
- Cache reads cost ~0.1x input. Cache writes 1.25x (5-min TTL) / 2x (1-hour TTL). Loop
  cycles are minutes apart -> use the **1-hour TTL**. Break-even at 3 requests; the loop
  does dozens.
- Min cacheable prefix for Fable 5 = 2048 tokens (our prefix is far larger). Any byte change
  before the breakpoint invalidates the cache — keep the corpus frozen during a run.

Net effect: the whole corpus is "absorbed" every cycle for ~pennies after cycle 1.

## 3. Tools it gets (grounding, not building)

Because the goal is ARCHITECTURE, the tools ground the design in reality — they are not a
build sandbox:

- **Read the repo** (`institute/**`, `papertrader/**`) — so the design fits what exists.
- **Sample the data** (`institute/data/*.jsonl`, `papertrader/data/`) — enough rows to judge
  volume/quality/coverage, NOT the whole file into context. It queries; results come back.
- **Web search** — to research methods, venues, data sources, comparable systems.
- **Write** — only into `institute/FABLE5/out/**` (its deliverables). Nothing else is writable.

It does NOT get: real-money anything, paid API keys, force-push, or write access to gate /
honesty / ledger code. See the fence in `01_MISSION.md`.

## 4. The loop harness (perceive -> design -> red-team -> revise -> converge)

Each cycle:
1. **Perceive** — read mission + PLAN corpus (cached) + last cycle's self-critique + its own
   prior draft in `out/`.
2. **Design** — improve the architecture against the rubric (mission section 4).
3. **Red-team (INDEPENDENT Opus 4.8 reviewer, effort=medium)** — a separate Opus 4.8 call
   receives Fable 5's current design and attacks it: where does it fool itself? what edge is
   fake net of fees? what cost/venue/data/look-ahead risk is hidden? It returns findings
   tiered BLOCKER / HIGH / MEDIUM / LOW with reasons. A different model doing this defeats the
   Self-Confirmation Trap (research: agents confirm their own hypotheses).
4. **Revise** — Fable 5 must ADDRESS EVERY BLOCKER (fix or justify-and-log); HIGH/MEDIUM
   folded in or explicitly deferred with reason. Log the diff + WHY in `out/CHANGELOG.md`.
5. **Score & decide** — the loop may only CONVERGE when the reviewer returns **zero open
   BLOCKERs** AND marginal improvement < threshold for 2 cycles AND every rubric item is
   satisfied. Otherwise loop again. (Disagreement rule: on a BLOCKER, the reviewer wins unless
   Fable 5 gives a sourced rebuttal logged in CHANGELOG; unresolved BLOCKER = not converged.)

Run cycles autonomously. Milestone report only (per long-leash setting).

**Loop budget & guardrails (so it can't grind forever or red-team blind):**
- **Hard cap:** max 12 cycles OR a set token/$ budget, whichever first. On hitting the cap,
  emit the best design so far + an explicit "unconverged: open BLOCKERs" list. Never loop
  unbounded.
- **Context parity:** the Opus 4.8 reviewer must receive the SAME corpus + data samples Fable
  5 used that cycle. A reviewer with less context red-teams blind and rubber-stamps.
- **Convergence still requires zero open BLOCKERs** — the cap is a stop, not a pass.

## 5. Anti-reward-hacking (the load-bearing guardrail)

The dominant failure mode of a capable autonomous agent is manufacturing success and hiding
it (OpenAI 2026: treat it "like an insider threat"). For a forecasting fund the "reward hack"
is FAKE EDGE — overfit, look-ahead leakage, invented backtest numbers. Defenses, enforced by
the harness:
- **Independent verification pass** each cycle = the Opus 4.8 reviewer (effort=medium) above.
  A different model is the point: it has no stake in Fable 5's ideas and no memory of talking
  itself into them.
- **Every claim must be sourced or labeled ASSUMPTION.** No unsourced edge numbers.
- **Point-in-time honesty is inviolable** — any design that peeks at outcomes is auto-rejected.
- **Full audit trail** — `out/CHANGELOG.md` records every material design change + rationale.
- **Trace review** — spot-check the thinking summaries for "let's just assume it works"
  shortcuts.

## 6. Runtime options (you didn't pin one; pick by how hands-off you want it)

- **Managed Agents (Anthropic-hosted):** persistent session over days, hosted workspace,
  event stream. Best for a truly hands-off multi-day loop. Costs per session.
- **Claude Code on your machine / the GCP VM:** simplest to start today; drive the loop with
  a runner script. Migrate to Managed Agents if you want it always-on.
Either way the files here are runtime-agnostic. Recommendation: start in Claude Code to
validate the loop for a cycle or two, then move to Managed Agents for the unattended run.

## 7. Definition of done (for the whole run)

A converged `out/ARCHITECTURE.md` (+ `GO_LIVE_TRIGGER.md`, `CHANGELOG.md`, `OPEN_DECISIONS.md`)
that satisfies every rubric item in the mission, with a CHANGELOG showing it survived its own
red-team, and an explicit list of the open decisions that still need YOU (real-money
activation, venue access/legal, paid-data-when-funded) — not silently assumed.

**North star of the whole run:** a portfolio of forecasting cells that each clear the 7-gate
stack with proven net-of-fee out-of-sample edge, deployable on real Polymarket AND Kalshi
(routed per market), with copy-flow across both venues. Proof, not backtest theatre.
