"""Crypto-daily live sensor: two-phase snapshot + settle (A5).

Phase 1 (snapshot): fetches live open crypto-daily markets from Gamma, records
q_yes while the market is OPEN (real decision-time prior).
Phase 2 (settle): for rows whose end_date has passed, resolves y from Gamma
closed market data (0=NO won, 1=YES won).

Store: institute/data/crypto_markets.jsonl
"""
import json
import datetime
import urllib.request
import urllib.error
import os

from institute.corpus.store import append_jsonl, load_jsonl, overwrite_jsonl
from institute.classify.archetype import classify

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
CRYPTO_STORE = os.path.join(BASE_DIR, "data", "crypto_markets.jsonl")

_GAMMA_BASE = "https://gamma-api.polymarket.com"


def _gamma_get(path, base=_GAMMA_BASE, timeout=20):
    """Thin urllib GET -> parsed JSON. Raises on HTTP/network error."""
    url = base.rstrip("/") + path
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "institute/1.0", "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _parse_json_string(raw):
    """Parse a value that may already be a list or may be a JSON string (double-parse)."""
    if isinstance(raw, list):
        return raw
    return json.loads(raw)


def _symbol_from_question(question):
    """Derive BTC/ETH/SOL/? from question text."""
    q = question.lower()
    if "bitcoin" in q or "btc" in q:
        return "BTC"
    if "ethereum" in q or "eth" in q:
        return "ETH"
    if "solana" in q or "sol" in q:
        return "SOL"
    return "?"


def _parse_utc_iso(s):
    """Parse ISO8601 Z-suffix datetime string -> datetime (utc, naive)."""
    s = s.rstrip("Z").rstrip("z")
    # Handle fractional seconds
    if "." in s:
        s = s[:19]
    try:
        return datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return datetime.datetime.strptime(s[:10], "%Y-%m-%d")


def fetch_active_crypto(cutoff_hours=36, max_pages=20, _get=_gamma_get):
    """Page through Gamma active markets; return normalized crypto-daily dicts.

    Keeps a market iff:
    - classified as crypto-daily
    - endDate is between now and now+cutoff_hours (short-horizon filter)
    - clobTokenIds double-parses to >= 2 tokens
    - outcomePrices parses to a 2-list of floats

    Wraps each page in try/except; on network error breaks and returns what we have.
    """
    now = datetime.datetime.utcnow()
    cutoff = now + datetime.timedelta(hours=cutoff_hours)
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

                # Must be crypto-daily
                if classify(question, slug) != "crypto-daily":
                    continue

                # Must have a short-horizon end date
                end_raw = m.get("endDate") or m.get("end_date") or ""
                if not end_raw:
                    continue
                try:
                    end_dt = _parse_utc_iso(end_raw)
                except Exception:
                    continue
                if not (now <= end_dt <= cutoff):
                    continue

                # clobTokenIds: JSON string double-parse
                clob_raw = m.get("clobTokenIds")
                if clob_raw is None:
                    continue
                try:
                    tokens = _parse_json_string(clob_raw)
                except Exception:
                    continue
                if len(tokens) < 2:
                    continue

                # outcomePrices: also JSON string
                prices_raw = m.get("outcomePrices")
                if prices_raw is None:
                    continue
                try:
                    prices = _parse_json_string(prices_raw)
                    prices = [float(p) for p in prices]
                except Exception:
                    continue
                if len(prices) < 2:
                    continue

                market_id = str(m.get("id", "") or m.get("market_id", ""))
                if not market_id:
                    continue

                results.append({
                    "market_id": market_id,
                    "question": question,
                    "slug": slug,
                    "end_date": end_raw,
                    "q_yes": prices[0],
                    "yes_token": str(tokens[0]),
                    "symbol": _symbol_from_question(question),
                })
            except Exception:
                continue

        # If the page returned fewer than 100 results, we are done
        if len(data) < 100:
            break

    return results


def snapshot(store_path=CRYPTO_STORE, fetch=fetch_active_crypto, now=None):
    """Phase 1: fetch live crypto-daily markets and append newly-seen ones.

    Deduplicates: never snapshots the same market_id while still open.
    Returns list of newly-appended rows.
    """
    if now is None:
        now = datetime.datetime.utcnow()

    existing = load_jsonl(store_path)
    already_open = {
        r["market_id"] for r in existing
        if r.get("status") == "open"
    }

    fetched = fetch()
    new_rows = []
    for m in fetched:
        if m["market_id"] in already_open:
            continue
        row = {
            "market_id": m["market_id"],
            "archetype": "crypto-daily",
            "t0": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "q_yes": m["q_yes"],
            "question": m["question"],
            "end_date": m["end_date"],
            "status": "open",
            "y": None,
            "settled_ts": None,
            "meta": {
                "slug": m["slug"],
                "symbol": m["symbol"],
                "yes_token": m["yes_token"],
            },
        }
        new_rows.append(row)

    if new_rows:
        append_jsonl(store_path, new_rows)

    return new_rows


def resolve_outcome(row, _get=_gamma_get):
    """Query Gamma for a single market's resolved outcome.

    Returns 1 (YES won), 0 (NO won), or None (not yet resolved / error).
    """
    try:
        m = _get(f"/markets/{row['market_id']}")
        # Gamma may return a list; take first element
        if isinstance(m, list):
            m = m[0]
        if not m.get("closed"):
            return None
        prices_raw = m.get("outcomePrices")
        if prices_raw is None:
            return None
        prices = _parse_json_string(prices_raw)
        yp = float(prices[0])
        return 1 if yp >= 0.5 else 0
    except Exception:
        return None


def settle(store_path=CRYPTO_STORE, resolve=resolve_outcome, now=None):
    """Phase 2: settle open rows whose end_date is in the past.

    For each qualifying row calls resolve(row) -> y in {0,1} or None.
    Overwrites the store with updated rows. Returns rows settled this call.
    """
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
            # Not yet past deadline
            continue
        y = resolve(row)
        if y is None:
            continue
        row["y"] = y
        row["status"] = "settled"
        row["settled_ts"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")
        settled_this_call.append(row)

    overwrite_jsonl(store_path, rows)
    return settled_this_call
