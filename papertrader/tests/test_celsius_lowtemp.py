"""
Celsius + LOWEST-temperature market support (2026-07 expansion).

Covers:
  1. Parser: °C range, °C single discrete value, °C or-above/or-below
  2. Parser: "lowest temperature" metric detection (both °F and °C)
  3. Parser: existing °F regression cases unchanged
  4. Engine routing: metric=="low" pulls the daily-low ensemble
  5. Settlement: low-metric bets resolve against the daily LOW, not the high
  6. Ledger: old rows without a "metric" column still load fine

Run:  PYTHONPATH=papertrader python -m pytest papertrader/tests/test_celsius_lowtemp.py -q
"""
import os
import tempfile

from lib.polymarket import _parse_bucket
from lib import ledger as ledger_mod
from lib import engine
from lib import settlement


# ---------------------------------------------------------------------------
# Parser: Celsius patterns
# ---------------------------------------------------------------------------

def test_celsius_range():
    q = "Will the highest temperature in London be between 27-28°C on July 7?"
    b = _parse_bucket(q)
    assert b is not None
    assert b["low_f"] == 27 * 9 / 5 + 32
    assert b["high_f"] == 28 * 9 / 5 + 32
    assert b["is_open_ended_low"] is False and b["is_open_ended_high"] is False
    assert b["metric"] == "high"
    assert b["display_unit"] == "c"


def test_celsius_single_value():
    q = "Will the highest temperature in London be 28°C on July 7?"
    b = _parse_bucket(q)
    assert b is not None
    assert b["low_f"] == 28 * 9 / 5 + 32
    assert b["high_f"] == 29 * 9 / 5 + 32   # [X, X+1) in °C
    assert b["is_open_ended_low"] is False and b["is_open_ended_high"] is False


def test_celsius_or_above():
    q = "Will the highest temperature in London be 30°C or above on July 7?"
    b = _parse_bucket(q)
    assert b is not None
    assert b["low_f"] == 30 * 9 / 5 + 32
    assert b["is_open_ended_high"] is True
    assert b["high_f"] == 999.0


def test_celsius_or_below():
    q = "Will the highest temperature in London be 15°C or below on July 7?"
    b = _parse_bucket(q)
    assert b is not None
    assert b["high_f"] == 15 * 9 / 5 + 32
    assert b["is_open_ended_low"] is True
    assert b["low_f"] == -999.0


def test_lowest_temperature_detection_celsius():
    q = "Will the lowest temperature in London be 10°C on July 7?"
    b = _parse_bucket(q)
    assert b is not None
    assert b["metric"] == "low"
    assert b["low_f"] == 10 * 9 / 5 + 32
    assert b["high_f"] == 11 * 9 / 5 + 32


def test_lowest_temperature_detection_fahrenheit_range():
    # Existing US-style bucket format, but "lowest" instead of "highest".
    q = "Will the lowest temperature in Dallas be between 40-41°F on July 7?"
    b = _parse_bucket(q)
    assert b is not None
    assert b["metric"] == "low"
    assert b["low_f"] == 40.0 and b["high_f"] == 41.0


# ---------------------------------------------------------------------------
# Parser: °F regression — unchanged behavior for the live 9 US cities
# ---------------------------------------------------------------------------

def test_fahrenheit_between_regression():
    q = "Will the highest temperature in Dallas be between 96-97°F on June 13?"
    b = _parse_bucket(q)
    assert b == {
        "low_f": 96.0, "high_f": 97.0,
        "is_open_ended_low": False, "is_open_ended_high": False,
        "display_unit": "f", "metric": "high",
    }


def test_fahrenheit_or_below_regression():
    q = "Will the highest temperature in Dallas be 83°F or below on June 13?"
    b = _parse_bucket(q)
    assert b["low_f"] == -999.0
    assert b["high_f"] == 83.0
    assert b["is_open_ended_low"] is True
    assert b["metric"] == "high"
    assert b["display_unit"] == "f"


def test_non_temperature_question_still_none():
    assert _parse_bucket("Will it rain in Dallas tomorrow?") is None


# ---------------------------------------------------------------------------
# Engine routing
# ---------------------------------------------------------------------------

def test_engine_routes_low_metric_to_min_ensemble(monkeypatch):
    calls = {}

    def fake_get_forecast_for_city(city_cfg, target_date_str, cfg=None, raw_ensembles=None, metric="high"):
        calls["metric"] = metric
        return {"gfs_mean_f": 50.0, "ecmwf_mean_f": 50.0, "combined_mean_f": 50.0, "all_highs_f": [50.0]}

    from lib import forecasts as forecasts_mod
    monkeypatch.setattr(forecasts_mod, "get_forecast_for_city", fake_get_forecast_for_city)

    market_low = {"metric": "low"}
    engine.get_forecast_for_market(market_low, {"name": "London"}, "2026-07-07")
    assert calls["metric"] == "low"

    market_high = {"metric": "high"}
    engine.get_forecast_for_market(market_high, {"name": "Dallas"}, "2026-06-13")
    assert calls["metric"] == "high"

    # Missing "metric" key defaults to "high" (backward compat for existing markets)
    market_default = {}
    engine.get_forecast_for_market(market_default, {"name": "Dallas"}, "2026-06-13")
    assert calls["metric"] == "high"


