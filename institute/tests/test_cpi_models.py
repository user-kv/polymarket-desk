"""Tests for institute/verticals/cpi/models.py (B1).

Offline and deterministic -- no network.
"""
import math

from institute.verticals.cpi.models import seasonal_ar, random_walk, nowcast, all_models

# Synthetic MoM% history (36 months, known values)
# Covers 3 full years so seasonal_ar has enough seasonal observations.

def _make_hist(n=36, base=0.2, amp=0.1):
    """Generate a synthetic MoM% history with mild seasonality."""
    hist = []
    start_year = 2023
    for i in range(n):
        year = start_year + (i // 12)
        month = (i % 12) + 1
        mom = base + amp * math.sin(2 * math.pi * i / 12)
        hist.append({"year": year, "month": month, "mom": mom})
    return hist


HIST = _make_hist(36)


# ---------------------------------------------------------------------------
# seasonal_ar
# ---------------------------------------------------------------------------

def test_seasonal_ar_returns_finite_mu():
    result = seasonal_ar(HIST)
    assert math.isfinite(result["mu"]), "mu must be finite"


def test_seasonal_ar_sigma_floored():
    result = seasonal_ar(HIST)
    assert result["sigma"] >= 0.05, f"sigma={result['sigma']} below floor"


def test_seasonal_ar_name():
    result = seasonal_ar(HIST)
    assert result["name"] == "seasonal_ar"


def test_seasonal_ar_empty_hist():
    """Empty history falls back gracefully (no raise)."""
    result = seasonal_ar([])
    assert math.isfinite(result["mu"])
    assert result["sigma"] >= 0.05


def test_seasonal_ar_short_hist():
    """Too-short history falls back to random_walk style (no raise)."""
    result = seasonal_ar(HIST[:5])
    assert math.isfinite(result["mu"])
    assert result["sigma"] >= 0.05


# ---------------------------------------------------------------------------
# random_walk
# ---------------------------------------------------------------------------

def test_random_walk_returns_finite_mu():
    result = random_walk(HIST)
    assert math.isfinite(result["mu"])


def test_random_walk_sigma_floored():
    result = random_walk(HIST)
    assert result["sigma"] >= 0.05


def test_random_walk_name():
    result = random_walk(HIST)
    assert result["name"] == "random_walk"


def test_random_walk_empty():
    result = random_walk([])
    assert result["mu"] == 0.0
    assert result["sigma"] >= 0.05


def test_random_walk_uses_last_12():
    """mu should be close to the mean of the last 12 values."""
    last12 = [r["mom"] for r in HIST[-12:]]
    expected_mu = sum(last12) / len(last12)
    result = random_walk(HIST)
    assert abs(result["mu"] - expected_mu) < 1e-9


# ---------------------------------------------------------------------------
# nowcast
# ---------------------------------------------------------------------------

def test_nowcast_with_cleveland_uses_external_value():
    """When cleveland_mom is provided, mu must equal it exactly."""
    result = nowcast(HIST, cleveland_mom=0.4)
    assert result["mu"] == 0.4


def test_nowcast_with_cleveland_name():
    result = nowcast(HIST, cleveland_mom=0.4)
    assert result["name"] == "nowcast"


def test_nowcast_with_cleveland_sigma_floored():
    result = nowcast(HIST, cleveland_mom=0.4)
    assert result["sigma"] >= 0.05


def test_nowcast_no_cleveland_falls_back_no_raise():
    """cleveland_mom=None -> falls back gracefully (no raise)."""
    result = nowcast(HIST, cleveland_mom=None)
    assert math.isfinite(result["mu"])
    assert result["sigma"] >= 0.05
    assert result["name"] == "nowcast"


def test_nowcast_no_cleveland_empty_hist():
    """Falls back even with no history (no raise)."""
    result = nowcast([], cleveland_mom=None)
    assert math.isfinite(result["mu"])
    assert result["sigma"] >= 0.05


def test_nowcast_wider_sigma_without_cleveland():
    """When no cleveland, sigma should be >= rw sigma (wider due to uncertainty)."""
    rw = random_walk(HIST)
    nc = nowcast(HIST, cleveland_mom=None)
    assert nc["sigma"] >= rw["sigma"]


# ---------------------------------------------------------------------------
# all_models
# ---------------------------------------------------------------------------

def test_all_models_returns_three():
    models = all_models(HIST)
    assert len(models) == 3


def test_all_models_all_names_present():
    models = all_models(HIST)
    names = {m["name"] for m in models}
    assert "seasonal_ar" in names
    assert "random_walk" in names
    assert "nowcast" in names


def test_all_models_all_finite_mu_sigma():
    models = all_models(HIST)
    for m in models:
        assert math.isfinite(m["mu"]), f"{m['name']} mu not finite"
        assert math.isfinite(m["sigma"]), f"{m['name']} sigma not finite"
        assert m["sigma"] >= 0.05, f"{m['name']} sigma below floor"


def test_all_models_deterministic():
    """Same input -> same output (pure function)."""
    r1 = all_models(HIST)
    r2 = all_models(HIST)
    for m1, m2 in zip(r1, r2):
        assert m1["mu"] == m2["mu"]
        assert m1["sigma"] == m2["sigma"]


def test_all_models_with_cleveland():
    models = all_models(HIST, cleveland_mom=0.35)
    nc = next(m for m in models if m["name"] == "nowcast")
    assert nc["mu"] == 0.35
