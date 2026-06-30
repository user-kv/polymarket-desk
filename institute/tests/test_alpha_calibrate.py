"""Tests for institute.alpha.calibrate — offline, no network (A6)."""
import math
from institute.alpha.calibrate import extremize, maybe_calibrate, ALPHA, CALIB_MIN_N


def test_extremize_half_is_half():
    """Fixed point: extremize(0.5) == 0.5."""
    assert abs(extremize(0.5) - 0.5) < 1e-9


def test_extremize_above_half_pushed_higher():
    """extremize(0.8) > 0.8 (pushed toward 1)."""
    assert extremize(0.8) > 0.8


def test_extremize_below_half_pushed_lower():
    """extremize(0.2) < 0.2 (pushed toward 0)."""
    assert extremize(0.2) < 0.2


def test_extremize_symmetry():
    """extremize(p) + extremize(1-p) == 1 (within floating-point tolerance)."""
    for p in [0.1, 0.3, 0.5, 0.7, 0.9]:
        total = extremize(p) + extremize(1.0 - p)
        assert abs(total - 1.0) < 1e-9, f"Symmetry failed for p={p}: sum={total}"


def test_extremize_monotone():
    """Higher input -> higher output (monotonicity)."""
    ps = [0.1, 0.3, 0.5, 0.7, 0.9]
    extremized = [extremize(p) for p in ps]
    assert extremized == sorted(extremized)


def test_extremize_clips_extreme_inputs():
    """Clips to EPS before logit so no math domain error."""
    result = extremize(0.0)
    assert 0 < result < 1
    result = extremize(1.0)
    assert 0 < result < 1


# ── maybe_calibrate ───────────────────────────────────────────────────────────

def test_maybe_calibrate_off_below_threshold():
    """n < CALIB_MIN_N -> returns p unchanged (structural no-op today)."""
    p = 0.8
    result = maybe_calibrate(p, n=10)
    assert result == p, f"Expected {p}, got {result}"


def test_maybe_calibrate_off_at_threshold_minus_one():
    p = 0.8
    result = maybe_calibrate(p, n=CALIB_MIN_N - 1)
    assert result == p


def test_maybe_calibrate_on_at_threshold():
    """n >= CALIB_MIN_N -> applies extremize."""
    p = 0.8
    result = maybe_calibrate(p, n=CALIB_MIN_N)
    assert abs(result - extremize(p)) < 1e-9


def test_maybe_calibrate_on_above_threshold():
    p = 0.8
    result = maybe_calibrate(p, n=500)
    assert abs(result - extremize(p)) < 1e-9


def test_maybe_calibrate_half_unchanged_when_on():
    """extremize(0.5) == 0.5, so maybe_calibrate(0.5, n=500) == 0.5."""
    result = maybe_calibrate(0.5, n=500)
    assert abs(result - 0.5) < 1e-9
