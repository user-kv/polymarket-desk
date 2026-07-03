# The Institute — Vertical Template (03)

## CHANGELOG
- **Data contracts hardened**: every module interface now specifies exact types, nullability,
  and failure behaviour. Prior version had ambiguous interfaces that required builder
  guesswork (e.g., `primary_series` return schema unspecified; `ResolvedMarket.stake`
  had no stated default contract).
- **Look-ahead made structurally impossible**: `snapshot()` now explicitly passes `now`
  through to all model calls and data fetches; `distribution_fn` receives `now` as a
  REQUIRED parameter — models that ignore it are detectable in tests.
- **Re-forecasting structurally impossible**: `snapshot()` idempotency is now a typed
  contract (market_id already in store → no-op; error if attempted overwrite).
- **Pairwise independence audit** added as a mandatory build gate in Module 4, not an
  optional audit item. Vertical cannot register in gate pipeline until audit passes.
- **Multiple-testing correction** added to the readiness checklist: when a new vertical
  is evaluated, the kill threshold is adjusted for the number of verticals live.
- **Sigma honesty**: sigma floor raised from 0.05 to `max(0.05, vertical_trailing_stdev / 3)`;
  prevents trivially tight distributions on volatile series.
- **Non-Normal distribution guidance**: explicit Shapiro-Wilk test required before
  staying with Normal assumption; do not default to Normal without checking OOS residuals.
- **Engine 3 budget gate**: added explicit EV-vs-token-cost check before enabling Engine 3
  for any vertical.
- **Engine 4 cron warning**: template now blocks Engine 4 as a primary signal on cron-only
  deployments; relegates it to confirmation-only until WebSocket is live.
- **Multiple-testing correction**: added Bonferroni-style threshold adjustment to the
  calibration schedule — the more verticals live, the higher the per-vertical bar.
- **SPEC.md required content**: expanded to include engine justification, kill criteria,
  and data contract specification — so each vertical's design is auditable.
- **Anti-pattern AP8 added**: Normal distribution assumed without residual check.
- **Customization slots table** updated with explicit data types for each slot input/output.
- Bloat cut: removed duplicated explanation of two-phase sensor (it is fully defined here
  once, not twice).

---

**Status:** PLANNING ONLY. Blueprint for stamping out new verticals.
**Date:** 2026-06-30
**Generalizes:** weather bot (M1–M5) + CPI vertical (B1) into a reusable anatomy.

A "vertical" is a deep specialist module covering ONE market archetype end-to-end:
data ingestion → model(s) → ensemble → calibrate → parse market questions → snapshot →
settle → feed Gate pipeline. Every vertical is self-contained, independently testable,
and plugs into gates + allocator without touching their internals.

---

## The canonical module anatomy

```
institute/verticals/<slug>/
    __init__.py
    data.py         # all network calls live here; all other modules are pure
    models.py       # 3+ independent forecasters -> (mu, sigma) or (p_i)
    ensemble.py     # combine models -> predictive distribution or p_model
    calibrate.py    # per-model RMSE weights + bias correction; walk-forward only
    parse.py        # market question text -> structured claim or None
    sensor.py       # two-phase snapshot/settle; the point-in-time honesty contract

institute/resolve/<slug>_adapter.py     # ResolvedMarket loader
institute/data/<slug>_markets.jsonl     # live store (gitignored with carve-out)
institute/tests/test_<slug>_*.py        # offline only; 0 real network calls
```

Each module is described with exact interfaces below. CUSTOMIZATION SLOTS mark where
each vertical injects its own logic. Everything else is Institute standard — do not
re-implement or override.

---

## Module 1 — `data.py` (fetchers)

**Contract:** every function that touches the network lives here. All other modules
are pure. No exceptions.

**Standard interface:**
```python
# Injectable _get for testing — do NOT call urllib directly in other modules.
def _get_json(url: str, timeout: int = 25,
              _get=None) -> dict | list:
    """Default: urllib GET, parse JSON. Returns {} on ANY failure. Never raises."""

def _get_text(url: str, timeout: int = 25,
              _get=None) -> str:
    """Default: urllib GET, decode UTF-8. Returns '' on ANY failure. Never raises."""

# --- SLOT D1: Primary data source ---
def primary_series(_get=_get_json) -> list[dict]:
    """Fetch main historical series. Returns [] on failure.
    Each dict MUST contain at least: {"period": str, "value": float}
    Ordered OLD → NEW. Caller may assume this ordering.
    """

# --- SLOT D2: Backup / cross-check source ---
def secondary_series(_get=_get_text) -> list[dict]:
    """Same schema as primary_series. Used if primary fails or for cross-validation.
    Returns [] on failure. Never raises.
    """

# --- SLOT D3: Optional external nowcast (best-effort) ---
def optional_nowcast(_get=_get_text) -> dict | None:
    """Returns {"value": float, "source": str} or None on any failure.
    Callers MUST handle None — ensemble degrades gracefully without it.
    Never raises.
    """
```

