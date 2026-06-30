"""Tests for institute/resolve/cpi_adapter.py (B1).

Offline and deterministic -- no network.
"""
import os
import tempfile

from institute.corpus.store import overwrite_jsonl
from institute.resolve.cpi_adapter import load_rows


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _settled_row(market_id, y=1, q_yes=0.35, p_model=0.42):
    return {
        "market_id": market_id,
        "archetype": "econ-cpi",
        "t0": "2026-06-30T00:00:00Z",
        "q_yes": q_yes,
        "question": "Will monthly inflation increase by 0.3% in June 2026?",
        "end_date": "2026-07-15T00:00:00Z",
        "status": "settled",
        "y": y,
        "settled_ts": "2026-07-15T12:00:00Z",
        "meta": {
            "indicator": "us_cpi_mom",
            "period": "2026-06",
            "lo": 0.25,
            "hi": 0.35,
            "mu": 0.30,
            "sigma": 0.10,
            "p_model": p_model,
            "forecast_ts": "2026-06-30T12:00:00Z",
            "slug": "cpi-0-3-june-2026",
        },
    }


def _open_row(market_id, q_yes=0.30):
    return {
        "market_id": market_id,
        "archetype": "econ-cpi",
        "t0": "2026-06-30T00:00:00Z",
        "q_yes": q_yes,
        "question": "Will monthly inflation increase by 0.2% in July 2026?",
        "end_date": "2026-08-15T00:00:00Z",
        "status": "open",
        "y": None,
        "settled_ts": None,
        "meta": {
            "indicator": "us_cpi_mom",
            "period": "2026-07",
            "lo": 0.15,
            "hi": 0.25,
            "mu": 0.28,
            "sigma": 0.10,
            "p_model": 0.38,
            "forecast_ts": "2026-06-30T12:00:00Z",
            "slug": "cpi-0-2-july-2026",
        },
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_load_rows_returns_only_settled():
    """Settled + open -> only the settled row returned."""
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "cpi_markets.jsonl")
        overwrite_jsonl(store, [_settled_row("c001"), _open_row("c002")])

        rows = load_rows(store_path=store)

        assert len(rows) == 1
        assert rows[0]["market_id"] == "c001"


def test_load_rows_archetype_is_econ_cpi():
    """Returned rows must have archetype=='econ-cpi'."""
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "cpi_markets.jsonl")
        overwrite_jsonl(store, [_settled_row("c010")])

        rows = load_rows(store_path=store)
        assert rows[0]["archetype"] == "econ-cpi"


def test_load_rows_p_model_in_meta():
    """p_model must be preserved in meta (point-in-time honest)."""
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "cpi_markets.jsonl")
        overwrite_jsonl(store, [_settled_row("c011", p_model=0.42)])

        rows = load_rows(store_path=store)
        assert "p_model" in rows[0]["meta"]
        assert rows[0]["meta"]["p_model"] == 0.42


def test_load_rows_resolved_market_shape():
    """Row has all ResolvedMarket fields."""
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "cpi_markets.jsonl")
        overwrite_jsonl(store, [_settled_row("c012", y=0, q_yes=0.30)])

        rows = load_rows(store_path=store)
        row = rows[0]

        for field in ("market_id", "archetype", "t0", "q_yes", "y",
                      "realized_pnl", "realized_side", "stake", "meta"):
            assert field in row, f"missing field: {field}"

        assert row["y"] == 0
        assert row["realized_pnl"] is None
        assert row["realized_side"] is None
        assert row["stake"] == 1.0


def test_load_rows_empty_store():
    """Empty store -> [] (no crash)."""
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "cpi_markets.jsonl")
        overwrite_jsonl(store, [])
        assert load_rows(store_path=store) == []


def test_load_rows_missing_store():
    """Non-existent store -> [] (no crash)."""
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "does_not_exist.jsonl")
        assert load_rows(store_path=store) == []


def test_load_rows_skips_non_integer_y():
    """y=None with status='settled' is skipped (malformed row)."""
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "cpi_markets.jsonl")
        bad = _settled_row("c099")
        bad["y"] = None
        overwrite_jsonl(store, [bad])
        assert load_rows(store_path=store) == []


def test_load_rows_multiple_settled():
    """Multiple settled rows all returned."""
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "cpi_markets.jsonl")
        overwrite_jsonl(store, [
            _settled_row("c020", y=1),
            _settled_row("c021", y=0),
            _settled_row("c022", y=1),
        ])
        rows = load_rows(store_path=store)
        assert len(rows) == 3
        ids = {r["market_id"] for r in rows}
        assert ids == {"c020", "c021", "c022"}
