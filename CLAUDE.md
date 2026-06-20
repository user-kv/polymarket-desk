# Polymarket Weather Desk — CLAUDE.md

## Project
Weather paper-trading bot (fake money only). AU user on VPN — build stays venue-agnostic.
Codebase root: `c:/Users/kavee/projects/polymarket/`

## Architecture
```
papertrader/
  papertrader.py              CLI: scan | settle | report | status | backtest | walkforward
  lib/
    engine.py                 core bet-decision logic (YES + NO side, brain sizing)
    forecasts.py              Open-Meteo ensemble fetch; RMSE-weighted model combination (M2)
    calibration.py            per-city bias + per-model RMSE weights (M2)
    brain.py                  Gemini Flash Kelly sizing brain + veto (M3)
    prob_calibration.py       Platt scaling for probability calibration
    walkforward.py            walk-forward OOS backtest harness
    backtest.py               backtesting engine
    polymarket.py             Gamma API client (clobTokenIds needs double-parse)
    cities.py                 city configs (KDAL, KATL + expansion cities)
    ledger.py                 bets.csv read/write (side + brain columns added M4)
    settlement.py             Wunderground resolution; NO-side win inversion (M4)
    tuning.py                 hyperparameter tuning
  data/
    bets.csv  bankroll.json  calibration.json  scans/  tuning_log.csv
  tests/
    test_engine_longshot.py   test_walkforward.py
desk/                         Research Desk + Second Brain (router, memory, digest)
wiki/                         research notes (raw/ = ignore, don't read unless asked)
```

## Milestone Status
- **M1 ✅** committed `0cbd041` (2026-06-20): walk-forward OOS backtest + Platt calibration.
  OOS verdict (165 markets): yes_raw +21.9% ROI; no_longshot_cal 8/8 wins; calibration hurts at low n — don't deploy yet.
- **M2 ✅** (2026-06-20): RMSE-weighted model combination + per-station model weights.
  - `lib/forecasts.py`: `bucket_probability_by_model` uses inverse-RMSE weights per model. `get_historical_forecast_for_city` returns per-model highs for weight fitting.
  - `lib/calibration.py`: `compute_model_weights()` fits per-city GFS/ECMWF/ICON/GEM/UKMO/AIFS RMSE from 7-day archive, stores in `calibration.json`. Auto-called by `calibrate` command.
- **M3 ✅** (2026-06-20): Brain-Kelly sizing (Gemini Flash, off by default via `use_brain: false`).
  - `lib/brain.py`: Gemini Flash veto + Kelly multiplier (0.5–2.0). Falls back to mock (1.0) when key absent. Enable: set `use_brain: true` + `GEMINI_API_KEY` env var.
  - Engine calls brain after all rules pass; can VETO or resize; may NEVER invent bets.
- **M4 ✅** (2026-06-20): Live NO-side paper betting (exploits favorite-longshot bias).
  - Engine evaluates NO side when YES fails rule 1; qualifies when `ask > prob + threshold` AND `ask ≤ 0.15`. NO entry price = `1 - ask`.
  - Settlement: NO bets win when bucket does NOT resolve.
  - Ledger: `side`, `brain_multiplier`, `brain_rationale` columns added to `bets.csv`.

## Key Constraints
- Fake money only. Never add real-money automation.
- Resolution source: **Wunderground** (not NWS CLI).
- `git add` specific paths only — never `-A`.
- Don't deploy probability calibration until n ≥ ~200 markets.

## Working Style
- Autonomous perceive→reason→plan→act→verify→critique→improve loop.
- Report at milestones only — no status narration during implementation.
- Start fresh chat at each milestone completion.
- Truncate large bash outputs: `| head -50` or `| tail -30`. Never dump full scan JSONs.
- Do NOT read `data/scans/`, `logs/`, or `wiki/raw/` files unless explicitly asked.
- Prefer targeted reads (specific file + line range) over exploratory reads.