**Rules (all mandatory):**
- Every public function catches ALL exceptions; returns `[]` or `None` on failure.
- User-Agent header: `institute/1.0`
- Free tier first: no API key required at the free tier. Premium is an injectable
  `_get` override.
- Pure transform functions (`mom_pct()`, `parse_csv()`) live here too but do NOT
  touch the network. They are testable inline without injection.

**[SLOT D1] Primary data sources by vertical:**
- Weather: Open-Meteo ensemble API (temperature members, free, no key)
- CPI: BLS public API v1 (CPI-U series, free, no key, 25 calls/day)
- Employment: BLS establishment survey / FRED `PAYEMS` (free CSV)
- Politics: 538 poll aggregator, Wikipedia infobox, RCP poll averages (free)
- Sports: ESPN unofficial API, sportsreference.com scrape, SportsDB API (free)
- Crypto: CoinGecko free tier (10–50 calls/min), CMC free tier

**[SLOT D2] Backup source:** same data, different endpoint.
- CPI: FRED `CPIAUCSL` CSV (same series, different provider)
- Weather: NWS gridpoints API (reality-check on Open-Meteo)

**[SLOT D3] Optional nowcast:**
- CPI: Cleveland Fed nowcast (free, no key)
- Employment: Atlanta Fed Wage Tracker
- Weather: not needed — Open-Meteo already IS the NWP ensemble

---

## Module 2 — `models.py` (forecasters)

**Contract:** pure functions only. Zero network calls. Each model returns its own
uncertainty estimate. Each model must be independently testable.

**Standard interface — quant verticals (Engine 1):**
```python
def model_name(history: list[dict], now: str, **context) -> dict:
    """Pure function. No network calls. `now` is the snapshot timestamp (ISO8601Z).
    Model MUST NOT use any data from history where period > now.
    Returns {"name": str, "mu": float, "sigma": float}.
    sigma >= max(0.05, trailing_stdev / 3)  # see sigma floor rule below
    On insufficient history: return {"name": ..., "mu": 0.0, "sigma": 0.5}
    Never raises.
    """
```

**Standard interface — qualitative verticals (Engine 3):**
```python
def swarm_agent(question: str, evidence: str, persona: str,
                llm_call=None) -> dict:
    """LLM call; llm_call is injectable for tests (replaces with mock).
    Returns {"p": float, "rationale": str}.
    p in (0, 1). rationale <= 100 tokens.
    q_yes MUST NOT appear in evidence or persona strings.
    Never raises; on LLM failure returns {"p": 0.5, "rationale": "fallback"}.
    """
```

**Sigma floor rule (honesty gate):**
```python
def sigma_floor(trailing_values: list[float]) -> float:
    """Minimum sigma for this vertical, based on observed volatility.
    floor = max(0.05, stdev(trailing_values[-24:]) / 3)
    This prevents an overconfident narrow sigma when models happen to agree.
    """
```
A sigma of 0.001 on a CPI vertical claiming certainty to 0.001pp is dishonest.
Every model's sigma must reflect the historical volatility of the series.

**[SLOT M1] Model family selection — the independence requirement:**
Models must use STRUCTURALLY DIFFERENT approaches. Different parameters on the same
model architecture is NOT independence (it will fail the pairwise audit).

```
Target diversity matrix (quant):
  Model A: Mechanistic/structural  (seasonal pattern, domain physics, ARIMA)
  Model B: Statistical/trailing    (random walk, trailing mean — honest naive anchor)
  Model C: External/independent    (third-party nowcast or leading-indicator regression
                                    using a DIFFERENT INPUT VARIABLE)

Examples:
  CPI:         seasonal_ar     |  random_walk       |  Cleveland Fed / PPI-OLS
  Temperature: GFS ensemble    |  ECMWF ensemble    |  ICON / UKMO / GEM
  Employment:  seasonal_ar     |  trailing_mean     |  ADP nowcast
  Polling:     RCP average     |  State-level shift |  Ensemble aggregator
  Crypto:      ARIMA(p,q)      |  GARCH vol         |  On-chain metrics regression

Target diversity matrix (qualitative, Engine 3):
  10 personas from: base-rate statistician, macroeconomist, contrarian,
  domain expert (archetype-specific), political scientist, geopolitical analyst,
  tech analyst, public health expert, legal analyst, market historian.
  Each persona WITHHOLDS q_yes during forecast (blind to market price).
```

