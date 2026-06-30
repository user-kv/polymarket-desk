# The Institute — Vertical Template (03)

**Status:** PLANNING ONLY. Blueprint for stamping out new verticals.
**Date:** 2026-06-30
**Generalizes:** weather bot (M1–M5) + CPI vertical (B1) into a reusable anatomy.

A "vertical" is a deep specialist module that covers ONE market archetype end-to-end:
data ingestion → model(s) → ensemble → calibrate → parse market questions → snapshot →
settle → feed Gate pipeline. Every vertical is self-contained, independently testable,
and plugs into the existing gates + allocator without touching their internals.

---

## The canonical module anatomy

```
institute/verticals/<slug>/
    __init__.py
    data.py         # free no-key fetchers for this vertical's data sources
    models.py       # 3+ independent forecasters -> (mu, sigma) or (p_i) per question
    ensemble.py     # combine models -> predictive distribution or p_model
    calibrate.py    # per-model RMSE/error weights + bias correction; walk-forward fit
    parse.py        # market question text + slug -> structured claim (lo, hi, archetype)
    sensor.py       # two-phase snapshot/settle; the point-in-time honesty contract
    [adapter.py]    # [optional] settled-row -> ResolvedMarket for the gate pipeline

institute/resolve/<slug>_adapter.py     # ResolvedMarket loader (if not inline)
institute/data/<slug>_markets.jsonl     # live store (gitignored with carve-out)
institute/tests/test_<slug>_*.py        # offline tests, inject all fetchers/fixtures
```

Each component is described in detail in the sections below. The CUSTOMIZATION SLOTS
mark where each vertical injects its own data, models, and edge engines.

---

## Module 1 — `data.py` (fetchers)

**Purpose:** everything that touches the network lives here. All other modules are pure.

**Standard interface:**
```python
def _get_json(url, timeout=25, _get=None): ...   # injectable; default = urllib
def _get_text(url, timeout=25, _get=None): ...   # injectable; default = urllib

def primary_series(_get=_get_json) -> list[dict]:   # main data source; OLD->NEW
def secondary_series(_get=_get_text) -> list[dict]: # backup source; same schema
def optional_nowcast(_get=_get_text) -> dict|None:  # BEST EFFORT; None on any failure
```

**Rules:**
- Every function catches ALL exceptions and returns `[]` or `None` on failure.
  The ensemble MUST degrade gracefully to remaining models.
- User-Agent header: `institute/1.0`
- No API key at the free tier. Design the Premium slot as an injectable `_get` override.
- Pure transform functions (e.g., `mom_pct(levels)`, `parse_csv(text)`) live here too
  but do not touch the network — they are tested inline.

**[SLOT D1] Primary data source:**
- Weather: `Open-Meteo ensemble API` (temperature members, free, no key)
- CPI: `BLS public API v1` (CPI-U series, free, no key, 25 calls/day)
- Employment: `BLS establishment survey` (FRED `PAYEMS`, free CSV)
- Politics: `538 poll aggregator`, Wikipedia infobox, RCP poll averages (all free)
- Sports: `ESPN unofficial API`, `sportsreference.com` scrape (free), `SportsDB API`
- Crypto: `CoinGecko API` (free tier, 10-50 calls/min), CMC (free tier)

**[SLOT D2] Secondary / backup source:**
- Same data from a different provider. Only used if primary fails OR as a cross-check.
- CPI: `FRED CSV` (CPIAUCSL, same series, different endpoint). If both agree → high confidence.
- Weather: `NWS gridpoints API` as a reality-check on Open-Meteo.

**[SLOT D3] Optional third-party nowcast (best-effort):**
- A pre-built forecast from a credible external source. If absent → ensemble degrades.
- CPI: Cleveland Fed nowcast (free, no key). Employment: Atlanta Fed Wage Tracker (free).
- Weather: (not needed — Open-Meteo already IS the ensemble of NWP models).
- Sports: injury feeds (no universal free source; ESPN injury report page is scrapable).

---

## Module 2 — `models.py` (forecasters)

**Purpose:** 3+ independent models, each forecasting the same measurable quantity, each
returning its own estimate of uncertainty.

