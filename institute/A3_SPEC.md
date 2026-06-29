# A3 — Close the Loop (Gates 2-3 + Strategy-gen + Paper Executor + Sports) — Spec

Opus-authored. Implementer: Sonnet 4.6. Build EXACTLY this. Pure stdlib
(`math, random, statistics, itertools, os, json, datetime, uuid`). NO numpy/scipy.
ASCII-only prints (Windows cp1252 — use `->` never unicode arrows). Match the
terse institute/ style (docstrings say WHY not WHAT). Do NOT modify A1/A2 logic;
you may ADD a Strategy dataclass to schema.py and ADD CLI branches.

## What A3 delivers
The cell lifecycle `PROPOSED -> BACKTEST(Gate1) -> MECHANISM(Gate2) ->
REDTEAM(Gate3) -> PAPER-FORWARD(Gate4 queue)` made real and runnable end to end,
plus a second archetype (sports). Gate 4+ (forward lockbox, allocator) are A4 —
A3 only ENQUEUES survivors for paper-forward and runs the paper executor that
will feed Gate 4.

## Files to create
```
institute/agents/__init__.py
institute/agents/llm.py            # provider-agnostic seam; deterministic mock default
institute/strategy/__init__.py
institute/strategy/generate.py     # map cells -> candidate Strategy proposals (+mechanism)
institute/gates/__init__.py
institute/gates/mechanism.py       # Gate 2
institute/gates/redteam.py         # Gate 3
institute/execute/__init__.py
institute/execute/paper.py         # forward-paper ledger (feeds Gate 4)
institute/pipeline.py              # orchestrate Gate1->2->3 -> paper-forward queue
institute/classify/sports.py       # sports baseline(s) + feature seam
institute/tests/test_generate.py
institute/tests/test_mechanism.py
institute/tests/test_redteam.py
institute/tests/test_paper.py
institute/tests/test_pipeline.py
institute/tests/test_sports.py
```
Edit: `institute/corpus/schema.py` (+Strategy dataclass), `institute/cli.py`
(+`propose`, `pipeline`, `paper` commands).

## Interfaces to bind to (exist)
- baselines: `price_follow`, `longshot_fade`, `_sim_profit(side,q_yes,y,cost)`, `evaluate`, `BASELINES`.
- scoring: `market_relative_S`, `clip`, `mean`.
- evidence.backtest: `returns_series(rows, baseline_fn, **kw)`, `win_loss_stream(...)`.
- evidence.gate1: `run_gate(archetype, baseline_name, rows=None, log=True)` -> dict with
  keys dsr/perm/pbo/sprt/verdict (verdict in pass|insufficient|fail). REGISTRY const there.
- map.predictability: `build(rows)` -> list[MapCell]; MapCell has .archetype/.baseline/.status/.ev_net/.mean_S/.n.
- resolve.weather_adapter: `load_rows()`.
- corpus.registry: `log_trial(path, trial)`, `all_trials(path)`, `trial_count(path)`; corpus.schema.Trial.
- corpus.store: `append_jsonl`, `load_jsonl`, `overwrite_jsonl`.
- All institute data files live under `institute/data/` (gitignored). Define path
  constants via `os.path.dirname(os.path.dirname(__file__))`.

## schema.py — ADD
```python
@dataclass
class Strategy:
    id: str               # uuid4 hex (short ok)
    archetype: str
    baseline: str         # name resolvable in baselines/sports registry
    params: dict          # field(default_factory=dict)
    mechanism: str        # one of MECHANISMS keys (see mechanism.py); "" if none
    hypothesis: str       # human-readable claim
    status: str = "proposed"   # proposed|gate1_pass|gate2_pass|gate3_pass|paper|rejected
    metrics: dict = field(default_factory=dict)
    ts: str = ""
    def dict(self): return asdict(self)
```

## agents/llm.py — the seam (model ROUTING, never picking; CONSTITUTION)
```python
# Provider-agnostic. Default = deterministic MOCK (no network, tests stay offline).
# Real providers wired later behind the same signature. Role -> model routing map
# is declared here as DATA so it is auditable:
ROUTING = {
    "reason":   "claude-opus-4-8",      # strategy-gen, red-team, allocator
    "judge":    "claude-opus-4-8",      # mechanism judging
    "classify": "claude-haiku-4-5",
    "index":    "claude-haiku-4-5",
}
def complete(prompt, role="reason", mock=True, **kw) -> str:
    # mock=True (default & in tests): return a deterministic stub string keyed off
    # role so callers have a stable contract. NEVER call a network in this build.
    # Leave a clearly-marked TODO block where a real client would dispatch by
    # ROUTING[role]. Return f"[MOCK:{role}] ok".
```
generate/mechanism/redteam MUST work with rule-based logic by default and only
*optionally* consult `llm.complete`; tests never hit a network.

