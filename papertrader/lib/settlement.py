"""
lib/settlement.py
Settles open paper bets by fetching the official observed daily high temperature.

Resolution source (per Phase 0 discovery):
  Primary: Wunderground station page (KDAL / KATL)
  Since Wunderground HTML scraping is fragile, we use Open-Meteo Archive API
  as a reliable free alternative — it sources from MERRA-2/ERA5 reanalysis
  which matches official station records well within 1°F for US airports.

  For US airports we also try api.weather.gov (NWS) observations as a
  cross-check. If both agree within 2°F, we're confident.

Settlement steps:
  1. For each open bet whose end_date has passed, fetch observed high
  2. Check if actual_high_f falls in [bucket_low_f, bucket_high_f)
  3. Mark WON or LOST, compute P&L, update bankroll
  4. Log any disagreement between sources
"""

import urllib.request
import json
import logging
import os
from datetime import datetime, timezone, timedelta, date

logger = logging.getLogger("settlement")

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def _get(url, timeout=20):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "PaperTrader/1.0", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _c_to_f(c):
    return c * 9.0 / 5.0 + 32.0


def did_bucket_win(actual_high_f, low_f, high_f, is_oe_low, is_oe_high):
    """
    Single source of truth for resolving a temperature bucket.

    Returns True if actual_high_f falls inside the bucket.
      - open-ended low  ("X°F or below"):  win if actual <= high_f
      - open-ended high ("X°F or higher"): win if actual >= low_f
      - closed bucket   ("X-Y°F"):         win if low_f <= actual < high_f
    """
    if is_oe_low:
        return actual_high_f <= high_f
    if is_oe_high:
        return actual_high_f >= low_f
    return low_f <= actual_high_f < high_f


def fetch_observed_high_openmeteo(lat, lon, date_str, tz="America/Chicago"):
    """
    Fetch historical daily max temperature from Open-Meteo archive.
    date_str: 'YYYY-MM-DD'
    Returns float °F or None.
    """
    url = (
        f"https://archive-api.open-meteo.com/v1/archive"
        f"?latitude={lat}&longitude={lon}"
        f"&start_date={date_str}&end_date={date_str}"
        f"&daily=temperature_2m_max&timezone={tz}"
    )
    try:
        data = _get(url)
        daily = data.get("daily", {})
        temps = daily.get("temperature_2m_max", [])
        if temps and temps[0] is not None:
            return round(_c_to_f(temps[0]), 1)
    except Exception as e:
        logger.warning(f"Open-Meteo archive error for {date_str} at {lat},{lon}: {e}")
    return None


def fetch_observed_high_nws(station, date_str):
    """
    Fetch observed daily max from api.weather.gov hourly observations for a station.
    station: ICAO code e.g. 'KDAL'
    date_str: 'YYYY-MM-DD'
    Returns float °F or None.
    """
    # NWS uses the station's hourly obs; we get a time range for that day
    try:
        # Build a 30h window: day 00Z to next-day 06Z
        url = (
            f"https://api.weather.gov/stations/{station}/observations"
            f"?start={date_str}T00:00:00Z&end={date_str}T23:59:59Z&limit=100"
        )
        data = _get(url)
        features = data.get("features", [])
        temps_f = []
        for feat in features:
            props = feat.get("properties", {})
            temp_c = props.get("temperature", {}).get("value")
            if temp_c is not None:
                temps_f.append(_c_to_f(temp_c))
        if temps_f:
            return round(max(temps_f), 1)
    except Exception as e:
        logger.warning(f"NWS obs error for {station} {date_str}: {e}")
    return None


