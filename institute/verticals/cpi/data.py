"""Free, no-key data fetchers for the US CPI vertical (B1).

All network functions are injectable (default to real implementations).
All degrade gracefully on error -- callers receive [] or None, never raise.

Free sources confirmed (2026-06-30):
  BLS public API v1:  https://api.bls.gov/publicAPI/v1/timeseries/data/CUSR0000SA0
  FRED CSV:           https://fred.stlouisfed.org/graph/fredgraph.csv?id=CPIAUCSL
  Cleveland Fed:      https://www.clevelandfed.org/indicators-and-data/
                      inflation-nowcasting (format varies; treated as best-effort)
"""
import csv
import io
import json
import urllib.request
import urllib.error


_HEADERS = {"User-Agent": "institute/1.0", "Accept": "*/*"}


# ---------------------------------------------------------------------------
# thin transport
# ---------------------------------------------------------------------------

def _get_json(url, timeout=25):
    """GET url -> parsed JSON dict/list. Raises on HTTP/network error."""
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _get_text(url, timeout=25):
    """GET url -> raw text string. Raises on HTTP/network error."""
    req = urllib.request.Request(url, headers=_HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8")


# ---------------------------------------------------------------------------
# BLS public API v1
# ---------------------------------------------------------------------------

_BLS_URL = "https://api.bls.gov/publicAPI/v1/timeseries/data/{series_id}"


def bls_cpi_series(series_id="CUSR0000SA0", _get=_get_json):
    """Fetch a BLS monthly index series (v1, no key).

    Returns list of {"year": int, "month": int, "value": float} sorted OLD->NEW.
    Returns [] on any error.

    period "M13" is the annual average -- skipped.
    """
    url = _BLS_URL.format(series_id=series_id)
    try:
        data = _get(url)
        series_data = data["Results"]["series"][0]["data"]
    except Exception:
        return []

    rows = []
    for item in series_data:
        try:
            period = item.get("period", "")
            if not period.startswith("M") or period == "M13":
                continue
            month = int(period[1:])
            year = int(item["year"])
            value = float(item["value"])
            rows.append({"year": year, "month": month, "value": value})
        except (KeyError, ValueError, TypeError):
            continue

    # Sort OLD -> NEW
    rows.sort(key=lambda r: (r["year"], r["month"]))
    return rows


# ---------------------------------------------------------------------------
# FRED CSV
# ---------------------------------------------------------------------------

_FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"


def fred_series(series_id="CPIAUCSL", _get=_get_text):
    """Fetch a FRED monthly series as CSV (no key).

    Returns list of {"date": "YYYY-MM-DD", "value": float} sorted OLD->NEW.
    Skips rows where value is "." (missing).
    Returns [] on any error.
    """
    url = _FRED_URL.format(series_id=series_id)
    try:
        text = _get(url)
    except Exception:
        return []

    rows = []
    try:
        reader = csv.DictReader(io.StringIO(text))
        for row in reader:
            try:
                date_str = row.get("observation_date", "").strip()
                val_str = row.get(series_id, "").strip()
                if not date_str or val_str in ("", "."):
                    continue
                rows.append({"date": date_str, "value": float(val_str)})
            except (ValueError, KeyError):
                continue
    except Exception:
        return []

    # Already OLD->NEW from FRED, but sort to be safe
    rows.sort(key=lambda r: r["date"])
    return rows


# ---------------------------------------------------------------------------
# Cleveland Fed Inflation Nowcast (best-effort, optional)
# ---------------------------------------------------------------------------

# DEVIATION: The Cleveland Fed nowcasting page at
# https://www.clevelandfed.org/indicators-and-data/inflation-nowcasting
# does not expose a stable, parseable free JSON/CSV endpoint without
# registration or API keys.  The old research.stlouisfed.org endpoint
# no longer resolves cleanly, and the Cleveland Fed's public data portal
# requires an API key for programmatic access.
# Per spec §1 and §11: "if it 404s in future this returns None and the
# ensemble copes" -- wired to always return None so the ensemble degrades
# to the two confirmed free models (BLS + FRED).
# The ensemble still runs correctly with two models; the nowcast slot is
# preserved for a future free endpoint.

_CLEVELAND_URL = (
    "https://www.clevelandfed.org/indicators-and-data/inflation-nowcasting"
)


def cleveland_nowcast(_get=_get_text):
    """Best-effort fetch of Cleveland Fed CPI MoM nowcast.

    Returns {"cpi_mom": float} if successfully parsed, else None.
    NEVER raises -- on ANY failure returns None so the ensemble degrades gracefully.

    Current status: returns None (see DEVIATION note above). The URL is
    preserved so this can be wired once a stable free endpoint is confirmed.
    """
    # DEVIATION: Cleveland Fed free endpoint not stably parseable without a key.
    # Ensemble degrades to seasonal_ar + random_walk (two confirmed free models).
    return None


# ---------------------------------------------------------------------------
# Pure transform: index levels -> MoM% changes
# ---------------------------------------------------------------------------

def monthly_mom_pct(levels):
    """Compute MoM% changes from a list of monthly index level dicts (OLD->NEW).

    Each level dict must have a "value" key (float).
    Returns list of dicts merging the t-th level's keys with
    {"mom": (v_t / v_{t-1} - 1) * 100}.
    The returned list is one shorter than levels.
    Pure transform -- no network.
    """
    if len(levels) < 2:
        return []
    result = []
    for i in range(1, len(levels)):
        prev = levels[i - 1]["value"]
        curr = levels[i]["value"]
        if prev == 0:
            continue
        row = dict(levels[i])
        row["mom"] = (curr / prev - 1.0) * 100.0
        result.append(row)
    return result