**Standard interface (quant verticals — Engine 1):**
```python
def model_name(history, **context) -> dict:
    """Pure function. No network. Returns {"name": str, "mu": float, "sigma": float}.
    mu    = point forecast of the TARGET quantity (next value, probability, etc.)
    sigma = model's own error estimate; floored at 0.05.
    """
```

**Standard interface (qualitative verticals — Engine 3):**
```python
def swarm_agent(question, evidence, persona) -> dict:
    """LLM call (injectable mock for tests).
    Returns {"p": float, "rationale": str}.
    p in (0,1); rationale <= 100 tokens.
    """
```

**[SLOT M1] Model family selection:**
The critical decision in any vertical. Independence principle: models must use
STRUCTURALLY DIFFERENT approaches, not just different parameters on the same approach.

```
Quant vertical — target diversity matrix:
  Model A: Mechanistic/structural    (seasonal pattern, domain physics)
  Model B: Statistical/trailing      (AR, trailing mean — the honest naive anchor)
  Model C: External/independent      (third-party nowcast, leading indicator, proxy data)

Examples by vertical:
  CPI:         seasonal_ar  |  random_walk      |  Cleveland Fed / PPI-regression
  Temperature: GFS ensemble |  ECMWF ensemble   |  ICON / UKMO / GEM / AIFS (Open-Meteo)
  Employment:  seasonal_ar  |  trailing_mean    |  ADP nowcast (free tier)
  Polling:     RCP avg      |  State-level shift |  Ensemble of poll aggregators
  Crypto:      ARIMA(p,q)   |  GARCH vol model  |  On-chain metrics regression

Qualitative vertical — persona diversity matrix (PolySwarm):
  10 personas sampled from: base-rate statistician, macroeconomist, contrarian,
  domain expert (archetype-specific), political scientist, geopolitical analyst,
  tech industry analyst, public health expert, legal analyst, market historian.
  Each persona WITHHOLDS the current market price q_yes during forecast.
```

**[SLOT M2] Error/uncertainty estimation:**
Each model must produce its OWN sigma (not a shared global sigma). Sources:
- Historical residuals (walk-forward OOS: compute errors model made on past data).
- For external nowcasts with no published RMSE: use the vertical's trailing error
  stdev as a floor.
- For LLM agents: sigma proxy = inter-agent std of the 10 swarm forecasts.
Sigma floor: 0.05 (prevents division-by-zero in inverse-RMSE weighting).

**Minimum effective model count:**
- 3 is the minimum for a functional ensemble. Below 3, collapsed diversity is too likely.
- Target: 3–5 well-diversified models. Beyond 5 quant models, returns diminish.
- For LLM swarms: 10 agents is the sweet spot (AIA Forecaster finding). 25 sampled from
  50 persona pool (PolySwarm). Diminishing returns past 10; cost scales linearly.

---

## Module 3 — `ensemble.py` (combination)

**Purpose:** combine model outputs into a single calibrated predictive distribution or
probability. Reuses institute-standard code where possible.

**Standard quant interface (reuse from CPI):**
```python
def combine(models, weights, bias=0.0) -> dict:
    """Weighted Gaussian mixture.
    mu*    = sum(w_i * mu_i) - bias
    sigma* = sqrt( sum(w_i * (sigma_i^2 + (mu_i - mu_raw)^2)) )
    Returns {"mu": mu*, "sigma": max(sigma*, 0.05)}
    """

def bucket_prob(mu, sigma, lo, hi) -> float:
    """P(lo <= X < hi) for X ~ Normal(mu, sigma). Uses norm_cdf via math.erf."""

def forecast_distribution(history, **context) -> dict:
    """Glue: call models, calibrate, combine. Returns {"mu","sigma","weights","n_train"}."""
```

**For non-Normal distributions:**
Some verticals need non-Gaussian predictive distributions:
- **Bounded quantity (win probability 0–1)**: use Beta distribution.
  `combine_beta(alpha_models, beta_models, weights)` → Beta(alpha*, beta*)
  `bucket_prob_beta(alpha, beta, lo, hi)` → regularized incomplete beta
- **Count/discrete**: Poisson or NegBin (e.g., goals scored).
  `combine_poisson(lambda_models, weights)` → weighted lambda*
- **Categorical**: Dirichlet (e.g., which of 5 candidates wins).
  Bucket probabilities = Dirichlet marginals per candidate.

