"""Deterministic, network-free tests for fetch_prices_v2.py and pit_index.py.

Live HTTP is behind the injectable fetch_fn/sleep_fn seams (fetch_json / time.sleep by
default) -- every test below injects a fake instead, so nothing here ever touches the network.

Run:
    python -m pytest test_fetch_prices_v2.py -v
    (or)
    python -m unittest test_fetch_prices_v2 -v
"""
import io
import json
import os
import sys
import tempfile
import unittest
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_prices_v2 as fp2  # noqa: E402
import pit_index  # noqa: E402


def _http_error(url, code):
    return urllib.error.HTTPError(url, code, "err", {}, io.BytesIO(b""))


class TestSeriesTickerDerivation(unittest.TestCase):
    """(d) Kalshi series_ticker derivation: prefix before the first '-'."""

    def test_derivation(self):
        self.assertEqual(
            fp2.series_ticker_from("KXWCGOAL-26JUL03AUSEGY-EGYMSABER21-1"), "KXWCGOAL"
        )
        self.assertEqual(fp2.series_ticker_from("ABC-DEF-GHI"), "ABC")
        self.assertEqual(fp2.series_ticker_from("NOPREFIX"), "NOPREFIX")


class TestBackoff(unittest.TestCase):
    """(f) Backoff on 429 using a fake clock -- no real sleeps."""

    def test_retries_on_429_then_succeeds(self):
        calls = {"n": 0}
        sleeps = []

        def fake_fetch(url):
            calls["n"] += 1
            if calls["n"] < 3:
                raise _http_error(url, 429)
            return {"ok": True}

        def fake_sleep(secs):
            sleeps.append(secs)

        result = fp2.fetch_with_retry("http://x", fetch_fn=fake_fetch, sleep_fn=fake_sleep)
        self.assertEqual(result, {"ok": True})
        self.assertEqual(calls["n"], 3)
        self.assertEqual(len(sleeps), 2)  # two backoff sleeps before the 3rd call succeeds
        self.assertTrue(sleeps[1] > sleeps[0])  # exponential

    def test_gives_up_after_max_retries(self):
        def fake_fetch(url):
            raise _http_error(url, 503)

        with self.assertRaises(urllib.error.HTTPError):
            fp2.fetch_with_retry(
                "http://x", fetch_fn=fake_fetch, sleep_fn=lambda s: None, max_retries=2
            )

    def test_non_retryable_status_raises_immediately(self):
        calls = {"n": 0}

        def fake_fetch(url):
            calls["n"] += 1
            raise _http_error(url, 404)

        with self.assertRaises(urllib.error.HTTPError):
            fp2.fetch_with_retry("http://x", fetch_fn=fake_fetch, sleep_fn=lambda s: None)
        self.assertEqual(calls["n"], 1)  # no retries for 404


class TestLiveToHistoricalFallback(unittest.TestCase):
    """(e) fallback live -> historical on 404 or an empty candlesticks list."""

    def test_live_404_falls_back_to_historical(self):
        m = {"id": "KXFOO-25JAN01-BAR", "event_ticker": "KXFOO-25JAN01",
             "close_time": "2025-01-01T00:00:00Z"}
        seen = []

        def fake_fetch(url):
            seen.append(url)
            if "/historical/" not in url:
                raise _http_error(url, 404)
            return {"candlesticks": [{
                "end_period_ts": 1000,
                "price": {"close": 0.5},
                "yes_bid": {"close": 0.4},
                "yes_ask": {"close": 0.6},
                "volume": 10,
            }]}

        candles, used = fp2.fetch_kalshi_candles_for_market(m, 60, fake_fetch, lambda s: None)
        self.assertEqual(used, "historical")
        self.assertEqual(candles[0][0], 1000)   # ts
        self.assertEqual(candles[0][4], 0.5)    # close
        self.assertEqual(candles[0][5], 0.4)    # yes_bid close
        self.assertEqual(candles[0][6], 0.6)    # yes_ask close
        self.assertTrue(any("/historical/" in u for u in seen))
        self.assertTrue(any("/series/" in u for u in seen))

    def test_live_empty_falls_back_to_historical(self):
        m = {"id": "KXFOO-25JAN01-BAR", "event_ticker": "KXFOO-25JAN01",
             "close_time": "2025-01-01T00:00:00Z"}

        def fake_fetch(url):
            if "/historical/" not in url:
                return {"candlesticks": []}
            return {"candlesticks": [{"end_period_ts": 2000, "price": {"close": 0.7}}]}

        candles, used = fp2.fetch_kalshi_candles_for_market(m, 60, fake_fetch, lambda s: None)
        self.assertEqual(used, "historical")
        self.assertEqual(candles[0][0], 2000)

    def test_live_success_uses_live(self):
        m = {"id": "KXFOO-25JAN01-BAR", "event_ticker": "KXFOO-25JAN01",
             "close_time": "2025-01-01T00:00:00Z"}

        def fake_fetch(url):
            self.assertIn("/series/", url)
            return {"candlesticks": [{"end_period_ts": 500, "price": {"close": 0.3}}]}

        candles, used = fp2.fetch_kalshi_candles_for_market(m, 60, fake_fetch, lambda s: None)
        self.assertEqual(used, "live")
        self.assertEqual(candles[0][0], 500)


