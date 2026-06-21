"""
Settlement timing guard (regression).

Polymarket sets a bet's end_date to ~noon UTC ON the weather day, which is still
morning across continental-US timezones — before the daily HIGH occurs. The old
guard (`now < end_dt + 1h`) let settlement fire mid-morning local time and fetch
a confident PARTIAL-day high, resolving bets wrong. The fix gates on 08:00 UTC
the day AFTER the weather day (past local midnight for UTC-4..UTC-8).

These tests assert fetch_observed_high is NOT called when bailing early.

Run:  PYTHONPATH=papertrader python -m pytest papertrader/tests/test_settlement_timing.py -q
"""
from datetime import datetime, timezone, timedelta

import lib.settlement as settlement


CITY = {
    "name": "Dallas", "station": "KDAL",
    "lat": 32.8471, "lon": -96.8518, "tz": "America/Chicago",
}
CFG = {"fee_on_winnings_pct": 2.0}


def _bet(end_date_iso, side="YES"):
    # Closed bucket the partial high (91.4) would WRONGLY satisfy and the
    # completed high (e.g. 95) would also satisfy — timing is the only variable.
    return {
        "city": "Dallas", "end_date": end_date_iso, "side": side,
        "bucket_low_f": "90", "bucket_high_f": "94",
        "is_open_ended_low": "False", "is_open_ended_high": "True",
        "stake": "20", "shares": "100", "gross_if_win": "100",
    }


def _patch_now(monkeypatch, fixed_now):
    class _DT(datetime):
        @classmethod
        def now(cls, tz=None):
            return fixed_now
    monkeypatch.setattr(settlement, "datetime", _DT)


def _patch_fetch(monkeypatch, value):
    calls = {"n": 0}

    def fake_fetch(city_cfg, target_date):
        calls["n"] += 1
        return (value, "openmeteo_archive", None)

    monkeypatch.setattr(settlement, "fetch_observed_high", fake_fetch)
    return calls


def test_does_not_settle_incomplete_day(monkeypatch):
    # end_date is noon UTC today; "now" is 13:00 UTC same day (morning local) —
    # the day is NOT over. Must bail BEFORE fetching.
    weather_day = "2026-06-21"
    end_date = f"{weather_day}T12:00:00Z"
    now = datetime(2026, 6, 21, 13, 0, tzinfo=timezone.utc)
    _patch_now(monkeypatch, now)
    calls = _patch_fetch(monkeypatch, 91.4)

    result = settlement.settle_bet(_bet(end_date), CITY, CFG)

    assert result is None, "must not settle before the weather day completes"
    assert calls["n"] == 0, "must not fetch observed high when bailing early"


def test_settles_completed_day(monkeypatch):
    # Weather day fully past: now is 08:00 UTC the NEXT day -> gate open.
    weather_day = "2026-06-21"
    end_date = f"{weather_day}T12:00:00Z"
    now = datetime(2026, 6, 22, 8, 0, tzinfo=timezone.utc)
    _patch_now(monkeypatch, now)
    calls = _patch_fetch(monkeypatch, 95.0)

    result = settlement.settle_bet(_bet(end_date), CITY, CFG)

    assert result is not None, "must settle once the weather day is complete"
    assert calls["n"] == 1
    # 95 is >= 90 with open-ended high -> bucket happened -> YES wins.
    assert result["result"] == "WON"


def test_gate_boundary_just_before(monkeypatch):
    # One minute before the 08:00-UTC-next-day gate: still must not settle.
    end_date = "2026-06-21T12:00:00Z"
    now = datetime(2026, 6, 22, 7, 59, tzinfo=timezone.utc)
    _patch_now(monkeypatch, now)
    calls = _patch_fetch(monkeypatch, 95.0)

    assert settlement.settle_bet(_bet(end_date), CITY, CFG) is None
    assert calls["n"] == 0
