"""
lib/nbm.py
NBM-aligned bucket probability veto.

Uses the raw ensemble members already fetched from Open-Meteo (GFS, ECMWF,
ICON, GEM, UKMO) to compute what fraction of members put the daily high inside
the target bucket.  These are the same models blended in NOAA's National Blend
of Models — so this raw-member fraction approximates NBM temperature percentile
probability without grib2 parsing or boto3.

Veto logic: if fewer than NBM_MIN_PROB of all members agree the bucket happens,
the YES bet is blocked even if the RMSE-weighted ensemble edge clears threshold.
This catches cases where one high-RMSE-weight model is an outlier while the rest
of the ensemble strongly disagrees.
"""

NBM_MIN_PROB = 0.03  # default: veto YES if < 3% of members say bucket happens


def get_raw_member_probability(forecast, bucket_low_f, bucket_high_f,
                               is_oe_low=False, is_oe_high=False):
    """
    Count fraction of ensemble members whose predicted daily high falls in bucket.

    Args:
        forecast: dict from forecasts.py containing 'all_highs_f' (list of floats,
                  one per ensemble member from GFS/ECMWF/ICON/GEM/UKMO)
        bucket_low_f, bucket_high_f: bucket boundaries in °F
        is_oe_low:  open-ended low  ("X°F or below")
        is_oe_high: open-ended high ("X°F or above")

    Returns float 0.0–1.0, or None if no member data available.
    """
    members = forecast.get("all_highs_f", [])
    if not members:
        return None

    count = 0
    for high in members:
        if is_oe_low:
            if high <= bucket_high_f:
                count += 1
        elif is_oe_high:
            if high >= bucket_low_f:
                count += 1
        else:
            if bucket_low_f <= high < bucket_high_f:
                count += 1

    return count / len(members)


def should_veto_yes(forecast, market, min_prob=None):
    """
    Return True if raw member count is too low to support a YES bet.

    Args:
        forecast: dict from forecasts.py
        market:   dict with bucket_low_f, bucket_high_f, is_open_ended_low/high
        min_prob: override for NBM_MIN_PROB (uses config nbm_min_member_prob_pct)

    Returns True → engine should block the YES bet.
    Returns False → either enough members agree, or no member data (no veto).
    """
    if min_prob is None:
        min_prob = NBM_MIN_PROB
    if min_prob <= 0:
        return False  # disabled

    prob = get_raw_member_probability(
        forecast,
        float(market.get("bucket_low_f", -999)),
        float(market.get("bucket_high_f", 999)),
        is_oe_low=str(market.get("is_open_ended_low", "False")).lower() in ("true", "1"),
        is_oe_high=str(market.get("is_open_ended_high", "False")).lower() in ("true", "1"),
    )

    if prob is None:
        return False  # no data — don't veto

    return prob < min_prob
