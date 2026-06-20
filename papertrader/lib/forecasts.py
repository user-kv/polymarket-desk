"""
lib/forecasts.py
Fetches Open-Meteo ensemble forecasts for a city and computes:
 - GFS ensemble mean (30 members: ncep_gefs_seamless member01..30)
 - ECMWF ensemble mean (50 members: ecmwf_ifs025_ensemble member01..50)
 - Combined probability that daily high falls in each temperature bucket
 - Model agreement check (GFS mean vs ECMWF mean within threshold)

Member naming from Phase 0 discovery (June 2026):
  GFS:   temperature_2m_member01_ncep_gefs_seamless .. member30
  ECMWF: temperature_2m_member01_ecmwf_ifs025_ensemble .. member50
  (Both also have a control/mean key without 'member')
"""

import urllib.request
import json
import logging
from datetime import datetime, timezone, timedelta
import math

logger = logging.getLogger("forecasts")


def _get(url, timeout=30):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "PaperTrader/1.0", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _c_to_f(c):
    return c * 9.0 / 5.0 + 32.0


def fetch_ensemble(city_cfg, forecast_days=2, base_url=None, models=None,
                   start_date=None, end_date=None):
    """
    Fetch all ensemble members for a city.
    Returns raw Open-Meteo JSON.

    If start_date/end_date (YYYY-MM-DD) are given, the ensemble API returns the
    archived run covering those past dates (used by the historical backtest).
    Otherwise it returns the live forecast for the next `forecast_days` days.
    """
    if base_url is None:
        base_url = "https://ensemble-api.open-meteo.com/v1/ensemble"
    if models is None:
        models = "gfs_seamless,ecmwf_ifs025"

    lat = city_cfg["lat"]
    lon = city_cfg["lon"]
    tz = city_cfg.get("tz", "auto")

    url = (
        f"{base_url}?latitude={lat}&longitude={lon}"
        f"&models={models}&hourly=temperature_2m&timezone={tz}"
    )
    if start_date and end_date:
        url += f"&start_date={start_date}&end_date={end_date}"
    else:
        url += f"&forecast_days={forecast_days}"
    logger.debug(f"Fetching ensemble for {city_cfg['name']}: {url}")
    return _get(url)


def compute_daily_high_ensemble(ensemble_data, target_date_str):
    """
    For each ensemble member, find the max hourly temperature_2m on target_date_str
    (format: 'YYYY-MM-DD') and convert to °F.

    Returns dict with:
        gfs_highs_f: list of daily-high floats from GFS members
        ecmwf_highs_f: list of daily-high floats from ECMWF members
        gfs_mean_f: mean of GFS highs
        ecmwf_mean_f: mean of ECMWF highs
        all_highs_f: combined list
        n_gfs: count of GFS members
        n_ecmwf: count of ECMWF members
    """
    hourly = ensemble_data.get("hourly", {})
    times = hourly.get("time", [])

    # Find which time-indices correspond to target_date
    target_indices = [
        i for i, t in enumerate(times) if t.startswith(target_date_str)
    ]
    if not target_indices:
        raise ValueError(f"No hourly data for date {target_date_str}")

    gfs_highs = []
    ecmwf_highs = []
    icon_highs = []
    gem_highs = []
    ukmo_highs = []

    for key, vals in hourly.items():
        if not key.startswith("temperature_2m_member"):
            continue
        try:
            day_vals = [vals[i] for i in target_indices if vals[i] is not None]
            if not day_vals:
                continue
            daily_high_c = max(day_vals)
            daily_high_f = _c_to_f(daily_high_c)
        except (IndexError, TypeError):
            continue

        if "ukmo" in key.lower():
            ukmo_highs.append(daily_high_f)
        elif "ncep_gefs" in key or "gfs" in key.lower():
            gfs_highs.append(daily_high_f)
        elif "ecmwf" in key:
            ecmwf_highs.append(daily_high_f)
        elif "icon" in key.lower():
            icon_highs.append(daily_high_f)
        elif "gem" in key.lower():
            gem_highs.append(daily_high_f)

    if not gfs_highs:
        raise ValueError("No GFS members found in ensemble data")
    if not ecmwf_highs:
        raise ValueError("No ECMWF members found in ensemble data")

    gfs_mean = sum(gfs_highs) / len(gfs_highs)
    ecmwf_mean = sum(ecmwf_highs) / len(ecmwf_highs)
    all_highs = gfs_highs + ecmwf_highs + icon_highs + gem_highs + ukmo_highs

    return {
        "gfs_highs_f": gfs_highs,
        "ecmwf_highs_f": ecmwf_highs,
        "icon_highs_f": icon_highs,
        "gem_highs_f": gem_highs,
        "ukmo_highs_f": ukmo_highs,
        "gfs_mean_f": gfs_mean,
        "ecmwf_mean_f": ecmwf_mean,
        "all_highs_f": all_highs,
        "n_gfs": len(gfs_highs),
        "n_ecmwf": len(ecmwf_highs),
        "n_icon": len(icon_highs),
        "n_gem": len(gem_highs),
        "n_ukmo": len(ukmo_highs),
        "combined_mean_f": sum(all_highs) / len(all_highs),
    }


