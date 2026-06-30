"""Three independent CPI MoM% forecasters (B1).

Each model takes a MoM% history (OLD->NEW) and returns:
    {"name": str, "mu": float, "sigma": float}

mu    = point forecast of the NEXT month's MoM%
sigma = estimate of the model's own forecast error stdev (floored at 0.05)

No network.  All pure functions -- testable in isolation.
"""
import math
import statistics
import datetime


_SIGMA_FLOOR = 0.05


def _stdev(xs):
    """Population stdev; returns SIGMA_FLOOR if < 2 elements or xs is empty."""
    if len(xs) < 2:
        return _SIGMA_FLOOR
    return max(_SIGMA_FLOOR, statistics.stdev(xs))


def _mom_values(mom_hist):
    """Extract plain float MoM% values from history dicts."""
    return [r["mom"] for r in mom_hist]


# ---------------------------------------------------------------------------
# Model 1: seasonal_ar
# ---------------------------------------------------------------------------

def seasonal_ar(mom_hist):
    """Seasonal mean + AR(1) residual correction.

    Determine the TARGET month (month after the last observation in mom_hist).
    Collect all past MoM% values for that calendar month (up to last 10 years).
    mu = seasonal_mean + AR1_coef * last_residual
    sigma = stdev of in-sample residuals (vs seasonal mean).

    If fewer than 3 seasonal obs, falls back to random_walk.
    """
    if not mom_hist:
        return {"name": "seasonal_ar", "mu": 0.0, "sigma": _SIGMA_FLOOR}

    # Determine target calendar month
    last = mom_hist[-1]
    last_month = last.get("month")
    last_year = last.get("year")
    if last_month is None or last_year is None:
        # Try "date" key (FRED format)
        date_str = last.get("date", "")
        try:
            parts = date_str.split("-")
            last_year = int(parts[0])
            last_month = int(parts[1])
        except (IndexError, ValueError):
            rw = random_walk(mom_hist)
            return {"name": "seasonal_ar", "mu": rw["mu"], "sigma": rw["sigma"]}

    target_month = (last_month % 12) + 1

    # Collect observations for the target month (last 10 years)
    cutoff_year = last_year - 10
    seasonal_obs = []
    for r in mom_hist:
        r_month = r.get("month")
        r_year = r.get("year")
        if r_month is None or r_year is None:
            date_str = r.get("date", "")
            try:
                parts = date_str.split("-")
                r_year = int(parts[0])
                r_month = int(parts[1])
            except (IndexError, ValueError):
                continue
        if r_month == target_month and r_year >= cutoff_year:
            seasonal_obs.append(r["mom"])

    if len(seasonal_obs) < 3:
        # Not enough seasonal obs: fall back to trailing mean but keep our name
        rw = random_walk(mom_hist)
        return {"name": "seasonal_ar", "mu": rw["mu"], "sigma": rw["sigma"]}

    seasonal_mean = sum(seasonal_obs) / len(seasonal_obs)
    residuals = [v - seasonal_mean for v in seasonal_obs]
    sigma = _stdev(residuals)

    # AR(1): last obs residual vs its own seasonal mean
    last_mom = last["mom"]
    last_r_month = last.get("month")
    if last_r_month is None:
        try:
            last_r_month = int(last.get("date", "")[:10].split("-")[1])
        except (IndexError, ValueError):
            last_r_month = 0

    # Seasonal mean for the LAST month (not the target)
    last_month_obs = []
    for r in mom_hist[:-1]:
        r_month = r.get("month")
        if r_month is None:
            try:
                r_month = int(r.get("date", "")[:10].split("-")[1])
            except (IndexError, ValueError):
                continue
        if r_month == last_r_month:
            last_month_obs.append(r["mom"])

    last_seasonal_mean = (
        sum(last_month_obs) / len(last_month_obs) if last_month_obs else 0.0
    )
    last_residual = last_mom - last_seasonal_mean

    # Gentle AR(1) shrinkage (0.2 coefficient)
    ar1_coef = 0.2
    mu = seasonal_mean + ar1_coef * last_residual

    return {"name": "seasonal_ar", "mu": mu, "sigma": sigma}


# ---------------------------------------------------------------------------
# Model 2: random_walk
# ---------------------------------------------------------------------------

def random_walk(mom_hist):
    """Naive trailing base rate: mean of last 12 MoM% observations.

    sigma = stdev of the last 12 (the honest anchor).
    """
    if not mom_hist:
        return {"name": "random_walk", "mu": 0.0, "sigma": _SIGMA_FLOOR}

    recent = _mom_values(mom_hist[-12:])
    mu = sum(recent) / len(recent) if recent else 0.0
    sigma = _stdev(recent)
    return {"name": "random_walk", "mu": mu, "sigma": sigma}


# ---------------------------------------------------------------------------
# Model 3: nowcast (Cleveland Fed or fallback)
# ---------------------------------------------------------------------------

def nowcast(mom_hist, cleveland_mom=None):
    """Cleveland Fed nowcast model.

    If cleveland_mom is provided: mu = cleveland_mom, sigma = trailing error approx.
    Else: falls back to random_walk mu with a slightly wider sigma (no crash).

    Name: "nowcast".
    """
    rw = random_walk(mom_hist)

    if cleveland_mom is not None:
        # Use the external nowcast value; sigma approximated from trailing history
        sigma = max(rw["sigma"] * 1.1, _SIGMA_FLOOR)
        return {"name": "nowcast", "mu": float(cleveland_mom), "sigma": sigma}

    # No external nowcast: fall back to random walk with widened sigma
    wider_sigma = max(rw["sigma"] * 1.2, _SIGMA_FLOOR)
    return {"name": "nowcast", "mu": rw["mu"], "sigma": wider_sigma}


# ---------------------------------------------------------------------------
# Ensemble entry point
# ---------------------------------------------------------------------------

def all_models(mom_hist, cleveland_mom=None):
    """Return all three independent model forecasts as a list."""
    return [
        seasonal_ar(mom_hist),
        random_walk(mom_hist),
        nowcast(mom_hist, cleveland_mom=cleveland_mom),
    ]
