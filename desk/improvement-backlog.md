# Improvement Backlog — auto/self-improve-2026-06-21

Session start: 2026-06-21 14:52 AEST (04:52 UTC). Agent: Opus 4.8 orchestrating, Sonnet 4.6 implementing.
Branch: `auto/self-improve-2026-06-21`. Fake money only. All behavioural changes need a passing test or backtest/walkforward delta.

## Perceive — state of the desk (verified this session)
- Tests: 11 pass, but **only when run from `papertrader/`** (imports are `lib.*`, no `conftest.py` / sys.path shim). `pytest` from repo root errors at collection. No CI runs tests — "green" rests on local runs.
- Ledger: 2 open NO bets, **0 settled** (pre-M5 longshot losses archived 2026-06-20, bankroll reset to $2000). No live ROI signal yet — the walk-forward harness on historical snapshots is the only evidence machine.
- `data/calibration.json` is `{}` — **M2 is inert**: per-city bias correction and RMSE model-weights are no-ops; live forecasts run equal-weight, zero bias-correction. `calibrate` only runs in the **weekly** cron (Sun 09:00 UTC), which today hasn't fired yet (it's 04:52 UTC). Weekly cron line does NOT git-commit; calibration.json reaches the repo only because the every-30-min scan cron git-adds `papertrader/data`. Should self-heal at 09:00 UTC — MONITOR, don't hand-edit (a local commit would race the VM).
- Scheduler: GCP VM sole scheduler. scan+settle every 30 min (commits `papertrader/data`, `desk/...`), `run_cycle` daily 14:15 UTC, `weekly` Sun 09:00 UTC. GH Actions schedules disabled. Last scan 04:00 UTC today.
- Backtest/walkforward refetch observed highs from the network for every (station,date) on every run — 254 markets, ~3 s each ≈ 10+ min/run, network-flaky. No disk cache. This throttles all iteration on trading logic.
- Settlement scoring: NWS and Open-Meteo reanalysis disagree by up to ~5°F on several days (e.g. Austin 06-16 86.4 vs 91.4). Settlement prefers NWS when both present; warning only fires above 5°F. Comparability constraint — do NOT swap resolution source. Note only.

## Ranked backlog (impact × confidence ÷ effort)

### 1. Disk cache for observed highs (backtest/walkforward) — DONE? no — FOUNDATIONAL
`backtest.score_markets` / `settlement.fetch_observed_high` re-hit Open-Meteo + NWS for every (station,date) every run. Add a persistent JSON cache keyed `station|date` in `data/` so repeated backtests are seconds, not 10+ min, and resilient to API hiccups. **Unblocks fast verification of every trading-logic change below** — that's why it's #1 despite being reliability not trading.
- Verify: 2nd `walkforward` run completes in seconds with byte-identical strategy numbers vs cold run.

### 2. Walk-forward must test the DEPLOYED path (NO on RAW prob)
The decision to enable `allow_no_side` cited `no_longshot_cal` going 8/8 OOS — but that strategy bets on **calibrated** probs, while the live engine bets the **raw** ensemble prob (calibration is correctly OFF at low n). The backtest validates a strategy we don't run. Add `no_longshot_raw` (and `both_raw`) to `walkforward._simulate` reporting so the evidence matches production.
- Verify: new strategy rows appear; compare `no_longshot_raw` vs `no_longshot_cal` ROI/win% to confirm the live config is justified (or flag if it isn't).

### 3. NO-side brain share/stake desync (engine.py) — latent money-path bug
`engine.py:209` computes `no_shares = no_stake / no_entry` **before** the brain multiplier rescales `no_stake` at `:240-245`. Result: NO bet ships with shares from the pre-brain stake but the post-brain stake → payout math wrong. YES recomputes shares after the multiplier (`:248`), so only NO is affected. Latent today (`use_brain: false`) but bites the moment the brain is enabled.
- Verify: unit test — NO bet with brain multiplier 2.0 must satisfy `shares == round(stake / (1-ask), 4)`.

### 4. `conftest.py` so tests collect from repo root — protects "green"
Add `papertrader/conftest.py` (or `tests/conftest.py`) that puts `papertrader/` on `sys.path`, so `pytest` works from anywhere. Removes the silent footgun where a root-level `pytest` "fails" and masks real signal.
- Verify: `python -m pytest papertrader/tests -q` from repo root passes all tests.

### 5. MONITOR — calibration.json populates at weekly cron (Sun 09:00 UTC)
Confirm after 09:00 UTC that `calibration.json` gains per-city `correction_f` + `model_weights` and that the next 30-min scan commits it. If still `{}` tomorrow, `calibrate`/weekly is failing — investigate then. No code change now.

## Done log
(commits appended as items land)
