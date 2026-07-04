"""Fetch DECISION-TIME price series for resolved Polymarket markets, from real trades.

The outcome store (fetch_history.py) has labels + final prices only. To backtest "would we
have beaten the market", we need the price AS IT STOOD over the market's life. The CLOB
prices-history endpoint does NOT serve archived/resolved markets (returns empty), so we
reconstruct the series from the Data API /trades endpoint: every executed trade is a real
price known at its timestamp. Each YES-side trade -> one point-in-time point. A backtest at
time T uses only trades with t <= T (no look-ahead).

Reads:  institute/data/history/polymarket_resolved.jsonl  (needs condition_id)
Writes: institute/data/history/prices/polymarket_trades.jsonl  (append-only, deduped by id)

Long-tail markets trade thinly -> sparse series is EXPECTED (it is why live capture is the
moat). n_trades is recorded so downstream code can skip markets too thin to backtest.

stdlib only. ASCII output. Usage:
    python fetch_prices.py --max 5000
"""
import argparse
import glob
import json
import os
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data", "history")
# both Polymarket outcome sources: Gamma (polymarket_resolved) + CLOB cursor (polymarket_clob_resolved)
IN_GLOB = os.path.join(DATA, "polymarket*resolved.jsonl")
OUT_FILE = os.path.join(DATA, "prices", "polymarket_trades.jsonl")
TRADES = "https://data-api.polymarket.com/trades"
UA = {"User-Agent": "institute-price-fetcher/1.0", "Accept": "application/json"}


def _get(url, timeout=40):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def _load_done(path):
    done = set()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    done.add(str(json.loads(line).get("id")))
                except Exception:
                    pass
    return done


def _trades_for(cid, cap=5000):
    """Paginate YES-side trades for a condition id, ascending by time. Returns [[t,p,size]]."""
    pts, offset, page = [], 0, 500
    while len(pts) < cap:
        url = f"{TRADES}?market={cid}&limit={page}&offset={offset}"
        try:
            batch = _get(url)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError):
            break
        if not isinstance(batch, list) or not batch:
            break
        for tr in batch:
            if tr.get("outcomeIndex") == 0:  # YES side
                try:
                    pts.append([int(tr["timestamp"]), float(tr["price"]), float(tr.get("size", 0))])
                except (KeyError, ValueError, TypeError):
                    pass
        if len(batch) < page:
            break
        offset += page
        time.sleep(0.2)
    pts.sort(key=lambda x: x[0])
    return pts


def _iter_markets():
    for path in sorted(glob.glob(IN_GLOB)):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    yield json.loads(line)
                except Exception:
                    continue


def fetch_prices(max_markets):
    in_files = glob.glob(IN_GLOB)
    if not in_files:
        print("no outcome store yet; run fetch_history.py first")
        return None
    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    done = _load_done(OUT_FILE)
    seen_cid = set()
    written = thin = err = 0
    out = open(OUT_FILE, "a", encoding="utf-8")
    for m in _iter_markets():
            if written >= max_markets:
                break
            mid = str(m.get("id"))
            cid = m.get("condition_id")
            # dedup across both source files by condition_id
            if mid in done or not cid or str(cid) in seen_cid:
                continue
            seen_cid.add(str(cid))
            try:
                points = _trades_for(cid)
            except Exception:
                err += 1
                continue
            done.add(mid)
            if len(points) < 2:
                thin += 1
            out.write(json.dumps({
                "venue": "polymarket",
                "id": mid,
                "condition_id": cid,
                "question": m.get("question"),
                "outcomes": m.get("outcomes"),
                "outcome_prices": m.get("outcome_prices"),  # final resolution
                "n_trades": len(points),
                "points": points,  # [[unix, yes_price, size], ...] point-in-time
                "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }, ensure_ascii=True) + "\n")
            out.flush()
            written += 1
            if written % 100 == 0:
                print(f"  priced {written} (thin<2={thin}, err={err})")
            time.sleep(0.2)
    out.close()
    return written, thin, err


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--max", type=int, default=5000, help="max NEW markets to price this run")
    args = ap.parse_args()
    print(f"[prices] reconstructing decision-time series from trades (max={args.max})...")
    res = fetch_prices(args.max)
    if res:
        w, thin, err = res
        total = sum(1 for _ in open(OUT_FILE, encoding="utf-8")) if os.path.exists(OUT_FILE) else 0
        print(f"[prices] wrote {w} (thin<2 trades={thin}, errors={err}); store total={total}")


if __name__ == "__main__":
    main()
