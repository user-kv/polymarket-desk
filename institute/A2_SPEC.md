# A2 — Evidence Machine (Gate 1) — Implementation Spec

Opus-authored spec. Implementer: Sonnet 4.6. Build EXACTLY this; do not redesign
the statistics. Pure stdlib (`math`, `random`, `statistics`) — NO numpy/scipy.

## Goal
Gate 1 of the 7-gate stack (CONSTITUTION §6): four independent attempts to
DISPROVE a cell's edge. A cell only passes if it survives all applicable tests.
The optimiser is assumed adversarial to the metric, so we deflate against the
trial registry and test the null hard.

## Files to create
```
institute/evidence/__init__.py
institute/evidence/backtest.py      # returns series from a baseline over rows
institute/evidence/stats.py         # DSR, permutation null, PBO/CSCV, SPRT (pure math)
institute/evidence/gate1.py         # orchestrates the four tests → verdict dict
institute/tests/test_stats.py       # unit tests for each statistic
institute/tests/test_gate1.py       # end-to-end gate on synthetic + real anchor
```
Also: extend `institute/cli.py` with `gate <archetype> <baseline>` command.

## Interfaces you MUST bind to (already exist)
- `institute.map.baselines._sim_profit(side, q_yes, y, cost=0.0)` → float per-$1 profit.
- `institute.map.baselines.price_follow / longshot_fade` → `(p_forecast, side|None)`.
- `institute.scoring.market_relative_S(p, q, y)`, `mean(xs)`.
- `institute.resolve.weather_adapter.load_rows()` → list[ResolvedMarket dict] with
  keys: q_yes, y, archetype, realized_pnl, realized_side, stake, market_id, t0, meta.
- `institute.corpus.registry.log_trial(path, trial)`, `trial_count(path)`,
  `all_trials(path)`. `institute.corpus.schema.Trial`.
- Registry path: `institute/data/trials.jsonl` (data/ is gitignored). Define a
  `REGISTRY` constant in gate1.py from `os.path.dirname` like cli.MAP_OUT does.

## backtest.py
```
def returns_series(rows, baseline_fn, cost=0.0, **kw) -> list[float]:
    # For each row where baseline emits side != None, append _sim_profit(side, q_yes, y, cost).
    # Prefer realized_pnl/stake when present AND realized_side == side (the anchor),
    #   mirroring baselines.evaluate's use_realized branch; else simulate.
    # Skip rows where side is None (no bet). Returns the per-bet net return vector.

def win_loss_stream(rows, baseline_fn, **kw) -> list[int]:
    # 1 if that bet's return > 0 else 0, same row filter as above. Feeds SPRT.
```

## stats.py — implement EXACTLY these (pure stdlib)
Helpers: `norm_cdf(x)` via `0.5*(1+math.erf(x/sqrt2))`; `norm_ppf(p)`
(Acklam or Beasley-Springer-Moro rational approx — include a known-good impl).

### deflated_sharpe(returns, n_trials, sr_benchmark=0.0)
Per-bet Sharpe `sr = mean/std` (population std; return verdict skip if std==0 or n<8).
Bailey & López de Prado DSR:
```
g3 = skew(returns); g4 = kurtosis(returns)  # g4 = standardised 4th moment (normal=3)
T  = len(returns)
# expected max Sharpe under the null of n_trials independent strategies:
emc = 0.5772156649  # Euler-Mascheroni
sr0 = sqrt(Var_sr_across_trials) * ((1-emc)*norm_ppf(1 - 1/n_trials)
        + emc*norm_ppf(1 - 1/(n_trials*e)))
# When per-trial Sharpe variance is unknown, approximate Var_sr ≈ (1/(T-1))*(1 - g3*sr + (g4-1)/4*sr^2)
# (the same variance used to standardise below). n_trials>=2 required for sr0; if n_trials<2, sr0=sr_benchmark.
dsr = norm_cdf( ((sr - sr0) * sqrt(T-1)) / sqrt(1 - g3*sr + ((g4-1)/4)*sr*sr) )
```
Return dict: {sr, sr0, dsr, T, passed: dsr >= 0.95, reason}.
Guard the sqrt denominator (clamp to >= 1e-9); if negative under sqrt, mark
passed=False with reason "ill-conditioned".