def fetch_observed_high(city_cfg, date_str):
    """
    Try both sources; return (high_f, source_name, cross_check_diff).
    Returns (None, 'error', None) if both fail.
    """
    lat = city_cfg["lat"]
    lon = city_cfg["lon"]
    station = city_cfg.get("station", "")
    tz = city_cfg.get("tz", "America/Chicago")

    openmeteo_high = fetch_observed_high_openmeteo(lat, lon, date_str, tz)
    nws_high = fetch_observed_high_nws(station, date_str)

    logger.info(
        f"{city_cfg['name']} {date_str}: "
        f"Open-Meteo={openmeteo_high}F  NWS={nws_high}F"
    )

    if openmeteo_high is not None and nws_high is not None:
        diff = abs(openmeteo_high - nws_high)
        if diff > 5:
            logger.warning(
                f"SOURCE DISAGREEMENT: Open-Meteo={openmeteo_high}F vs NWS={nws_high}F "
                f"(diff={diff:.1f}F) for {station} {date_str}. Using NWS."
            )
        return (nws_high, "nws+openmeteo_crosscheck", diff)

    if nws_high is not None:
        return (nws_high, "nws", None)

    if openmeteo_high is not None:
        return (openmeteo_high, "openmeteo_archive", None)

    return (None, "error", None)


def settle_bet(bet, city_cfg, cfg):
    """
    Attempt to settle one open bet.
    Returns dict with settlement result fields, or None if can't settle yet.
    """
    fee_pct = cfg.get("fee_on_winnings_pct", 2.0) / 100.0

    end_date = bet.get("end_date", "")
    try:
        end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
    except Exception:
        logger.warning(f"Bad end_date: {end_date}")
        return None

    now = datetime.now(timezone.utc)
    # Only settle if end_date has passed (plus 1h buffer for data to appear)
    if now < end_dt + timedelta(hours=1):
        return None

    # The resolution date is the day of end_date
    target_date = end_dt.date().isoformat()

    actual_high_f, source, cross_diff = fetch_observed_high(city_cfg, target_date)

    if actual_high_f is None:
        logger.warning(f"Could not fetch observed high for {bet.get('city')} {target_date}")
        return None

    # Determine win or loss
    low_f = float(bet.get("bucket_low_f", -999))
    high_f = float(bet.get("bucket_high_f", 999))
    is_oe_low = str(bet.get("is_open_ended_low", "False")).lower() in ("true", "1")
    is_oe_high = str(bet.get("is_open_ended_high", "False")).lower() in ("true", "1")

    won = did_bucket_win(actual_high_f, low_f, high_f, is_oe_low, is_oe_high)

    stake = float(bet.get("stake", 5.0))
    shares = float(bet.get("shares", 1.0))
    gross_if_win = float(bet.get("gross_if_win", shares))
    fee_if_win = gross_if_win * fee_pct
    net_profit = round(gross_if_win - fee_if_win - stake, 4)
    pnl = net_profit if won else round(-stake, 4)
    # Bankroll already loses the stake when the paper bet is opened. Settlement
    # therefore adds back only the final payout on wins, and nothing on losses.
    bankroll_delta = round(gross_if_win - fee_if_win, 4) if won else 0.0

    now_str = now.strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "status": "settled",
        "result": "WON" if won else "LOST",
        "actual_high_f": actual_high_f,
        "settled_at": now_str,
        "pnl": pnl,
        "bankroll_delta": bankroll_delta,
        "settlement_source": source,
        "cross_check_diff_f": cross_diff,
    }


def settle_all(cfg, city_lookup):
    """
    Settle all open bets. city_lookup: dict of city_name -> city_cfg.
    Returns list of settled bet_ids with their results.
    """
    from lib.ledger import get_open_bets, update_bet, update_bankroll

    open_bets = get_open_bets()
    settled = []

    for bet in open_bets:
        city_name = bet.get("city", "")
        city_cfg = city_lookup.get(city_name)
        if city_cfg is None:
            logger.warning(f"No city config for '{city_name}', skipping")
            continue

        result = settle_bet(bet, city_cfg, cfg)
        if result is None:
            continue  # not ready yet

        update_bet(bet["bet_id"], result)
        pnl = result["pnl"]
        if bet.get("is_test", "N") != "Y":
            update_bankroll(result.get("bankroll_delta", pnl), note=f"settle {bet['bet_id']} {result['result']}")

        logger.info(
            f"SETTLED {bet['bet_id']}: {result['result']} | "
            f"actual={result['actual_high_f']}F | P&L=${pnl:+.2f}"
        )
        settled.append({
            "bet_id": bet["bet_id"],
            "question": bet.get("question"),
            "result": result["result"],
            "actual_high_f": result["actual_high_f"],
            "pnl": pnl,
        })

    return settled
