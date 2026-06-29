# A4 — Portfolio Brain (SPEC)

**Owner:** Opus authored this spec + verifies. Sonnet 4.6 implements per spec.
**Milestone goal:** turn "many proven cells" into "one risk-managed book." Implements
CONSTITUTION Gates 4→7 and §7 sizing/risk. The book must show the same discipline A3
showed: **nothing gets capital unless the evidence earns it.** With today's data
(weather cell is `gate1_insufficient`, paper ledger empty) the live book is correctly
EMPTY — that is the system working.

## Hard rules (inherited, non-negotiable)
- Pure stdlib only. No numpy/scipy/pandas. `math`, `os`, `json`, `datetime`, `itertools`.
- **ASCII-only** in all `print`/render output (Windows cp1252).
- `git add` specific paths only (the committer handles this, not you).
- Fake money only — A4 computes *sizing*, it never places a real order.
- Reuse existing modules; do not duplicate. Bind to the signatures named below.
- Every new module gets a docstring citing the CONSTITUTION clause it implements.

## Modules to create
```
institute/portfolio/__init__.py
institute/portfolio/factor.py       # Gate 5 correlation from shared loadings
institute/portfolio/gate4.py        # Gate 4 capital-activation ladder (forward lockbox)
institute/portfolio/allocator.py    # Gate 5/6 fractional-Kelly + correlation caps
institute/portfolio/decay.py        # Gate 7 significance-gated decay detector
institute/portfolio/book.py         # orchestrator: cells -> eligible -> allocation
institute/tests/test_factor.py
institute/tests/test_gate4.py
institute/tests/test_allocator.py
institute/tests/test_decay.py
institute/tests/test_book.py
```
Plus: extend `institute/cli.py` with a `book` command. Update `cli.py` docstring.

---

## 1. `portfolio/factor.py` — correlation from shared loadings (Gate 5, Seam 2)

Correlation between cells is computed from **shared structural factor loadings**
(Barra-style), never from sparse pairwise pnl history. Source the loadings from the
existing `institute.classify.factors.loadings(archetype, meta)`.

For cross-cell correlation we use **stable structural factors only** — the numeric
betas, not per-instance categorical keys (which carry "?" placeholders at cell level
and describe intra-cluster concentration, not cross-cell co-movement). Define:

```python
# structural betas per archetype for Gate-5 correlation (numeric, history-free)
CELL_FACTORS = {
    "weather-daily": {"weather": 1.0},
    "crypto-daily":  {"crypto_beta": 1.0, "macro": 0.3},
    "sports-game":   {"sports": 1.0},
    "econ-release":  {"macro": 1.0},
}
```

Functions:
- `cell_vector(archetype) -> dict[str,float]`: return `CELL_FACTORS.get(archetype, {})`
  (copy, do not mutate the constant).
- `correlation(va, vb) -> float`: **cosine similarity** over the union of factor keys.
  `dot / (||va|| * ||vb||)`. If either norm is 0, return 0.0. All weights are >= 0 so
  the result lies in [0, 1]. Round to 4 dp. Two weather cells -> 1.0; weather vs crypto
  -> 0.0; crypto vs econ share `macro` -> a positive partial correlation.
- `corr_matrix(archetypes) -> list[list[float]]`: square matrix in the given order,
  diagonal = 1.0.

---

## 2. `portfolio/gate4.py` — capital-activation ladder / forward lockbox (Gate 4 + §B)

Reads the institute forward-paper ledger and decides whether a strategy has earned
graduation off paper. Bind to `institute.execute.paper.load`-style access via
`institute.corpus.store.load_jsonl` and `paper.PAPER_LEDGER`.

Constants (these are *changeable* params per CONSTITUTION §10 — define at top, do not
hardcode inline):
```python
N_FLOOR = 50          # moderate-effect sample floor
WEEKS_MIN = 4         # minimum forward span
P0 = 0.50             # SPRT null: no edge (break-even win rate baseline)
P1_LIFT = 0.10        # SPRT alt: p0 + lift, capped 0.98
```

`settled_for(strategy_id, ledger_path=paper.PAPER_LEDGER) -> list[dict]`:
return that strategy's `status=="settled"` ledger rows, sorted by `settled_ts`.

