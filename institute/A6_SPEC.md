# A6 — Alpha Engine + Cadence loop (the sensor -> fund step) — SPEC

**Owner:** Opus authored + verifies. Sonnet 4.6 implements per spec.
**Goal:** give the institute a *mind*. Today it records the market's prior (`q_yes`).
A6 makes it form its OWN prior `p_model`, blend it with the market, and let the
divergence flow through the EXISTING 7 gates as a first-class cell. One new subsystem
(the Alpha Engine) + one orchestration command (the Cadence). Everything else is reuse.

Design rationale + sources: `institute/AGENT_ORG_DESIGN.md`. Read it first.

## The one non-negotiable design law: point-in-time honesty
A forecast is only worth anything if it was made with NO knowledge of the outcome.
So `p_model` is formed **at snapshot time, on an OPEN market, from `q_yes` + persona
priors only**, and stored beside `q_yes`. It is NEVER recomputed at settle, NEVER sees
`y`. This mirrors the two-phase sensor exactly and is our backtest integrity. A baseline
that reads a stored forecast can therefore be scored over resolved rows without leakage,
because the number was frozen before the outcome existed.

Consequence (correct + intended): the `research` cell starts EMPTY and accumulates only
as the cron forecasts live markets going forward. Historical weather/crypto rows that
were snapshotted before A6 have no `p_model` -> the research baseline takes no bet on
them. There is no honest way to backfill. Same discipline as Gate-4's lockbox.

## Hard rules (inherited)
- Pure stdlib only. No numpy/scipy/pandas. ASCII-only prints (Windows cp1252).
- Fake money only. `git add` specific paths (committer handles).
- ALL network/LLM behind injectable params with a deterministic mock default, so the
  whole engine tests fully offline. No real network in any test.
- Reuse `agents/llm.py` seam, `scoring.py`, `prob_calibration` math, the gate pipeline,
  the allocator. Do NOT modify gate/allocator internals — plug in as a baseline.
- Don't deploy probability calibration until n >= ~200 (institute standing rule).

## Modules
```
institute/alpha/__init__.py
institute/alpha/personas.py      # the independent forecaster personas (data)
institute/alpha/engine.py        # swarm_forecast, reconcile, blend, forecast_market
institute/alpha/calibrate.py     # extremize() + maybe_calibrate() (gated off < n=200)
institute/alpha/forecast_store.py# forecast OPEN rows in a JSONL store, attach to meta
institute/cadence.py             # the org loop: one perceive->...->improve pass
institute/tests/test_alpha_engine.py
institute/tests/test_alpha_calibrate.py
institute/tests/test_forecast_store.py
institute/tests/test_research_baseline.py
institute/tests/test_cadence.py
```
Plus: register a `research` baseline in `map/baselines.py`; add ROUTING roles in
`agents/llm.py`; add CLI commands `forecast` and `cycle` to `institute/cli.py`; wire the
forecast pass + cycle into the GCP cron (`setup_gcp.sh`).

---

## 1. `alpha/personas.py`
A small, FIXED list of independent analytical lenses (research: independence + diversity
beats a bigger homogeneous pool; no inter-agent communication). Start with 5 — simplicity
first; the 25-of-50 swarm is a LATER milestone.
```python
PERSONAS = [
    {"id": "base_rate",  "lean":  0.00, "prompt": "Forecast purely from the historical base rate for this class of event. Ignore narrative."},
    {"id": "contrarian", "lean": -0.08, "prompt": "Assume the crowd is over-reacting to recent news. Fade the consensus."},
    {"id": "mechanism",  "lean":  0.00, "prompt": "Reason from the concrete causal mechanism that resolves this market."},
    {"id": "recency",    "lean": +0.05, "prompt": "Weight the most recent signal heavily; momentum tends to persist short-horizon."},
    {"id": "skeptic",    "lean": -0.05, "prompt": "Demand strong evidence for any YES; default toward the cheaper, safer side."},
]
```
`lean` is ONLY used by the deterministic mock to spread the ensemble realistically; the
real (mock=False) path ignores it and uses the prompt. Keep |lean| small.

## 2. `agents/llm.py` — add roles (do not change existing return contract)
Add to `ROUTING`: `"forecast": "claude-sonnet-4-6"`, `"supervise": "claude-opus-4-8"`.
Leave `complete()` exactly as is (existing tests assert the `[MOCK:role] ok` stub).
The Alpha Engine does its own parsing/mock — see below.

## 3. `alpha/engine.py`

