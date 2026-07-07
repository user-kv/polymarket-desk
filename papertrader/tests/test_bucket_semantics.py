"""Regression: venue-correct bucket resolution (2026-07-07 fix).

Polymarket closed buckets are INCLUSIVE of both ends and resolve against the
source's reported integer temperature in the market's native unit. The old
half-open [low, high) rule marked an observed 95°F as a LOSS on the "94-95°F"
bucket (and a WIN for its NO side) — mis-resolving every top-edge outcome.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib.settlement import did_bucket_win  # noqa: E402
from lib.forecasts import bucket_probability  # noqa: E402


def test_top_edge_inclusive_fahrenheit():
    # observed exactly the top integer of the bucket -> WIN
    assert did_bucket_win(95.0, 94.0, 95.0, False, False) is True
    # and the next bucket up does not claim it
    assert did_bucket_win(95.0, 96.0, 97.0, False, False) is False


def test_rounding_to_reported_integer():
    # 95.4 reports as 95 -> inside 94-95; 95.6 reports as 96 -> inside 96-97
    assert did_bucket_win(95.4, 94.0, 95.0, False, False) is True
    assert did_bucket_win(95.6, 94.0, 95.0, False, False) is False
    assert did_bucket_win(95.6, 96.0, 97.0, False, False) is True


def test_open_ended_rounding():
    # "96°F or higher": 95.6 reports as 96 -> WIN
    assert did_bucket_win(95.6, 96.0, 999.0, False, True) is True
    assert did_bucket_win(95.4, 96.0, 999.0, False, True) is False
    # "83°F or below": 83.4 reports as 83 -> WIN
    assert did_bucket_win(83.4, -999.0, 83.0, True, False) is True
    assert did_bucket_win(83.6, -999.0, 83.0, True, False) is False


def test_celsius_resolved_in_native_unit():
    # "be 28°C" stored as degenerate [82.4, 82.4]°F. Observed 82.0°F = 27.8°C
    # reports as 28°C -> WIN, even though 82.0 < 82.4 in °F terms.
    lo = hi = 28 * 9 / 5 + 32
    assert did_bucket_win(82.0, lo, hi, False, False, display_unit="c") is True
    # 82.9°F = 28.3°C -> still 28 -> WIN; 83.8°F = 28.8°C -> 29 -> LOSS
    assert did_bucket_win(82.9, lo, hi, False, False, display_unit="c") is True
    assert did_bucket_win(83.8, lo, hi, False, False, display_unit="c") is False


def test_celsius_open_ended_native_unit():
    # "15°C or below" (high bound 59.0°F): 15.4°C (59.7°F) reports 15 -> WIN
    hi = 15 * 9 / 5 + 32
    assert did_bucket_win(59.7, -999.0, hi, True, False, display_unit="c") is True
    assert did_bucket_win(60.1, -999.0, hi, True, False, display_unit="c") is False


def test_bucket_probability_matches_settlement_convention():
    # members straddling the 94-95 bucket edges under reported-integer rounding:
    # 93.6->94 in, 95.4->95 in, 95.6->96 out, 93.4->93 out
    members = [93.6, 95.4, 95.6, 93.4]
    assert bucket_probability(members, 94.0, 95.0) == 0.5
    # open-ended: ">= 96": only 95.6 rounds up to 96
    assert bucket_probability(members, 96.0, 999.0) == 0.25
