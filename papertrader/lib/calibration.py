"""
lib/calibration.py — self-correcting bias adjustment for the weather forecast.

Why this exists: the backtest showed Atlanta's ensemble forecast running
systematically COLD (every one of the last 4 days, by 2-8°F) while Dallas was
fine. That's a bias, not noise — likely the model under-representing the
airport/tarmac heat-island effect at KATL. Rather than hand-tune a fudge
factor, this module measures the bias from real outcomes and applies a damped
correction automatically. Re-run `python papertrader.py calibrate` periodically
(e.g. weekly) to refresh it as more data comes in — that's the "self
correcting" part.

Safety: correction is shrunk toward zero when the sample is small
(shrinkage = n / (n + K)), so 4 days of data can only ever produce a modest
correction, not a full overreaction. As more days accumulate, the correction
converges toward the true measured bias.

data/calibration.json shape:
  {"Atlanta": {"raw_bias_f": -4.28, "n_days": 4, "shrinkage": 0.29,
                "correction_f": 1.22, "updated_at": "..."},
   "Dallas":  {...}}

correction_f is ADDED to every ensemble member's forecast high before bucket
probabilities are computed (a forecast that ran cold gets warmed up).
"""

import os
import json
import math
import time
import logging
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("calibration")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
CALIBRATION_PATH = os.path.join(DATA_DIR, "calibration.json")

# Shrinkage constant: with K days of "pseudo-data" assumed at zero bias,
# shrinkage = n/(n+K). At n=4, K=10 -> shrinkage ≈ 0.29 (29% of raw bias
# applied). At n=20 -> shrinkage ≈ 0.67. At n=50 -> ≈ 0.83. This keeps small
# samples cautious while letting the correction strengthen as data accumulates.
SHRINKAGE_K = 10.0

# Don't bother correcting tiny, probably-noise biases.
MIN_BIAS_TO_CORRECT_F = 0.5


def _compute_per_model_mae(city_cfg, cfg, days=7):
    """
    Fetch the last `days` days of archived ensemble forecasts and compute MAE
    per model (GFS, ECMWF, ICON, AIFS, GEM, UKMO) versus the observed high.

    Returns dict: {slug: mae_f} for models with >= 2 days of data.
    Open-Meteo's ensemble archive only retains ~5-6 days, so `days` is a ceiling.
    """
    from lib import forecasts, settlement

    today = datetime.now(timezone.utc).date()
    dates = [(today - timedelta(days=d)).isoformat() for d in range(2, days + 2)]

    # Accumulate (error²) per model slug
    sq_errors = {slug: [] for slug in ("gfs", "ecmwf", "icon", "aifs", "gem", "ukmo")}
    _MODEL_KEYS = [
        ("gfs_highs_f", "gfs"),
        ("ecmwf_highs_f", "ecmwf"),
        ("icon_highs_f", "icon"),
        ("aifs_highs_f", "aifs"),
        ("gem_highs_f", "gem"),
        ("ukmo_highs_f", "ukmo"),
    ]

    consecutive_misses = 0
    for ds in dates:
        if consecutive_misses >= 2:
            break
        actual = settlement.fetch_observed_high(city_cfg, ds)[0]
        if actual is None:
            continue
        try:
            fc = forecasts.get_historical_forecast_for_city(city_cfg, ds, cfg)
        except Exception as e:
            logger.debug(f"Model weight history failed for {city_cfg['name']} {ds}: {e}")
            consecutive_misses += 1
            continue
        consecutive_misses = 0
        time.sleep(0.3)
        for key, slug in _MODEL_KEYS:
            highs = fc.get(key, [])
            if highs:
                model_mean = sum(highs) / len(highs)
                sq_errors[slug].append((model_mean - actual) ** 2)

    mae = {}
    for slug, errs in sq_errors.items():
        if len(errs) >= 2:
            mae[slug] = math.sqrt(sum(errs) / len(errs))  # RMSE (same units as bias)
    return mae


