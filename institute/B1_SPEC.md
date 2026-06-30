# B1 — Macro Nowcasting Vertical (US CPI first) — SPEC

**Owner:** Opus authored + verifies. Sonnet 4.6 implements per spec.
**Goal:** the FIRST deep, weather-bot-class vertical. Forecast the next **US CPI
month-over-month % (MoM)** print with an ENSEMBLE of independent FREE models, turn that
into a predictive distribution, price each Polymarket numeric-range market off it, calibrate,
and bet the edge through the EXISTING 7 gates. This is the macro analogue of the weather
bot: an ensemble predicting a measurable quantity, RMSE-weighted, bucket-integrated.

User decision (2026-06-30): depth-first, ONE vertical at a time, FULL weather-bot class,
**free data sources only**. No generic LLM swarm — this is a numerical model like the
weather bot (no LLM in the core forecast).

## The honesty law (same as A5/A6 — non-negotiable)
`p_model` for a market is computed **at snapshot time** from data available THEN (the
nowcast as-of that date; CPI history up to the last released print) and FROZEN into the
row. It NEVER sees the actual print it is forecasting. Settlement fills `y` from the BLS
release only after it publishes. Two-phase, point-in-time. A market's slot is forecast
ONCE (idempotent). This is our backtest integrity.

## Confirmed free data (probed 2026-06-30, no API key required — do not re-guess)
- **BLS public API v1** (resolution + history): `GET
  https://api.bls.gov/publicAPI/v1/timeseries/data/CUUR0000SA0` returns CPI-U (NSA, all
  items) index levels; `Results.series[0].data` = list of `{year, period:"M06",
  periodName:"June", value:"335.123"}`, newest first. No key (v1 limit ~25 calls/day, fine
  for cron). CUUR0000SA0 = CPI-U US city avg, all items, NSA. MoM% = pct change of
  consecutive monthly index levels. Seasonally-adjusted series (for the headline MoM the
  market usually means) = `CUSR0000SA0`.
- **FRED CSV** (model inputs, no key): `GET
  https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL` -> CSV
  `observation_date,CPIAUCSL` monthly back to 1947. `CPIAUCSL` = CPI-U SA. Use for the
  history-driven models so we never depend on a single source.
- **Cleveland Fed Inflation Nowcasting** (third, independent model — BEST EFFORT):
  free daily-updated nowcast of CPI MoM/YoY. If the fetch fails or format drifts, the
  ensemble MUST degrade gracefully to the other two models (never raise). Treat as
  optional: a wired source that strengthens the ensemble when present.

## Hard rules (inherited)
- Pure Python stdlib ONLY (`urllib`, `json`, `csv`, `math`, `datetime`, `re`, `os`,
  `statistics`). No numpy/scipy/pandas. ASCII-only prints (cp1252).
- Fake money only. `git add` specific paths (committer handles).
- ALL network behind injectable fetchers defaulting to real funcs; tests inject fixtures
  and run FULLY offline & deterministic. No real network in any test.
- Reuse `scoring.py`, `corpus.store`, the gate pipeline, the allocator. Plug in as a
  baseline + a resolve adapter; do NOT modify gate/allocator internals.
- Don't deploy probability (Platt) calibration until n >= ~200 (standing rule). The
  per-indicator BIAS + per-model RMSE weighting below are NOT that — they are the
  ensemble's own fitting and are always on.

## Modules
```
institute/verticals/__init__.py
institute/verticals/cpi/__init__.py
institute/verticals/cpi/data.py        # free no-key fetchers (BLS, FRED, Cleveland Fed)
institute/verticals/cpi/models.py      # 3 independent forecasters -> (mean, sigma) of next MoM%
institute/verticals/cpi/ensemble.py    # inverse-RMSE combine -> predictive Normal; bucket_prob
institute/verticals/cpi/calibrate.py   # per-model RMSE weights + bias, fit from history
institute/verticals/cpi/parse.py       # market question -> (indicator, period, lo, hi)
institute/verticals/cpi/sensor.py      # two-phase snapshot/settle (point-in-time honest)
institute/resolve/cpi_adapter.py       # settled cpi store -> ResolvedMarket rows
institute/tests/test_cpi_models.py
institute/tests/test_cpi_ensemble.py
institute/tests/test_cpi_parse.py
institute/tests/test_cpi_sensor.py
institute/tests/test_cpi_adapter.py
```
Plus: register `cpi_nowcast` baseline in `map/baselines.py`; add `BASELINE_MECHANISM`
entry; add CLI `cpi-snapshot`/`cpi-settle`; add cpi to `resolve.load_all_rows()`; wire
the cpi sensor into the GCP cron (daily is enough — CPI is monthly).