class TestKalshiIdempotencyAndAppendOnly(unittest.TestCase):
    """(b) idempotency: re-running produces no duplicate rows.
    (c) append-only: existing rows are never modified.
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.in_path = os.path.join(self.tmp, "kalshi_settled.jsonl")
        self.out_path = os.path.join(self.tmp, "prices", "kalshi_candles.jsonl")
        rows = [
            {"venue": "kalshi", "id": "KXA-1-M1", "event_ticker": "KXA-1",
             "close_time": "2025-01-02T00:00:00Z", "result": "yes", "category": "sports"},
            {"venue": "kalshi", "id": "KXB-1-M2", "event_ticker": "KXB-1",
             "close_time": "2025-01-03T00:00:00Z", "result": "no", "category": "econ"},
        ]
        with open(self.in_path, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")

    @staticmethod
    def _fake_fetch(url):
        return {"candlesticks": [{
            "end_period_ts": 1234,
            "price": {"close": 0.3},
            "yes_bid": {"close": 0.25},
            "yes_ask": {"close": 0.35},
            "volume": 5,
        }]}

    def test_idempotent_and_append_only(self):
        w1, err1 = fp2.fetch_kalshi(
            10, interval=60, fetch_fn=self._fake_fetch, sleep_fn=lambda s: None,
            in_path=self.in_path, out_path=self.out_path, call_sleep=0,
        )
        self.assertEqual(w1, 2)
        self.assertEqual(err1, 0)
        with open(self.out_path, encoding="utf-8") as f:
            lines_after_first = f.readlines()
        self.assertEqual(len(lines_after_first), 2)
        first_line_snapshot = lines_after_first[0]

        w2, err2 = fp2.fetch_kalshi(
            10, interval=60, fetch_fn=self._fake_fetch, sleep_fn=lambda s: None,
            in_path=self.in_path, out_path=self.out_path, call_sleep=0,
        )
        self.assertEqual(w2, 0)  # both markets already done -> nothing new
        with open(self.out_path, encoding="utf-8") as f:
            lines_after_second = f.readlines()
        self.assertEqual(len(lines_after_second), 2)              # no duplicate rows
        self.assertEqual(lines_after_second[0], first_line_snapshot)  # existing row unmodified

    def test_max_cap_respected(self):
        w, err = fp2.fetch_kalshi(
            1, interval=60, fetch_fn=self._fake_fetch, sleep_fn=lambda s: None,
            in_path=self.in_path, out_path=self.out_path, call_sleep=0,
        )
        self.assertEqual(w, 1)


class TestPitIndexNoLookAhead(unittest.TestCase):
    """(a) no-look-ahead property, including the exact-boundary ts == t exclusion case."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.kalshi_path = os.path.join(self.tmp, "kalshi_candles.jsonl")
        self.poly_path = os.path.join(self.tmp, "polymarket_trades.jsonl")
        with open(self.kalshi_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({
                "venue": "kalshi", "id": "KXA-1-M1", "event_ticker": "KXA-1",
                "period_interval": 60,
                "candles": [
                    [100, 0.1, 0.2, 0.05, 0.15, 0.10, 0.20, 3],
                    [200, 0.15, 0.25, 0.10, 0.20, 0.15, 0.25, 4],
                    [300, 0.20, 0.30, 0.15, 0.25, 0.20, 0.30, 5],
                ],
                "fetched_at": "2025-01-01T00:00:00Z",
            }) + "\n")
        with open(self.poly_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({
                "venue": "polymarket", "id": "PM1", "condition_id": "0xabc",
                "n_trades": 3,
                "points": [[150, 0.5, 10], [250, 0.55, 5], [350, 0.6, 8]],
                "fetched_at": "2025-01-01T00:00:00Z",
            }) + "\n")
        self.idx = pit_index.PitIndex(kalshi_path=self.kalshi_path, poly_path=self.poly_path)

    def test_no_look_ahead_kalshi_all_queried_ts(self):
        for t in [50, 100, 101, 150, 200, 201, 250, 300, 301, 999]:
            pt = self.idx.price_at("KXA-1-M1", t)
            if pt is not None:
                self.assertLess(pt.ts, t, f"look-ahead at t={t}: got ts={pt.ts}")

    def test_exact_boundary_excluded(self):
        # candle at ts=200 must NOT be visible when querying t=200 (strict <, not <=)
        pt = self.idx.price_at("KXA-1-M1", 200)
        self.assertIsNotNone(pt)
        self.assertEqual(pt.ts, 100)
        self.assertLess(pt.ts, 200)

        pt2 = self.idx.price_at("KXA-1-M1", 300)
        self.assertEqual(pt2.ts, 200)
        self.assertLess(pt2.ts, 300)

    def test_no_look_ahead_polymarket(self):
        pt = self.idx.price_at("PM1", 250)
        self.assertIsNotNone(pt)
        self.assertEqual(pt.ts, 150)
        self.assertLess(pt.ts, 250)
        # exact boundary: PM1's earliest point is ts=150, so querying t=150 must exclude it
        pt2 = self.idx.price_at("PM1", 150)
        self.assertIsNone(pt2)

    def test_before_first_point_returns_none(self):
        self.assertIsNone(self.idx.price_at("KXA-1-M1", 50))
        self.assertIsNone(self.idx.price_at("PM1", 100))

    def test_unknown_market_returns_none(self):
        self.assertIsNone(self.idx.price_at("NOPE", 10_000))

    def test_spread_at_strictly_before(self):
        sp = self.idx.spread_at("KXA-1-M1", 300)
        self.assertIsNotNone(sp)
        self.assertEqual(sp.ts, 200)
        self.assertEqual(sp.yes_bid, 0.15)
        self.assertEqual(sp.yes_ask, 0.25)
        self.assertLess(sp.ts, 300)

    def test_spread_at_polymarket_market_is_none(self):
        # Polymarket markets carry no bid/ask candles -> spread_at must return None, not raise.
        self.assertIsNone(self.idx.spread_at("PM1", 300))