### `swarm_forecast(market, personas=PERSONAS, _complete=llm.complete, mock=True) -> list[dict]`
Run each persona INDEPENDENTLY (no shared state, no cross-talk). Returns one
`{"persona": id, "p": float}` per persona.
- **mock=True (default, all tests):** deterministic, NO network. For persona i and a
  market with `q = clip(market["q_yes"])`, compute a reproducible pseudo-forecast:
  ```
  h = (int(hashlib.sha256((persona_id + ":" + market_id).encode()).hexdigest(), 16) % 1000) / 1000.0
  jitter = (h - 0.5) * 0.10          # +/-0.05 deterministic spread
  p_i = clip(q + persona["lean"] + jitter)
  ```
  This anchors on the market prior, spreads the ensemble deterministically, and CANNOT
  peek at `y` (it isn't in scope). Use `scoring.clip`.
- **mock=False:** build a prompt = persona["prompt"] + the market question + `q` + any
  evidence in `market["meta"]`; call `_complete(prompt, role="forecast", mock=False)`;
  parse the first float in [0,1] from the reply via `_parse_prob`. On parse failure,
  fall back to that persona's deterministic mock value (never raise; never skip a
  persona — a missing forecaster silently shrinks the ensemble and biases it).

`_parse_prob(text) -> float|None`: regex the first `0?\.\d+` or integer-percent; clip;
None if nothing parseable.

### `reconcile(forecasts, market, _complete=llm.complete, mock=True) -> dict`
Aggregate the per-persona list into `p_model`. Returns
`{"p_model": float, "p_std": float, "n": int}`.
- `mean = sum(p_i)/n`; `p_std = popn stddev of p_i` (pure stdlib).
- **mock=True:** `p_model = mean` (simple mean — research: naive LLM-judge aggregation is
  WORSE than the mean; the supervisor must only deviate on hard evidence).
- **mock=False:** call the Opus `supervise` role with the disagreement summary and ask
  for a reconciled probability ONLY IF it can cite a concrete resolving fact; parse via
  `_parse_prob`. If it returns None OR the result is within 0.03 of the mean, KEEP THE
  MEAN. The supervisor may nudge on evidence, never overrule on vibes.

### `blend(p_model, q_market, w=0.70) -> float`
`return clip(w * p_model + (1.0 - w) * clip(q_market))`. w=0.70 is the PolySwarm prior
(independent analysis dominates, market informs). Per-archetype learned `w` is LATER.

### `forecast_market(market, w=0.70, personas=PERSONAS, _complete=llm.complete, mock=True) -> dict`
The full per-market pass. Returns:
```python
{"p_model": float, "p_std": float, "p_final": float, "n_agents": int, "w": w}
```
where `p_final = blend(p_model, market["q_yes"], w)`. Calibration is applied LATER, in
`forecast_store`, only when the cell has n>=200 — keep `forecast_market` calibration-free.

## 4. `alpha/calibrate.py`
```python
ALPHA = 3 ** 0.5   # ~1.732, AIA's fixed extremization coefficient (no overfit)
CALIB_MIN_N = 200  # institute standing rule
```
- `extremize(p, alpha=ALPHA)`: logit-space scaling toward the tails.
  `z = log(clip(p)/(1-clip(p)))`; `return 1/(1+exp(-alpha*z))`. Pure `math`.
- `maybe_calibrate(p, n, alpha=ALPHA)`: `return extremize(p, alpha) if n >= CALIB_MIN_N
  else p`. This is the ONLY place calibration switches on; today n is tiny so it is a
  structural no-op. Document that clearly.

## 5. `alpha/forecast_store.py`
`forecast_open(store_path, fetch_forecaster=forecast_market, now=None, max_forecasts=25,
mock=True) -> list[dict]`
- Load the JSONL store (reuse `corpus.store`). For each row with `status=="open"` that
  does NOT already carry `meta.p_final` (idempotent — never re-forecast a market; the
  first, point-in-time forecast is the honest one), call `fetch_forecaster(row, mock=mock)`
  and write `p_model/p_std/p_final/n_agents/forecast_ts` into `row["meta"]`.
- Stop after `max_forecasts` newly-forecast rows this call (TOKEN BUDGET — research:
  context/cost overflow is the silent killer; the cron MUST be capped).
- `overwrite_jsonl` and return the rows forecast this call. NEVER touch settled rows.
- NEVER reads `y` (it may be None anyway on open rows; assert the row is open).

