"""Tests for institute/verticals/cpi/sensor.py (B1).

Offline and deterministic -- inject all fetchers/fixtures.
POINT-IN-TIME HONESTY: y is never read at snapshot. All assertions verify this.
"""
import datetime
import os
import tempfile

from institute.corpus.store import overwrite_jsonl, load_jsonl
from institute.verticals.cpi.sensor import snapshot, settle


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _fake_fetch_two():
    """Two parseable CPI markets (injected; no network)."""
    return [
        {
            "market_id": "cpi-001",
            "question": "Will monthly inflation increase by 0.3% in June 2026?",
            "slug": "cpi-0-3-june-2026",
            "end_date": "2026-07-15T00:00:00Z",
            "q_yes": 0.35,
            "indicator": "us_cpi_mom",
            "period": "2026-06",
            "lo": 0.25,
            "hi": 0.35,
        },
        {
            "market_id": "cpi-002",
            "question": "Will monthly inflation increase by 0.2% in June 2026?",
            "slug": "cpi-0-2-june-2026",
            "end_date": "2026-07-15T00:00:00Z",
            "q_yes": 0.30,
            "indicator": "us_cpi_mom",
            "period": "2026-06",
            "lo": 0.15,
            "hi": 0.25,
        },
    ]


def _fake_distribution(period):
    """Deterministic fake distribution (no network)."""
    return {"mu": 0.30, "sigma": 0.10, "weights": {"m1": 1.0}, "n_train": 36}


_FIXED_NOW = datetime.datetime(2026, 6, 30, 12, 0, 0)


# ---------------------------------------------------------------------------
# snapshot tests
# ---------------------------------------------------------------------------

def test_snapshot_writes_two_open_rows():
    """First snapshot with fake fetch -> 2 new open rows."""
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "cpi_markets.jsonl")
        new = snapshot(
            store_path=store,
            fetch=_fake_fetch_two,
            distribution=_fake_distribution,
            now=_FIXED_NOW,
        )
        assert len(new) == 2
        for row in new:
            assert row["status"] == "open"
            assert row["y"] is None
            assert row["archetype"] == "econ-cpi"


def test_snapshot_freezes_p_model():
    """p_model must be frozen in meta at snapshot time."""
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "cpi_markets.jsonl")
        new = snapshot(
            store_path=store,
            fetch=_fake_fetch_two,
            distribution=_fake_distribution,
            now=_FIXED_NOW,
        )
        for row in new:
            assert "p_model" in row["meta"], "p_model must be frozen in meta"
            p = row["meta"]["p_model"]
            assert 0.0 < p < 1.0, f"p_model={p} out of (0,1)"


def test_snapshot_idempotent():
    """Second snapshot with same fetch -> 0 new (already open)."""
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "cpi_markets.jsonl")
        first = snapshot(
            store_path=store,
            fetch=_fake_fetch_two,
            distribution=_fake_distribution,
            now=_FIXED_NOW,
        )
        assert len(first) == 2

        second = snapshot(
            store_path=store,
            fetch=_fake_fetch_two,
            distribution=_fake_distribution,
            now=_FIXED_NOW,
        )
        assert len(second) == 0, "idempotent: no new rows on re-run"


def test_snapshot_y_never_set_at_snapshot_time():
    """y must be None in every newly-snapshotted row (point-in-time honesty)."""
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "cpi_markets.jsonl")
        new = snapshot(
            store_path=store,
            fetch=_fake_fetch_two,
            distribution=_fake_distribution,
            now=_FIXED_NOW,
        )
        for row in new:
            assert row["y"] is None, "y MUST be None at snapshot (honesty law)"


def test_snapshot_meta_has_required_fields():
    """Meta must carry indicator, period, lo, hi, mu, sigma, p_model, forecast_ts."""
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "cpi_markets.jsonl")
        new = snapshot(
            store_path=store,
            fetch=_fake_fetch_two,
            distribution=_fake_distribution,
            now=_FIXED_NOW,
        )
        required = {"indicator", "period", "lo", "hi", "mu", "sigma",
                    "p_model", "forecast_ts"}
        for row in new:
            missing = required - set(row["meta"].keys())
            assert not missing, f"meta missing keys: {missing}"


def test_snapshot_period_cached_one_distribution_call():
    """Both markets share the same period -> distribution called only once."""
    call_count = [0]

    def counting_distribution(period):
        call_count[0] += 1
        return _fake_distribution(period)

    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "cpi_markets.jsonl")
        snapshot(
            store_path=store,
            fetch=_fake_fetch_two,
            distribution=counting_distribution,
            now=_FIXED_NOW,
        )
        assert call_count[0] == 1, "distribution should be called once per period"


