"""
Disk-backed observed-high cache tests.

Verifies:
  1. A past date fetched via two separate _make_actual_cache() instances hits the
     network only once (second instance loads from disk).
  2. Today's date is NOT written to the disk file even after a successful fetch
     (but is still returned correctly in-memory).

Run from papertrader/:
    python -m pytest tests/test_observed_cache.py -q
"""
import json
import os
from datetime import datetime, timezone

import lib.backtest as backtest
import lib.settlement as settlement


PAST_DATE = "2020-01-01"
CITY_CFG = {"name": "TestCity", "wunderground_station": "FAKE"}
FAKE_HIGH = 85.0


def test_past_date_disk_cache(monkeypatch, tmp_path):
    """Second _make_actual_cache() instance loads the past date from disk — no second fetch."""
    call_count = {"n": 0}

    def fake_fetch(city_cfg, date_str):
        call_count["n"] += 1
        return (FAKE_HIGH, "fake", 0.0)

    monkeypatch.setattr(settlement, "fetch_observed_high", fake_fetch)
    monkeypatch.setattr(backtest, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(backtest, "_OBSERVED_CACHE_FILE",
                        os.path.join(str(tmp_path), "observed_highs_cache.json"))

    # First cache instance — fetches from network
    get1 = backtest._make_actual_cache()
    result1 = get1(CITY_CFG, PAST_DATE)
    assert result1 == FAKE_HIGH, f"Expected {FAKE_HIGH}, got {result1}"
    assert call_count["n"] == 1, "Should have fetched once"

    # Disk file must exist now
    cache_file = os.path.join(str(tmp_path), "observed_highs_cache.json")
    assert os.path.exists(cache_file), "Cache file should have been written"

    disk = json.loads(open(cache_file).read())
    expected_key = f"{CITY_CFG['name']}|{PAST_DATE}"
    assert expected_key in disk, f"Key '{expected_key}' missing from disk cache"
    assert disk[expected_key] == FAKE_HIGH

    # Second cache instance — should load from disk, not fetch again
    get2 = backtest._make_actual_cache()
    result2 = get2(CITY_CFG, PAST_DATE)
    assert result2 == FAKE_HIGH
    assert call_count["n"] == 1, "Second instance should NOT have called the network"


def test_today_not_written_to_disk(monkeypatch, tmp_path):
    """Today's date is returned in-memory but NOT persisted to the disk file."""
    today = datetime.now(timezone.utc).date().isoformat()

    def fake_fetch(city_cfg, date_str):
        return (FAKE_HIGH, "fake", 0.0)

    monkeypatch.setattr(settlement, "fetch_observed_high", fake_fetch)
    monkeypatch.setattr(backtest, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(backtest, "_OBSERVED_CACHE_FILE",
                        os.path.join(str(tmp_path), "observed_highs_cache.json"))

    get = backtest._make_actual_cache()
    result = get(CITY_CFG, today)
    assert result == FAKE_HIGH, "Today's high should be returned in-memory"

    cache_file = os.path.join(str(tmp_path), "observed_highs_cache.json")
    if os.path.exists(cache_file):
        disk = json.loads(open(cache_file).read())
        today_key = f"{CITY_CFG['name']}|{today}"
        assert today_key not in disk, "Today's date must NOT be written to disk"
