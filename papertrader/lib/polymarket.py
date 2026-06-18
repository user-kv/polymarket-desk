"""
lib/polymarket.py
Fetches weather temperature markets from Gamma API and live ask prices from CLOB.

Key facts discovered in Phase 0 (June 2026):
- Markets look like: "Will the highest temperature in Dallas be between 96-97°F on June 13?"
- Resolution source: Wunderground KDAL/KATL station (NOT NWS CLI)
- Slug pattern: highest-temperature-in-dallas-on-june-13-2026-96-97f
- clobTokenIds[0] = YES token, clobTokenIds[1] = NO token
- CLOB asks are sorted highest-price first; best ask = lowest price in list
- Gamma API paginates at 100 per page; no reliable tag/keyword filter — scan by offset
"""

import urllib.request
import urllib.parse
import json
import time
import logging
import re
from datetime import datetime, timezone

logger = logging.getLogger("polymarket")


def _get(url, timeout=15):
    """HTTP GET with JSON return. Raises on non-200."""
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "PaperTrader/1.0", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def _celsius_to_f(c):
    return c * 9 / 5 + 32


def _to_float(v, default=0.0):
    """Tolerant float parse for Gamma volume/liquidity (may be str, None, or num)."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def fetch_weather_markets(cfg, cutoff_hours=48):
    """
    Scan Gamma API pages and return all active temperature markets for
    cities listed in config, resolving within cutoff_hours from now.

    Returns list of dicts with keys:
        city, question, slug, end_date, yes_token, no_token,
        bucket_low_f, bucket_high_f, is_open_ended_low, is_open_ended_high,
        resolution_source, market_id, event_id, event_slug
    """
    cfg_cities = {c["polymarket_name"].lower(): c for c in cfg["cities"]}
    now_utc = datetime.now(timezone.utc)
    results = []
    seen_slugs = set()
    base = cfg.get("gamma_api_base", "https://gamma-api.polymarket.com")
    page_size = cfg.get("scan_page_size", 100)
    max_pages = cfg.get("scan_max_offset_pages", 50)

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
            logger.debug(f"Empty page at offset {offset}, stopping scan")
            break

        for m in batch:
            question = m.get("question", "")
            slug = m.get("slug", "")

            # Only daily-high markets are supported. Daily-low markets need a
            # separate low-temperature forecast path and must not be scored as highs.
            q_lower = question.lower()
            if "highest temperature" not in q_lower:
                continue
            matched_city = None
            for city_name, city_cfg in cfg_cities.items():
                if city_name in q_lower:
                    matched_city = city_cfg
                    break

            if not matched_city or slug in seen_slugs:
                continue

            # Parse end date and check within cutoff
            end_str = m.get("endDate", "")
            try:
                end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
            except Exception:
                continue

            hours_left = (end_dt - now_utc).total_seconds() / 3600
            if hours_left < 0 or hours_left > cutoff_hours:
                continue  # already expired or too far out

            # Parse bucket bounds from question text
            bucket = _parse_bucket(question)
            if bucket is None:
                logger.debug(f"Could not parse bucket from: {question}")
                continue

            tokens = m.get("clobTokenIds", [])
            # clobTokenIds comes as a JSON string from the Gamma API, not a list
            if isinstance(tokens, str):
                try:
                    tokens = json.loads(tokens)
                except Exception:
                    tokens = []
            if len(tokens) < 2:
                continue

            event_info = {}
            events = m.get("events", [])
            if events:
                event_info = {
                    "event_id": events[0].get("id", ""),
                    "event_slug": events[0].get("slug", ""),
                }

            seen_slugs.add(slug)
            results.append({
                "city": matched_city["name"],
                "station": matched_city["station"],
                "question": question,
                "slug": slug,
                "market_id": m.get("id", ""),
                "end_date": end_str,
                "end_dt": end_dt,
                "hours_left": round(hours_left, 1),
                "yes_token": tokens[0],
                "no_token": tokens[1],
                "bucket_low_f": bucket["low_f"],
                "bucket_high_f": bucket["high_f"],
                "is_open_ended_low": bucket["is_open_ended_low"],
                "is_open_ended_high": bucket["is_open_ended_high"],
                "resolution_source": m.get(
                    "resolutionSource",
                    f"https://www.wunderground.com/history/daily/us/{matched_city['station'].lower()}"
                ),
                # Captured for the desk-layer liquidity rule (research round 5): avoid
                # illiquid markets you can't realistically fill, and the hyper-saturated
                # ones where pro bots have already closed the latency window.
                "volume_num": _to_float(m.get("volumeNum", m.get("volume"))),
                "liquidity_num": _to_float(m.get("liquidityNum", m.get("liquidity"))),
                **event_info,
            })

        time.sleep(0.05)  # polite pacing

    logger.info(f"Found {len(results)} weather markets within {cutoff_hours}h")
    return results


def _parse_bucket(question):
    """
    Parse temperature bucket bounds (in °F) from a question string.
    Handles patterns like:
      "...between 96-97°F..."
      "...96°F or higher..."
      "...83°F or below..."
      "...between 90-91°F..."

    Returns dict with keys: low_f, high_f, is_open_ended_low, is_open_ended_high
    Returns None if parse fails.
    """
    q = question.lower()

    # Pattern: "between X-Y°F" or "between X and Y°F"
    m = re.search(r"between\s+([\d.]+)[-\s]+(?:and\s+)?([\d.]+)\s*[°f]", q)
    if m:
        low = float(m.group(1))
        high = float(m.group(2))
        return {
            "low_f": low, "high_f": high,
            "is_open_ended_low": False, "is_open_ended_high": False
        }

    # Pattern: "X°F or higher" / "X°F or above"
    m = re.search(r"([\d.]+)\s*[°f]\s*or\s+(?:higher|above)", q)
    if m:
        low = float(m.group(1))
        return {
            "low_f": low, "high_f": 999.0,
            "is_open_ended_low": False, "is_open_ended_high": True
        }

    # Pattern: "X°F or below" / "X°F or lower"
    m = re.search(r"([\d.]+)\s*[°f]\s*or\s+(?:below|lower)", q)
    if m:
        high = float(m.group(1))
        return {
            "low_f": -999.0, "high_f": high,
            "is_open_ended_low": True, "is_open_ended_high": False
        }

    # Pattern: "X°F or below" written differently (e.g. 83forbelow in slug)
    m = re.search(r"([\d.]+)\s*[°°f]+\s*or\s*below", question.lower())
    if m:
        high = float(m.group(1))
        return {
            "low_f": -999.0, "high_f": high,
            "is_open_ended_low": True, "is_open_ended_high": False
        }

    return None


def fetch_best_ask(yes_token, cfg=None):
    """
    Returns the lowest ask price for the YES token from the CLOB order book.
    This is what you'd actually pay to buy YES shares.
    Returns float (e.g. 0.13) or None if book is empty/error.
    """
    base = "https://clob.polymarket.com"
    if cfg:
        base = cfg.get("clob_api_base", base)
    url = f"{base}/book?token_id={yes_token}"
    try:
        book = _get(url)
        asks = book.get("asks", [])
        if not asks:
            return None
        prices = [float(a["price"]) for a in asks if float(a.get("size", 0)) > 0]
        if not prices:
            return None
        return min(prices)  # lowest ask = cheapest price to buy YES
    except Exception as e:
        logger.warning(f"CLOB error for token {yes_token[:12]}...: {e}")
        return None


def enrich_markets_with_prices(markets, cfg=None):
    """
    Add 'ask_price' to each market dict by calling the CLOB.
    Modifies in place. Returns the list.
    """
    for m in markets:
        ask = fetch_best_ask(m["yes_token"], cfg)
        m["ask_price"] = ask
        if ask is None:
            logger.warning(f"No ask price for {m['question']}")
        time.sleep(0.05)
    return markets