## 6. `research` baseline (`map/baselines.py`)
```python
def research(rm, edge=0.05, std_ceiling=0.20):
    """Bet our model's edge vs the market, but only when confident and decisive.
    Reads the point-in-time forecast frozen at snapshot. No forecast -> no bet."""
    meta = rm.get("meta", {})
    p = meta.get("p_final")
    if p is None:
        return rm["q_yes"], None                 # never forecast -> abstain
    if meta.get("p_std", 1.0) > std_ceiling:
        return p, None                           # swarm too divided -> abstain
    q = rm["q_yes"]
    if p - q > edge:   return p, "YES"
    if q - p > edge:   return p, "NO"
    return p, None
```
Register: `BASELINES["research"] = (research, {}, True)` (use_realized=True like
longshot_fade). Add to `generate.BASELINE_MECHANISM`:
`"research": ("model_vs_crowd", "independent ensemble forecast diverges from the PM price; bet the edge")`.
`pipeline.run_all` will pick it up automatically (it iterates registered baselines);
`factor.CELL_FACTORS` already has the archetypes. NO pipeline/gate/allocator edits.

## 7. `cadence.py` — the org loop (one pass)
`run_cycle(stores=None, bankroll=10000.0, mock=True, log=False) -> dict`
Ties the existing pieces into perceive->reason->plan->act->verify->critique->improve:
1. PERCEIVE+VERIFY: (the cron already runs snapshot/settle before this; cadence does not
   place network calls itself unless `mock=False`).
2. REASON: for each wired store, `forecast_store.forecast_open(path, mock=mock)`.
3. PLAN+GATE+ACT: `rows = resolve.load_all_rows()`; `book = book.build_book(rows=rows,
   bankroll=bankroll)` (research cells now flow through Gates 1-7 + allocator).
4. CRITIQUE: include `gate4`/decay summary already in the book.
Return `{"forecast": {store: n_forecast}, "book": book}`. Pure orchestration; all heavy
lifting is in modules that already have tests.

## 8. CLI (`institute/cli.py`)
- `cmd_forecast()`: run `forecast_open` over each wired store (crypto now; weather store
  if/when present), print `f"forecast {k} open markets across {s} stores"` (ASCII).
- `cmd_cycle()`: `cadence.run_cycle()`, then print `book.render(out["book"])`.
- Wire both `elif` branches + the module docstring.

## 9. Cron (`setup_gcp.sh`)
Extend the institute cron line (the :05/:35 one) so the VM forms forecasts autonomously:
`... crypto-snapshot && institute.cli forecast && crypto-settle && ...` then `git add
institute/data`. Keep it AFTER snapshot (so new open markets get a point-in-time forecast
the same tick they appear) and BEFORE settle. The `max_forecasts` cap bounds cost.

## 10. Tests (offline, deterministic — NO real network)
- **test_alpha_engine.py:** swarm_forecast(mock) is deterministic + reproducible across
  calls; returns one entry per persona; all p in (0,1). reconcile(mock) == mean; p_std
  ==0 when all equal. blend(0.8,0.4,0.7)==clip(0.68). forecast_market returns p_final ==
  blend(p_model,q). Inject a fake `_complete` returning `"0.73"` -> mock=False parses
  0.73; returning garbage -> falls back to the persona mock (no raise).
- **test_alpha_calibrate.py:** extremize(0.5)==0.5; extremize(0.8)>0.8; extremize(0.2)<0.2;
  symmetry extremize(p)+extremize(1-p)==1 (within 1e-9). maybe_calibrate(0.8, n=10)==0.8
  (off); maybe_calibrate(0.8, n=500)==extremize(0.8) (on).
- **test_forecast_store.py:** temp store with 2 open rows (no p_final) + 1 settled ->
  forecast_open writes p_final to the 2 open rows only, leaves settled untouched; second
  call forecasts 0 (idempotent); max_forecasts=1 forecasts exactly 1; asserts no row's `y`
  was read/changed.
- **test_research_baseline.py:** p_final-q>edge -> "YES"; q-p_final>edge -> "NO"; within
  edge -> None; p_std>ceiling -> None; missing p_final -> None. Confirm it scores through
  `baselines.evaluate` without error on a small resolved set.
- **test_cadence.py:** run_cycle(mock=True) over a temp crypto store with forecast-able
  open rows returns a dict with `forecast` counts and a `book` whose render() is .isascii().

Run `python -m pytest institute/tests -q` from repo root -> all green (prior + new).

## 11. Deviations
If the spec forces an unsound choice, fix it soundly with a one-line `# DEVIATION:`
comment and report it. In particular: if any existing test asserts the exact `complete()`
mock string, do NOT change `complete()`; keep all forecast parsing inside `alpha/`.
