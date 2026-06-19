# TRADING_ROUTER.md — read this FIRST

This is the **Context** layer of the Four C's. Every reasoning run (brief, autopsy,
self-mod) reads this file before doing anything else. It is the map of the desk.

## What this system is
A **fake-money** weather prediction-market paper-trading research desk that learns
from every resolved trade. **No real orders, no wallet, no exchange API keys — ever.**
That is enforced in code by `desk/kernel/invariants.py` and cannot be self-modified.

## The authority chain (do not violate)
1. **Kernel** (`desk/kernel/`) — immutable. The 5 discipline rules, the fake-money
   invariant, the param bounds, and the fitness definition. Nothing may edit it.
2. **Deterministic engine** (`papertrader/lib/engine.py`) — GROUND TRUTH for BET/SKIP.
   The LLM may confirm or VETO a bet; it may **never** turn a SKIP into a BET.
3. **Brief / debate** (`desk/brief.py`) — advisory reasoning + confidence.
4. **Memory** (`desk/memory/`) — append-only lessons + rebuildable index.

## Routing — where to look
- Researching a city's market → recall lessons: `desk/memory/lessons/<city>.md`
  (via `store.recall(category)` / `recall_asof` in backtests).
- Past mistakes / generalized rules → the `rule:` field of each lesson.
- "Am I bad at this category?" → `desk/risk.py` win-rates (declines losing ones).
- "Is this market liquid enough?" → `desk/risk.passes_liquidity`.
- Did I learn from a loss? → `desk/autopsy.py` writes the lesson (Reflexion).

## The two loops (Cadence)
- **Reactive (cheap, frequent):** trigger on model-run publish times 00/06/12/18Z —
  scan, price, settle, reconcile the index. Run by systemd timers / cron.
- **Reflective/Strategic (expensive, daily or on-resolve):** `desk/run_cycle.py` —
  autopsies, briefs, and the self-mod gate. Run by Prefect with budget caps.

## Self-modification (autonomous, guard-railed)
Frozen by default. Controlled by `desk/selfmod_config.json` (kill switch). A new tool
must pass: overseer → static analysis → sandbox → walk-forward fitness beat → git
commit. See `desk/promote.py`. Review the daily digest (`desk/digest.py`) and revert
anything with `git revert`.

## The edge (why this can work)
The documented weather edge is **latency to a fresh model run** (5–15 min on active
markets) — so prefer fresh runs and **less bot-saturated markets**. Discipline +
calibration + learning from losses is the durable part; chasing the most liquid
markets against pro bots is not.
