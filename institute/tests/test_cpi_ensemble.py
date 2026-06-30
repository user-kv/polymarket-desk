"""Tests for institute/verticals/cpi/ensemble.py (B1).

Offline and deterministic -- no network.
"""
import math

from institute.verticals.cpi.ensemble import (
    norm_cdf,
    bucket_prob,
    combine,
    forecast_distribution,
)
from institute.verticals.cpi.calibrate import inverse_rmse_weights


# ---------------------------------------------------------------------------
# norm_cdf
# ---------------------------------------------------------------------------

def test_norm_cdf_zero_is_half():
    """Phi(0) = 0.5 (symmetry of N(0,1))."""
    assert abs(norm_cdf(0) - 0.5) < 1e-9


def test_norm_cdf_large_positive_near_one():
    """Phi(8) very close to 1."""
    assert norm_cdf(8) > 0.999


def test_norm_cdf_large_negative_near_zero():
    """Phi(-8) very close to 0."""
    assert norm_cdf(-8) < 0.001


def test_norm_cdf_symmetry():
    """Phi(x) + Phi(-x) == 1."""
    for x in [0.5, 1.0, 1.96, 2.5]:
        assert abs(norm_cdf(x) + norm_cdf(-x) - 1.0) < 1e-12


# ---------------------------------------------------------------------------
# inverse_rmse_weights
# ---------------------------------------------------------------------------

def test_inverse_rmse_weights_sums_to_one():
    rmse_map = {"seasonal_ar": 0.15, "random_walk": 0.20, "nowcast": 0.18}
    w = inverse_rmse_weights(rmse_map)
    assert abs(sum(w.values()) - 1.0) < 1e-9


def test_inverse_rmse_weights_lower_rmse_gets_higher_weight():
    rmse_map = {"model_a": 0.10, "model_b": 0.30}
    w = inverse_rmse_weights(rmse_map)
    # model_a has lower RMSE so should have higher weight
    assert w["model_a"] > w["model_b"]


def test_inverse_rmse_weights_skips_bias_key():
    rmse_map = {"seasonal_ar": 0.15, "random_walk": 0.20, "bias": -0.01}
    w = inverse_rmse_weights(rmse_map)
    assert "bias" not in w
    assert abs(sum(w.values()) - 1.0) < 1e-9


def test_inverse_rmse_weights_equal_rmse_gives_equal_weights():
    rmse_map = {"a": 0.20, "b": 0.20}
    w = inverse_rmse_weights(rmse_map)
    assert abs(w["a"] - w["b"]) < 1e-9