For the Institute's current scope, Normal is correct for most measurable-quantity
markets (CPI MoM%, temperature °F, economic growth %). Use Normal first; specialize
only when residuals are clearly non-Normal (test with Shapiro-Wilk on OOS residuals).

**LLM swarm aggregation:**
```python
def aggregate_swarm(p_list) -> dict:
    """Simple mean of forecaster probabilities. Returns {"p_swarm", "p_std"}."""
    n = len(p_list)
    p_swarm = sum(p_list) / n
    p_std = (sum((p - p_swarm)**2 for p in p_list) / n) ** 0.5
    return {"p_swarm": p_swarm, "p_std": p_std}
    # Note: DO NOT use debate/LLM-judge — it overweights outliers and cascades sycophancy
    # Note: DO NOT use geometric mean of log-odds unless calibrated from data
```

**[SLOT E1] Blending rule (model vs market):**
The AIA/PolySwarm blend: `p_final = w * p_model + (1-w) * q_market`.
Default w=0.70 (swarm dominates over market). Recalibrate per archetype from OOS data:
- Liquid, well-traded markets: w→0.30 (market knows more than the model)
- Illiquid long-tail: w→0.70–0.90 (model adds real independent information)
- Early paper period: use PolySwarm's 0.70 as a fixed prior; learn from OOS data.

---

## Module 4 — `calibrate.py` (weight fitting + bias)

**Purpose:** learn from errors. The weather bot's shrinkage calibration pattern, generalized.

**Standard interface:**
```python
def fit_weights(history, build_models, min_train=24) -> dict:
    """Walk-forward OOS. For each period t after min_train:
       fit each model on data < t, record error vs actual at t.
    Returns {model_name: rmse, "bias": mean_signed_error_of_ensemble}.
    If history too short: return uniform {name: 1.0} and bias=0.0.
    Pure, deterministic, no network.
    """

def inverse_rmse_weights(rmse_map) -> dict:
    """w_i = (1/RMSE_i) / sum(1/RMSE_j).
    Guards RMSE<=0 with small floor. Sums to 1.
    """
```

**Bias correction (weather-bot shrinkage pattern):**
```python
def shrinkage_correction(raw_bias, n, K=10):
    """Bayesian shrinkage: correction = (n/(n+K)) * raw_bias.
    K=10 means 4 observations → 29% correction. 50 obs → 83%.
    Prevents overreaction to small samples.
    """
    return (n / (n + K)) * raw_bias
```

**Platt extremization (gated until n≥200 per vertical):**
```python
def platt_extremize(p, alpha=1.732):
    """Push probability toward extremes: undoes RLHF hedge-toward-0.5.
    Only safe when raw p is on the correct side of 0.5.
    alpha = sqrt(3) ≈ 1.732 (Neyman & Roughgarden 2022).
    """
    import math
    lo = math.log(p / (1 - p))
    return 1 / (1 + math.exp(-alpha * lo))
```

**[SLOT C1] Calibration schedule:**
- RMSE weights: refit monthly (or after every 10 new resolved markets).
- Bias correction: refit weekly (captures regime drift faster).
- Platt alpha: fit from data once n≥200, then update quarterly.
- Model pairwise correlation audit: run after every calibration cycle.
  If any pair > 0.7, flag the vertical for model diversity review.

**[SLOT C2] Recalibration trigger:**
- Welch-z decay (already built): if a model's OOS Brier degrades significantly vs
  the baseline, downweight it automatically. The calibration module feeds the gate pipeline.

---

## Module 5 — `parse.py` (question → claim)

**Purpose:** map raw market question text into a structured, typed claim the vertical
can evaluate. The hardest module to get right; the most important for avoiding mismatches.

**Standard interface:**
```python
def parse_market(question: str, slug: str) -> dict|None:
    """Returns structured claim or None if not parseable by THIS vertical.
    Conservative: if ambiguous, return None. Better to abstain than misparse.
    """
```

**[SLOT P1] Claim schema by vertical type:**

Numeric-range markets (CPI, temperature, jobs, GDP):
```python
{"indicator": str,      # "us_cpi_mom", "dallas_high_f", "nfp_thousands"
 "period": str,         # "2026-07" or "2026-07-04"
 "lo": float,           # lower bound (can be -inf)
 "hi": float,           # upper bound (can be +inf)
 "unit": str}           # "pct", "fahrenheit", "thousands"
```

