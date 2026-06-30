"""Tests for institute/resolve/crypto_adapter.py (A5).

All tests are offline and deterministic -- no network calls.
"""
import os
import tempfile

from institute.corpus.store import overwrite_jsonl
from institute.resolve.crypto_adapter import load_rows


def _settled_row(market_id, y=1, q_yes=0.9):
    return {
        "market_id": market_id,
        "archetype": "crypto-daily",
        "t0": "2026-06-30T00:00:00Z",
        "q_yes": q_yes,
        "question": "Will ETH be above $1200?",
        "end_date": "2026-06-30T16:00:00Z",
        "status": "settled",
        "y": y,
        "settled_ts": "2026-06-30T17:00:00Z",
        "meta": {"slug": "eth-1200", "symbol": "ETH", "yes_token": "tok-yes"},
    }


def _open_row(market_id, q_yes=0.6):
    return {
        "market_id": market_id,
        "archetype": "crypto-daily",
        "t0": "2026-06-30T00:00:00Z",
        "q_yes": q_yes,
        "question": "Will BTC be above $60k?",
        "end_date": "2026-07-01T16:00:00Z",
        "status": "open",
        "y": None,
        "settled_ts": None,
        "meta": {"slug": "btc-60k", "symbol": "BTC", "yes_token": "tok-yes-btc"},
    }


def test_load_rows_returns_only_settled():
    """One settled + one open row -> only the settled row is returned."""
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "crypto_markets.jsonl")
        overwrite_jsonl(store, [_settled_row("m001"), _open_row("m002")])

        rows = load_rows(store_path=store)

        assert len(rows) == 1
        assert rows[0]["market_id"] == "m001"
        assert rows[0]["archetype"] == "crypto-daily"
        assert rows[0]["y"] == 1
        assert rows[0]["q_yes"] == 0.9


def test_load_rows_resolved_market_shape():
    """Emitted row has ResolvedMarket dict shape with expected fields."""
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "crypto_markets.jsonl")
        overwrite_jsonl(store, [_settled_row("m010", y=0, q_yes=0.05)])

        rows = load_rows(store_path=store)
        assert len(rows) == 1
        row = rows[0]

        # ResolvedMarket fields
        assert "market_id" in row
        assert "archetype" in row
        assert "t0" in row
        assert "q_yes" in row
        assert "y" in row
        assert "realized_pnl" in row
        assert "realized_side" in row
        assert "stake" in row
        assert "meta" in row

        assert row["archetype"] == "crypto-daily"
        assert row["y"] == 0
        assert row["realized_pnl"] is None
        assert row["realized_side"] is None
        assert row["stake"] == 1.0


def test_load_rows_empty_store():
    """Empty store -> [] (no crash)."""
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "crypto_markets.jsonl")
        overwrite_jsonl(store, [])
        rows = load_rows(store_path=store)
        assert rows == []


def test_load_rows_missing_store():
    """Non-existent store -> [] (no crash)."""
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "does_not_exist.jsonl")
        rows = load_rows(store_path=store)
        assert rows == []


def test_load_rows_skips_non_integer_y():
    """Row with y=None (still open-ish) is skipped even if status is settled."""
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "crypto_markets.jsonl")
        bad_row = _settled_row("m099")
        bad_row["y"] = None  # malformed settled row
        overwrite_jsonl(store, [bad_row])

        rows = load_rows(store_path=store)
        assert rows == []


def test_load_rows_meta_preserved():
    """meta dict from the store is passed through to the ResolvedMarket."""
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "crypto_markets.jsonl")
        overwrite_jsonl(store, [_settled_row("m003")])

        rows = load_rows(store_path=store)
        assert rows[0]["meta"]["symbol"] == "ETH"
        assert rows[0]["meta"]["slug"] == "eth-1200"