def test_inverse_rmse_weights_guards_zero_rmse():
    """rmse=0 should not raise (floored)."""
    rmse_map = {"a": 0.0, "b": 0.20}
    w = inverse_rmse_weights(rmse_map)
    assert sum(w.values()) > 0
    assert abs(sum(w.values()) - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# bucket_prob
# ---------------------------------------------------------------------------

def test_bucket_prob_full_range_is_near_one():
    """P(-inf, +inf) is clipped to (1 - EPS) by scoring.clip."""
    from institute.scoring import EPS
    p = bucket_prob(0.3, 0.1, float("-inf"), float("inf"))
    # clip() caps at 1 - EPS (= 0.99); assert it is at or near that ceiling
    assert p >= 1.0 - EPS - 1e-12


def test_bucket_prob_symmetric_bucket_around_mu_is_reasonable():
    """Symmetric bucket [mu-0.1, mu+0.1] with sigma=0.1 -> covers ~68% -> < 1."""
    mu, sigma = 0.3, 0.1
    lo, hi = mu - sigma, mu + sigma
    p = bucket_prob(mu, sigma, lo, hi)
    # ~68% of a Normal is within 1 sigma
    assert 0.60 < p < 0.80


def test_bucket_prob_far_bucket_is_small():
    """Bucket far from mu -> probability at EPS floor (clipped from near-0)."""
    from institute.scoring import EPS
    p = bucket_prob(0.3, 0.05, 1.0, 2.0)
    # clip() floors at EPS (= 0.01); very remote bucket hits the floor
    assert p <= EPS + 1e-12


def test_bucket_prob_always_in_eps_range():
    """Result always in [EPS, 1-EPS]."""
    from institute.scoring import EPS
    for lo, hi in [(float("-inf"), 0.0), (0.0, float("inf")),
                   (float("-inf"), float("inf")), (-1.0, 0.0)]:
        p = bucket_prob(0.3, 0.1, lo, hi)
        assert EPS <= p <= 1.0 - EPS


def test_bucket_prob_none_bounds_treated_as_infinite():
    """lo=None and hi=None are treated as -inf/+inf (clips to 1-EPS)."""
    from institute.scoring import EPS
    p = bucket_prob(0.3, 0.1, None, None)
    assert p >= 1.0 - EPS - 1e-12


# ---------------------------------------------------------------------------
# combine
# ---------------------------------------------------------------------------

def test_combine_basic():
    models = [
        {"name": "a", "mu": 0.3, "sigma": 0.1},
        {"name": "b", "mu": 0.5, "sigma": 0.1},
    ]
    weights = {"a": 0.5, "b": 0.5}
    result = combine(models, weights)
    assert abs(result["mu"] - 0.4) < 1e-9
    assert result["sigma"] >= 0.05


def test_combine_widens_sigma_when_models_disagree():
    """When models disagree strongly, pooled sigma > average component sigma."""
    models = [
        {"name": "a", "mu": 0.0, "sigma": 0.05},
        {"name": "b", "mu": 1.0, "sigma": 0.05},
    ]
    weights = {"a": 0.5, "b": 0.5}
    result = combine(models, weights)
    # Mean component sigma is 0.05 but disagreement is huge
    assert result["sigma"] > 0.4


def test_combine_bias_shifts_mu():
    models = [{"name": "a", "mu": 0.3, "sigma": 0.1}]
    weights = {"a": 1.0}
    result_no_bias = combine(models, weights, bias=0.0)
    result_bias = combine(models, weights, bias=0.05)
    assert abs(result_bias["mu"] - (result_no_bias["mu"] - 0.05)) < 1e-9


def test_combine_sigma_floored_at_0_05():
    """sigma is never below 0.05 even with zero-variance models."""
    models = [{"name": "a", "mu": 0.3, "sigma": 0.0}]
    weights = {"a": 1.0}
    result = combine(models, weights)
    assert result["sigma"] >= 0.05


def test_combine_empty_models():
    """Empty models list returns defaults without crashing."""
    result = combine([], {})
    assert result["sigma"] >= 0.05


# ---------------------------------------------------------------------------
# forecast_distribution (integration)
# ---------------------------------------------------------------------------

def _make_hist(n=36, base=0.2, amp=0.1):
    hist = []
    start_year = 2023
    for i in range(n):
        yr = start_year + (i // 12)
        mo = (i % 12) + 1
        mom = base + amp * math.sin(2 * math.pi * i / 12)
        hist.append({"year": yr, "month": mo, "mom": mom})
    return hist


HIST = _make_hist(36)


def test_forecast_distribution_returns_expected_keys():
    result = forecast_distribution(HIST)
    assert "mu" in result
    assert "sigma" in result
    assert "weights" in result
    assert "n_train" in result


def test_forecast_distribution_mu_is_finite():
    result = forecast_distribution(HIST)
    assert math.isfinite(result["mu"])


def test_forecast_distribution_sigma_floored():
    result = forecast_distribution(HIST)
    assert result["sigma"] >= 0.05


def test_forecast_distribution_weights_sum_to_one():
    result = forecast_distribution(HIST)
    w = result["weights"]
    assert abs(sum(w.values()) - 1.0) < 1e-9


def test_forecast_distribution_n_train_matches_hist():
    result = forecast_distribution(HIST)
    assert result["n_train"] == len(HIST)


def test_forecast_distribution_deterministic():
    r1 = forecast_distribution(HIST)
    r2 = forecast_distribution(HIST)
    assert r1["mu"] == r2["mu"]
    assert r1["sigma"] == r2["sigma"]


def test_forecast_distribution_with_injectable_models():
    """Injectable build_models for full determinism in offline tests."""
    def fake_models(hist, cleveland_mom=None):
        return [
            {"name": "m1", "mu": 0.3, "sigma": 0.1},
            {"name": "m2", "mu": 0.4, "sigma": 0.1},
        ]

    result = forecast_distribution(HIST, build_models=fake_models)
    assert math.isfinite(result["mu"])
    assert result["sigma"] >= 0.05