Binary event markets (politics, sports outcomes):
```python
{"event_type": str,     # "election_winner", "match_outcome", "geopolitical_event"
 "entity": str,         # "Donald Trump", "Manchester City", "NATO_Article5_invoked"
 "outcome": str,        # "YES" / "NO" + description
 "resolution_date": str,# ISO8601
 "ambiguity_level": str}# "low" / "medium" / "high" → if high, return None
```

**[SLOT P2] Parsing rules:**
- Numeric precision: "will CPI increase by 0.3%" → bucket [0.25, 0.35) — round to
  1 decimal means the bucket is ±0.05 around the stated value.
- "more than X" → lo=X, hi=+inf. "less than X" → lo=-inf, hi=X. "between A and B" → lo=A, hi=B.
- Month/date extraction: maintain a MONTHS dict + current-year context.
- Abstain conservatively: "UK CPI", "China CPI", "PCE deflator" → None for the US CPI
  vertical. Scope is load-bearing — wrong parse means wrong bet.
- Ambiguous resolution criteria (e.g., "significant" conflict, "major" announcement):
  return None. Ambiguity transfers to the question, not the forecast.

---

## Module 6 — `sensor.py` (the two-phase honest contract)

**Purpose:** the structural moat. SNAPSHOT freezes the forecast at decision time from
data available THEN. SETTLE fills the outcome after resolution. The two phases NEVER
share data in either direction.

```python
OPEN_ROW_SCHEMA = {
    "market_id": str,
    "archetype": str,               # "econ-cpi", "weather-dallas", "politics-us"
    "t0": "ISO8601Z",               # snapshot timestamp — FROZEN
    "q_yes": float,                 # market price at t0 — FROZEN
    "question": str,
    "end_date": "ISO8601Z",
    "status": "open",               # → "settled" after resolve
    "y": None,                      # → 0 or 1 after settle
    "settled_ts": None,             # → ISO8601Z after settle
    "meta": {
        # Vertical-specific frozen forecast:
        "p_model": float,           # final calibrated model probability
        "forecast_ts": "ISO8601Z",  # when p_model was computed
        # Engine 1 fields (quant verticals):
        "mu": float, "sigma": float, "weights": dict, "n_train": int,
        # Engine 3 fields (LLM verticals):
        "p_swarm": float, "p_std": float, "p_supervisor": float,
        # Vertical-specific parsed claim:
        "indicator": str, "period": str, "lo": float, "hi": float,
        # Everything else the vertical needs for settle:
        "slug": str
    }
}
```

**SNAPSHOT function:**
```python
def snapshot(store_path, fetch_fn, distribution_fn, now=None):
    """For each new active market not already in store:
      1. parse_market() → structured claim; skip if None
      2. distribution_fn(claim, now) → {mu, sigma, p_model, ...}  [POINT IN TIME]
      3. Freeze p_model + claim into meta; set t0=now, status="open", y=None
      4. Append to store (jsonl); return new rows

    IDEMPOTENT: market already in store → skip. Never re-forecast.
    distribution_fn uses only data available at `now`. Never looks forward.
    """
```

**SETTLE function:**
```python
def settle(store_path, resolve_fn, now=None):
    """For each open row past end_date:
      1. resolve_fn(row) → y in {0, 1} or None (not yet published)
      2. If y is not None: set status="settled", y=y, settled_ts=now; overwrite
      3. Return settled rows

    POINT-IN-TIME: resolve_fn reads the ACTUAL OUTCOME from an official source.
    y is NEVER read during snapshot. The two phases are structurally isolated.
    """
```

**[SLOT S1] fetch_active markets:**
- Gamma API: `GET gamma-api.polymarket.com/markets?active=true&closed=false&order=volume`
- Parse clobTokenIds (double-parse quirk — see polymarket.py); parse outcomePrices.
- Filter by `parse_market()` returning non-None AND valid prices.
- Default page size 100, paginate up to max_pages=15.

