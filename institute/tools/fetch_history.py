"""Fetch resolved prediction-market history and store it append-only.

Purpose: our live-captured priors are thin. This pulls the FREE, abundant resolved-market
history from Polymarket (Gamma) and Kalshi (public API) so the Institute has real backtest
ground truth. Outcomes of resolved markets are known and safe to store as labels; the
point-in-time honesty rule applies to FORECASTS, not to a labeled outcome dataset.

Storage: institute/data/history/{venue}_resolved.jsonl  (append-only, deduped by id)
         institute/data/history/manifest.json           (counts + last-fetch timestamps)

stdlib only (no requests/pandas). ASCII output only (Windows cp1252 safe).

Usage:
    python fetch_history.py --venue polymarket --max 2000
    python fetch_history.py --venue kalshi     --max 2000
    python fetch_history.py --venue all        --max 2000
"""
import argparse
import json
import os
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "history")
UA = "institute-history-fetcher/1.0 (paper-research)"

POLY_GAMMA = "https://gamma-api.polymarket.com/markets"
KALSHI_API = "https://api.elections.kalshi.com/trade-api/v2/markets"


def _get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _load_ids(path):
    ids = set()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ids.add(str(json.loads(line).get("id")))
                except Exception:
                    pass
    return ids


def _append(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=True) + "\n")