**[SLOT M2] Uncertainty estimation:**
Each model produces its OWN sigma. Sources:
- Historical residuals via walk-forward OOS.
- External nowcast with no published RMSE: use vertical's trailing error stdev as floor.
- LLM agents: sigma proxy = inter-agent std of 10 swarm forecasts.
- Sigma floor: `max(0.05, trailing_stdev / 3)` — never return sigma below this.

**Model count:**
- 3 is the minimum. Below 3, diversity collapse is too likely.
- Target: 3–5 well-diversified models. Beyond 5 quant models, returns diminish.
- For LLM swarms: 10 agents (budget starting point). AIA finding: diminishing returns
  past 10; PolySwarm uses 50 for higher coverage at higher cost.

---

## Module 3 — `ensemble.py` (combination)

**Contract:** pure functions only. Deterministic given same inputs. No network calls.

**Standard quant interface:**
```python
def combine(models: list[dict], weights: dict[str, float],
            bias: float = 0.0) -> dict:
    """Weighted Gaussian mixture.
    models: [{"name": str, "mu": float, "sigma": float}, ...]
    weights: {model_name: float} — need not sum to 1; normalised internally.
    Returns {"mu": float, "sigma": float}.
    sigma = max(sqrt(mixture_variance), sigma_floor)
    If models is empty: return {"mu": 0.0, "sigma": 0.5}
    Never raises.

    FORMULA:
      mu_raw  = sum(w_i * mu_i)          [weighted mean before bias]
      mu*     = mu_raw - bias
      sigma*  = sqrt( sum(w_i * (sigma_i^2 + (mu_i - mu_raw)^2)) )
                ^within-model variance   ^across-model disagreement
    """

def bucket_prob(mu: float, sigma: float,
                lo: float | None, hi: float | None) -> float:
    """P(lo <= X < hi) for X ~ Normal(mu, sigma).
    lo=None means -inf; hi=None means +inf.
    Result clipped via scoring.clip to (EPS, 1-EPS).
    """

def forecast_distribution(history: list[dict], now: str,
                           build_models=None, **context) -> dict:
    """Glue: call models with `now`, calibrate, combine.
    `now` is passed through to every model call — models cannot use data after now.
    Returns {"mu": float, "sigma": float, "weights": dict, "n_train": int}
    """
```

**Distribution honesty check (mandatory before deploying any new vertical):**
```python
# In calibrate.py, after fitting OOS residuals:
from scipy.stats import shapiro  # or pure stdlib alternative

def check_normality(residuals: list[float]) -> bool:
    """Returns True if Normal assumption is reasonable (p-value > 0.05).
    If False: flag the vertical for non-Normal ensemble (Beta, Poisson, etc.).
    Run this on walk-forward OOS residuals before assuming Normal is correct.
    """
    if len(residuals) < 8: return True  # too few to test; assume OK
    stat, p = shapiro(residuals[:50])   # Shapiro-Wilk; cap at 50 for power
    return p > 0.05
```

**For non-Normal distributions (use only if normality check fails):**
- Bounded 0–1 (win probability): Beta distribution. `combine_beta(alpha_i, beta_i, w)`
- Count/discrete (goals scored): Poisson or NegBin. `combine_poisson(lambda_i, w)`
- Categorical (which of N candidates): Dirichlet. Marginals per candidate.
Normal is correct for most economic-quantity markets (CPI MoM%, temperature). Specialize
ONLY when OOS residuals fail the normality check.

**LLM swarm aggregation:**
```python
def aggregate_swarm(p_list: list[float]) -> dict:
    """Simple mean (budget). Returns {"p_swarm": float, "p_std": float}.
    DO NOT use debate/LLM-judge aggregation — sycophancy cascade.
    DO NOT use geometric mean of log-odds unless calibrated from OOS data.
    Upgrade path: confidence-weighted Bayesian combination (PolySwarm pattern).
    """
    n = len(p_list)
    if n == 0: return {"p_swarm": 0.5, "p_std": 0.5}
    p_swarm = sum(p_list) / n
    p_std = (sum((p - p_swarm)**2 for p in p_list) / n) ** 0.5
    return {"p_swarm": p_swarm, "p_std": p_std}
```

**[SLOT E1] Model-vs-market blend weight `w`:**
```python
# p_final = w * p_model + (1-w) * q_market
# Default: w = 0.70 (illiquid long-tail markets — model adds real signal)
# Recalibrate per archetype from OOS data:
#   Liquid, well-traded: w → 0.30 (market knows more)
#   Illiquid long-tail:  w → 0.70–0.90
#   Early paper period:  use 0.70 as fixed prior; update quarterly
```

---

## Module 4 — `calibrate.py` (weight fitting + bias)

**Contract:** pure, deterministic, walk-forward OOS only. NO in-sample fitting.
No network calls. Must be testable with injected history.