**[SLOT S2] resolve function (vertical-specific):**
Each vertical implements its own truth source:
```python
def resolve_<slug>(row, source_fn=None) -> int|None:
    """Read the official published outcome for row["meta"]["period"].
    Returns 1 if claim resolved YES, 0 if NO, None if not yet published.
    On error: return None (retry next run). NEVER raise.
    """
```
Examples:
- CPI: BLS series → compute realized MoM%; compare to [lo, hi).
- Weather: Wunderground historical high for the city+date.
- NFP: BLS employment situation release.
- Election: AP/Reuters projected winner.

**[SLOT S3] Cron schedule:**
- Monthly release verticals (CPI, NFP): daily cron; snapshot picks up new markets;
  settle checks for new prints daily after release date.
- Daily event verticals (weather): daily cron; settle fills the previous day's outcome.
- Binary event markets (politics, sports): daily cron; settle after resolution date.

---

## Module 7 — `adapter.py` / `resolve/<slug>_adapter.py`

**Purpose:** translate the vertical's settled rows into the standard `ResolvedMarket`
format consumed by the gate pipeline and baselines.

```python
def load_rows(store_path=DEFAULT_STORE) -> list[dict]:
    """Settled rows with int y → ResolvedMarket dicts.
    Empty/missing store → [].  No network.
    """
    # ResolvedMarket schema:
    return [{
        "market_id": row["market_id"],
        "archetype": row["archetype"],
        "t0": row["t0"],
        "q_yes": row["q_yes"],
        "y": row["y"],          # 0 or 1 (int)
        "realized_pnl": None,   # filled by ledger after real execution
        "realized_side": None,
        "stake": 1.0,
        "meta": row["meta"]     # all frozen forecast fields ride in meta
    } for row in _load_settled(store_path)]
```

**[SLOT A1] Gate pipeline registration:**
```python
# map/baselines.py — add the vertical's baseline:
def <slug>_baseline(rm, edge=0.05):
    p = rm.get("meta", {}).get("p_model")
    if p is None: return rm["q_yes"], None
    q = rm["q_yes"]
    if p - q > edge: return p, "YES"
    if q - p > edge: return p, "NO"
    return p, None

BASELINES["<slug>"] = (<slug>_baseline, {}, True)
BASELINE_MECHANISM["<slug>"] = ("model_vs_crowd", "<description>")

# resolve/__init__.py — add to load_all_rows():
from institute.resolve.<slug>_adapter import load_rows as load_<slug>
rows += load_<slug>()

# factor.CELL_FACTORS — add archetype correlation:
"<archetype>": {"<correlation_group>": 1.0}
# e.g., "econ-cpi": {"macro": 1.0}; "weather-dallas": {"weather": 1.0}
```

---

## The point-in-time two-phase honesty pattern (in detail)

This is the Institute's structural moat. Understand it fully before building anything.

```
TIME AXIS:
─────────────────────────────────────────────────────────────────────────
t0           t_now (cron)    t_resolution      t_settle (cron)
│                │                 │                  │
│  Market listed │  SNAPSHOT       │  Event resolves  │  SETTLE
│  on Polymarket │  runs here      │  officially      │  runs here
└────────────────┴────────────────────────────────────┴──────────────────

SNAPSHOT:
  - Fetches ALL data available at t_now (BLS, FRED, Open-Meteo, news, etc.)
  - Runs models + ensemble → p_model
  - FREEZES p_model + all inputs into the row as-of t_now
  - Writes to jsonl store; row is IMMUTABLE after this point
  - Does NOT know the outcome; q_yes is the only market signal used

SETTLE:
  - Reads the official published outcome (BLS, Wunderground, AP, etc.)
  - Fills y=0 or y=1 in the row
  - NEVER alters p_model, q_yes, or any meta frozen at snapshot
  - NEVER re-runs the models; just resolves what was already frozen

THE LAW: p_model for a market is computed ONCE, from data before t_resolution,
and FROZEN. The settle phase ONLY fills y. There is no information flow from
outcome to forecast in any direction.

WHY THIS MATTERS:
  1. Backtests are honest: replay any run using historical data at t0. No lookahead.
  2. Competitor moat: a competitor cannot reconstruct our frozen priors retroactively
     because they don't know what data was available at t0 (we logged it).
  3. Live/paper parity: the live system and the paper backtest run identical code.
```

