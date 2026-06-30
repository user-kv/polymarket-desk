"""Two-phase CPI market sensor: snapshot + settle (B1).

POINT-IN-TIME HONESTY LAW (non-negotiable):
  - p_model is computed at snapshot from data available THEN (released CPI history
    up to the last published print + today's nowcast) and FROZEN into the row.
  - p_model NEVER sees the actual print it is forecasting.
  - settle fills y from BLS only AFTER the release date.
  - snapshot is idempotent: a market already carrying meta.p_model is never re-forecast.
  - y is NEVER read at snapshot time.

Store: institute/data/cpi_markets.jsonl
"""
import datetime
import json
import os
import urllib.request
import urllib.error

from institute.corpus.store import append_jsonl, load_jsonl, overwrite_jsonl
from institute.verticals.cpi.parse import parse_market
from institute.verticals.cpi import data as _data

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
CPI_STORE = os.path.join(BASE_DIR, "data", "cpi_markets.jsonl")

_GAMMA_BASE = "https://gamma-api.polymarket.com"


# ---------------------------------------------------------------------------
# Gamma helpers (same double-parse as crypto sensor)
# ---------------------------------------------------------------------------

def _gamma_get(path, base=_GAMMA_BASE, timeout=20):
    """Thin urllib GET -> parsed JSON. Raises on HTTP/network error."""
    url = base.rstrip("/") + path
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "institute/1.0", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _parse_json_field(raw):
    """Double-parse: raw may already be a list or may be a JSON string."""
    if isinstance(raw, list):
        return raw
    return json.loads(raw)


def _parse_utc_iso(s):
    """Parse ISO8601 Z-suffix string -> datetime (utc, naive)."""
    s = s.rstrip("Z").rstrip("z")
    if "." in s:
        s = s[:19]
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return datetime.datetime.strptime(s[:10], "%Y-%m-%d")


# ---------------------------------------------------------------------------
# Phase 0: fetch active CPI markets from Gamma
# ---------------------------------------------------------------------------

def fetch_active_cpi(max_pages=15, _get=_gamma_get):
    """Page Gamma active markets; return list of normalised CPI dicts.

    Keeps a market iff:
    - parse_market returns non-None (US CPI MoM with parseable bounds)
    - clobTokenIds double-parses to >= 2 tokens
    - outcomePrices parses to a 2-float list
    """
    results = []

    for page in range(max_pages):
        offset = page * 100
        path = (
            f"/markets?limit=100&active=true&closed=false"
            f"&order=volume&ascending=false&offset={offset}"
        )
        try:
            data = _get(path)
        except Exception:
            break

        if not data:
            break

        for m in data:
            try:
                question = m.get("question", "") or ""
                slug = m.get("slug", "") or ""

                parsed = parse_market(question, slug)
                if parsed is None:
                    continue

                # clobTokenIds double-parse
                clob_raw = m.get("clobTokenIds")
                if clob_raw is None:
                    continue
                tokens = _parse_json_field(clob_raw)
                if len(tokens) < 2:
                    continue

                # outcomePrices double-parse
                prices_raw = m.get("outcomePrices")
                if prices_raw is None:
                    continue
                prices = [float(p) for p in _parse_json_field(prices_raw)]
                if len(prices) < 2:
                    continue

                market_id = str(m.get("id", "") or m.get("market_id", ""))
                if not market_id:
                    continue

                end_raw = m.get("endDate") or m.get("end_date") or ""

                results.append({
                    "market_id": market_id,
                    "question": question,
                    "slug": slug,
                    "end_date": end_raw,
                    "q_yes": prices[0],
                    "indicator": parsed["indicator"],
                    "period": parsed["period"],
                    "lo": parsed["lo"],
                    "hi": parsed["hi"],
                })
            except Exception:
                continue

        if len(data) < 100:
            break

    return results


# ---------------------------------------------------------------------------
# Default distribution function (live; overridable for tests)
# ---------------------------------------------------------------------------

def _live_distribution(period):
    """Fetch BLS/FRED history, compute MoM%, call ensemble.forecast_distribution.

    period: "YYYY-MM" -- NOT used to filter history; it identifies the TARGET
    print (which we do NOT see here -- honesty law).

    Returns {"mu","sigma","weights","n_train"} or raises on failure.
    """
    from institute.verticals.cpi.ensemble import forecast_distribution

    # Primary: BLS seasonally-adjusted series
    levels = _data.bls_cpi_series()
    if not levels:
        # Fallback: FRED CSV
        fred_rows = _data.fred_series()
        if fred_rows:
            # Convert FRED rows to level dicts with year/month keys
            converted = []
            for r in fred_rows:
                try:
                    parts = r["date"].split("-")
                    converted.append({
                        "year": int(parts[0]),
                        "month": int(parts[1]),
                        "value": r["value"],
                    })
                except (IndexError, ValueError):
                    continue
            levels = converted
        else:
            levels = []

    mom_hist = _data.monthly_mom_pct(levels)

    # POINT-IN-TIME CLAMP (honesty by construction): drop any history at or after
    # the TARGET period so the model can never ingest the print it is forecasting,
    # regardless of WHEN snapshot runs (e.g. a late snapshot after a cron outage).
    # This also guarantees the models forecast `period` exactly (the month after the
    # last retained observation), not whatever month BLS happens to end on today.
    try:
        ty, tm = period.split("-")
        target = (int(ty), int(tm))
        mom_hist = [r for r in mom_hist
                    if r.get("year") is not None and r.get("month") is not None
                    and (r["year"], r["month"]) < target]
    except (ValueError, AttributeError):
        pass  # malformed period -> use full history (degrade, never crash)

    cleveland = _data.cleveland_nowcast()
    cleveland_mom = cleveland.get("cpi_mom") if cleveland else None

    return forecast_distribution(mom_hist, cleveland_mom=cleveland_mom)


