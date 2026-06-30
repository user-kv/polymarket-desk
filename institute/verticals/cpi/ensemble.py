"""Combine independent CPI model forecasts into a predictive Normal (B1).

Workflow:
  1. all_models(mom_hist)        -> list of {"name","mu","sigma"}
  2. fit_weights(mom_hist)       -> {name: rmse, "bias": float}
  3. inverse_rmse_weights(rmse)  -> {name: weight} summing to 1
  4. combine(models, weights)    -> {"mu","sigma"}
  5. bucket_prob(mu, sigma, lo, hi) -> float in (0,1)

All pure functions (except forecast_distribution which calls data fetchers).
"""
import math

from institute.scoring import clip
from institute.verticals.cpi.models import all_models as _all_models
from institute.verticals.cpi.calibrate import fit_weights, inverse_rmse_weights


# ---------------------------------------------------------------------------
# Standard-normal CDF via math.erf  (pure stdlib)
# ---------------------------------------------------------------------------

def norm_cdf(x):
    """Standard normal CDF: Phi(x) = 0.5 * (1 + erf(x / sqrt(2)))."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


# ---------------------------------------------------------------------------
# Mixture combine
# ---------------------------------------------------------------------------

def combine(models, weights, bias=0.0):
    """Weighted mixture of Gaussian components -> single Gaussian approximation.

    mu*     = sum(w_i * mu_i) - bias
    sigma*  = sqrt( sum(w_i * (sigma_i^2 + (mu_i - mu_raw)^2)) )
              (mixture variance: within-component + across-component spread)

    Returns {"mu": float, "sigma": float}.
    sigma is floored at 0.05.
    """
    if not models:
        return {"mu": 0.0, "sigma": 0.05}

    total_w = sum(weights.get(m["name"], 0.0) for m in models)
    if total_w == 0.0:
        # Fallback: equal weights
        n = len(models)
        weights = {m["name"]: 1.0 / n for m in models}
        total_w = 1.0

    # Normalise weights
    norm_w = {m["name"]: weights.get(m["name"], 0.0) / total_w for m in models}

    # Weighted mean (before bias correction)
    mu_raw = sum(norm_w[m["name"]] * m["mu"] for m in models)

    # Mixture variance: within + between
    variance = sum(
        norm_w[m["name"]] * (m["sigma"] ** 2 + (m["mu"] - mu_raw) ** 2)
        for m in models
    )

    mu_star = mu_raw - bias
    sigma_star = max(math.sqrt(max(variance, 0.0)), 0.05)

    return {"mu": mu_star, "sigma": sigma_star}


# ---------------------------------------------------------------------------
# Bucket probability
# ---------------------------------------------------------------------------

def bucket_prob(mu, sigma, lo, hi):
    """P(lo <= X < hi) for X ~ Normal(mu, sigma).

    lo=-inf and hi=+inf are allowed (one-sided markets).
    Result is clipped via scoring.clip to keep it in (EPS, 1-EPS).
    """
    sigma = max(float(sigma), 1e-9)

    if lo == float("-inf") or lo is None:
        p_lo = 0.0
    else:
        p_lo = norm_cdf((lo - mu) / sigma)

    if hi == float("inf") or hi is None:
        p_hi = 1.0
    else:
        p_hi = norm_cdf((hi - mu) / sigma)

    raw = p_hi - p_lo
    return clip(raw)


# ---------------------------------------------------------------------------
# Full distribution (glue)
# ---------------------------------------------------------------------------

def forecast_distribution(mom_hist, cleveland_mom=None, build_models=None):
    """Build models, fit weights, combine -> predictive distribution.

    Returns:
        {"mu": float, "sigma": float, "weights": dict, "n_train": int}

    mom_hist: list of {"mom": float, ...} dicts, OLD->NEW.
    cleveland_mom: optional float from the nowcast model.
    build_models: injectable for testing; defaults to all_models.
    """
    if build_models is None:
        build_models = _all_models

    models = build_models(mom_hist, cleveland_mom=cleveland_mom)

    rmse_map = fit_weights(mom_hist, build_models=build_models)
    bias = rmse_map.get("bias", 0.0)
    weights = inverse_rmse_weights(rmse_map)

    dist = combine(models, weights, bias=bias)
    return {
        "mu": dist["mu"],
        "sigma": dist["sigma"],
        "weights": weights,
        "n_train": len(mom_hist),
    }