**Foreknowledge defense (Engine 3 specific):**
When the agentic search fetches news, each result must be checked:
```
For each search result r:
  published_at = r["published_at"]  # from RSS/API
  if published_at > t0:
      discard(r)  # post-event data — cannot use
  if published_at > t_resolution:
      log_anomaly(r)  # search engine may be serving live results
```
AIA Forecaster found ~1.65% contamination in live runs. The LLM-as-judge check:
`"Was this information publicly available before [t0]? Answer YES or NO."` — discard
any result where the judge says NO or is uncertain.

---

## Customization slots summary (blueprint for new vertical builders)

| Slot | What to customize | Where |
|------|------------------|-------|
| D1 | Primary data source URL + parser | `data.py` |
| D2 | Backup data source | `data.py` |
| D3 | Optional external nowcast | `data.py` |
| M1 | 3+ independent model families | `models.py` |
| M2 | Per-model sigma estimation method | `models.py` |
| E1 | Model-vs-market blend weight w | `ensemble.py` |
| P1 | Claim schema (numeric vs binary) | `parse.py` |
| P2 | Parsing rules + ambiguity policy | `parse.py` |
| S1 | Market discovery filter | `sensor.py` |
| S2 | Official resolve source + logic | `sensor.py` |
| S3 | Cron cadence (daily / monthly / on-demand) | `sensor.py` |
| A1 | Baseline name + Gate registration | `adapter.py` + `baselines.py` |
| C1 | Calibration schedule | `calibrate.py` |
| C2 | Recalibration trigger criteria | `calibrate.py` |

**Invariants that MUST NOT be customized (they are the Institute standard):**
- `fit_weights` walk-forward loop (RMSE, not in-sample)
- `inverse_rmse_weights` formula
- `combine` mixture-variance formula (within + between model spread)
- `norm_cdf` via `math.erf` (pure stdlib)
- `bucket_prob` clipping via `scoring.clip`
- Two-phase sensor structure (snapshot idempotency, settle isolation)
- `ResolvedMarket` schema (downstream gate pipeline expects it)
- Gate pipeline (never modify gate/allocator internals from a vertical)
- Quarter-Kelly sizing (allocator handles this; vertical just produces p_model)

---

## Edge engine fit by market type

Every vertical should explicitly choose which engines to run:

| Market type | Engine 1 (Quant) | Engine 2 (Bias) | Engine 3 (News) | Engine 4 (Copy) |
|------------|-----------------|-----------------|-----------------|-----------------|
| Economic releases (CPI, NFP) | PRIMARY | bias check, anchor check | optional | supplemental |
| Weather / physical quantity | PRIMARY | bias check | not used | not used |
| Political elections | not primary | horizon compression, FLB | PRIMARY | supplemental |
| Sports outcomes | partial (statistical models) | FLB (longshots overpriced) | PRIMARY | supplemental |
| Geopolitics | rare | FLB | PRIMARY (GDELT, wire) | not typical |
| Crypto / price | partial (GARCH, on-chain) | FLB, overreaction | supplemental | HIGH (on-chain flow) |
| Science / replication | not typical | FLB on longshots | PRIMARY (arXiv) | not typical |
| Culture / entertainment | not typical | FLB | PRIMARY | not typical |

The table is a guide, not a rule. A vertical may use only Engine 1 (weather), only
Engine 3 (geopolitics), or all four (politics close to election). The point is to
be DELIBERATE: state which engines are active and why, in the vertical's SPEC.

---

## Standard test harness (offline, deterministic — 0 real network calls)

Every vertical MUST pass `pytest institute/tests -q` fully offline. The pattern:

```python
# Fixture pattern (inject everywhere):
FAKE_SERIES = [{"year": 2024, "month": i, "mom": 0.2 + i*0.01} for i in range(1,25)]

def fake_fetch_json(url, timeout=25):  # replaces _get_json in data.py
    return {"Results": {"series": [{"data": FAKE_SERIES}]}}

def fake_distribution(claim, now=None):  # replaces forecast_distribution in sensor.py
    return {"mu": 0.3, "sigma": 0.05, "p_model": 0.42, "forecast_ts": now}

def test_snapshot_idempotent(tmp_path):
    store = str(tmp_path / "test.jsonl")
    fake_markets = [{"market_id": "m1", "q_yes": 0.35, "question": "Will CPI be 0.3%?",
                     "end_date": "2026-08-01T00:00:00Z"}]
    n1 = sensor.snapshot(store, fetch=lambda: fake_markets,
                          distribution=fake_distribution, now="2026-07-01T00:00:00Z")
    assert len(n1) == 1
    n2 = sensor.snapshot(store, fetch=lambda: fake_markets,
                          distribution=fake_distribution, now="2026-07-02T00:00:00Z")
    assert len(n2) == 0  # idempotent — same market not re-snapshotted

def test_settle_does_not_alter_p_model(tmp_path):
    # ...snapshot, then settle, then assert meta["p_model"] unchanged...
```