**Standard interface:**
```python
def fit_weights(history: list[dict], build_models,
                min_train: int = 24, now: str = None) -> dict:
    """Walk-forward OOS ONLY.
    For each period t after min_train:
      fit each model on data strictly before t (data[t].period < now), record error.
    Returns {model_name: rmse, "bias": mean_signed_error_of_ensemble}.
    If len(history) < min_train: return {name: 1.0 for each model, "bias": 0.0}.
    Never raises. Never uses future data (now is the guard).
    """

def inverse_rmse_weights(rmse_map: dict) -> dict:
    """w_i = (1/RMSE_i) / sum(1/RMSE_j).
    RMSE floor: max(RMSE_i, 1e-6) — prevents division by zero.
    Returns {model_name: float} summing to 1.0.
    Excludes "bias" key from weight computation.
    """

def shrinkage_correction(raw_bias: float, n: int, K: int = 10) -> float:
    """Bayesian shrinkage: correction = (n / (n + K)) * raw_bias.
    K=10: at n=4 → 29% applied; at n=50 → 83%.
    Prevents overreaction to small samples.
    """
    return (n / (n + K)) * raw_bias

def platt_extremize(p: float, alpha: float = 1.732) -> float:
    """Push probability toward extremes; undoes RLHF hedge-toward-0.5.
    alpha = sqrt(3) ≈ 1.732 (Neyman & Roughgarden 2022).
    THREE GATES REQUIRED before calling:
      1. n >= 200 resolved markets for this archetype
      2. p is on the CORRECT side of 0.5 (caller must verify)
      3. swarm p_std < 0.20 (high consensus)
    If any gate fails, return p unchanged.
    """
    import math
    lo = math.log(p / (1 - p))
    return 1 / (1 + math.exp(-alpha * lo))
```

**[SLOT C1] Calibration schedule:**
- RMSE weights: refit monthly or after every 10 new resolved markets.
- Bias correction: refit weekly (captures regime drift faster).
- Platt alpha: fit from data at n≥200; update quarterly thereafter.
- **Pairwise independence audit**: run after EVERY calibration cycle.
  If any model pair > 0.70 Pearson correlation on OOS errors → flag for diversity
  review. Vertical is NOT deployment-ready until this passes.

**[SLOT C2] Multiple-testing correction:**
When evaluating whether a vertical is generating real edge:
```
Bonferroni-adjusted significance level = 0.05 / (number of live verticals)
At 5 live verticals:  require p < 0.01 per vertical kill-or-keep decision
At 10 live verticals: require p < 0.005

Practical rule: the MORE verticals in production, the MORE resolved markets
required before trusting a kill-or-keep decision. Document the live vertical
count at the time any kill criterion was evaluated.
```

**[SLOT C3] Recalibration trigger:**
If a model's rolling 30-day Brier score degrades by >20% vs its trailing
12-month baseline, downweight it automatically in the next cycle. Do not
retire a model on a single bad month — require 3 consecutive degraded months.

---

## Module 5 — `parse.py` (question → claim)

**Contract:** pure function. No network. Conservative: abstain rather than misparse.
A wrong parse → silent wrong bet. A None return → missed opportunity. The cost
of a wrong bet vastly exceeds the cost of a missed opportunity.

**Standard interface:**
```python
def parse_market(question: str, slug: str) -> dict | None:
    """Map raw market question text to a structured typed claim.
    Returns None if: question is out of scope for this vertical,
                     OR ambiguous scope / resolution criterion,
                     OR indicator cannot be cleanly extracted.
    Conservative bias: when in doubt, return None.
    Never raises.
    """
```

**[SLOT P1] Claim schemas:**

Numeric-range markets (CPI, temperature, jobs, GDP):
```python
{
    "indicator":  str,    # "us_cpi_mom" | "dallas_high_f" | "nfp_thousands"
    "period":     str,    # "2026-07" or "2026-07-04" (ISO date string)
    "lo":         float,  # lower bound; use float("-inf") for open lower end
    "hi":         float,  # upper bound; use float("inf") for open upper end
    "unit":       str,    # "pct" | "fahrenheit" | "thousands"
    "ambiguity":  str,    # "low" | "medium" | "high" — high → return None
}
```

Binary event markets (politics, sports, geopolitics):
```python
{
    "event_type":       str,  # "election_winner" | "match_outcome" | "geo_event"
    "entity":           str,  # "Donald Trump" | "Manchester City" | "NATO_Art5"
    "outcome":          str,  # "YES" or "NO" + brief description
    "resolution_date":  str,  # ISO8601
    "ambiguity_level":  str,  # "low" | "medium" | "high" → high returns None
}
```

