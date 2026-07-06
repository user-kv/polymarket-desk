"""
lib/cities.py — builds the multi-city config from live Polymarket data.

Polymarket runs temperature markets for far more cities than this bot tracks at
any one time. This module:
  1. Scans the Gamma API for active temperature markets (no city filter) and
     pulls each one's resolution station (ICAO code), found either in the
     `resolutionSource` Wunderground URL or, for NOAA-sourced markets, in a
     `weather.gov/wrh/timeseries?site=XXXX` link inside the description.
  2. Looks up each ICAO code's lat/lon/timezone from the free mwgg/Airports
     dataset (one-time download, cached to data/airports_cache.json).
  3. Returns city-config dicts in the shape lib/forecasts.py expects.

PHASE-1 SCOPE (2026-06-16): Polymarket actually runs temperature markets in ~43
cities, but ~34 of them use Celsius + a different bucket format (a single
discrete value like "be 28C", and some are LOWEST-temperature markets rather
than highest). Originally `fetch_resolution_map` only returned cities whose
markets matched the *exact* format then supported: "highest temperature ...
between X-Y°F" / "X°F or above/below" — the 9 US cities (Atlanta, Austin,
Dallas, Denver, Houston, LA, Miami, NYC, SF).

2026-07 EXPANSION: lib/polymarket.py's `_parse_bucket` now also parses °C
buckets (range / open-ended / single discrete value) and detects
"lowest temperature" markets, converting everything to °F at parse time;
lib/forecasts.py now has a daily-LOW ensemble path alongside daily-HIGH. So
the format filter below is lifted — any city whose question contains
"highest temperature" or "lowest temperature" and parses successfully is
included, regardless of °F/°C or high/low.
"""

import os
import re
import json
import time
import logging
import urllib.request

logger = logging.getLogger("cities")

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
AIRPORTS_CACHE = os.path.join(DATA_DIR, "airports_cache.json")
AIRPORTS_URL = "https://raw.githubusercontent.com/mwgg/Airports/master/airports.json"

# Matches "... highest/lowest temperature in <city> be ...". Used to find
# candidate city names for both °F and °C, high and low markets.
CITY_NAME_RE = re.compile(r"(?:highest|lowest) temperature in ([a-z\s\.]+?) be")


def _get(url, timeout=20):
    req = urllib.request.Request(
        url, headers={"User-Agent": "PaperTrader/1.0", "Accept": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _load_airports():
    """One-time download (~9MB) of ICAO -> lat/lon/tz, cached locally."""
    if os.path.exists(AIRPORTS_CACHE):
        with open(AIRPORTS_CACHE, encoding="utf-8") as f:
            return json.load(f)
    logger.info("Downloading airport database (one-time)...")
    data = _get(AIRPORTS_URL, timeout=60)
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(AIRPORTS_CACHE, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return data


def _extract_icao(text):
    """Pull an ICAO code out of a Wunderground URL or a weather.gov site= link."""
    if not text:
        return None
    # Wunderground history URLs end in the ICAO code, e.g. .../us/tx/dallas/KDAL
    m = re.search(r"/([A-Z]{4})$", text.strip())
    if m:
        return m.group(1)
    # NOAA-sourced markets link to weather.gov/wrh/timeseries?site=XXXX
    m = re.search(r"site=([A-Z]{4})", text)
    if m:
        return m.group(1)
    return None


def fetch_resolution_map(cfg):
    """
    Scan Gamma API (no city filter) for active 'highest/lowest temperature in X'
    markets in any supported bucket format (°F or °C, range/open-ended/single
    discrete value). Format validity is delegated to lib.polymarket._parse_bucket
    — a market is included only if that parser can actually make sense of it.
    Returns {city_name_lowercase: icao_code}.
    """
    from lib.polymarket import _parse_bucket
    base = cfg.get("gamma_api_base", "https://gamma-api.polymarket.com")
    page_size = cfg.get("scan_page_size", 100)
    max_pages = cfg.get("scan_max_offset_pages", 50)
    out = {}
    for page in range(max_pages):
        offset = page * page_size
        url = (
            f"{base}/markets?limit={page_size}&active=true&closed=false"
            f"&offset={offset}&order=volume&ascending=false"
        )
        try:
            batch = _get(url)
        except Exception as e:
            logger.warning(f"Gamma API error at offset {offset}: {e}")
            break
        if not batch:
            break
        for m in batch:
            q = m.get("question", "")
            ql = q.lower()
            if "highest temperature" not in ql and "lowest temperature" not in ql:
                continue
            if _parse_bucket(q) is None:
                continue  # unsupported bucket format — skip rather than mis-evaluate
            mm = CITY_NAME_RE.search(ql)
            if not mm:
                continue
            city = mm.group(1).strip()
            if city in out:
                continue
            icao = _extract_icao(m.get("resolutionSource") or "") or _extract_icao(
                m.get("description") or ""
            )
            if icao:
                out[city] = icao
            else:
                logger.warning(f"Could not find ICAO code for {city} ({q!r})")
        time.sleep(0.05)
    logger.info(f"Found {len(out)} cities with a supported bucket format (°F/°C, high/low)")
    return out


def build_city_configs(resolution_map):
    """Look up each ICAO code's lat/lon/tz; return list of city-config dicts."""
    airports = _load_airports()
    out = []
    for city_name, icao in sorted(resolution_map.items()):
        airport = airports.get(icao)
        if not airport:
            logger.warning(f"No airport data for {city_name} ({icao}), skipping")
            continue
        out.append({
            "name": city_name.title(),
            "station": icao,
            "lat": round(airport["lat"], 4),
            "lon": round(airport["lon"], 4),
            "polymarket_name": city_name,
            "tz": "auto",
            "wunderground_station": icao,
            "resolution_source": f"https://www.wunderground.com/history/daily/{icao.lower()}",
        })
    return out


def build_and_apply(cfg, config_path):
    """One-shot: fetch resolution map, build configs, write into config.json."""
    res_map = fetch_resolution_map(cfg)
    cities = build_city_configs(res_map)
    new_cfg = dict(cfg)
    new_cfg["cities"] = cities
    new_cfg["_cities_note"] = (
        "Auto-built from live Polymarket data via lib/cities.py. Since the "
        "2026-07 expansion, both °F and °C bucket formats and both "
        "highest- and lowest-temperature markets are supported "
        "(lib/polymarket.py's _parse_bucket + lib/forecasts.py's daily-low "
        "ensemble path)."
    )
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(new_cfg, f, indent=2)
    logger.info(f"Wrote {len(cities)} cities to {config_path}")
    return cities
