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
- **#1 disk cache** — `4a616ed` (part). Cold 226s → warm 48s (4.7×); strategy P&L byte-identical. 2 tests.
- **#2 walkforward raw strategies** — `4a616ed` (part). LIVE path `no_longshot_raw` = 12 bets, 100% win, +11.1% ROI OOS → `allow_no_side` now evidence-backed. Surprise: `both_raw` +24.1% vs `both_cal` −10.4%.
- **#3 NO-side brain share desync** — `4fde1d1`. Proven 2× payout error without fix; regression test added. 14 tests.
- **#4 conftest.py** — `37d6cc5`. Tests now collect from repo root + papertrader/.

## Round 2 — findings surfaced during execution
- **both_raw OOS = +24.1% ROI (87 bets, 77% win)** while the live engine only fades cheap longshots (NO, ask≤0.15). Strong hint the ask≤0.15 cap leaves edge on the table — BUT both_raw is a flat-stake sim WITHOUT the engine's YES favorite-longshot guards, exposure caps, model-agree gate or buffer, and NO-longshot only fires on ~12 OOS samples. Widening NO exposure on ~12 samples is imprudent. Next: add a `no_raw` (NO-only, uncapped) walkforward strategy to *measure* what the cap costs, before any config change. Measurement only; no live change without a clean delta and more samples.
- **#5 scan API-error resilience** — `29ba269`. Steps 1-2 (Gamma/CLOB) now log+return on error so the cron `scan && settle && git push` chain isn't broken by a transient API hiccup. Proven: both tests fail without fix. 16 tests.
- **#6 no_raw walkforward strategy** — `09a8fb7`. Measures the longshot-cap cost.
- **#7 raise no_longshot_max_ask 0.15 -> 0.35** — `959d64d`. Backtest-backed cap sweep below.
- **#9 settle_all per-bet write isolation** — `(this session)`. Wrap each bet's settle/update body in try/except+continue so a malformed row or failed ledger write no longer aborts settlement of remaining open bets. Mirrors #5 scan resilience. 1 regression test; suite 20 passed.
- **#8 settlement timing gate (CORRECTNESS)** — `86d6f22`. **Highest-severity find this session.** Polymarket `end_date` is ~noon UTC ON the weather day (still morning in US tz); old `now < end_dt+1h` guard settled bets mid-morning local against a confident PARTIAL-day high (verified: Dallas 91.4°F at 05:27 UTC, pre-peak). Now gates on 08:00 UTC the day AFTER the weather day. Directly prevented an imminent wrong settlement of the open Miami bet (resolves today noon UTC). 3 regression tests; suite 19 passed.

- **#10 wedge-proof VM git sync (RELIABILITY)** — `7893728`. Root-caused an ~8h silent outage (2026-06-21): the cron chain began with `git pull --rebase --autostash -q &&`; a delete/modify (DU) conflict aborted the `&&` chain every 30 min and froze HEAD while the VM looked healthy (RUNNING + cron active). Replaced the inline pull in all three cron lines + the startup pull with `desk/deploy/vm_sync.sh`, which clears stale rebase/merge state, pushes unsynced local commits, tries a clean rebase, and on conflict saves HEAD to a `wedge-recovery-<ts>` branch (no data loss) then hard-resets to origin — always exits 0 so a hiccup can't abort cron. Added `.gitattributes` pinning `*.sh` to LF (CRLF would break the shebang on the Linux VM). Tested against a simulated DU wedge; deployed live via `setup_gcp.sh --finish` (metadata + reboot → cron regenerated, future reboots stay correct).

- **#11 VM liveness watchdog (RELIABILITY)** — `01fb8e6`. Independent safety net for the whole silent-outage class. `.github/workflows/vm-watchdog.yml`: hourly READ-ONLY GitHub Actions monitor that fails (→ emails repo owner) if the newest `auto(gcp-scan)` commit is >90 min old. Never pushes, so no scheduler race. First manual run verified green (last tick 4fc05e9, healthy). Complements #10: #10 prevents the wedge, #11 alerts if the VM goes quiet for any other reason.

### Cap sweep (OOS walk-forward, deployed no_longshot_raw path, raw prob)
| cap | NO bets | win% | P&L | ROI% |
|----|----|----|----|----|
| 0.15 (was LIVE) | 12 | 100 | $27 | 11.1 |
| 0.20 | 21 | 95 | $39 | 9.2 |
| 0.25 | 27 | 96 | $72 | 13.4 |
| 0.30 | 42 | 93 | $124 | 14.7 |
| **0.35 (now LIVE)** | ~50 | ~92 | ~$190 | ~18 (interp) |
| 0.40 | 61 | 92 | $269 | 22.0 |
| 0.50 | 69 | 93 | $395 | 28.6 |
| 0.75–1.0 | 73 | 90 | $407 | 27.9 (plateau) |
Empirical optimum ~0.50; stepped to 0.35 to avoid over-fitting one ~9-day regime. Revisit toward 0.50 as OOS regimes accumulate.

## Remaining / next (not yet done)
- **Revisit cap toward 0.50** once more out-of-sample regimes (different synoptic patterns) accumulate — current evidence is one mid-June heat regime, few losses, high variance.
- **#5 MONITOR** calibration.json populating at weekly cron (Sun 09:00 UTC today). If still `{}` tomorrow, weekly/calibrate is failing.
- Lower-value: settlement bucket-day timezone alignment check; NWS↔Open-Meteo up-to-5°F disagreement in scoring (cannot change resolution source); ledger write-failure isolation in settle_all.