Store: `institute/verticals/cpi/` writes to `institute/data/cpi_markets.jsonl` (add to the
.gitignore carve-out so it persists like the other market stores).

---

## 1. `data.py` — free fetchers (all injectable, all degrade gracefully)
- `_get_json(url, timeout=25)` / `_get_text(url, timeout=25)`: thin urllib, `User-Agent:
  institute/1.0`. Raise on error (callers wrap).
- `bls_cpi_series(series_id="CUSR0000SA0", _get=_get_json) -> list[dict]`: call the BLS v1
  endpoint; return `[{"year": int, "month": int, "value": float}, ...]` sorted OLD->NEW
  (parse `period` "M06" -> 6; skip annual "M13"). On error return `[]`.
- `fred_series(series_id="CPIAUCSL", _get=_get_text) -> list[dict]`: download the CSV,
  parse `observation_date,<id>`; return `[{"date": "YYYY-MM-DD", "value": float}, ...]`
  OLD->NEW, skipping blank "." values. On error return `[]`.
- `cleveland_nowcast(_get=_get_text) -> dict|None`: BEST EFFORT. Try to fetch the Cleveland
  Fed inflation nowcast and return `{"cpi_mom": float}` (MoM% for the current month) or
  None on ANY failure. Document the URL used; if it 404s in future this returns None and
  the ensemble copes. Never raise.
- `monthly_mom_pct(levels) -> list[dict]`: given index levels OLD->NEW
  (`[{...,"value"}]`), return MoM% changes `[{"year","month","mom": (v_t/v_{t-1}-1)*100},
  ...]` (one shorter). Pure transform, no network.

## 2. `models.py` — three INDEPENDENT forecasters of next-month MoM%
Each returns `{"name": str, "mu": float, "sigma": float}` (mu = point forecast of next
MoM%, sigma = its own historical error stdev, floored at 0.05 to avoid 0-division). All
take the MoM% history (OLD->NEW) so they are pure + testable; the nowcast model also takes
the optional Cleveland value.
- `seasonal_ar(mom_hist) -> dict`: mu = (calendar-month seasonal mean over the last <=10
  yrs for the TARGET month) + a small AR(1) adjustment on the last residual; sigma = stdev
  of in-sample residuals. Name "seasonal_ar".
- `random_walk(mom_hist) -> dict`: mu = mean of the last 12 MoM% (trailing base rate);
  sigma = stdev of the last 12. Name "random_walk". (The honest naive anchor.)
- `nowcast(mom_hist, cleveland_mom=None) -> dict`: if `cleveland_mom` is not None, mu =
  cleveland_mom, sigma = trailing nowcast-vs-actual error (approx by stdev of last 12 MoM%
  if no error history); else FALL BACK to `random_walk`'s mu with a slightly wider sigma so
  a missing nowcast never breaks the ensemble. Name "nowcast".
`all_models(mom_hist, cleveland_mom=None) -> list[dict]`: returns the three.

## 3. `calibrate.py` — per-model RMSE weights (the weather-weights analogue)
- `fit_weights(mom_hist, build_models, min_train=24) -> dict`: walk-forward over the
  history: for each month t (after min_train), build each model on data < t, record its
  error vs the actual MoM% at t. Return `{model_name: rmse}` plus `{"bias": mean signed
  error of the ENSEMBLE mean}`. Pure, deterministic, no network. If history too short,
  return uniform `{name: 1.0}` and bias 0.0.
- `inverse_rmse_weights(rmse_map) -> dict`: `w_i = (1/rmse_i) / sum(1/rmse_j)`; guard
  rmse<=0 with a small floor. Sums to 1.

