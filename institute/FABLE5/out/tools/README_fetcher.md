# fetch_prices_v2 + pit_index

## Usage
```
python fetch_prices_v2.py --venue all --max 2000            # kalshi candles + poly trades
python fetch_prices_v2.py --venue kalshi --max 500 --interval 60
python fetch_prices_v2.py --venue polymarket --max 2000
python fetch_prices_v2.py --probe                            # read-only coverage probe
```
`--sleep` sets seconds between HTTP calls (default 0.2s). Kalshi 429/5xx get exponential
backoff, up to 5 retries. `--probe` writes nothing but the printed report.

## Storage layout
- `institute/data/history/prices/kalshi_candles.jsonl` — one row per Kalshi market:
  `{venue, id, event_ticker, period_interval, candles:[[ts,open,high,low,close,yes_bid_close,
  yes_ask_close,volume],...], source_endpoint, fetched_at}`.
- `institute/data/history/prices/polymarket_trades.jsonl` — same schema as the existing
  `fetch_prices.py`; this tool appends to the SAME file and shares its dedup convention.
- `institute/data/history/manifest.json` — gains a `kalshi_candles` section (same shape as
  the other venue entries fetch_history.py writes).

## Honesty invariants and their tests
1. **No look-ahead**: `pit_index.price_at(id, t)` returns the last point with `ts < t` (strict;
   `ts == t` is excluded). Asserted by `TestPitIndexNoLookAhead.test_no_look_ahead_kalshi_all_queried_ts`,
   `.test_exact_boundary_excluded`, `.test_no_look_ahead_polymarket`.
2. **Idempotency**: running the fetch loop twice over identical fake data adds zero rows the
   second time. Asserted by `TestKalshiIdempotencyAndAppendOnly.test_idempotent_and_append_only`.
3. **Append-only**: previously written rows are byte-identical after a second run.
   Asserted by the same test (`lines_after_second[0] == first_line_snapshot`).
4. **series_ticker derivation** (prefix before first `-`): `TestSeriesTickerDerivation.test_derivation`.
5. **live -> historical fallback** on 404 or empty `candlesticks`:
   `TestLiveToHistoricalFallback.test_live_404_falls_back_to_historical`,
   `.test_live_empty_falls_back_to_historical`, `.test_live_success_uses_live`.
6. **Backoff on 429** with no real sleeps (fake clock records calls): `TestBackoff.test_retries_on_429_then_succeeds`,
   `.test_gives_up_after_max_retries`, `.test_non_retryable_status_raises_immediately` (404 is not retried).

## Running tests
```
python -m pytest test_fetch_prices_v2.py -v
python -m unittest test_fetch_prices_v2 -v
```
16/16 pass offline, no network access required (fetch_json is only ever called through the
injectable `fetch_fn`/`sleep_fn` seam in tests).