## strategy/generate.py — Strategy-gen (Quant), Gate-budgeted
```python
# Default mechanism per baseline (the causal "why"); used to seed proposals.
BASELINE_MECHANISM = {
    "longshot_fade": ("favorite_longshot_bias",
                      "cheap longshots are systematically overpriced; fade (bet NO)"),
    "price_follow":  ("", "null: copies the price, no claimed edge"),
    "odds_follow":   ("market_consensus", "sharp sportsbook odds beat thin PM price"),
    "power_rating_fade": ("model_vs_crowd",
                      "power-rating model disagrees with crowd-driven PM price"),
}

def propose_from_map(cells, budget=10) -> list[Strategy]:
    # For each MapCell that is NOT the price_follow null and shows mean_S>0 (any n),
    # emit ONE Strategy with baseline=cell.baseline, archetype=cell.archetype,
    # mechanism+hypothesis from BASELINE_MECHANISM (mechanism "" if unknown).
    # Stop at budget (§11C strategy-gen is budgeted to bound search intensity).
    # status="proposed", ts=utcnow iso, id=uuid4 hex[:12]. Return list.

def propose(rows=None, budget=10) -> list[Strategy]:
    # load weather rows if None; build map; call propose_from_map.

def log_proposals(strategies, registry_path):
    # log each as a Trial(strategy_id=s.id, archetype, params={"baseline":...},
    # verdict="proposed", metrics=s.metrics). Honest registry = honest deflation.
```

## gates/mechanism.py — Gate 2 (the "why" gate)
```python
MECHANISMS = {
  "favorite_longshot_bias": "tails systematically overpriced (behavioural)",
  "recency_overreaction":   "crowd overweights latest event",
  "liquidity_vacuum":       "thin book -> stale/whippy price",
  "model_vs_crowd":         "quant model has info the crowd's price lacks",
  "market_consensus":       "sharper external market (sportsbook) leads PM price",
}

def check(strategy, rows, baseline_fn, **kw) -> dict:
    # 1) mechanism must be a non-empty key in MECHANISMS, else HOLD ("no stated mechanism").
    # 2) CONSISTENCY: the error pattern must match the claimed mechanism. Concretely:
    #    - favorite_longshot_bias: bets must be NO on cheap longshots AND the
    #      realized/sim win rate must exceed the implied break-even (priced) rate.
    #      Verify: among placed bets (side!=None), mean executable cost < 0.5 AND
    #      win_pct (from baselines.evaluate) > 100*mean_cost (beats break-even).
    #    - model_vs_crowd / market_consensus / recency_overreaction / liquidity_vacuum:
    #      generic consistency = mean_S > 0 on the rows (edge beyond price exists).
    # Return {passed: bool, mechanism, reason, evidence:{...}}.
    # passed=True only if mechanism stated AND its consistency test holds.
```
This is where judgement lives; expose an optional `use_llm=False` that, when True,
calls `llm.complete(prompt, role="judge")` and folds an advisory note into reason
(does not override the deterministic verdict in this build).

## gates/redteam.py — Gate 3 (adversarial)
Independent battery that tries to BREAK a surviving cell. Each returns a finding;
cell survives only if NO finding is fatal.
```python
def attack_lookahead(strategy, rows, baseline_fn, **kw) -> finding
   # leak check: baseline must depend only on q_yes (knowable at t0). Detect by
   # perturbing/removing y in a copy of rows and confirming the DECISION (side)
   # is unchanged for every row (decisions must not depend on the outcome y).
   # Fatal if any decision flips when y is altered.
def attack_regime(strategy, rows, baseline_fn, **kw) -> finding
   # split rows into 3 contiguous thirds; compute ev_net per third (baselines.evaluate).
   # Fatal if edge is carried by ONE third only: i.e. >=2 thirds have ev_net<=0
   # while overall>0 (fragile/regime-dependent). Warn (non-fatal) if 1 third <=0.
def attack_fills(strategy, rows, baseline_fn, **kw) -> finding
   # re-evaluate EV with a stress cost (cost=0.03 friction on _sim_profit via kw or
   # a re-sim). Fatal if EV_net flips negative under realistic worse fills.
def run(strategy, rows, baseline_fn, **kw) -> dict
   # run all three; survived = no fatal findings. Return {survived, findings:[...]}.
```
Optional `use_llm` adds an advisory Opus("reason") note; never overrides determinism here.