`gate4_status(strategy_id, ledger_path=paper.PAPER_LEDGER) -> dict`:
1. rows = settled_for(...). `n = len(rows)`.
2. If `n == 0`: return verdict `"accumulating"`, everything zero/None, reason
   `"no settled forward outcomes"`.
3. win/loss stream: `w = 1 if row["pnl"] > 0 else 0` in chronological order.
4. forward EV = mean of `row["pnl"]` (per-$1 already, since paper pnl is per unit).
5. span_weeks = (last settled_ts - first settled_ts) in days / 7.0. Parse the
   `"%Y-%m-%dT%H:%M:%SZ"` timestamps with `datetime.datetime.strptime`; if any parse
   fails, treat span_weeks as 0.0 (do not crash).
6. SPRT early-stop: `p1 = min(0.98, P0 + P1_LIFT)`; `s = stats.sprt(stream, P0, p1)`.
7. Verdict:
   - `"graduated"` if `s["decision"] == "accept_H1"` **and** `ev > 0`
     (a large measured edge graduates on fewer than N_FLOOR samples — §B), **or**
     if `n >= N_FLOOR and span_weeks >= WEEKS_MIN and ev > 0`.
   - `"rejected"` if `s["decision"] == "accept_H0"` **or** (`n >= N_FLOOR and ev <= 0`).
   - else `"accumulating"`.
8. Return `{strategy_id, n, ev: round(ev,6), span_weeks: round(.,2), sprt: s["decision"],
   verdict, reason}` where reason is a short ASCII string explaining the verdict.

A cell is **eligible for allocation iff `verdict == "graduated"`.**

---

## 3. `portfolio/allocator.py` — fractional-Kelly + correlation caps (Gate 5/6, §7)

A cell carries the standalone metrics dict produced by `map.baselines.evaluate`
(`{n, win_pct, mean_S, ev_net, naive_roi}`) plus archetype + a strategy id.

Represent an input cell as a plain dict:
```python
{"id": str, "archetype": str, "baseline": str,
 "metrics": {...evaluate output...},
 "mean_price": float,          # mean executable entry price for the bet side
 "max_drawdown_live": float}   # owner-set; default below if missing
```

Constants (changeable params):
```python
KELLY_FRACTION = 0.25          # start ~0.25, tune (CONSTITUTION §10 table)
CELL_CAP = 0.10                # max bankroll fraction in one cell
ARCHETYPE_CAP = 0.25           # max per archetype
CLUSTER_CAP = 0.25             # max per correlated cluster
TOTAL_CAP = 0.60               # max deployed; remainder is RESERVE (§7)
CLUSTER_CORR = 0.50            # cells with corr >= this share a cluster
DEFAULT_CELL_DD = -0.20        # default per-cell drawdown halt (§7)
DEFAULT_BOOK_DD = -0.15        # default book drawdown halt (§7)
```

### 3a. Kelly per cell
`kelly_fraction(win_prob, payoff_b, calib) -> float`:
- Binary Kelly: `f_star = win_prob - (1 - win_prob) / payoff_b` (= (b*p-(1-p))/b).
- If `payoff_b <= 0` return 0.0. If `f_star <= 0` return 0.0 (no edge -> no size).
- Scale: `f = f_star * KELLY_FRACTION * calib`. Clip to `[0, CELL_CAP]`.

`payoff_b` for our bets comes from the executable price: a bet at price `pr` pays
`(1/pr - 1)` on a win. Compute `payoff_b = 1.0/clip(mean_price) - 1.0` using
`institute.scoring.clip`. `win_prob = metrics["win_pct"]/100.0`.

`calibration_quality(cell) -> float`: monotone map of `mean_S` into [0,1].
`min(1.0, max(0.0, metrics["mean_S"] / CALIB_TARGET))` with `CALIB_TARGET = 0.05`
(a cell scoring our proven +0.063 weather skill earns ~full weight; a zero/negative-S
cell earns 0 -> gets cut, not just trusted less, per §7).

### 3b. Clustering
`cluster(cells) -> list[list[int]]`: union-find / transitive grouping on indices where
`factor.correlation(cell_vector(a), cell_vector(b)) >= CLUSTER_CORR`. Same-archetype
cells always cluster (corr 1.0). Return list of index-groups.