**[SLOT P2] Parsing rules:**
- "≥0.3%" → bucket [0.25, 0.35) — 1 decimal place means ±0.05 around stated value.
- "more than X" → lo=X, hi=float("inf"). "less than X" → lo=float("-inf"), hi=X.
- "between A and B" → lo=A, hi=B.
- Return None for: UK CPI, China CPI, PCE deflator (not the same vertical as US CPI).
- Return None for: "significant conflict", "major announcement" (ambiguous resolution).
- Return None for: any question where the resolution criterion is not objectively
  verifiable from a named public source.

---

## Module 6 — `sensor.py` (the two-phase honest contract)

**This is the Institute's structural moat. Break this contract and every backtest
becomes a phantom. Read it fully before building anything.**

```
TIME AXIS:
────────────────────────────────────────────────────────────────
t0            t_now (cron)   t_resolution    t_settle (cron)
│                 │                │                │
│ Market listed   │ SNAPSHOT       │ Event resolves │ SETTLE
│ on Polymarket   │ (write-once)   │ officially     │ (fill y only)
└─────────────────┴───────────────────────────────┴─────────────

SNAPSHOT (write-once):
  - Data: only data with period < now is used. Models receive `now` explicitly.
  - Runs models + ensemble → p_model
  - Freezes p_model + all inputs into row at t_now
  - Writes to jsonl store; row is IMMUTABLE after write
  - Idempotency: market_id already in store → skip. Never re-forecast. EVER.
  - Does NOT know the outcome. q_yes is the only market signal used.

SETTLE (fill y only):
  - Reads the official published outcome after resolution
  - Fills y=0 or y=1 in the row
  - NEVER alters p_model, q_yes, or any meta frozen at snapshot
  - NEVER re-runs models
  - NEVER passes outcome data back to any model or calibration function

THE LAW: p_model is computed ONCE, from data before t_resolution, and FROZEN.
Settle fills y. There is zero information flow from outcome to forecast.
```

**SNAPSHOT schema:**
```python
OPEN_ROW_SCHEMA = {
    "market_id":   str,           # unique per market
    "archetype":   str,           # "econ-cpi" | "weather-dallas" | "politics-us"
    "t0":          str,           # ISO8601Z — snapshot timestamp, FROZEN
    "q_yes":       float,         # market price at t0, FROZEN
    "question":    str,
    "end_date":    str,           # ISO8601Z
    "status":      "open",        # → "settled" after resolve
    "y":           None,          # → 0 or 1 (int) after settle; never float
    "settled_ts":  None,          # → ISO8601Z after settle
    "meta": {
        "p_model":        float,  # final calibrated probability, FROZEN
        "forecast_ts":    str,    # ISO8601Z when p_model was computed
        # Engine 1 fields:
        "mu":       float,
        "sigma":    float,
        "weights":  dict,         # {model_name: float}
        "n_train":  int,
        # Engine 3 fields:
        "p_swarm":      float,
        "p_std":        float,
        "p_supervisor": float,
        # Parsed claim (vertical-specific):
        "indicator": str,
        "period":    str,
        "lo":        float,
        "hi":        float,
        "slug":      str,
    }
}
```

**SNAPSHOT function contract:**
```python
def snapshot(store_path: str,
             fetch_fn: Callable[[], list[dict]],
             distribution_fn: Callable[[dict, str], dict],
             now: str = None) -> list[dict]:
    """For each new active market not already in store:
      1. parse_market(q["question"], slug) → claim; skip if None
      2. distribution_fn(claim, now) → {mu, sigma, p_model, ...}
         `now` is passed explicitly; distribution_fn MUST NOT use data after now.
      3. Freeze p_model + claim into meta; set t0=now, status="open", y=None
      4. Append to store (jsonl); return new rows written this run

    IDEMPOTENCY CONTRACT:
      - If market_id already in store: skip unconditionally. No update. No re-forecast.
      - Raise ValueError if caller attempts to force-overwrite an existing market_id.
    """

def settle(store_path: str,
           resolve_fn: Callable[[dict], int | None],
           now: str = None) -> list[dict]:
    """For each open row past end_date:
      1. resolve_fn(row) → y in {0, 1} or None (not yet published)
      2. If y is int: set status="settled", y=y, settled_ts=now; overwrite row
      3. Return rows settled in this run

    CONTRACT:
      - resolve_fn MUST NOT alter p_model, q_yes, or any meta field.
      - resolve_fn returns None on error; settle retries on next cron run.
      - NEVER re-runs models; NEVER passes outcome to calibration.
    """
```

**[SLOT S1] fetch_active markets:**
```python
# Gamma API: GET gamma-api.polymarket.com/markets?active=true&closed=false&order=volume
# Parse clobTokenIds (double-parse quirk — see polymarket.py::parse_clob_token_ids)
# Parse outcomePrices (JSON string in JSON)
# Filter: parse_market() returning non-None AND 0 < q_yes < 1
# Pagination: default page_size=100, max_pages=15
# Return: [{"market_id": str, "q_yes": float, "question": str, "end_date": str}, ...]
```