**Required test coverage per vertical:**
1. `parse.py`: all question phrasings → correct claim; ambiguous/out-of-scope → None
2. `models.py`: each model returns finite mu + sigma ≥ 0.05; fallback is safe
3. `ensemble.py`: weights sum to 1; bucket_prob over (-inf,inf) ≈ 1; disagreement widens sigma
4. `calibrate.py`: inverse_rmse_weights behavior; shrinkage formula
5. `sensor.py`: snapshot idempotency; settle isolation (p_model unchanged); past-end-date settle
6. `adapter.py`: settled rows → ResolvedMarket; open rows excluded; empty store → []

---

## Checklist: vertical ready for gate pipeline

```
[ ] data.py: all fetchers injectable; degrade gracefully on failure
[ ] models.py: ≥3 models with STRUCTURALLY DIFFERENT approaches (check pairwise error corr)
[ ] ensemble.py: mixture variance formula; blend weight w set per vertical
[ ] calibrate.py: walk-forward OOS; shrinkage; bias stored per-model
[ ] parse.py: conservative; ambiguous → None; scope clearly bounded
[ ] sensor.py: snapshot idempotent; settle isolated; two-phase law enforced
[ ] adapter.py: load_rows registered in resolve/__init__.py
[ ] baselines.py: baseline function registered with mechanism description
[ ] factor.py: archetype added to CELL_FACTORS correlation map
[ ] tests: all green, fully offline, ≥6 test modules
[ ] gitignore: data/<slug>_markets.jsonl in carve-out (persists like other stores)
[ ] SPEC.md: engines chosen + justified; free/premium data mapped; failure modes named
[ ] cron: line added to GCP VM cron for snapshot+settle
[ ] paper run: ≥30 snapshots before live capital; OOS Brier tracked
```

---

## Anti-patterns to avoid (learned from weather bot + CPI vertical)

**AP1: Collapsed model diversity**
CPI's `nowcast` falls back to `random_walk` when Cleveland Fed is absent → 2 effective
models, not 3. Fix: always have a fallback that is genuinely independent (PPI regression).
Test: compute pairwise error correlation matrix. If any pair > 0.7 — the vertical has 1 fewer
effective model than it thinks.

**AP2: Re-forecasting after snapshot**
The snapshot is a write-once contract. Re-running the model with new data and overwriting
p_model in an existing row is a silent honesty violation. The sensor's deduplication logic
(`market_id already in store → skip`) is the defense. Test for it explicitly.

**AP3: parse.py being too permissive**
Accepting "GDP growth above 2.5%" as a CPI market because it mentions a percentage is a
mismatch. The downstream settle will compute MoM% from BLS and compare to a GDP bucket.
The result is either a crash or a silent wrong bet. Always return None if the indicator
is ambiguous.

**AP4: Network in tests**
A test that calls a real API is not a test — it's a dependency on external uptime.
Inject all fetchers. The `_get` parameter pattern in every data.py function is the standard.

**AP5: Sigma collapse from tied models**
If all models agree exactly (e.g., all three use the same trailing window), sigma* → the
within-model variance only. The ensemble looks very confident when it should be uncertain.
The mixture variance formula catches BETWEEN-model spread only if models genuinely disagree.

**AP6: Platt calibration applied before n≥200**
At n=20, the Platt alpha fit from 20 data points is meaningless noise. Apply it too early
and it randomly amplifies errors. The n≥200 gate is a hard rule, not a guideline.

**AP7: Skipping the Gate pipeline**
A vertical that bets directly, bypassing Gates 1–7 and the allocator, violates the
Institute architecture. Every bet must flow through the standard pipeline. The vertical
only produces p_model; it has no opinion on stake size or portfolio construction.