def test_snapshot_persists_to_disk():
    """Rows written to disk are loadable and match in-memory result."""
    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "cpi_markets.jsonl")
        new = snapshot(
            store_path=store,
            fetch=_fake_fetch_two,
            distribution=_fake_distribution,
            now=_FIXED_NOW,
        )
        loaded = load_jsonl(store)
        assert len(loaded) == len(new)
        assert {r["market_id"] for r in loaded} == {r["market_id"] for r in new}


# ---------------------------------------------------------------------------
# settle tests
# ---------------------------------------------------------------------------

def _make_open_row(market_id, end_date, q_yes=0.35, lo=0.25, hi=0.35):
    """Build a minimal open CPI row."""
    return {
        "market_id": market_id,
        "archetype": "econ-cpi",
        "t0": "2026-06-30T00:00:00Z",
        "q_yes": q_yes,
        "question": "Will monthly inflation increase by 0.3% in June 2026?",
        "end_date": end_date,
        "status": "open",
        "y": None,
        "settled_ts": None,
        "meta": {
            "indicator": "us_cpi_mom",
            "period": "2026-06",
            "lo": lo,
            "hi": hi,
            "mu": 0.30,
            "sigma": 0.10,
            "p_model": 0.42,
            "forecast_ts": "2026-06-30T12:00:00Z",
            "slug": "cpi-0-3-june-2026",
        },
    }


def test_settle_past_row_with_resolve_1():
    """Open row past end_date with resolve->1 -> settled y==1."""
    past = "2026-07-14T00:00:00Z"
    row = _make_open_row("s001", past)

    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "cpi_markets.jsonl")
        overwrite_jsonl(store, [row])

        def fake_resolve(r):
            return 1

        now = datetime.datetime(2026, 7, 15, 12, 0, 0)
        done = settle(store_path=store, resolve=fake_resolve, now=now)

        assert len(done) == 1
        assert done[0]["y"] == 1
        assert done[0]["status"] == "settled"
        assert done[0]["settled_ts"] is not None

        # Verify persisted to disk
        loaded = load_jsonl(store)
        assert loaded[0]["status"] == "settled"
        assert loaded[0]["y"] == 1


def test_settle_future_row_stays_open():
    """Open row with FUTURE end_date is NOT touched."""
    future = "2026-08-01T00:00:00Z"
    row = _make_open_row("s002", future)

    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "cpi_markets.jsonl")
        overwrite_jsonl(store, [row])

        def fake_resolve(r):
            return 1  # should never be called

        now = datetime.datetime(2026, 7, 15, 12, 0, 0)
        done = settle(store_path=store, resolve=fake_resolve, now=now)

        assert len(done) == 0
        loaded = load_jsonl(store)
        assert loaded[0]["status"] == "open"


def test_settle_resolve_none_stays_open():
    """resolve() returning None (BLS not published) -> row stays open."""
    past = "2026-07-14T00:00:00Z"
    row = _make_open_row("s003", past)

    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "cpi_markets.jsonl")
        overwrite_jsonl(store, [row])

        def fake_resolve_none(r):
            return None

        now = datetime.datetime(2026, 7, 15, 12, 0, 0)
        done = settle(store_path=store, resolve=fake_resolve_none, now=now)

        assert len(done) == 0
        loaded = load_jsonl(store)
        assert loaded[0]["status"] == "open"


def test_settle_resolve_zero_settles_correctly():
    """resolve()->0 settles y==0 (bucket miss)."""
    past = "2026-07-14T00:00:00Z"
    row = _make_open_row("s004", past)

    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "cpi_markets.jsonl")
        overwrite_jsonl(store, [row])

        def fake_resolve(r):
            return 0

        now = datetime.datetime(2026, 7, 15, 12, 0, 0)
        done = settle(store_path=store, resolve=fake_resolve, now=now)

        assert len(done) == 1
        assert done[0]["y"] == 0


def test_settle_preserves_frozen_p_model():
    """Settling must not overwrite or clear the frozen p_model in meta."""
    past = "2026-07-14T00:00:00Z"
    row = _make_open_row("s005", past)
    original_p_model = row["meta"]["p_model"]

    with tempfile.TemporaryDirectory() as d:
        store = os.path.join(d, "cpi_markets.jsonl")
        overwrite_jsonl(store, [row])

        def fake_resolve(r):
            return 1

        now = datetime.datetime(2026, 7, 15, 12, 0, 0)
        done = settle(store_path=store, resolve=fake_resolve, now=now)

        assert done[0]["meta"]["p_model"] == original_p_model, \
            "settle must not modify the frozen p_model"