### permutation_pvalue(rows, baseline_fn, B=2000, seed=0, **kw)
Observed statistic = mean market-relative S over rows where a bet is placed
(use scoring.market_relative_S(p,q,y)). Then B times: shuffle the y labels across
rows (keep q_yes fixed), recompute the statistic. 
p = (#{stat_perm >= stat_obs} + 1)/(B+1). passed = p < 0.05.
Return {stat_obs, p_value, B, passed}.

### pbo_cscv(returns_matrix, S=8)
returns_matrix: list of C config return-vectors, all length T (rows aligned in time).
If C < 2: return {pbo: None, passed: True, reason: "single config — PBO N/A"}.
CSCV: split T rows into S equal contiguous blocks; for each of the C(S, S/2)
ways to choose half the blocks as IS (rest OOS): pick config with best IS mean
Sharpe; record its OOS rank ω = rank/(C+1) (fraction of configs it beats OOS).
logit λ = ln(ω/(1-ω)); PBO = fraction of splits with λ <= 0. passed = pbo < 0.5.
Keep it simple: use mean/std Sharpe per block-set; itertools.combinations.
Return {pbo, n_splits, passed}.

### sprt(win_loss, p0, p1, alpha=0.05, beta=0.05)
Wald SPRT on a Bernoulli stream. logA = ln((1-beta)/alpha), logB = ln(beta/(1-alpha)).
Accumulate llr += ln(p1/p0) if win else ln((1-p1)/(1-p0)). 
Decide "accept_H1" when llr>=logA, "accept_H0" when llr<=logB, else "continue".
Return {decision, llr, n_used, p0, p1}.
Caller picks p0 = break-even win rate for the strategy's odds. For longshot_fade
NO bets at price≈(1-q): break-even win rate = price = (1-q). Use the MEAN executable
price across the cell's bets as p0; p1 = min(0.98, p0 + 0.10) (target 10pp edge).

## gate1.py
```
def run_gate(archetype, baseline_name, rows=None, log=True) -> dict:
    # load rows via weather_adapter if rows is None; filter to archetype.
    # resolve baseline_fn from baselines (price_follow/longshot_fade).
    # build returns_series + win_loss_stream.
    # n_trials = max(2, trial_count(REGISTRY)+1)  (this run counts).
    # run deflated_sharpe, permutation_pvalue, sprt. PBO: pass the single
    #   config matrix [returns] (→ N/A) for now; wire multi-config in A3.
    # verdict = "pass" if dsr.passed and perm.passed and sprt.decision=="accept_H1"
    #            else "insufficient" if sprt.decision=="continue" else "fail".
    # if log: registry.log_trial(REGISTRY, Trial(id=..., archetype, strategy_id=baseline_name,
    #   metrics={...}, verdict=verdict, ts=utcnow_iso())).
    # return the full dict (all four sub-results + verdict).

def render(result) -> str   # one-screen summary table.
```

## CLI
`python -m institute.cli gate weather-daily longshot_fade` → print gate1.render(run_gate(...)).
Use ASCII only in prints (Windows cp1252 console — no →, use ->).

## Tests (all must pass; pure stdlib)
test_stats.py:
- norm_cdf(0)≈0.5, norm_ppf(0.975)≈1.96 (±0.01).
- deflated_sharpe on a strong constant-ish positive series with n_trials=2 → dsr high (>0.9);
  with n_trials=1000 → dsr strictly LOWER (deflation bites). Assert monotonic.
- permutation_pvalue: on a longshot-biased synthetic set (q≈0.2, mostly y=0) with
  longshot_fade → p < 0.05; on random y → p NOT < 0.05 (use fixed seed).
- sprt: a stream of mostly-wins vs p0=0.5,p1=0.7 → "accept_H1"; mostly-losses → "accept_H0".
- pbo_cscv single config → passed True, pbo None.
test_gate1.py:
- run_gate("weather-daily","longshot_fade", log=False) returns dict with all keys;
  dsr/perm/sprt present; verdict in {pass,insufficient,fail}. (n is small/real, so
  do NOT assert pass — assert structure + that perm.stat_obs > 0 matches +EV anchor.)
- run_gate logs a trial when log=True into a tmp REGISTRY (monkeypatch path) and
  trial_count increments.

## Constraints
- Pure stdlib. No new deps. ASCII prints. Deterministic (seed all randomness).
- Don't touch A1 files except adding the `gate` branch to cli.py main().
- Keep functions small, commented like the existing institute style (terse, why-not-what).