class TestPolymarketIdempotencyAndDedup(unittest.TestCase):
    """(b/c) for the Polymarket path: dual dedup (id + condition_id) against a
    pre-existing shared store, idempotent re-runs, append-only writes."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.in_path = os.path.join(self.tmp, "polymarket_resolved.jsonl")
        self.out_path = os.path.join(self.tmp, "prices", "polymarket_trades.jsonl")
        rows = [
            {"venue": "polymarket", "id": "111", "condition_id": "0xaaa", "question": "A?",
             "outcomes": "[\"Yes\", \"No\"]", "outcome_prices": "[\"1\", \"0\"]"},
            {"venue": "polymarket", "id": "222", "condition_id": "0xbbb", "question": "B?",
             "outcomes": "[\"Yes\", \"No\"]", "outcome_prices": "[\"0\", \"1\"]"},
            # same condition_id as a pre-existing store row, different id -> must be skipped
            {"venue": "polymarket", "id": "333", "condition_id": "0xccc", "question": "C?",
             "outcomes": "[\"Yes\", \"No\"]", "outcome_prices": "[\"1\", \"0\"]"},
        ]
        with open(self.in_path, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        # Pre-existing shared store (as written by the ORIGINAL fetch_prices.py):
        os.makedirs(os.path.dirname(self.out_path), exist_ok=True)
        with open(self.out_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"venue": "polymarket", "id": "999",
                                "condition_id": "0xccc", "n_trades": 3,
                                "points": [[100, 0.5, 10.0]]}) + "\n")

    @staticmethod
    def _fake_fetch(url):
        # one page of two YES-side trades, then empty pages end pagination
        if "offset=0" in url:
            return [
                {"outcomeIndex": 0, "timestamp": 100, "price": "0.4", "size": "10"},
                {"outcomeIndex": 0, "timestamp": 200, "price": "0.5", "size": "20"},
            ]
        return []

    def test_dedup_idempotency_append_only(self):
        w1, thin1, err1 = fp2.fetch_polymarket(
            10, fetch_fn=self._fake_fetch, sleep_fn=lambda s: None,
            in_glob=self.in_path, out_path=self.out_path, call_sleep=0,
        )
        # 0xccc skipped via pre-existing condition_id; 111 + 222 written
        self.assertEqual(w1, 2)
        self.assertEqual(err1, 0)
        with open(self.out_path, encoding="utf-8") as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 3)  # 1 pre-existing + 2 new
        pre_existing_snapshot = lines[0]
        self.assertEqual(json.loads(pre_existing_snapshot)["id"], "999")  # untouched
        written_cids = {json.loads(l)["condition_id"] for l in lines[1:]}
        self.assertEqual(written_cids, {"0xaaa", "0xbbb"})

        # Second run: nothing new, nothing mutated.
        w2, _, _ = fp2.fetch_polymarket(
            10, fetch_fn=self._fake_fetch, sleep_fn=lambda s: None,
            in_glob=self.in_path, out_path=self.out_path, call_sleep=0,
        )
        self.assertEqual(w2, 0)
        with open(self.out_path, encoding="utf-8") as f:
            lines2 = f.readlines()
        self.assertEqual(len(lines2), 3)
        self.assertEqual(lines2[0], pre_existing_snapshot)


class TestManifestNonClobbering(unittest.TestCase):
    """update_manifest_kalshi_candles must add its section without touching others."""

    def test_existing_sections_preserved(self):
        tmp = tempfile.mkdtemp()
        manifest_path = os.path.join(tmp, "manifest.json")
        candles_path = os.path.join(tmp, "prices", "kalshi_candles.jsonl")
        os.makedirs(os.path.dirname(candles_path), exist_ok=True)
        with open(candles_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"venue": "kalshi", "id": "K1", "candles": []}) + "\n")
        existing = {
            "polymarket": {"total_rows": 2100, "file": "x"},
            "kalshi": {"total_rows": 153228, "file": "y"},
        }
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(existing, f)

        result = fp2.update_manifest_kalshi_candles(
            1, path=candles_path, manifest_path=manifest_path)

        on_disk = json.load(open(manifest_path, encoding="utf-8"))
        self.assertEqual(on_disk["polymarket"], existing["polymarket"])  # not clobbered
        self.assertEqual(on_disk["kalshi"], existing["kalshi"])          # not clobbered
        self.assertEqual(on_disk["kalshi_candles"]["total_rows"], 1)
        self.assertEqual(result["kalshi_candles"]["added_this_run"], 1)


class TestCandleShapeNormalization(unittest.TestCase):
    """Live API (2026-07-05) serves *_dollars string fields; older/numeric shape is
    integer CENTS under the bare key. Both must normalize to float dollars, and the
    unit is decided by TYPE, never magnitude (a 1-cent int must not become $1)."""

    def test_dollars_string_shape(self):
        row = fp2._flatten_candle({
            "end_period_ts": 1783112400,
            "price": {"close_dollars": "0.0100", "open_dollars": "0.9400",
                      "high_dollars": "0.9400", "low_dollars": "0.0100"},
            "yes_bid": {"close_dollars": "0.0000"},
            "yes_ask": {"close_dollars": "0.0100"},
            "volume_fp": "5580.50",
        })
        self.assertEqual(row[4], 0.01)   # close
        self.assertEqual(row[1], 0.94)   # open
        self.assertEqual(row[5], 0.0)    # yes_bid close
        self.assertEqual(row[6], 0.01)   # yes_ask close
        self.assertEqual(row[7], 5580.5)

    def test_integer_cents_shape(self):
        row = fp2._flatten_candle({
            "end_period_ts": 100,
            "price": {"close": 1, "open": 94},   # ints = cents
            "yes_bid": {"close": 34},
            "volume": 7,
        })
        self.assertEqual(row[4], 0.01)   # 1 cent, NOT $1 — the tail-corruption trap
        self.assertEqual(row[1], 0.94)
        self.assertEqual(row[5], 0.34)

    def test_float_dollars_shape(self):
        row = fp2._flatten_candle({"end_period_ts": 100, "price": {"close": 0.3}})
        self.assertEqual(row[4], 0.3)


class TestDoubleNotFoundIsNoData(unittest.TestCase):
    """404 on BOTH endpoints = permanent no-data, recorded (not a retryable error)."""

    def test_both_404_returns_empty_none(self):
        def fetch_404(url):
            raise _http_error(url, 404)
        m = {"id": "KXAGICO-COMP-27Q3", "close_time": "2026-01-01T00:00:00Z"}
        candles, src = fp2.fetch_kalshi_candles_for_market(
            m, 60, fetch_fn=fetch_404, sleep_fn=lambda s: None)
        self.assertEqual(candles, [])
        self.assertEqual(src, "none")

    def test_historical_500_still_raises(self):
        def fetch_mixed(url):
            raise _http_error(url, 404 if "/series/" in url else 500)
        m = {"id": "KXX-1-M1", "close_time": "2026-01-01T00:00:00Z"}
        with self.assertRaises(urllib.error.HTTPError):
            fp2.fetch_kalshi_candles_for_market(
                m, 60, fetch_fn=fetch_mixed, sleep_fn=lambda s: None)


class TestKalshiCategoryPriority(unittest.TestCase):
    """Priority categories (climate/weather/politics/etc.) are fetched before the rest,
    regardless of file order; null category goes to pass 2."""

    def test_priority_categories_fetched_first(self):
        tmp = tempfile.mkdtemp()
        in_path = os.path.join(tmp, "kalshi_settled.jsonl")
        out_path = os.path.join(tmp, "prices", "kalshi_candles.jsonl")
        rows = [
            {"id": "KXSPORTS-NULLCAT", "event_ticker": "KXSPORTS",
             "close_time": "2025-01-01T00:00:00Z", "category": None},
            {"id": "KXWEATHER-1", "event_ticker": "KXWEATHER",
             "close_time": "2025-01-01T00:00:00Z", "category": "Weather"},
            {"id": "KXSPORTS-2", "event_ticker": "KXSPORTS",
             "close_time": "2025-01-01T00:00:00Z", "category": "sports"},
            {"id": "KXPOLITICS-1", "event_ticker": "KXPOLITICS",
             "close_time": "2025-01-01T00:00:00Z", "category": "Politics"},
        ]
        with open(in_path, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")

        def fake_fetch(url):
            return {"candlesticks": [{"end_period_ts": 1, "price": {"close": 0.5}}]}

        w, err = fp2.fetch_kalshi(
            2, interval=60, fetch_fn=fake_fetch, sleep_fn=lambda s: None,
            in_path=in_path, out_path=out_path, call_sleep=0,
        )
        self.assertEqual(w, 2)
        self.assertEqual(err, 0)
        with open(out_path, encoding="utf-8") as f:
            fetched_ids = {json.loads(line)["id"] for line in f}
        self.assertEqual(fetched_ids, {"KXWEATHER-1", "KXPOLITICS-1"})


class TestPolymarketVolumeOrdering(unittest.TestCase):
    """Candidates are fetched highest-volume-first, not in file order."""

    def test_fetch_order_by_volume_desc(self):
        tmp = tempfile.mkdtemp()
        in_path = os.path.join(tmp, "polymarket_resolved.jsonl")
        out_path = os.path.join(tmp, "prices", "polymarket_trades.jsonl")
        rows = [
            {"id": "111", "condition_id": "0xlow", "question": "low?", "volume": "5"},
            {"id": "222", "condition_id": "0xhigh", "question": "high?", "volume": "500"},
            {"id": "333", "condition_id": "0xmid", "question": "mid?", "volume": "50"},
        ]
        with open(in_path, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")

        fetch_order = []

        def fake_fetch(url):
            # record which condition is being fetched, then end pagination immediately
            for cid in ("0xhigh", "0xmid", "0xlow"):
                if f"market={cid}" in url:
                    if "offset=0" in url:
                        fetch_order.append(cid)
                    return []
            return []

        w, thin, err = fp2.fetch_polymarket(
            10, fetch_fn=fake_fetch, sleep_fn=lambda s: None,
            in_glob=in_path, out_path=out_path, call_sleep=0,
        )
        self.assertEqual(w, 3)
        self.assertEqual(err, 0)
        self.assertEqual(fetch_order, ["0xhigh", "0xmid", "0xlow"])


class TestHardeningGuards(unittest.TestCase):
    """The two verifier-flagged latent traps must now fail loudly, not guess."""

    def test_candle_without_end_period_ts_raises(self):
        # A period-START ts would leak up to one period of look-ahead; refuse to guess.
        with self.assertRaises(ValueError):
            fp2._flatten_candle({"ts": 1234, "price": {"close": 0.3}})

    def test_unparseable_close_time_market_is_counted_as_error_not_written(self):
        tmp = tempfile.mkdtemp()
        in_path = os.path.join(tmp, "kalshi_settled.jsonl")
        out_path = os.path.join(tmp, "prices", "kalshi_candles.jsonl")
        with open(in_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"venue": "kalshi", "id": "KXBAD-1-M1",
                                "event_ticker": "KXBAD-1",
                                "close_time": "not-a-date", "result": "yes"}) + "\n")
        w, err = fp2.fetch_kalshi(
            10, interval=60, fetch_fn=lambda url: {"candlesticks": []},
            sleep_fn=lambda s: None, in_path=in_path, out_path=out_path, call_sleep=0,
        )
        self.assertEqual(w, 0)
        self.assertEqual(err, 1)
        # nothing written -> the market is retried on the next run (done-set rebuilds from output)
        self.assertFalse(os.path.exists(out_path) and open(out_path).read().strip())


if __name__ == "__main__":
    unittest.main()
