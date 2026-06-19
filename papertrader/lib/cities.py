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
than highest) that lib/polymarket.py's `_parse_bucket` and lib/forecasts.py's
daily-HIGH-only ensemble don't support yet. Adding those without that work
would silently mis-evaluate them. So `fetch_resolution_map` only returns
cities whose markets match the *exact* format already supported: "highest
temperature ... between X-Y°F" / "X°F or above/below" — currently 9 US cities
(Atlanta, Austin, Dallas, Denver, Houston, LA, Miami, NYC, SF) vs. the 2
(Dallas, Atlanta) previously hard-coded. Extending to the Celsius/low-temp
cities is a separate follow-up (new bucket parser + a daily-LOW ensemble
function) — see the note left in config.json's `_cities_note`.
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

# Matches "... highest temperature in <city> be ..." with a trailing °F bucket
# of the supported shapes (range / open-ended). Only used to find candidate
# city names; the actual bucket-format gate is QUESTION_FAHRENHEIT_HIGH_RE.
CITY_NAME_RE = re.compile(r"highest temperature in ([a-z\s\.]+?) be")


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
    Scan Gamma API (no city filter) for active 'highest temperature in X' °F
    markets in the already-supported range/open-ended bucket format.
    Returns {city_name_lowercase: icao_code}.
    """
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
            if "highest temperature" not in ql or "°f" not in ql:
                continue  # phase-1: Fahrenheit highest-temp markets only
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
    logger.info(f"Found {len(out)} cities with a supported °F bucket format")
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
        "Auto-built 2026-06-16 from live Polymarket data via lib/cities.py "
        "(9 US cities, Fahrenheit highest-temp range/open-ended buckets only). "
        "Polymarket also runs ~34 more cities using Celsius + single-value "
        "buckets and/or LOWEST-temperature markets — not yet supported by "
        "lib/polymarket.py's bucket parser or the daily-high-only ensemble. "
        "Re-run `python papertrader.py cities --apply` after that support "
        "lands to pick those up too."
    )
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(new_cfg, f, indent=2)
    logger.info(f"Wrote {len(cities)} cities to {config_path}")
    return cities