# ---------------------------------------------------------------------------
# Settlement: low-metric bets resolve against the daily LOW
# ---------------------------------------------------------------------------

def test_settlement_uses_low_fetch_for_low_metric_bets(monkeypatch):
    calls = {"high": 0, "low": 0}

    def fake_high(city_cfg, date_str):
        calls["high"] += 1
        return (95.0, "test", None)

    def fake_low(city_cfg, date_str):
        calls["low"] += 1
        return (40.0, "test", None)

    monkeypatch.setattr(settlement, "fetch_observed_high", fake_high)
    monkeypatch.setattr(settlement, "fetch_observed_low", fake_low)

    from datetime import datetime, timezone

    class _DT(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 6, 22, 8, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(settlement, "datetime", _DT)

    city = {"name": "London", "station": "EGLL", "lat": 51.5, "lon": -0.1, "tz": "Europe/London"}
    cfg = {"fee_on_winnings_pct": 2.0}

    bet_low = {
        "city": "London", "end_date": "2026-06-21T12:00:00Z", "side": "YES",
        "bucket_low_f": "38", "bucket_high_f": "42",
        "is_open_ended_low": "False", "is_open_ended_high": "False",
        "stake": "20", "shares": "100", "gross_if_win": "100",
        "metric": "low",
    }
    result = settlement.settle_bet(bet_low, city, cfg)
    assert result is not None
    assert calls["low"] == 1 and calls["high"] == 0
    assert result["actual_high_f"] == 40.0
    assert result["result"] == "WON"  # 38 <= 40 < 42


def test_settlement_defaults_missing_metric_to_high(monkeypatch):
    calls = {"high": 0, "low": 0}
    monkeypatch.setattr(settlement, "fetch_observed_high", lambda c, d: (calls.__setitem__("high", calls["high"] + 1) or (95.0, "t", None)))
    monkeypatch.setattr(settlement, "fetch_observed_low", lambda c, d: (calls.__setitem__("low", calls["low"] + 1) or (40.0, "t", None)))

    from datetime import datetime, timezone

    class _DT(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 6, 22, 8, 0, tzinfo=timezone.utc)

    monkeypatch.setattr(settlement, "datetime", _DT)

    city = {"name": "Dallas", "station": "KDAL", "lat": 32.8, "lon": -96.8, "tz": "America/Chicago"}
    cfg = {"fee_on_winnings_pct": 2.0}
    # No "metric" key at all — old-style bet row.
    bet_no_metric = {
        "city": "Dallas", "end_date": "2026-06-21T12:00:00Z", "side": "YES",
        "bucket_low_f": "90", "bucket_high_f": "94",
        "is_open_ended_low": "False", "is_open_ended_high": "True",
        "stake": "20", "shares": "100", "gross_if_win": "100",
    }
    result = settlement.settle_bet(bet_no_metric, city, cfg)
    assert result is not None
    assert calls["high"] == 1 and calls["low"] == 0


# ---------------------------------------------------------------------------
# Ledger backward compat: old rows without a "metric" column still load
# ---------------------------------------------------------------------------

def test_ledger_reads_old_rows_without_metric_column(monkeypatch, tmp_path):
    old_cols = [c for c in ledger_mod.BETS_COLS if c != "metric"]
    bets_path = tmp_path / "bets.csv"
    import csv
    with open(bets_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=old_cols)
        w.writeheader()
        w.writerow({
            "bet_id": "old1", "timestamp": "2026-06-01T00:00:00Z", "city": "Dallas",
            "station": "KDAL", "question": "q", "slug": "s", "market_id": "1",
            "yes_token": "t", "end_date": "2026-06-01T12:00:00Z",
            "bucket_low_f": "90", "bucket_high_f": "91",
            "is_open_ended_low": "False", "is_open_ended_high": "False",
            "side": "YES", "ask_price": "0.5", "stake": "5", "shares": "10",
            "gross_if_win": "10", "fee_if_win": "0.2",
            "net_profit_if_win": "4.8", "net_loss_if_lose": "-5",
            "ensemble_prob": "0.5", "edge_pct": "10", "gfs_mean_f": "90",
            "ecmwf_mean_f": "90", "n_members": "50",
            "brain_multiplier": "1.0", "brain_rationale": "",
            "status": "settled", "result": "WON", "actual_high_f": "90.5",
            "settled_at": "2026-06-02T00:00:00Z", "pnl": "4.8", "is_test": "N",
        })

    monkeypatch.setattr(ledger_mod, "BETS_PATH", str(bets_path))
    bets = ledger_mod.load_bets()
    assert len(bets) == 1
    b = bets[0]
    # Old row genuinely has no "metric" key — callers must default via .get()
    assert b.get("metric", "high") == "high"
    assert b["bet_id"] == "old1"
