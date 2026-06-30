"""Tests for institute.cadence — offline, deterministic, no network (A6).

Verifies:
  - run_cycle(mock=True) returns a dict with forecast counts and a book.
  - book.render() output is .isascii() (Windows cp1252 safe).
  - Forecast counts match what was in the temp store.
  - Works correctly with an empty store and a non-existent store.
"""
import os
import tempfile

from institute.cadence import run_cycle
from institute.corpus.store import overwrite_jsonl
from institute.portfolio.book import render


# ── helpers ───────────────────────────────────────────────────────────────────

def _open_row(market_id, q_yes=0.4):
    return {
        "market_id": market_id,
        "question": f"Will {market_id} resolve YES?",
        "q_yes": q_yes,
        "status": "open",
        "y": None,
        "meta": {},
    }


def _write_store(path, rows):
    overwrite_jsonl(path, rows)


# ── tests ─────────────────────────────────────────────────────────────────────

def test_run_cycle_returns_expected_structure():
    """run_cycle returns dict with 'forecast' and 'book' keys."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w") as f:
        path = f.name
    try:
        rows = [_open_row("m1"), _open_row("m2")]
        _write_store(path, rows)

        stores = {"crypto": path}
        out = run_cycle(stores=stores, mock=True)

        assert "forecast" in out
        assert "book" in out
        assert isinstance(out["forecast"], dict)
        assert "crypto" in out["forecast"]
    finally:
        os.unlink(path)


def test_run_cycle_forecast_count_matches_open_rows():
    """Forecast count should equal the number of open unforecast rows."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w") as f:
        path = f.name
    try:
        rows = [_open_row("m1"), _open_row("m2"), _open_row("m3")]
        _write_store(path, rows)

        stores = {"crypto": path}
        out = run_cycle(stores=stores, mock=True)

        assert out["forecast"]["crypto"] == 3
    finally:
        os.unlink(path)


def test_run_cycle_book_render_is_ascii():
    """book.render() output must be ASCII-only (Windows cp1252 safety)."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w") as f:
        path = f.name
    try:
        rows = [_open_row("m1")]
        _write_store(path, rows)

        stores = {"crypto": path}
        out = run_cycle(stores=stores, mock=True)

        rendered = render(out["book"])
        assert rendered.isascii(), "render() produced non-ASCII output"
    finally:
        os.unlink(path)


def test_run_cycle_empty_store():
    """Empty store -> forecast count 0, still returns a valid book."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w") as f:
        path = f.name
    try:
        _write_store(path, [])

        stores = {"crypto": path}
        out = run_cycle(stores=stores, mock=True)

        assert out["forecast"]["crypto"] == 0
        assert "allocation" in out["book"]
    finally:
        os.unlink(path)


def test_run_cycle_missing_store():
    """Missing store file -> forecast count 0, no crash."""
    stores = {"crypto": "/tmp/nonexistent_store_cadence_test.jsonl"}
    out = run_cycle(stores=stores, mock=True)

    assert out["forecast"]["crypto"] == 0
    assert "book" in out


def test_run_cycle_idempotent():
    """Second call on same store forecasts 0 new rows."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w") as f:
        path = f.name
    try:
        rows = [_open_row("m1"), _open_row("m2")]
        _write_store(path, rows)

        stores = {"crypto": path}
        first = run_cycle(stores=stores, mock=True)
        second = run_cycle(stores=stores, mock=True)

        assert first["forecast"]["crypto"] == 2
        assert second["forecast"]["crypto"] == 0
    finally:
        os.unlink(path)