## 4. `ensemble.py` — combine -> predictive Normal -> bucket probability
- `combine(models, weights, bias=0.0) -> dict`: weighted mean `mu* = sum(w_i*mu_i) - bias`;
  pooled sigma `sigma* = sqrt( sum(w_i*(sigma_i^2 + (mu_i-mu_raw)^2)) )` (mixture variance:
  within-model + across-model spread, so disagreement widens the distribution). Return
  `{"mu": mu*, "sigma": max(sigma*, 0.05)}`.
- `norm_cdf(x)`: standard normal CDF via `math.erf` (pure stdlib).
- `bucket_prob(mu, sigma, lo, hi) -> float`: `clip( Phi((hi-mu)/sigma) - Phi((lo-mu)/sigma) )`
  with `lo=-inf`/`hi=+inf` allowed (one-sided markets). Use `scoring.clip`.
- `forecast_distribution(mom_hist, cleveland_mom=None) -> dict`: glue — build models, fit
  weights, combine; return `{"mu","sigma","weights","n_train"}`. This is the per-release
  predictive distribution the sensor freezes.

## 5. `parse.py` — market question -> structured claim
`parse_market(question, slug) -> dict|None`. Recognize US CPI MoM markets first (lead
scope). Return `{"indicator":"us_cpi_mom","period":"YYYY-MM","lo":float,"hi":float}` or
None if not a parseable US-CPI-MoM market.
- "Will monthly inflation increase by 0.3% in June?" -> the print rounds to 1 decimal, so
  0.3 means the bucket `[0.25, 0.35)` -> lo=0.25, hi=0.35.
- "...more than X%" -> lo=X, hi=+inf ; "...less than X%" -> lo=-inf, hi=X ;
  "...between A% and B%" -> lo=A, hi=B.
- Map the month name + current year context to `period`. Keep a small MONTHS dict.
- Be CONSERVATIVE: if the indicator/region is ambiguous (UK, China, GDP, YoY annual),
  return None for B1 (those are later increments). Better to abstain than misparse.

## 6. `sensor.py` — two-phase, point-in-time honest
Store: `CPI_STORE = institute/data/cpi_markets.jsonl`. Reuse `corpus.store`.
Open row schema:
```python
{"market_id": str, "archetype": "econ-cpi", "t0": iso8601Z, "q_yes": float,
 "question": str, "end_date": iso8601Z, "status": "open", "y": None, "settled_ts": None,
 "meta": {"indicator","period","lo","hi","mu","sigma","p_model","forecast_ts","slug"}}
```
- `fetch_active_cpi(_get=..., max_pages=15) -> list[dict]`: page Gamma
  `/markets?...active=true&closed=false&order=volume&ascending=false`; keep markets where
  `parse_market` returns non-None AND clobTokenIds double-parses AND outcomePrices is a
  2-float list; `q_yes = float(prices[0])`. (Same Gamma double-parse as crypto.)