def bucket_probability_by_model(forecast, low_f, high_f, model_weights=None):
    """
    RMSE-weighted-by-MODEL bucket probability (M2 upgrade from equal-weight).

    When `model_weights` is provided (dict keyed by model slug, values summing
    to 1.0), each model's probability contribution is scaled by its weight — so
    a model with lower historical RMSE gets a larger vote. Falls back to equal
    weight when a model has no weight entry or when no weights are given.

    The weight dict uses the same keys as the per-model highs lists below, e.g.
    {"gfs": 0.35, "ecmwf": 0.40, "icon": 0.10, "aifs": 0.10, "gem": 0.03, "ukmo": 0.02}.
    """
    _MODEL_KEYS = [
        ("gfs_highs_f", "gfs"),
        ("ecmwf_highs_f", "ecmwf"),
        ("icon_highs_f", "icon"),
        ("aifs_highs_f", "aifs"),
        ("gem_highs_f", "gem"),
        ("ukmo_highs_f", "ukmo"),
    ]
    probs = []
    weights = []
    for key, slug in _MODEL_KEYS:
        highs = forecast.get(key, [])
        if highs:
            probs.append(bucket_probability(highs, low_f, high_f))
            w = (model_weights or {}).get(slug, 1.0)
            weights.append(w)
    if not probs:
        return bucket_probability(forecast.get("all_highs_f", []), low_f, high_f)
    total_w = sum(weights)
    if total_w <= 0:
        return sum(probs) / len(probs)
    return sum(p * w for p, w in zip(probs, weights)) / total_w


def bucket_probability(highs_f, low_f, high_f):
    """
    Fraction of ensemble members whose daily high falls in [low_f, high_f).
    Open-ended low: low_f == -999 means 'anything below high_f'
    Open-ended high: high_f == 999 means 'anything above low_f'
    """
    count = 0
    for h in highs_f:
        if low_f == -999.0:
            if h <= high_f:
                count += 1
        elif high_f == 999.0:
            if h >= low_f:
                count += 1
        else:
            if low_f <= h < high_f:
                count += 1
    return count / len(highs_f) if highs_f else 0.0


def models_agree(gfs_mean_f, ecmwf_mean_f, max_diff_c=1.5):
    """
    True if GFS and ECMWF mean daily highs are within max_diff_c degrees Celsius of each other.
    Converts the F difference to C for comparison.
    """
    diff_f = abs(gfs_mean_f - ecmwf_mean_f)
    diff_c = diff_f * 5.0 / 9.0
    return diff_c <= max_diff_c


