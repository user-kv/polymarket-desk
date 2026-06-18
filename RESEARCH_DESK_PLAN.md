# Research Desk + Second Brain — Architecture Plan (v2)

*v1 drafted 2026-06-19. v2 rewritten 2026-06-19 after a 5-round SOTA research loop
(memory · multi-agent debate · self-improvement safety · orchestration/cloud · domain edge).
Plan only — nothing built yet. Supersedes `claude_implementation_guide.md` where research found a
better fit. End goal: a self-improving, guard-railed, cloud-resident paper-trading research desk
built on the existing `papertrader/` that learns from every resolved trade — FAKE MONEY ONLY.*

## TL;DR
Build on the existing `papertrader/`. Keep a **single strong agent + a lessons library** as the
default; switch on a lean **Bull/Bear/Risk debate (≤2 rounds)** only if it *measurably* beats the
single agent on a backtest. Memory = **append-only markdown lessons (immutable episodic log) +
rebuildable SQLite index** structured on the CoALA episodic/semantic/procedural split. Self-mod is
**evolutionary and benchmark-gated** around an **immutable protected kernel**. Host **free on Oracle
Cloud Always Free (4 ARM/24 GB)**, Hetzner CAX11 ($3.79/mo) as fallback. Fast loop on systemd
timers; expensive LLM loop on **Prefect**. Mind the **June 15 2026 Agent-SDK billing change**.

---

## Where I diverge from the guide (and why) — updated
| Guide / v1 says | v2 recommendation | Why (research round) |
|---|---|---|
| OpenBB data layer | **Skip.** Keep Open-Meteo + Polymarket. **Add ML ensembles AIFS + GraphCast.** | OpenBB is equities. AIFS (ECMWF, CRPS-trained, 4×/day) + GraphCast are competitive/better and free via Open-Meteo. (R5) |
| Clone TradingAgents (7 agents) | **Borrow roles; lean Bull/Bear/Risk + synthesizer, ≤2 debate rounds. Single-agent+lessons is the default baseline.** | Debate has sharp diminishing returns (2 rounds capture most gain; saturates ~5–7 agents). Single strong agent w/ skill library often matches a crew at lower cost. (R2) |
| Paperclip workflow | **Skip.** Prefect for the LLM loop. | Paperclip too heavy; Prefect gives retries/durability/observability without Temporal's server. (R4) |
| Flat markdown memory | **Append-only md lessons (immutable log) + rebuildable SQLite index; CoALA episodic/semantic/procedural split.** | This *is* SSGM "reversible reconciliation" — bounds drift to O(N) not O(T). (R1) |
| Windows Task Scheduler | **Oracle Cloud Always Free (4 ARM/24 GB, $0)**; Hetzner CAX11 ($3.79) fallback. systemd timers + Prefect. | Laptop-independent, possibly free. (R4) |

The **Four C's** and the **gated phased build** are kept. The deterministic engine/ledger stays the
**ground-truth authority** the LLM cannot override (R5 trading-survey).

---

## What already exists vs. what's new
Existing `papertrader/` already delivers most of "Phase 1 foundation": data layer
(`lib/forecasts.py`, `lib/polymarket.py`), deterministic 5-rule engine (`lib/engine.py`), ledger /
settlement / calibration, a backtest skeleton (`lib/backtest.py`), and 70+ scan snapshots usable as
mock markets.

New on top: (1) LLM brief/debate layer, (2) Second Brain memory, (3) autopsy agent (= Reflexion),
(4) risk self-awareness, (5) guard-railed self-modification, (6) cloud migration.

---

## Target architecture
```
polymarket/
  papertrader/              # existing deterministic engine (kept; the ground-truth authority)
  desk/                     # NEW research desk
    kernel/                 # IMMUTABLE protected core — self-mod may NEVER edit
      invariants.py         #   5 discipline rules, fake-money-only, no real orders/keys/wallet
      fitness.py            #   out-of-sample CRPS + Brier(Murphy) + paper-PnL definition
    router/TRADING_ROUTER.md       # Context (read first)
    agents/                        # Bull / Bear / Risk / synthesizer prompts (Agent SDK)
    overseer.py                    # async LLM overseer — can cancel/freeze a self-mod run (SICA)
    autopsy.py                     # Reflexion: resolved trade -> verbal lesson (+ Write Gate)
    brief.py                       # single-agent baseline OR ≤2-round debate -> brief + confidence
    memory/
      lessons/<cat>.md             # episodic: append-only immutable log
      semantic/<cat>.md            # generalized rules (Write-Gate validated)
      index.sqlite                 # mutable, rebuildable; time-decay/regime-aware retrieval
      build_index.py               # periodic reconciliation md -> sqlite (bounds drift)
    tools/                         # self-written tools (sandboxed, archived, backtest-gated)
  RESEARCH_DESK_PLAN.md
```

**Three-speed execution** (R5 trading-survey reactive/reflective/strategic):
- *Reactive* (cheap, **triggered on model-run publish 00/06/12/18Z**, not flat 2h): scan, price,
  settle, update index. The latency-to-new-run is the documented edge (5–15 min on active markets) —
  so target **less bot-saturated / lower-volume markets** + add a **liquidity/volume rule**.
- *Reflective* (Claude Agent SDK headless, daily/on-resolve, `--max-budget-usd`+`--max-turns`):
  brief, autopsy, lessons.