**[SLOT S2] resolve function — one per vertical:**
```python
def resolve_<slug>(row: dict, source_fn=None) -> int | None:
    """Read the official published outcome for row["meta"]["period"].
    Returns: 1 if claim resolved YES, 0 if NO, None if not yet published.
    On error: return None (retry on next run). NEVER raise.
    source_fn is injectable for tests (replaces real HTTP call).
    MUST use data published AFTER row["end_date"] — never proxy a pre-event source.
    """

# Examples by vertical:
# CPI:     BLS series → compute realized MoM%; compare to [lo, hi)
# Weather: Wunderground historical high for city+date
# NFP:     BLS employment situation release
# Election: AP/Reuters projected winner
```

**[SLOT S3] Cron schedule:**
- Monthly releases (CPI, NFP): daily cron; snapshot picks up new markets; settle
  checks for new prints daily after release date.
- Daily events (weather): daily cron; settle fills previous day's outcome.
- Binary events (politics, sports): daily cron; settle after resolution date.

**Engine 3 foreknowledge defense (additional gate for agentic search):**
```python
# For each search result r from agentic worker:
if r["published_at"] > now:      # t0 is our snapshot `now`
    discard(r)                   # post-event data; cannot use
# AIA contamination rate: ~1.65% of results are post-event.
# LLM-as-judge check: "Was this publicly available before [now]? YES/NO."
# Discard if judge answers NO or is uncertain.
# Cost of skipping: phantom backtest +20–30% vs live performance.
```

---

## Module 7 — `adapter.py` / `resolve/<slug>_adapter.py`

**Contract:** pure function. No network. Translates settled rows to `ResolvedMarket`
format for the gate pipeline. Skips open rows silently.

```python
# ResolvedMarket schema (gate pipeline contract — do NOT modify):
RESOLVED_MARKET = {
    "market_id":     str,
    "archetype":     str,
    "t0":            str,      # ISO8601Z
    "q_yes":         float,
    "y":             int,      # 0 or 1; never None here
    "realized_pnl":  None,     # float — filled by ledger post-execution
    "realized_side": None,     # "YES" | "NO" — filled by ledger
    "stake":         1.0,      # float — default 1.0 until ledger fills it
    "meta":          dict,     # all frozen forecast fields from sensor row
}

def load_rows(store_path: str = DEFAULT_STORE) -> list[dict]:
    """Return settled rows as ResolvedMarket dicts.
    Open rows (y is None): silently excluded.
    Missing/empty store: return [].
    Never raises.
    """
```

**[SLOT A1] Gate pipeline registration (four steps, all required):**
```python
# 1. map/baselines.py — add the vertical's baseline function:
def <slug>_baseline(rm: dict, edge: float = 0.05) -> tuple[float, str | None]:
    p = rm.get("meta", {}).get("p_model")
    if p is None: return rm["q_yes"], None   # no forecast → abstain
    q = rm["q_yes"]
    if p - q > edge: return p, "YES"
    if q - p > edge: return p, "NO"
    return p, None

BASELINES["<slug>"] = (<slug>_baseline, {}, True)
BASELINE_MECHANISM["<slug>"] = ("model_vs_crowd", "<one-line description>")

# 2. resolve/__init__.py — add to load_all_rows():
from institute.resolve.<slug>_adapter import load_rows as load_<slug>
rows += load_<slug>()

# 3. factor.CELL_FACTORS — add archetype correlation group:
"<archetype>": {"<correlation_group>": 1.0}
# Examples: "econ-cpi": {"macro": 1.0}; "weather-dallas": {"weather": 1.0}
# Correlation group is used for portfolio stress-test (correlated drawdown check).

# 4. Register kill criterion in kill_registry (see § below).
```

---

## Kill criterion registry (mandatory per vertical)

Each vertical registers a pre-set kill criterion BEFORE it receives live capital.
Kill criteria are evaluated against OOS data only. They CANNOT be modified once set.

```python
KILL_REGISTRY = {
    "<slug>": {
        "metric":          "brier_ratio",        # "brier_ratio" | "win_rate" | "mean_S"
        "threshold":       1.0,                  # kill if metric >= threshold (brier_ratio)
        "sample_size":     50,                   # resolved markets required before kill eval
        "comparison_base": "longshot_fade",      # baseline to compare against
        "set_at":          "2026-06-30",         # date criterion was registered
        "live_verticals_at_set": 2,              # for Bonferroni correction audit
    }
}
# Kill criterion evaluation:
# brier_ratio = vertical_brier / longshot_fade_brier on SAME resolved market set.
# If brier_ratio >= 1.0 AND n >= sample_size: halt deployment of this vertical.
# Do NOT expand sample_size to rescue a failing vertical. The criterion is frozen.
```