### 3c. Marginal-contribution gate (Gate 5)
Within a cluster, a cell is only funded if it **improves the cluster** — i.e. its
standalone `ev_net` is positive AND not strictly dominated. Concrete deterministic rule:
- Sort cluster members by `ev_net` desc.
- The top member is the cluster's anchor (always considered).
- A non-anchor member is funded only if its `ev_net >= MARGINAL_FLOOR` where
  `MARGINAL_FLOOR = 0.5 * anchor.ev_net` (it must contribute at least half the anchor's
  edge to justify adding correlated exposure). Members below the floor get
  `status="gate5_wait"`, weight 0, reason `"dominated within cluster"`.

### 3d. Allocation
`allocate(cells, bankroll, **overrides) -> dict`:
1. For each cell compute `raw = kelly_fraction(...)` and `calib`.
2. Build clusters; apply the marginal-contribution gate (3c) — waiting cells get raw 0.
3. Apply caps in order: per-cell (already clipped in Kelly), then **scale within each
   cluster** so cluster sum <= CLUSTER_CAP, then **scale within each archetype** so
   archetype sum <= ARCHETYPE_CAP, then **scale globally** so total <= TOTAL_CAP.
   Scaling = multiply each member weight by `min(1, cap/sum)`. Record which cap bound
   each cell (`capped_by` in {"none","cell","cluster","archetype","total"} — the
   tightest that actually reduced it).
4. `reserve_frac = 1.0 - sum(final weights)` (>= 1 - TOTAL_CAP).
5. Each funded cell: `dollars = round(weight * bankroll, 2)`,
   `max_drawdown_live = cell.get("max_drawdown_live", DEFAULT_CELL_DD)`,
   `status = "allocated"` (weight>0) or `"gate5_wait"` (weight 0 from 3c) or
   `"no_edge"` (raw Kelly was 0).
6. Return:
```python
{"bankroll": bankroll,
 "deployed": round(sum dollars, 2),
 "reserve": round(reserve_frac * bankroll, 2),
 "book_drawdown_halt": DEFAULT_BOOK_DD,
 "clusters": [[ids...], ...],
 "allocations": [
    {"id","archetype","baseline","weight": round(.,4),"dollars","calib": round(.,3),
     "kelly_raw": round(.,4),"cluster": int_index,"capped_by","status","reason"} ...]}
```
Allocations sorted by weight desc.

---

## 4. `portfolio/decay.py` — Gate 7 decay detector (continuous, symmetric, §F)

Gate 7 fires **only on statistically significant edge degradation, never on a normal
drawdown.** Monitors a live cell's chronological per-bet pnl stream.

`detect(pnl_series, recent_frac=0.4, alpha=0.05, min_window=8) -> dict`:
1. `n = len(pnl_series)`. If `n < 2*min_window`: return
   `{"decayed": False, "reason": "insufficient history", "p_value": None,
     "early_ev": None, "recent_ev": None, "n": n}` (never demote on thin data).
2. Split chronologically: `k = max(min_window, int(round(n * recent_frac)))`;
   `early = series[:n-k]`, `recent = series[n-k:]`. Guard `len(early) >= min_window`.
3. One-sided test of H0: recent mean >= early mean (no decay) vs H1: recent < early.
   Use a **Welch z-approximation** (pure stdlib; no t-distribution needed):
   - `me, mr` = means; `ve, vr` = sample variances (ddof=1); `ne, nr` = sizes.
   - `se = sqrt(ve/ne + vr/nr)`. If `se == 0`: decayed = `mr < me`, p_value 0.0 or 1.0.
   - `z = (mr - me) / se`. `p_value = stats.norm_cdf(z)` (left tail = P(recent worse)).
4. `decayed = (p_value < alpha) and (mr < me) and (mr <= 0 or mr < 0.5*me)`.
   The extra magnitude clause ensures we demote on *material* erosion (recent edge
   collapsed toward/below zero), not a statistically-significant-but-still-profitable
   wobble. Symmetric: the same detector, run continuously, is what re-promotes when
   recent EV recovers (out of scope to act on here; just report `recent_ev`).