- *Strategic* (on demand): backtest replay, self-mod proposals + evaluation.

---

## Phased build (gated — each phase runs clean before the next)
- **Phase 1 — Base loop + memory:** Router + memory; **single-agent** brief on a mock market
  (`data/scans/*.json`); autopsy writes a lesson via the **Write Gate**; next run reads it.
- **Phase 2 — Risk self-awareness:** SQLite category win-rates w/ **time-decay/regime-aware
  retrieval**; agent declines historically-losing categories. Add the **liquidity rule**.
- **Phase 3 — Backtesting:** Extend `lib/backtest.py` to **walk-forward, out-of-sample, with
  transaction costs and outcome-embargo** (no episode exposes its outcome until resolution — kills
  look-ahead/"oracle fallacy"). This backtest becomes the Phase-4 fitness validator. Optionally A/B
  the debate layer vs the single-agent baseline here.
- **Phase 4 — Self-modification (autonomous, guard-railed):** DGM-style — propose a tool/change →
  evaluate on the Phase-3 backtest → **promote only if it beats the current champion out-of-sample**;
  keep an archive of variants. First demo: autopsy finds the missing AIFS data → writes an AIFS
  fetcher tool. Guardrails below.
- **Phase 5 — Cloud:** Oracle Cloud Always Free (Hetzner fallback); systemd timers + Prefect;
  secrets in env; Anthropic OpenTelemetry for the digest/cost dashboard.

---

## Self-modification guardrails (the safety floor — no human approval gate)
1. **Immutable protected kernel** — `desk/kernel/` (5 rules, fake-money-only, fitness definition)
   cannot be edited by the loop. Prevents reward-hacking & goal drift (R3).
2. **Git-commit-per-change** — every change is one isolated commit → instant revert. *(needs `git
   init` — repo doesn't exist yet.)*
3. **Benchmark-gated promotion** — a new tool must beat the champion on the **walk-forward
   out-of-sample** backtest (CRPS/Brier/PnL), not just pass a unit test; keep a variant archive (DGM).
4. **Static analysis + vuln scan**, then **real OS-level sandbox** (container/restricted user,
   read-only kernel mount, network allowlist) — in-process "polite" sandboxes get bypassed (R3).
5. **Independent LLM overseer** — async reviewer that can cancel/freeze a self-mod run on
   pathological behavior; the autonomous stand-in for the human gate (SICA, R3).
6. **Kill-switch flag** + **`--max-budget-usd`/`--max-turns`** (default unlimited — must set
   explicitly) + **daily OpenTelemetry digest** of what changed.
7. **Memory Write Gate** — a new lesson must not contradict protected core facts before storage
   (memory twin of the test harness; blocks memory poisoning) (R1/SSGM).

---

## Decisions (locked 2026-06-19)
1. **Cloud:** validate locally first → Oracle Cloud Always Free at Phase 5 (Hetzner CAX11 fallback).
2. **Self-mod autonomy:** fuller autonomy (no human gate) — guardrails 1–7 carry safety.
3. **Scope:** weather-only for now.
4. **LLM budget:** ~$5/day cap. NB **June 15 2026**: Agent SDK / `claude -p` headless bill from a
   **separate credit pool at API rates** ($20 Pro/$100 Max5x/$200 Max20x), not subscription. Route
   cheap subtasks to **Haiku**, reserve **Opus** for debate/autopsy.
5. **Default reasoning:** single agent + lessons library; debate switched on only if it beats the
   baseline in backtest.
6. **Forecast:** expand ensemble with **AIFS + GraphCast** via Open-Meteo.
7. **Fitness:** out-of-sample **CRPS + Brier(Murphy decomposition) + paper-PnL** — strictly proper,
   harder to game than PnL alone.

## Convergence note
Five research rounds; each produced structural improvements, then sources began overlapping and every
pillar settled on a SOTA-grounded choice. A 6th round would tune parameters, not structure — so the
architecture is treated as converged. Open *parameter* questions left for build time: exact liquidity
threshold, debate-vs-single A/B outcome, AIFS weight in the ensemble, reconciliation window size.

## Sources (by round)
- R1 memory: SSGM arxiv 2603.11768 · Agentic-Trading survey arxiv 2605.19337 · CoALA/Agent Workflow Memory · Mem0/Letta/Zep comparisons
- R2 debate: TradingAgents arxiv 2412.20138 · "Strong Single Agent Baseline" arxiv 2601.12307 · single-vs-multi arxiv 2604.02460 · Agent-framework 2026 benchmarks (LangGraph/Claude SDK/CrewAI)
- R3 self-improvement: SICA (ICLR) · Darwin Gödel Machine arxiv 2505.22954 · Reflexion arxiv 2303.11366 · Guardrails 2026 (Permission/Approval/Audit/Kill-switch) · NemoClaw sandbox bypass
- R4 orchestration/cloud: Temporal vs Prefect · Hetzner/Oracle Cloud Always Free · Claude Agent SDK headless + June-15-2026 billing + OpenTelemetry
- R5 domain: Polymarket weather strategy (latency edge 5–15 min) · CRPS/Brier proper scores · ECMWF AIFS arxiv 2412.15832 · suislanchez/polymarket-kalshi-weather-bot