def compute_model_weights(cfg, days=7):
    """
    Compute inverse-RMSE model weights per city and merge them into the saved
    calibration.json. Called automatically by compute_and_save (M2).

    Weight formula: w_m = (1/RMSE_m) / sum(1/RMSE_i) — so a model with half
    the error gets twice the vote. Stored as a dict:
      {"gfs": 0.35, "ecmwf": 0.40, "icon": 0.10, ...}
    """
    cal = load_calibration()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for city_cfg in cfg.get("cities", []):
        name = city_cfg["name"]
        mae = _compute_per_model_mae(city_cfg, cfg, days=days)
        if not mae:
            continue
        inv = {slug: 1.0 / rmse for slug, rmse in mae.items() if rmse > 0}
        total_inv = sum(inv.values())
        if total_inv <= 0:
            continue
        weights = {slug: round(v / total_inv, 4) for slug, v in inv.items()}
        entry = cal.setdefault(name, {})
        entry["model_weights"] = weights
        entry["model_weights_updated_at"] = now
        logger.info(f"  {name} model weights: " +
                    ", ".join(f"{s}={w:.3f}" for s, w in sorted(weights.items())))

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CALIBRATION_PATH, "w", encoding="utf-8") as f:
        json.dump(cal, f, indent=2)
    return cal


def get_model_weights(city_name):
    """Return the per-model weight dict for a city, or None if not computed yet."""
    cal = load_calibration()
    entry = cal.get(city_name)
    return (entry or {}).get("model_weights")


def compute_and_save(cfg, days=14):
    """
    Run the historical model-accuracy check (reuses lib.backtest), derive a
    damped correction per city, and persist it to data/calibration.json.
    Returns the calibration dict.
    """
    from lib import backtest  # local import to avoid a circular import at module load

    hist = backtest.run_historical_backtest(cfg, days=days)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    calibration = {}
    for city, c in hist["per_city"].items():
        n = c.get("n_days", 0)
        if n == 0:
            continue
        raw_bias = c["bias_f"]
        shrinkage = n / (n + SHRINKAGE_K)
        correction = round(-raw_bias * shrinkage, 2)  # negate: cold bias -> positive correction
        if abs(raw_bias) < MIN_BIAS_TO_CORRECT_F:
            correction = 0.0
        calibration[city] = {
            "raw_bias_f": raw_bias,
            "n_days": n,
            "shrinkage": round(shrinkage, 2),
            "correction_f": correction,
            "updated_at": now,
        }

    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CALIBRATION_PATH, "w", encoding="utf-8") as f:
        json.dump(calibration, f, indent=2)
    logger.info(f"Calibration saved: {CALIBRATION_PATH}")

    # M2: also compute per-model RMSE weights using available archive data.
    # model_weights are stored inside the same calibration.json entries.
    try:
        compute_model_weights(cfg, days=min(days, 7))
    except Exception as e:
        logger.warning(f"Model weight computation failed (non-fatal): {e}")

    return load_calibration()  # return the fully merged dict (bias + weights)


def load_calibration():
    """Return the saved calibration dict, or {} if none exists yet."""
    if not os.path.exists(CALIBRATION_PATH):
        return {}
    try:
        with open(CALIBRATION_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load calibration.json: {e}")
        return {}


def get_correction_f(city_name):
    """Convenience: just the correction (°F) to add for one city, 0.0 if none."""
    cal = load_calibration()
    entry = cal.get(city_name)
    return entry["correction_f"] if entry else 0.0


def print_summary(calibration):
    print("\n" + "=" * 60)
    print("  CALIBRATION  (self-correcting forecast bias)")
    print("=" * 60)
    if not calibration:
        print("  No calibration data yet — need at least 1 day of history.")
    for city, c in calibration.items():
        direction = "warming up" if c["correction_f"] > 0 else (
            "cooling down" if c["correction_f"] < 0 else "no correction")
        print(f"  {city}:")
        print(f"    Measured bias : {c['raw_bias_f']:+.2f}°F over {c['n_days']} days")
        print(f"    Shrinkage     : {c['shrinkage']*100:.0f}% (more days -> stronger correction)")
        print(f"    Applying      : {c['correction_f']:+.2f}°F to every forecast ({direction})")
    print("=" * 60)