- `snapshot(store_path=CPI_STORE, fetch=fetch_active_cpi, distribution=None, now=None)`:
  for each fetched market not already open in the store, compute the predictive
  distribution ONCE for its `period` (cache by period so we don't refit per bucket), then
  `p_model = bucket_prob(mu, sigma, lo, hi)`; freeze mu/sigma/p_model into meta; append.
  `distribution` defaults to a closure that pulls BLS/FRED/Cleveland live and calls
  `ensemble.forecast_distribution`; tests inject a deterministic one. Dedupe on open
  market_id. Return new rows. POINT-IN-TIME: uses only released history + today's nowcast.
- `settle(store_path=CPI_STORE, resolve=resolve_cpi, now=None)`: for open rows past
  `end_date`, call `resolve(row)` -> `y in {0,1}` or None. `y=1` iff the ACTUAL released
  MoM% for that period falls in `[lo,hi)`. Set y/status/settled_ts; overwrite; return
  settled.
- `resolve_cpi(row, bls=data.bls_cpi_series) -> int|None`: fetch BLS series; compute the
  realized MoM% for `meta.period`; if not yet published return None; else
  `1 if lo <= mom < hi else 0`. On error None (retry next run).

## 7. `resolve/cpi_adapter.py`
`load_rows(store_path=CPI_STORE) -> list[dict]`: settled rows with int `y` ->
`ResolvedMarket(market_id, archetype="econ-cpi", t0, q_yes, y, realized_pnl=None,
realized_side=None, stake=1.0, meta=row["meta"]).dict()`. The frozen `p_model` rides in
meta. Empty/missing store -> []. No network.
Add `econ-cpi` to `factor.CELL_FACTORS`: `{"macro": 1.0}` (correlates with other macro
cells; CONSTITUTION Seam 2). Add `cpi_adapter` to `resolve.load_all_rows()`.

## 8. `cpi_nowcast` baseline (`map/baselines.py`)
```python
def cpi_nowcast(rm, edge=0.05):
    """Bet our calibrated nowcast vs the crowd on a CPI range bucket.
    Reads the point-in-time p_model frozen at snapshot. No model -> abstain."""
    meta = rm.get("meta", {})
    p = meta.get("p_model")
    if p is None:
        return rm["q_yes"], None
    q = rm["q_yes"]
    if p - q > edge:  return p, "YES"
    if q - p > edge:  return p, "NO"
    return p, None
```
Register `BASELINES["cpi_nowcast"] = (cpi_nowcast, {}, True)`; add
`BASELINE_MECHANISM["cpi_nowcast"] = ("model_vs_crowd", "free macro nowcast ensemble
diverges from the crowd's CPI-bucket price; bet the edge")`. Flows through Gates 1-7 +
allocator unchanged.

## 9. CLI + cron
- `cmd_cpi_snapshot()`: `sensor.snapshot()`, print `f"snapshotted {n} CPI range markets"`.
- `cmd_cpi_settle()`: `sensor.settle()`, print `f"settled {n} CPI markets"`.
- Wire both elifs + docstring. CPI is monthly, so add a DAILY cron line (e.g. `20 12 * * *`)
  on the VM running snapshot+settle for cpi, committing `institute/data`. (The snapshot is
  point-in-time honest, so daily re-snapshots simply pick up newly-listed markets; existing
  rows are never re-forecast.)
- NOTE: unlike A6's LLM forecast, this vertical's forecast is a FREE deterministic numeric
  model, so there is NO INSTITUTE_LIVE_FORECAST gate and no placeholder-burn risk — the
  frozen p_model is a real forecast from real data. It is safe to run live immediately.

## 10. Tests (offline, deterministic — NO real network; inject all fetchers/fixtures)
- **test_cpi_parse.py:** the three phrasings (by-X%, more-than, between) parse to correct
  lo/hi; "0.3%" -> [0.25,0.35); non-US / GDP / YoY questions -> None.
- **test_cpi_models.py:** on a small synthetic MoM history each model returns finite
  mu + sigma>=0.05; nowcast(cleveland=0.4) -> mu==0.4; nowcast(cleveland=None) falls back
  (no raise); deterministic.
- **test_cpi_ensemble.py:** inverse_rmse_weights sums to 1 and weights the lower-RMSE model
  more; bucket_prob over (-inf,inf)==~1, symmetric bucket around mu is < 1; combine widens
  sigma when models disagree; norm_cdf(0)==0.5.
- **test_cpi_sensor.py:** inject a fake fetch (2 parseable markets) + a deterministic
  distribution -> snapshot writes 2 open rows with p_model frozen; re-run -> 0 new
  (idempotent). settle: an open row past end_date with an injected resolve->1 settles y==1;
  future-dated stays open; resolve->None stays open. Assert `y` never read at snapshot.
- **test_cpi_adapter.py:** settled+open mixed store -> load_rows returns only settled as
  ResolvedMarket dicts with archetype=="econ-cpi" and p_model in meta; empty -> [].

Run `python -m pytest institute/tests -q` from repo root -> all green (162 prior + new).

## 11. Deviations
If the spec forces an unsound choice, fix it soundly with a one-line `# DEVIATION:`
comment and report it. In particular: confirm the exact Cleveland Fed nowcast URL/parse at
build time; if it is not cleanly fetchable without a key, wire `cleveland_nowcast` to
return None (ensemble degrades to two models) and report that — do NOT add a paid/keyed
source (free-only rule).
