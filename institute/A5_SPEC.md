# A5 — Crypto-daily live sensor (second archetype) — SPEC

**Owner:** Opus authored + verifies. Sonnet 4.6 implements per spec.
**Goal:** give the gates a *second* archetype to chew on. Build a two-phase
crypto-daily sensor (snapshot live q -> settle y) feeding the SAME map/gate/book
pipeline weather already uses. Honest by construction: `q_yes` is captured **while the
market is live** (real decision-time prior), `y` is filled from Polymarket's own
resolution at settlement. No reconstructed/synthetic prices.

## Why two phases (do not shortcut this)
A *closed* market's `outcomePrices` are the 0/1 settlement — useless as a prior. A live
market's `outcomePrices[0]` is the current market-implied P(YES) — a real prior. So we
must record q while OPEN and y once CLOSED. This mirrors the papertrader scan/settle
split and the institute paper_ledger.

## Confirmed live Gamma facts (probed 2026-06-30, do not re-guess)
- Base: `https://gamma-api.polymarket.com`; reachable from this machine (read-only).
- `GET /markets?limit=100&active=true&closed=false&order=volume&ascending=false&offset=N`
  returns a list of market dicts (paginated 100/page).
- Crypto daily markets exist, e.g. question `"Will the price of Ethereum be above $1,200
  on June 30?"`, slug `ethereum-above-1200-on-june-30-2026`, `endDate`
  `"2026-06-30T16:00:00Z"`, `outcomePrices` `["0.9995","0.0005"]` (YES,NO live prices),
  `clobTokenIds` a JSON **string** (double-parse, same as weather).
- A market is resolved when `GET /markets/<id>` returns `closed=true`; then
  `outcomePrices` is approximately `["1","0"]` (YES won) or `["0","1"]` (NO won).

## Hard rules (inherited)
- Pure stdlib (`urllib`, `json`, `os`, `datetime`, `csv` not needed). No third-party deps.
- ASCII-only prints. `git add` specific paths only (committer handles).
- Fake money only; this sensor reads public data, places nothing.
- Network functions MUST be injectable so tests run fully offline & deterministic.
- Reuse existing schema/store. Do not modify existing files except `institute/cli.py`
  and add `institute/resolve/__init__.py` content (it currently only marks the package).

## Modules
```
institute/sensor/crypto.py            # snapshot + settle (two-phase live sensor)
institute/resolve/crypto_adapter.py   # crypto store -> ResolvedMarket rows
institute/resolve/__init__.py         # add load_all_rows() aggregator
institute/tests/test_crypto_sensor.py
institute/tests/test_crypto_adapter.py
```
Plus extend `institute/cli.py`: commands `crypto-snapshot`, `crypto-settle`, and point
`map`/`pipeline`/`book` at the aggregated rows.

---

## 1. `sensor/crypto.py`

Store path: `CRYPTO_STORE = institute/data/crypto_markets.jsonl` (gitignored data dir).
Use `institute.corpus.store.append_jsonl / load_jsonl / overwrite_jsonl`.

A stored row (open):
```python
{"market_id": str, "archetype": "crypto-daily", "t0": iso8601Z,
 "q_yes": float, "question": str, "end_date": iso8601Z,
 "status": "open", "y": None, "settled_ts": None,
 "meta": {"slug": str, "symbol": "BTC"|"ETH"|"SOL"|"?", "yes_token": str}}
```

### Network helpers (thin, injectable)
- `_gamma_get(path, base="https://gamma-api.polymarket.com", timeout=20)`:
  urllib GET with `User-Agent: institute/1.0`, `Accept: application/json`; json return.
- `fetch_active_crypto(cutoff_hours=36, max_pages=20, _get=_gamma_get) -> list[dict]`:
  page `/markets?...active=true&closed=false&order=volume&ascending=false&offset=`.
  Keep a market iff:
  - `archetype.classify(question, slug) == "crypto-daily"` (reuse the classifier), AND
  - it is a daily/short-horizon market: `endDate` parses and is between now and
    now+cutoff_hours (skip the long-dated "by Dec 31 2026" markets), AND
  - `clobTokenIds` double-parses to >= 2 tokens, AND
  - `outcomePrices` parses (it is a JSON string too) to a 2-list of floats.
  Return normalized dicts: `{market_id, question, slug, end_date, q_yes=float(prices[0]),
  yes_token=tokens[0], symbol}` where `symbol` is derived from the question
  (BTC/bitcoin->"BTC", ETH/ethereum->"ETH", SOL/solana->"SOL", else "?").
  Wrap the whole loop in try/except per page; on network error break and return what we
  have (never raise to the caller).

### Phase 1 — snapshot
`snapshot(store_path=CRYPTO_STORE, fetch=fetch_active_crypto, now=None) -> list[dict]`:
- `now` defaults to `datetime.datetime.utcnow()` (match repo style).
- Load existing rows; build a set of already-open `market_id`s (dedupe: never snapshot
  the same market twice while still open).