---

## Edge engine fit by market type

Every vertical MUST explicitly declare which engines are active and why in SPEC.md.

| Market type | Engine 1 (Quant) | Engine 2 (Bias) | Engine 3 (News) | Engine 4 (Copy) |
|------------|-----------------|-----------------|-----------------|-----------------|
| Economic releases (CPI, NFP) | PRIMARY | anchor check | optional if liquid | confirmation only |
| Weather / physical quantity | PRIMARY | bias check | not used | not used |
| Political elections | not primary | horizon compression, FLB | PRIMARY | confirmation only |
| Sports outcomes | partial (stats) | FLB on longshots | PRIMARY | confirmation only |
| Geopolitics | rare | FLB | PRIMARY (GDELT, wire) | not typical |
| Crypto / price | partial (GARCH) | FLB, overreaction | supplemental | HIGH (on-chain flow) |
| Science / replication | not typical | FLB on longshots | PRIMARY (arXiv) | not typical |
| Culture / entertainment | not typical | FLB | PRIMARY | not typical |

**Engine 3 budget gate:** before enabling Engine 3 for any vertical, estimate:
`expected_EV_per_bet × projected_bets_per_run > token_cost_per_run`
If not clearly positive at paper-trade EV estimates: use Engine 2 only until Engine
3 proves its edge on the first 50 resolved markets.

**Engine 4 cron restriction:** Engine 4 is a CONFIRMATION signal only on cron-cycle
deployments. It CANNOT be the primary signal source without WebSocket implementation.
See 02_EDGE_ENGINES.md §Engine 4 for the entry-slippage argument.

---

## Standard test harness (offline, deterministic — zero real network calls)

Every vertical MUST pass `pytest institute/tests -q` fully offline. All fetchers and
LLM calls are injectable. A test that calls a real API is not a test.

```python
# Standard fixture pattern:
FAKE_SERIES = [{"period": f"2024-{i:02d}", "value": 0.2 + i * 0.01}
               for i in range(1, 25)]

def fake_fetch_json(url, timeout=25): ...    # returns FAKE_SERIES wrapped in BLS schema
def fake_distribution(claim, now=None):      # replaces forecast_distribution
    return {"mu": 0.3, "sigma": 0.05, "p_model": 0.42,
            "forecast_ts": now, "weights": {}, "n_train": 20}

def test_snapshot_idempotent(tmp_path):
    store = str(tmp_path / "test.jsonl")
    fake_markets = [{"market_id": "m1", "q_yes": 0.35,
                     "question": "Will CPI be 0.3%?",
                     "end_date": "2026-08-01T00:00:00Z"}]
    n1 = sensor.snapshot(store, fetch=lambda: fake_markets,
                         distribution=fake_distribution, now="2026-07-01T00:00:00Z")
    assert len(n1) == 1
    n2 = sensor.snapshot(store, fetch=lambda: fake_markets,
                         distribution=fake_distribution, now="2026-07-02T00:00:00Z")
    assert len(n2) == 0  # idempotent

def test_settle_does_not_alter_p_model(tmp_path):
    # snapshot → settle → assert meta["p_model"] unchanged
    ...

def test_now_is_respected_by_models(tmp_path):
    # pass now="2024-06-01", inject history that includes 2024-07 data;
    # assert model output equals result with history[:cutoff] only.
    # This is the look-ahead impossibility test.
    ...
```

**Required test coverage per vertical:**
1. `parse.py`: all phrasings → correct claim; ambiguous/out-of-scope → None
2. `models.py`: each model returns finite mu + sigma ≥ sigma_floor; fallback is safe;
   model with `now` set to early date does not use future data
3. `ensemble.py`: weights sum to 1; bucket_prob over (-inf, inf) ≈ 1; disagreement widens sigma
4. `calibrate.py`: walk-forward; shrinkage formula; pairwise audit returns False on correlated pair
5. `sensor.py`: snapshot idempotency; settle isolation (p_model unchanged); past-end-date settle;
   ValueError on forced overwrite attempt
6. `adapter.py`: settled rows → ResolvedMarket; open rows excluded; empty store → []

---

## Customization slots reference