# ---------------------------------------------------------------------------
# Phase 1: snapshot
# ---------------------------------------------------------------------------

def snapshot(
    store_path=CPI_STORE,
    fetch=None,
    distribution=None,
    now=None,
):
    """Snapshot active CPI markets from Gamma.

    For each newly-seen market:
      1. Compute the predictive distribution for its period ONCE (cache by period).
      2. Compute p_model = bucket_prob(mu, sigma, lo, hi).
      3. Freeze mu/sigma/p_model into meta and append the row.

    Idempotent: markets already open in the store are never re-forecast.
    POINT-IN-TIME: y is never read here; forecast uses only released history.

    fetch: injectable for tests (default: fetch_active_cpi).
    distribution: injectable for tests; called as distribution(period) ->
                  {"mu","sigma","weights","n_train"}.
                  Default calls _live_distribution(period) which hits BLS/FRED.
    now: injectable datetime for tests.

    Returns list of newly-appended rows.
    """
    from institute.verticals.cpi.ensemble import bucket_prob

    if fetch is None:
        fetch = fetch_active_cpi
    if now is None:
        now = datetime.datetime.utcnow()

    existing = load_jsonl(store_path)
    already_open = {
        r["market_id"] for r in existing
        if r.get("status") == "open"
    }

    fetched = fetch()
    new_rows = []

    # Cache distribution per period (no need to refit for every bucket)
    dist_cache = {}

    for m in fetched:
        if m["market_id"] in already_open:
            continue

        period = m["period"]

        # Compute or retrieve cached distribution
        if period not in dist_cache:
            if distribution is not None:
                # Injected (test) distribution
                dist_cache[period] = distribution(period)
            else:
                try:
                    dist_cache[period] = _live_distribution(period)
                except Exception:
                    dist_cache[period] = {"mu": 0.0, "sigma": 0.2,
                                          "weights": {}, "n_train": 0}

        dist = dist_cache[period]
        mu = dist["mu"]
        sigma = dist["sigma"]

        lo = m["lo"]
        hi = m["hi"]
        p_model = bucket_prob(mu, sigma, lo, hi)

        row = {
            "market_id": m["market_id"],
            "archetype": "econ-cpi",
            "t0": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "q_yes": m["q_yes"],
            "question": m["question"],
            "end_date": m["end_date"],
            "status": "open",
            "y": None,
            "settled_ts": None,
            "meta": {
                "indicator": m["indicator"],
                "period": period,
                "lo": lo,
                "hi": hi,
                "mu": mu,
                "sigma": sigma,
                "p_model": p_model,
                "forecast_ts": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "slug": m["slug"],
            },
        }
        new_rows.append(row)

    if new_rows:
        append_jsonl(store_path, new_rows)

    return new_rows


# ---------------------------------------------------------------------------
# BLS-based resolver
# ---------------------------------------------------------------------------

def resolve_cpi(row, bls=None):
    """Resolve a CPI row using the BLS series.

    Fetches the released index level for row["meta"]["period"] and computes
    the realised MoM%.

    Returns 1 (bucket hit), 0 (miss), or None (not yet published / error).
    NEVER reads row["y"] -- that would violate point-in-time honesty.
    """
    if bls is None:
        bls = _data.bls_cpi_series

    try:
        meta = row.get("meta", {})
        period = meta.get("period", "")  # "YYYY-MM"
        lo = meta.get("lo")
        hi = meta.get("hi")

        if not period or lo is None or hi is None:
            return None

        parts = period.split("-")
        target_year = int(parts[0])
        target_month = int(parts[1])

        levels = bls()
        if not levels:
            return None

        # Find two consecutive months: (target-1) and target
        prev_val = None
        curr_val = None
        for lv in levels:
            yr = lv.get("year")
            mo = lv.get("month")
            if yr is None or mo is None:
                continue
            if yr == target_year and mo == target_month:
                curr_val = lv["value"]
            # Previous month
            prev_month = target_month - 1
            prev_year = target_year
            if prev_month == 0:
                prev_month = 12
                prev_year -= 1
            if yr == prev_year and mo == prev_month:
                prev_val = lv["value"]

        if curr_val is None or prev_val is None or prev_val == 0:
            return None  # not yet published

        mom = (curr_val / prev_val - 1.0) * 100.0
        return 1 if lo <= mom < hi else 0

    except Exception:
        return None


# ---------------------------------------------------------------------------
# Phase 2: settle
# ---------------------------------------------------------------------------

def settle(store_path=CPI_STORE, resolve=None, now=None):
    """Settle open CPI rows whose end_date is past.

    For each qualifying row calls resolve(row) -> y in {0,1} or None.
    y=None means the BLS data is not yet published -- retry next run.
    Overwrites the store with updated rows.

    resolve: injectable for tests (default: resolve_cpi).
    now: injectable datetime for tests.

    Returns rows settled this call.
    """
    if resolve is None:
        resolve = resolve_cpi
    if now is None:
        now = datetime.datetime.utcnow()

    rows = load_jsonl(store_path)
    settled_this_call = []

    for row in rows:
        if row.get("status") != "open":
            continue
        try:
            end_dt = _parse_utc_iso(row["end_date"])
        except Exception:
            continue
        if end_dt >= now:
            continue  # not yet past deadline

        y = resolve(row)
        if y is None:
            continue  # BLS not published yet; retry next cron

        row["y"] = y
        row["status"] = "settled"
        row["settled_ts"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        settled_this_call.append(row)

    overwrite_jsonl(store_path, rows)
    return settled_this_call
