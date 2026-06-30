"""Tests for institute.alpha.forecast_store — offline, deterministic, no network (A6).

Point-in-time honesty invariants verified here:
  - Only open rows without p_final get forecast.
  - Settled rows are never touched.
  - Second call forecasts 0 new rows (idempotent).
  - max_forecasts cap is respected.
  - y is never read or modified.
"""
import os
import json
import tempfile

from institute.alpha.forecast_store import forecast_open
from institute.corpus.store import load_jsonl, overwrite_jsonl


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


def _settled_row(market_id, q_yes=0.3, y=0):
    return {
        "market_id": market_id,
        "question": f"Will {market_id} resolve YES?",
        "q_yes": q_yes,
        "status": "settled",
        "y": y,
        "meta": {},
    }


def _write_store(path, rows):
    overwrite_jsonl(path, rows)


def _fake_forecaster(row, mock=True):
    """Deterministic fake forecaster; never reads y."""
    q = row["q_yes"]
    return {
        "p_model": q + 0.05,
        "p_std": 0.02,
        "p_final": q + 0.03,
        "n_agents": 5,
        "w": 0.70,
    }


# ── tests ─────────────────────────────────────────────────────────────────────

def test_forecast_open_writes_to_open_rows_only():
    """forecast_open writes p_final to the 2 open rows; leaves settled untouched."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w") as f:
        path = f.name
    try:
        rows = [_open_row("m1"), _open_row("m2"), _settled_row("m3")]
        _write_store(path, rows)

        newly = forecast_open(path, fetch_forecaster=_fake_forecaster, mock=True)
        assert len(newly) == 2

        updated = load_jsonl(path)
        open_rows = [r for r in updated if r["status"] == "open"]
        settled_rows = [r for r in updated if r["status"] == "settled"]

        # All open rows should have p_final now
        for r in open_rows:
            assert r["meta"].get("p_final") is not None, f"Missing p_final on {r['market_id']}"

        # Settled row unchanged
        assert len(settled_rows) == 1
        assert settled_rows[0]["market_id"] == "m3"
        assert settled_rows[0]["meta"].get("p_final") is None
    finally:
        os.unlink(path)


def test_forecast_open_idempotent():
    """Second call forecasts 0 new rows (idempotent)."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w") as f:
        path = f.name
    try:
        rows = [_open_row("m1"), _open_row("m2")]
        _write_store(path, rows)

        first = forecast_open(path, fetch_forecaster=_fake_forecaster, mock=True)
        assert len(first) == 2

        second = forecast_open(path, fetch_forecaster=_fake_forecaster, mock=True)
        assert len(second) == 0, f"Expected 0 on second call, got {len(second)}"
    finally:
        os.unlink(path)


def test_forecast_open_max_forecasts_respected():
    """max_forecasts=1 means exactly 1 row is forecast."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w") as f:
        path = f.name
    try:
        rows = [_open_row("m1"), _open_row("m2"), _open_row("m3")]
        _write_store(path, rows)

        newly = forecast_open(
            path, fetch_forecaster=_fake_forecaster, max_forecasts=1, mock=True
        )
        assert len(newly) == 1

        # Second call with cap=1 should get 1 more
        newly2 = forecast_open(
            path, fetch_forecaster=_fake_forecaster, max_forecasts=1, mock=True
        )
        assert len(newly2) == 1
    finally:
        os.unlink(path)


def test_forecast_open_does_not_modify_y():
    """y must never be changed (point-in-time honesty)."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w") as f:
        path = f.name
    try:
        rows = [_open_row("m1"), _settled_row("m2", y=1)]
        _write_store(path, rows)

        forecast_open(path, fetch_forecaster=_fake_forecaster, mock=True)

        updated = load_jsonl(path)
        for r in updated:
            if r["market_id"] == "m1":
                assert r["y"] is None, "y changed on open row"
            elif r["market_id"] == "m2":
                assert r["y"] == 1, "y changed on settled row"
    finally:
        os.unlink(path)


def test_forecast_open_missing_store_returns_empty():
    """Missing store file returns empty list without error."""
    result = forecast_open(
        "/tmp/nonexistent_store_xyz.jsonl",
        fetch_forecaster=_fake_forecaster,
        mock=True,
    )
    assert result == []


def test_forecast_open_stores_forecast_fields():
    """Verify all expected meta fields are written."""
    with tempfile.NamedTemporaryFile(suffix=".jsonl", delete=False, mode="w") as f:
        path = f.name
    try:
        rows = [_open_row("m1")]
        _write_store(path, rows)

        forecast_open(path, fetch_forecaster=_fake_forecaster, mock=True)
        updated = load_jsonl(path)

        row = updated[0]
        meta = row["meta"]
        for field in ("p_model", "p_std", "p_final", "n_agents", "forecast_ts"):
            assert field in meta, f"Missing meta field: {field}"
        assert 0 < meta["p_final"] < 1
    finally:
        os.unlink(path)