| Slot | What to customize | Module | Input type | Output type |
|------|------------------|--------|------------|-------------|
| D1 | Primary data source URL + parser | `data.py` | url: str | list[dict] with "period", "value" |
| D2 | Backup data source | `data.py` | url: str | same schema as D1 |
| D3 | Optional external nowcast | `data.py` | url: str | {"value": float, "source": str} or None |
| M1 | 3+ independent model families | `models.py` | history: list[dict], now: str | {"name", "mu", "sigma"} |
| M2 | Per-model sigma estimation | `models.py` | OOS residuals: list[float] | sigma: float >= sigma_floor |
| E1 | Model-vs-market blend weight w | `ensemble.py` | archetype: str | w: float in [0.3, 0.9] |
| P1 | Claim schema (numeric vs binary) | `parse.py` | question: str | dict or None |
| P2 | Parsing rules + ambiguity policy | `parse.py` | question: str | None if ambiguous |
| S1 | Market discovery filter | `sensor.py` | market batch: list[dict] | filtered list[dict] |
| S2 | Official resolve source + logic | `sensor.py` | row: dict | 0, 1, or None |
| S3 | Cron cadence | deployment config | — | cron expression |
| A1 | Baseline + Gate registration | `adapter.py` + `baselines.py` | — | registered in 4 places |
| C1 | Calibration schedule | `calibrate.py` | — | RMSE, bias, audit cadence |
| C2 | Multiple-testing correction | `calibrate.py` | n_live_verticals: int | adjusted threshold |
| C3 | Recalibration trigger | `calibrate.py` | rolling Brier delta | downweight trigger |

**Invariants — MUST NOT be customized:**
- `fit_weights` walk-forward loop (RMSE, not in-sample)
- `inverse_rmse_weights` formula
- `combine` mixture-variance formula (within + between model spread)
- `norm_cdf` via `math.erf` (pure stdlib)
- `bucket_prob` clipping via `scoring.clip`
- Two-phase sensor structure (snapshot idempotency, settle isolation)
- `ResolvedMarket` schema
- Gate pipeline internals (vertical produces p_model; allocator handles sizing)
- Quarter-Kelly sizing (allocator only)

---

## Readiness checklist: vertical may enter gate pipeline

```
[ ] data.py: all fetchers injectable; degrade gracefully on failure; _get injectable
[ ] models.py: ≥3 structurally different families; each accepts `now`; sigma >= sigma_floor
[ ] ensemble.py: mixture variance formula; blend weight w documented; normality check run
[ ] calibrate.py: walk-forward OOS only; shrinkage; pairwise independence audit PASSES
[ ] parse.py: conservative; ambiguous → None; scope clearly bounded in tests
[ ] sensor.py: snapshot idempotent; settle isolated; `now` passed to distribution_fn
[ ] sensor.py: ValueError on overwrite attempt confirmed by test
[ ] adapter.py: load_rows registered in resolve/__init__.py
[ ] baselines.py: baseline function + mechanism description registered
[ ] factor.py: archetype added to CELL_FACTORS correlation map
[ ] kill_registry: kill criterion registered with sample size + comparison baseline
[ ] SPEC.md: engines chosen + justified; net edge stated; kill criterion documented;
             free/premium data mapped; data contracts specified
[ ] tests: all green, fully offline, ≥6 test modules, look-ahead test included
[ ] gitignore: data/<slug>_markets.jsonl in carve-out
[ ] paper run: ≥30 snapshots before any capital allocation; OOS Brier tracked
[ ] cron: line added to GCP VM cron for snapshot+settle
[ ] Engine 3 (if used): EV > token cost check documented in SPEC.md
[ ] Engine 4 (if used): WebSocket deployed OR confirmed as confirmation-only
[ ] multiple-testing: Bonferroni-adjusted significance level computed and documented
```

---

## Anti-patterns (do not repeat)

**AP1: Collapsed model diversity**
CPI `nowcast` falls back to `random_walk` → 2 effective models. Fix: always have a
fallback that is genuinely independent (PPI regression). Enforce via pairwise audit.

**AP2: Re-forecasting after snapshot**
The snapshot is write-once. Overwriting p_model in an existing row violates the law.
The `ValueError on overwrite` test makes this structurally impossible.

**AP3: parse.py too permissive**
Accepting "GDP growth above 2.5%" as a CPI market. Downstream settle will compare a
GDP bucket against BLS MoM data → wrong bet or crash. Return None if indicator ambiguous.

**AP4: Network in tests**
A test calling a real API is a dependency on external uptime. Inject all fetchers.
The `_get` parameter pattern is the standard. No exceptions.

**AP5: Sigma collapse from tied models**
All models use the same trailing window → sigma* collapses to within-model variance.
The pairwise audit detects this; the `disagreement widens sigma` test verifies it.

**AP6: Platt calibration before n≥200**
At n=20, Platt alpha from 20 points is noise. Apply it too early → random error
amplification. Three-gate check is mandatory.

**AP7: Skipping the gate pipeline**
A vertical betting directly, bypassing Gates 1–7 and the allocator, violates the
architecture. Vertical produces p_model only. Sizing is the allocator's job.

**AP8: Normal distribution assumed without residual check**
Assuming Gaussian residuals without running Shapiro-Wilk on OOS errors. For bounded
quantities (win rates, poll percentages), the Normal assumption often fails. Run the
check before finalizing ensemble.py.
```