- For each fetched market not already open: build an open row (above), append it.
- Return the newly-appended rows. Print nothing (CLI prints).

### Phase 2 — settle
`settle(store_path=CRYPTO_STORE, resolve=resolve_outcome, now=None) -> list[dict]`:
- Load rows. For each `status=="open"` row whose `end_date` is in the past (parse Z):
  call `resolve(row)` -> `y in {0,1}` or `None` (not yet resolved on venue).
  - If y is None: leave open.
  - Else set `y`, `status="settled"`, `settled_ts=now`.
- `overwrite_jsonl` with the updated list. Return the rows that were settled this call.

`resolve_outcome(row, _get=_gamma_get) -> int | None`:
- `m = _get(f"/markets/{row['market_id']}")`. If a list is returned, take `[0]`.
- If not `m.get("closed")`: return None (venue hasn't resolved yet).
- Parse `outcomePrices` (JSON string) -> [yp, np_]. `y = 1 if float(yp) >= 0.5 else 0`.
- On any error return None (stay open; try again next run).

---

## 2. `resolve/crypto_adapter.py`

Mirror `weather_adapter.load_rows` exactly in spirit:
`load_rows(store_path=sensor.crypto.CRYPTO_STORE) -> list[dict]`:
- Load the crypto store; keep `status=="settled"` rows with integer `y`.
- Emit `ResolvedMarket(market_id, archetype="crypto-daily", t0=row["t0"],
  q_yes=row["q_yes"], y=row["y"], realized_pnl=None, realized_side=None, stake=1.0,
  meta=row.get("meta", {})).dict()`.
- Empty store -> `[]` (no crash). No network here — pure read.

## 3. `resolve/__init__.py`

```python
"""Resolved-market aggregation across archetypes."""
from institute.resolve import weather_adapter, crypto_adapter

def load_all_rows():
    """All settled ResolvedMarket rows from every wired adapter (weather + crypto)."""
    return weather_adapter.load_rows() + crypto_adapter.load_rows()
```
(Keep the existing package marker behavior; just add this.)

## 4. CLI (`institute/cli.py`)

- Add `cmd_crypto_snapshot()`: call `sensor.crypto.snapshot()`, print
  `f"snapshotted {len(new)} live crypto markets -> {CRYPTO_STORE}"` (ASCII).
  If 0, print `"no new live crypto-daily markets found"`.
- Add `cmd_crypto_settle()`: call `sensor.crypto.settle()`, print
  `f"settled {len(done)} crypto markets"`.
- Point the analytics commands at the aggregate: in `cmd_map`, `cmd_pipeline`,
  `cmd_book`, load rows via `institute.resolve.load_all_rows()` and pass `rows=...`
  (predictability.build(rows), pipeline.run_all(rows=rows), book.build_book(rows=rows)).
  `cmd_status` should also report crypto store presence + settled count.
- Wire the two new `elif` branches and add both to the module docstring.

NOTE: `pipeline.run_all` filters cells to `baseline in BASELINES`; `longshot_fade` is
archetype-agnostic, so a crypto cell appears automatically once crypto rows exist. Do
NOT add a new baseline. `factor.CELL_FACTORS` already has `crypto-daily`.

---

## 5. Tests (offline, deterministic — NO real network)

**test_crypto_sensor.py**
- `fetch` injection: a fake fetch returning two normalized crypto dicts. Call
  `snapshot(store_path=temp, fetch=fake_fetch)` -> 2 new open rows; calling again with
  the same fetch -> 0 new (dedupe holds).
- `settle` injection: pre-write an open row with a past `end_date` to a temp store;
  `resolve` fake returns 1 -> `settle(store_path=temp, resolve=fake_resolve)` marks it
  settled with y==1; an open row with a FUTURE end_date is left open; a `resolve`
  returning None leaves the row open.
- `resolve_outcome`: feed an injected `_get` returning `{"closed": True,
  "outcomePrices": "[\"1\", \"0\"]"}` -> 1; `["0","1"]` -> 0; `{"closed": False}` -> None.
- `fetch_active_crypto`: feed an injected `_get` returning one page of raw Gamma dicts
  (one ETH daily within cutoff, one long-dated "by Dec 31" market, one non-crypto) ->
  only the ETH daily survives; q_yes == float(outcomePrices[0]); symbol == "ETH";
  second call page is empty list -> loop terminates.

**test_crypto_adapter.py**
- Write a temp crypto store with one settled + one open row; `load_rows(temp)` returns
  exactly the settled one as a ResolvedMarket dict with `archetype=="crypto-daily"`.
- Empty/missing store -> `[]`.

All tests use temp files (`tempfile.TemporaryDirectory`) and injected network fns.
Run `python -m pytest institute/tests -q` from repo root -> all green (83 prior + new).

## 6. Deviations
If the spec forces an unsound choice, fix it soundly with a one-line `# DEVIATION:`
comment and report it.