## execute/paper.py — forward-paper executor (feeds Gate 4)
A forward ledger of paper positions per cell. NOT the papertrader ledger — a thin
institute-side jsonl so Gate 4 can count post-freeze resolved outcomes per cell.
```python
PAPER_LEDGER = institute/data/paper_ledger.jsonl
# A position: {id, strategy_id, archetype, baseline, market_id, t0, q_yes_entry,
#   side, status:"open"|"settled", y:None|0|1, pnl:None|float, settled_ts}
def open_position(strategy, market_snapshot, baseline_fn, **kw) -> dict | None:
    # market_snapshot: {market_id, q_yes, t0, ...}. Run baseline_fn -> (p, side).
    # if side is None: return None (no bet). Else append an open position; return it.
def settle(market_id, y, ledger_path=PAPER_LEDGER) -> dict | None:
    # find open position(s) for market_id, set y, compute pnl via _sim_profit(side,
    # q_yes_entry, y), status="settled". Overwrite ledger. Return settled position.
def forward_count(strategy_id, ledger_path=PAPER_LEDGER) -> int:
    # number of SETTLED positions for this strategy (the Gate-4 counter).
def open_positions(ledger_path=PAPER_LEDGER) -> list   # status=="open"
```

## classify/sports.py — second archetype
```python
# No live sports resolved-data sensor yet -> baselines + feature seam + tests on
# synthetic rows. Same ResolvedMarket shape (q_yes,y,meta).
def odds_follow(rm, **kw):
    # if meta has 'book_prob' (sharp sportsbook implied prob), bet toward it vs price:
    # side "YES" if book_prob > q_yes + 0.03 else "NO" if book_prob < q_yes-0.03 else None.
    # forecast p = book_prob (fallback q_yes if absent -> side None).
def power_rating_fade(rm, **kw):
    # if meta has 'model_prob', same disagreement logic vs q_yes (thresh 0.05).
SPORTS_BASELINES = {"odds_follow": odds_follow, "power_rating_fade": power_rating_fade}
```
Also register these so pipeline/gates can resolve a baseline by name across weather+sports:
add a small `institute/strategy/registry_fns.py` OR a `resolve_baseline(name)` in
generate.py that looks in baselines.* then sports.SPORTS_BASELINES. Pick the
simplest: a single `resolve_baseline(name)` helper in `institute/strategy/generate.py`.

## pipeline.py — orchestrate the loop
```python
def run_cell(archetype, baseline_name, rows=None, use_llm=False) -> dict:
    # 1) build strategy via generate (mechanism from BASELINE_MECHANISM)
    # 2) gate1 = evidence.gate1.run_gate(archetype, baseline_name, rows, log=True)
    # 3) if gate1 verdict == "fail": stop, status rejected.
    #    (verdict "insufficient" still proceeds to gate2/3 as DIAGNOSTIC but the
    #     cell cannot reach paper until gate1 passes — record gate1_ok flag.)
    # 4) gate2 = mechanism.check(...); if not passed: stop at MECHANISM (held).
    # 5) gate3 = redteam.run(...); if not survived: stop at REDTEAM (rejected).
    # 6) if gate1 passed AND gate2 AND gate3: status="paper" (enqueue for forward).
    #    else status reflects furthest gate reached.
    # Return {strategy, gate1, gate2, gate3, status, gate1_ok}.
def run_all(rows=None) -> list   # run every non-null cell from the current map.
def render(results) -> str       # ASCII table: archetype baseline g1 g2 g3 status.
```

## CLI additions
- `python -m institute.cli propose`  -> print proposed strategies (id, archetype, baseline, mechanism).
- `python -m institute.cli pipeline`  -> run_all + render.
- `python -m institute.cli paper`     -> print open paper positions + per-strategy forward_count.
All ASCII.

## Tests (all must pass; offline, seeded, pure stdlib)
- test_generate: propose() yields >=1 Strategy for weather longshot_fade with
  mechanism=="favorite_longshot_bias"; price_follow null is NOT proposed.
- test_mechanism: longshot_fade on the real weather rows -> passed True, mechanism
  favorite_longshot_bias; a strategy with mechanism="" -> passed False (held).
- test_redteam: a leak-free baseline (longshot_fade) -> attack_lookahead non-fatal;
  a synthetic "cheating" baseline that returns side based on rm["y"] -> attack_lookahead FATAL.
  fill stress on a thin +EV synthetic set that survives; a marginal set that flips -> fatal.
- test_paper: open_position on a snapshot creates an open row; settle() sets pnl &
  status; forward_count increments; use a tmp ledger path (monkeypatch/arg), never
  touch the real ledger.
- test_pipeline: run_cell("weather-daily","longshot_fade", rows=real) returns dict
  with gate1/gate2/gate3/status keys; status reflects gate1 insufficient at n=13
  (NOT "paper"); run_all returns a list incl. weather cells.
- test_sports: odds_follow bets YES when book_prob>>q_yes, NO when <<, None when ~equal;
  power_rating_fade respects model_prob; on a synthetic biased sports set the chosen
  baseline shows mean_S>0 via baselines.evaluate.

## Run to verify (from repo root)
```
python -m pytest institute/tests -q          # ALL must pass (31 existing + new)
python -m institute.cli propose
python -m institute.cli pipeline
```
Report: files created, final pytest line, and the `pipeline` output. Note any spec
deviation + why. Keep the report concise.