def fetch_polymarket(max_rows):
    """Paginate Gamma closed=true markets. Keep only resolved ones with an outcome."""
    path = os.path.join(DATA, "polymarket_resolved.jsonl")
    seen = _load_ids(path)
    new = []
    offset, page = 0, 500
    while len(new) < max_rows:
        url = f"{POLY_GAMMA}?closed=true&limit={page}&offset={offset}&order=endDate&ascending=false"
        try:
            batch = _get(url)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            print(f"[polymarket] stop at offset {offset}: {e}")
            break
        if not batch:
            break
        for m in batch:
            mid = str(m.get("id"))
            if mid in seen:
                continue
            seen.add(mid)
            new.append({
                "venue": "polymarket",
                "id": mid,
                "question": m.get("question"),
                "slug": m.get("slug"),
                "start_date": m.get("startDate") or m.get("createdAt"),
                "end_date": m.get("endDate"),
                "closed_time": m.get("closedTime"),
                "outcomes": m.get("outcomes"),
                "outcome_prices": m.get("outcomePrices"),
                "clob_token_ids": m.get("clobTokenIds"),   # JSON string; parse for price history
                "condition_id": m.get("conditionId"),
                "resolved": m.get("umaResolutionStatus") or m.get("resolvedBy"),
                "volume": m.get("volume"),
                "liquidity": m.get("liquidity"),
                "category": m.get("category"),
                "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })
        offset += len(batch)  # advance by rows actually returned (API may cap page size)
        time.sleep(0.3)  # be polite
        if len(batch) == 0:
            break
    _append(path, new[:max_rows])
    return len(new[:max_rows]), path


def _load_field(path, field):
    vals = set()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    v = json.loads(line).get(field)
                    if v:
                        vals.add(str(v))
                except Exception:
                    pass
    return vals


def fetch_polymarket_clob(max_rows):
    """Cursor-paginate ALL markets via CLOB (past Gamma's ~2100 offset ceiling).

    Keeps closed markets with a resolved winner. Dedups by condition_id and skips condition_ids
    already captured by the Gamma pull, so the two sources don't double-count.
    """
    path = os.path.join(DATA, "polymarket_clob_resolved.jsonl")
    seen = _load_field(path, "condition_id")
    seen |= _load_field(os.path.join(DATA, "polymarket_resolved.jsonl"), "condition_id")
    new = []
    cursor = ""
    while len(new) < max_rows:
        url = "https://clob.polymarket.com/markets"
        if cursor:
            url += f"?next_cursor={cursor}"
        try:
            resp = _get(url)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as e:
            print(f"[polymarket-clob] stop: {e}")
            break
        data = resp.get("data", [])
        if not data:
            break
        for m in data:
            cid = m.get("condition_id")
            if not m.get("closed") or not cid or str(cid) in seen:
                continue
            toks = m.get("tokens") or []
            winner = next((t.get("outcome") for t in toks if t.get("winner")), None)
            if winner is None:
                continue  # not resolved to a clean winner
            seen.add(str(cid))
            new.append({
                "venue": "polymarket",
                "id": str(cid),
                "condition_id": str(cid),
                "question": m.get("question"),
                "slug": m.get("market_slug"),
                "end_date": m.get("end_date_iso"),
                "closed_time": m.get("end_date_iso"),
                "start_date": m.get("game_start_time"),
                "outcomes": json.dumps([t.get("outcome") for t in toks]),
                "outcome_prices": json.dumps([str(t.get("price")) for t in toks]),
                "clob_token_ids": json.dumps([t.get("token_id") for t in toks]),
                "winner_outcome": winner,
                "tags": m.get("tags"),
                "source": "clob",
                "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })
        cursor = resp.get("next_cursor")
        if not cursor or cursor == "LTE=":  # "LTE=" = base64 -1 = end
            break
        time.sleep(0.25)
    _append(path, new[:max_rows])
    return len(new[:max_rows]), path


def fetch_kalshi(max_rows):
    """Paginate settled Kalshi markets via cursor. Public market endpoint."""
    path = os.path.join(DATA, "kalshi_settled.jsonl")
    seen = _load_ids(path)
    new = []
    cursor = None
    while len(new) < max_rows:
        url = f"{KALSHI_API}?status=settled&limit=200"
        if cursor:
            url += f"&cursor={cursor}"
        try:
            resp = _get(url)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            print(f"[kalshi] stop: {e}")
            break
        markets = resp.get("markets", [])
        if not markets:
            break
        for m in markets:
            mid = str(m.get("ticker"))
            if mid in seen:
                continue
            # Skip multivariate/parlay legs (KXMVE*): auto-generated combo bets, not real
            # standalone markets. They flood the recent feed (91k+ sports parlays).
            if m.get("mve_collection_ticker") or mid.startswith("KXMVE"):
                seen.add(mid)
                continue
            seen.add(mid)
            new.append({
                "venue": "kalshi",
                "id": mid,
                "question": m.get("title"),
                "event_ticker": m.get("event_ticker"),
                "close_time": m.get("close_time"),
                "result": m.get("result"),
                "yes_price_close": m.get("last_price"),
                "volume": m.get("volume"),
                "category": m.get("category"),
                "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            })
        cursor = resp.get("cursor")
        if not cursor:
            break
        time.sleep(0.3)
    _append(path, new[:max_rows])
    return len(new[:max_rows]), path


def fetch_kalshi_events(max_rows):
    """Paginate settled Kalshi EVENTS with nested markets (the deep path).

    The /markets?status=settled feed is shallow and flooded with KXMVE parlay legs;
    /events?status=settled cursor-paginates real history AND carries a category field.
    ~1,100 markets per 200-event page.
    """
    path = os.path.join(DATA, "kalshi_settled.jsonl")
    seen = _load_ids(path)
    new = []
    cursor = None
    while len(new) < max_rows:
        url = ("https://api.elections.kalshi.com/trade-api/v2/events"
               "?status=settled&limit=200&with_nested_markets=true")
        if cursor:
            url += f"&cursor={cursor}"
        try:
            resp = _get(url)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError) as e:
            print(f"[kalshi-events] stop: {e}")
            break
        events = resp.get("events", [])
        if not events:
            break
        for ev in events:
            cat = ev.get("category")
            for m in (ev.get("markets") or []):
                mid = str(m.get("ticker"))
                if mid in seen:
                    continue
                if m.get("mve_collection_ticker") or mid.startswith("KXMVE"):
                    seen.add(mid)
                    continue
                seen.add(mid)
                new.append({
                    "venue": "kalshi",
                    "id": mid,
                    "question": (ev.get("title") or "") + (" | " + m.get("yes_sub_title") if m.get("yes_sub_title") else ""),
                    "event_ticker": ev.get("event_ticker"),
                    "close_time": m.get("close_time"),
                    "result": m.get("result"),
                    "yes_price_close": m.get("last_price_dollars") or m.get("last_price"),
                    "volume": m.get("volume"),
                    "liquidity": m.get("liquidity_dollars"),
                    "category": cat,
                    "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                })
        cursor = resp.get("cursor")
        if not cursor:
            break
        time.sleep(0.3)
    _append(path, new[:max_rows])
    return len(new[:max_rows]), path


def update_manifest(results):
    mpath = os.path.join(DATA, "manifest.json")
    manifest = {}
    if os.path.exists(mpath):
        try:
            manifest = json.load(open(mpath, "r", encoding="utf-8"))
        except Exception:
            manifest = {}
    for venue, (count, path) in results.items():
        total = 0
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                total = sum(1 for _ in f)
        manifest[venue] = {
            "last_fetch": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "added_this_run": count,
            "total_rows": total,
            "file": os.path.relpath(path, HERE),
        }
    os.makedirs(DATA, exist_ok=True)
    json.dump(manifest, open(mpath, "w", encoding="utf-8"), indent=2)
    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--venue",
                    choices=["polymarket", "polymarket-clob", "kalshi", "kalshi-events", "all"],
                    default="all")
    ap.add_argument("--max", type=int, default=2000, help="max NEW rows per venue")
    args = ap.parse_args()

    results = {}
    if args.venue in ("polymarket", "all"):
        print("[polymarket] fetching resolved markets (Gamma)...")
        results["polymarket"] = fetch_polymarket(args.max)
        print(f"[polymarket] added {results['polymarket'][0]} new rows")
    if args.venue in ("polymarket-clob", "all"):
        print("[polymarket-clob] cursor-paginating all markets (past Gamma ceiling)...")
        results["polymarket_clob"] = fetch_polymarket_clob(args.max)
        print(f"[polymarket-clob] added {results['polymarket_clob'][0]} new rows")
    if args.venue == "kalshi":
        print("[kalshi] fetching settled markets (shallow feed)...")
        results["kalshi"] = fetch_kalshi(args.max)
        print(f"[kalshi] added {results['kalshi'][0]} new rows")
    if args.venue in ("kalshi-events", "all"):
        print("[kalshi-events] paginating settled events w/ nested markets (deep path)...")
        results["kalshi"] = fetch_kalshi_events(args.max)
        print(f"[kalshi-events] added {results['kalshi'][0]} new rows")

    manifest = update_manifest(results)
    print("\n=== manifest ===")
    for venue, info in manifest.items():
        print(f"{venue:12} total={info['total_rows']:>7}  (+{info['added_this_run']} this run)")


if __name__ == "__main__":
    main()
