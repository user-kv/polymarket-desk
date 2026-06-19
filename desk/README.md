# Research Desk — self-improving paper-trading layer

A **fake-money** weather prediction-market research desk that learns from every
resolved trade, layered on top of the existing `papertrader/`. Built from
[RESEARCH_DESK_PLAN.md](../RESEARCH_DESK_PLAN.md) (v2, after a 5-round SOTA research
loop). **No real orders, no wallet, no exchange API keys — enforced in the kernel.**

## How it works (the Four C's)
```
        ┌──────────────── kernel/ (IMMUTABLE) ────────────────┐
        │ invariants: fake-money-only, 5 rules, param bounds   │
        │ fitness: CRPS + Brier(Murphy) + PnL  (the ruler)     │
        └──────────────────────────────────────────────────────┘
 papertrader/lib/engine.py   →  GROUND TRUTH  BET / SKIP
 desk/brief.py               →  reason + confidence (may VETO, never upgrade)
 desk/memory/                →  append-only lessons  +  rebuildable SQLite index
 desk/autopsy.py             →  Reflexion: resolved trade → generalized lesson
 desk/risk.py                →  decline losing categories + liquidity rule
 desk/backtest_wf.py         →  walk-forward OOS fitness (embargo + costs)
 desk/{overseer,sandbox,promote}.py → guard-railed self-modification
 desk/run_cycle.py           →  the orchestrator (cron/Prefect entry point)
```

## Run it now (zero cost, mock LLM)
```bash
python -m desk.run_cycle            # one full reflective cycle
python -m desk.brief --scan papertrader/data/scans/<file>.json   # briefs on a scan
python -m desk.digest               # write/print the daily change digest
python -m desk.backtest_wf          # walk-forward fitness on the ledger
for t in desk/tests/test_*.py; do python "$t"; done              # 36 tests
```

## Going live — the two human steps
1. **Real LLM:** create `desk/.env` with `DESK_LLM=claude` + `ANTHROPIC_API_KEY=...`
   (cheap subtasks → Haiku, debate/autopsy → Opus). Until then the **mock** backend
   runs the full pipeline deterministically.
2. **Cloud:** see [deploy/README-DEPLOY.md](deploy/README-DEPLOY.md) — Oracle Cloud
   Always Free ($0) or Hetzner CAX11; `bash desk/deploy/setup_vps.sh`.

## The six self-modification guardrails (self-mod is OFF by default)
1. **Immutable kernel** — the loop can't edit the rules or its own fitness ruler.
2. **Git-commit-per-change** — every change is one commit; `git revert` to undo.
3. **Benchmark-gated** — must beat the champion on walk-forward OOS CRPS/Brier;
   PnL alone can never promote (anti-reward-hack).
4. **Static analysis + sandbox** — AST scan, then isolated subprocess (`python -I`,
   stripped env, timeout); banned imports/calls rejected.
5. **Independent overseer** — kernel-integrity + kill-switch + pathology gate with
   FREEZE authority (the autonomous stand-in for a human approval gate).
6. **Daily digest** — `digest_latest.md` so an autonomous system stays legible.

Kill switch: `desk/selfmod_config.json` → `self_modification_enabled: false`.