5. Return `{"decayed", "p_value": round(.,4), "early_ev": round(me,6),
   "recent_ev": round(mr,6), "z": round(z,4), "n", "reason"}`.

---

## 5. `portfolio/book.py` — orchestrator

`build_book(rows=None, bankroll=10000.0, use_llm=False, log=False) -> dict`:
1. `rows = weather_adapter.load_rows()` if None.
2. Run `pipeline.run_all(rows=rows, use_llm=use_llm, log=log)`.
3. For each pipeline result whose `status in ("paper",)` (gates 1-3 cleared AND gate1
   passed), check `gate4.gate4_status(strategy.id)`. Collect cells with
   verdict `"graduated"` into the eligible list, building the allocator cell dict from
   the strategy + its `map.baselines.evaluate` metrics (compute mean_price from the
   archetype rows: mean of executable entry price for the taken side — for NO bets
   that is `1 - q_yes`, for YES `q_yes`; reuse the baseline_fn to get the side).
4. `alloc = allocator.allocate(eligible, bankroll)` (empty list -> empty book, reserve
   = full bankroll).
5. Return `{"eligible": [...ids], "gate4": [...status dicts for paper cells],
   "allocation": alloc}`.

`render(book) -> str`: ASCII table. Header line, then either the allocations
(id, archetype, baseline, weight, dollars, status) or `"(no cells graduated to capital
-- book is all reserve)"`. Footer: deployed / reserve / book drawdown halt. Must be
`.isascii()`.

**Expected live output today:** weather cell is `gate1_insufficient` so it never reaches
the `"paper"` branch; eligible is empty; book is 100% reserve. This is correct and a
test must assert it.

---

## 6. CLI

Add to `cli.py`:
```python
def cmd_book():
    from institute.portfolio import book
    b = book.build_book()
    print(book.render(b))
```
Wire `elif cmd == "book": cmd_book()` and add the line to the module docstring:
`    python -m institute.cli book      # build the risk-managed book (Gates 4-7)`.

---

## 7. Tests (pytest, offline, deterministic)

- **test_factor.py**: weather-weather corr == 1.0; weather-crypto == 0.0; crypto-econ
  share macro -> 0 < corr < 1; `corr_matrix` diagonal all 1.0, symmetric.
- **test_gate4.py**: empty ledger -> `accumulating`. Build a temp ledger via
  `paper.open_position` + `paper.settle` (temp path) with a strong win streak ->
  SPRT `accept_H1` -> `graduated`. A losing streak past N_FLOOR (monkeypatch N_FLOOR
  small, e.g. set `gate4.N_FLOOR = 6` in the test) -> `rejected`.
- **test_allocator.py**:
  - `kelly_fraction`: a +EV cell (p=0.9, b=4.0, calib=1) -> positive, clipped <= CELL_CAP;
    a -EV cell (p=0.2, b=1.0) -> 0.0.
  - Two identical weather cells (corr 1.0) cluster together; cluster sum weight
    <= CLUSTER_CAP; the dominated one (lower ev_net below the marginal floor) gets
    `status=="gate5_wait"`.
  - One weather + one crypto cell -> two clusters; total deployed <= TOTAL_CAP;
    reserve == bankroll - deployed (within rounding); reserve >= bankroll*(1-TOTAL_CAP).
- **test_decay.py**:
  - flat-profitable stream -> `decayed False`.
  - early-positive then recent-collapsed-to-negative stream -> `decayed True`,
    `p_value < 0.05`.
  - short stream (< 2*min_window) -> `decayed False`, reason "insufficient history".
- **test_book.py**: `build_book(log=False)` returns the expected keys; with live data
  `allocation["allocations"] == []` and reserve == bankroll (nothing graduated);
  `render(book).isascii()` is True and does not crash.

Run `python -m pytest institute/tests -q` from repo root -> all green (target: the
existing 49 plus the new A4 tests). Use `datetime.datetime.now(datetime.UTC)` is NOT
required — match the existing `datetime.datetime.utcnow()` style already in the repo to
stay consistent (the deprecation warning is known and accepted).

## 8. Deviations
If the spec forces an unsound choice (e.g. a degenerate variance, a clustering edge
case), fix it the sound way and leave a one-line `# DEVIATION:` comment explaining why.
Report any deviation in your final message.