def near_mean_buffer(bucket_low_f, bucket_high_f, combined_mean_f, buffer_f=3.0):
    """
    Returns True if the bucket overlaps with the +/- buffer zone around the mean.
    We skip buckets that straddle the mean — they are the 'coin flip' zone.
    """
    buf_low = combined_mean_f - buffer_f
    buf_high = combined_mean_f + buffer_f

    # Open-ended low means the bucket is "at or below high_f"
    effective_low = -200.0 if bucket_low_f == -999.0 else bucket_low_f
    effective_high = 200.0 if bucket_high_f == 999.0 else bucket_high_f

    # Overlaps if: effective_low < buf_high AND effective_high > buf_low
    return effective_low < buf_high and effective_high > buf_low


def _extract_all_members(ensemble_data, target_date_str):
    """Extract daily highs from ALL member keys regardless of model-name suffix.
    Used for single-model fetches (e.g. AIFS-only) where no suffix is appended."""
    hourly = ensemble_data.get("hourly", {})
    times = hourly.get("time", [])
    target_indices = [i for i, t in enumerate(times) if t.startswith(target_date_str)]
    highs = []
    for key, vals in hourly.items():
        if not key.startswith("temperature_2m_member"):
            continue
        try:
            day_vals = [vals[i] for i in target_indices if vals[i] is not None]
            if day_vals:
                highs.append(_c_to_f(max(day_vals)))
        except (IndexError, TypeError):
            continue
    return highs


def fetch_raw_ensembles_for_city(city_cfg, cfg=None):
    """
    Fetch raw ensemble JSONs (main and aifs) for a city and return them.
    This avoids redundant network calls when evaluating multiple target dates.
    """
    import time
    base_url = "https://ensemble-api.open-meteo.com/v1/ensemble"
    main_models = "gfs_seamless,ecmwf_ifs025,icon_seamless,gem_global,ukmo_global_ensemble_20km"
    aifs_models = "ecmwf_aifs025"
    if cfg:
        base_url = cfg.get("openmeteo_ensemble_url", base_url)
        main_models = cfg.get("openmeteo_models", main_models)

    raw_main = fetch_ensemble(city_cfg, forecast_days=3, base_url=base_url, models=main_models)
    
    raw_aifs = None
    try:
        raw_aifs = fetch_ensemble(city_cfg, forecast_days=3, base_url=base_url, models=aifs_models)
    except Exception as e:
        logger.warning(f"AIFS fetch failed (non-fatal, continuing without it): {e}")

    # Be polite to Open-Meteo API to avoid 429 errors
    time.sleep(1.0)
    
    return {"main": raw_main, "aifs": raw_aifs}


def get_forecast_for_city(city_cfg, target_date_str, cfg=None, raw_ensembles=None):
    """
    Extract daily highs from raw ensembles for the target date.
    If raw_ensembles is not provided, fetches them.
    
    If data/calibration.json has a saved bias correction for this city (see
    lib/calibration.py — derived from comparing past forecasts to actual
    outcomes), it's added to every member's high before returning.
    """
    if raw_ensembles is None:
        raw_ensembles = fetch_raw_ensembles_for_city(city_cfg, cfg)

    raw_main = raw_ensembles["main"]
    raw_aifs = raw_ensembles.get("aifs")

    result = compute_daily_high_ensemble(raw_main, target_date_str)

    # Merge AIFS separately
    if raw_aifs:
        aifs_highs = _extract_all_members(raw_aifs, target_date_str)
        if aifs_highs:
            merged = result["all_highs_f"] + aifs_highs
            result["aifs_highs_f"] = aifs_highs
            result["n_aifs"] = len(aifs_highs)
            result["all_highs_f"] = merged
            result["combined_mean_f"] = sum(merged) / len(merged)
            logger.debug(f"AIFS added {len(aifs_highs)} members (total={len(merged)})")

    # Apply self-correcting bias calibration, if any has been computed for this city.
    try:
        from lib import calibration
        corr = calibration.get_correction_f(city_cfg["name"])
        if corr:
            # Shift every per-model group too (not just the pooled list) so
            # bucket_probability_by_model — which reads the per-model lists —
            # also benefits from the correction.
            for key in ("gfs_highs_f", "ecmwf_highs_f", "icon_highs_f", "aifs_highs_f", "gem_highs_f", "ukmo_highs_f"):
                if result.get(key):
                    result[key] = [h + corr for h in result[key]]
            result["all_highs_f"] = [h + corr for h in result["all_highs_f"]]
            result["gfs_mean_f"] += corr
            result["ecmwf_mean_f"] += corr
            result["combined_mean_f"] += corr
            result["calibration_correction_f"] = corr
            logger.info(f"  Applied {corr:+.2f}°F calibration correction for {city_cfg['name']}")
        # M2: attach per-model RMSE weights so engine can pass them to
        # bucket_probability_by_model without re-reading the calibration file.
        weights = calibration.get_model_weights(city_cfg["name"])
        if weights:
            result["model_weights"] = weights
    except Exception as e:
        logger.warning(f"Calibration lookup failed (non-fatal, using uncorrected forecast): {e}")

    return result


def get_historical_forecast_for_city(city_cfg, target_date_str, cfg=None):
    """
    Reconstruct the archived ensemble forecast for a PAST date (YYYY-MM-DD).

    Same shape as get_forecast_for_city, but queries the ensemble API with
    start_date/end_date so we can measure how the model would have called a day
    that has since been observed. Used by the historical (Mode 2) backtest and
    by calibration.py's per-model weight computation (M2).

    Returns a dict with per-model highs (gfs_highs_f, ecmwf_highs_f, etc.)
    when the archive has sufficient data. Falls back to pooled all_highs_f when
    GFS or ECMWF members are missing (rate-limited or archive-expired response).

    Caveat: the archived run is short-lead, so accuracy from this is an
    optimistic bound on true 2-day-ahead skill.
    """
    base_url = "https://ensemble-api.open-meteo.com/v1/ensemble"
    main_models = "gfs_seamless,ecmwf_ifs025,icon_seamless,gem_global,ukmo_global_ensemble_20km"
    aifs_models = "ecmwf_aifs025"
    if cfg:
        base_url = cfg.get("openmeteo_ensemble_url", base_url)
        main_models = cfg.get("openmeteo_models", main_models)

    raw_main = fetch_ensemble(
        city_cfg, base_url=base_url, models=main_models,
        start_date=target_date_str, end_date=target_date_str,
    )

    # Try rich per-model parse first (needed for RMSE weighting in M2).
    # Falls back to tolerant pooling when the archive only returns partial data.
    try:
        result = compute_daily_high_ensemble(raw_main, target_date_str)
    except ValueError:
        highs = _extract_all_members(raw_main, target_date_str)
        if not highs:
            raise ValueError(f"No ensemble members returned for {target_date_str}")
        result = {
            "all_highs_f": highs,
            "combined_mean_f": sum(highs) / len(highs),
            "n_members": len(highs),
            "gfs_highs_f": [],
            "ecmwf_highs_f": [],
        }

    try:
        raw_aifs = fetch_ensemble(
            city_cfg, base_url=base_url, models=aifs_models,
            start_date=target_date_str, end_date=target_date_str,
        )
        aifs_highs = _extract_all_members(raw_aifs, target_date_str)
        if aifs_highs:
            result["aifs_highs_f"] = aifs_highs
            result["n_aifs"] = len(aifs_highs)
            merged = result["all_highs_f"] + aifs_highs
            result["all_highs_f"] = merged
            result["combined_mean_f"] = sum(merged) / len(merged)
    except Exception as e:
        logger.warning(f"AIFS historical fetch failed (non-fatal): {e}")

    return result
