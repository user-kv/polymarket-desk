"""Fetch DECISION-TIME price series for BOTH venues (Kalshi candlesticks + Polymarket trades).

Extends fetch_prices.py's Polymarket trade-reconstruction approach with a Kalshi candlestick
fetcher, so both venues have point-in-time price series usable by pit_index.py without any
look-ahead. Same honesty rule as fetch_prices.py: a backtest at time T may only use points with
ts < T.

Kalshi candlesticks:
    Live:       GET {KALSHI_BASE}/series/{series_ticker}/markets/{ticker}/candlesticks
    Archived:   GET {KALSHI_BASE}/historical/markets/{ticker}/candlesticks
    We try the live path first; on 404 or an empty candlesticks list we fall back to the
    historical (archived-settled) path. No auth required for either.
    series_ticker is derived from the market ticker as the prefix before the first '-'
    (e.g. "KXWCGOAL-26JUL03AUSEGY-EGYMSABER21-1" -> "KXWCGOAL").

Polymarket trades:
    Same Data-API /trades reconstruction as fetch_prices.py, writing to the SAME output file
    (institute/data/history/prices/polymarket_trades.jsonl) so both tools share one store and
    never duplicate rows (done-set is derived from the file's own "id"/"condition_id" fields).

Reads:
    institute/data/history/kalshi_settled.jsonl            (Kalshi candidates)
    institute/data/history/polymarket*resolved.jsonl        (Polymarket candidates)
Writes (append-only, deduped from the output files themselves):
    institute/data/history/prices/kalshi_candles.jsonl
    institute/data/history/prices/polymarket_trades.jsonl
    institute/data/history/manifest.json  (adds a "kalshi_candles" section)

Spec-silent decisions (documented here per task instructions):
  - Kalshi candlestick lookback window: kalshi_settled.jsonl has no market-open timestamp, so
    start_ts = close_time - 60 days (a conservative window covering nearly all Kalshi market
    lifespans). Markets that ran longer will have a truncated series (n.b. not a look-ahead
    concern, only a completeness one).
  - Candle flattening always normalizes to [ts, open, high, low, close, yes_bid_close,
    yes_ask_close, volume] with None for any field the API omits, rather than keeping the raw
    dict on a "different structure" fallback -- simpler and downstream (pit_index.py) only ever
    needs ts/close/bid/ask.
  - fetch_with_retry retries on 429 and 5xx only; 404 is treated as a normal "not found here"
    signal used by the live->historical fallback, not an error.

stdlib only. ASCII output. Windows-safe paths (os.path.join throughout, no POSIX assumptions).

Usage:
    python fetch_prices_v2.py --venue all --max 2000
    python fetch_prices_v2.py --venue kalshi --max 500 --interval 60
    python fetch_prices_v2.py --probe
"""
import argparse
import datetime
import glob
import json
import os
import time
import urllib.error
import urllib.request
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
# institute/FABLE5/out/tools -> up 3 -> institute -> data/history
DATA = os.path.join(HERE, "..", "..", "..", "data", "history")
UA = {"User-Agent": "institute-price-fetcher-v2/1.0", "Accept": "application/json"}

KALSHI_BASE = "https://api.elections.kalshi.com/trade-api/v2"
POLY_TRADES = "https://data-api.polymarket.com/trades"

KALSHI_SETTLED_IN = os.path.join(DATA, "kalshi_settled.jsonl")
KALSHI_CANDLES_OUT = os.path.join(DATA, "prices", "kalshi_candles.jsonl")
POLY_RESOLVED_GLOB = os.path.join(DATA, "polymarket*resolved.jsonl")
POLY_TRADES_OUT = os.path.join(DATA, "prices", "polymarket_trades.jsonl")
MANIFEST_PATH = os.path.join(DATA, "manifest.json")

RETRY_STATUSES = (429, 500, 502, 503, 504)
MAX_RETRIES = 5
LOOKBACK_SECONDS = 60 * 24 * 3600  # 60 days; see docstring


# --------------------------------------------------------------------------------------
# HTTP seam -- tests inject a fake in place of fetch_json / pass fetch_fn explicitly.
# --------------------------------------------------------------------------------------
def fetch_json(url, timeout=40):
    """Live HTTP call. The only function that touches the network in this module."""
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read().decode("utf-8")
    return json.loads(body) if body else None


def fetch_with_retry(url, fetch_fn=fetch_json, sleep_fn=time.sleep, max_retries=MAX_RETRIES):
    """Call fetch_fn(url); exponential backoff on 429/5xx (max_retries attempts), else raise."""
    attempt = 0
    while True:
        try:
            return fetch_fn(url)
        except urllib.error.HTTPError as e:
            if e.code in RETRY_STATUSES and attempt < max_retries:
                sleep_fn(0.5 * (2 ** attempt))
                attempt += 1
                continue
            raise
        except (urllib.error.URLError, TimeoutError) as e:
            if attempt < max_retries:
                sleep_fn(0.5 * (2 ** attempt))
                attempt += 1
                continue
            raise


# --------------------------------------------------------------------------------------
# shared helpers
# --------------------------------------------------------------------------------------
def _iter_jsonl(path):
    if not os.path.exists(path):
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except Exception:
                continue


def _load_done_ids(path):
    done = set()
    for row in _iter_jsonl(path):
        mid = row.get("id")
        if mid is not None:
            done.add(str(mid))
    return done


def _parse_iso(s):
    if not s:
        return None
    try:
        return int(
            datetime.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")
            .replace(tzinfo=datetime.timezone.utc)
            .timestamp()
        )
    except Exception:
        return None


# --------------------------------------------------------------------------------------
# Kalshi candlesticks
# --------------------------------------------------------------------------------------
def series_ticker_from(ticker):
    """Derive series_ticker: the market ticker's prefix before its first '-'."""
    return str(ticker).split("-", 1)[0]


def build_candle_url(ticker, series, start_ts, end_ts, interval, historical=False):
    if historical:
        base = f"{KALSHI_BASE}/historical/markets/{ticker}/candlesticks"
    else:
        base = f"{KALSHI_BASE}/series/{series}/markets/{ticker}/candlesticks"
    return f"{base}?start_ts={start_ts}&end_ts={end_ts}&period_interval={interval}"


def _flatten_candle(c):
    """Normalize one Kalshi candlestick dict to [ts, open, high, low, close, ybid, yask, vol]."""
    # HONESTY INVARIANT: ts MUST be the period END. pit_index treats this ts as the
    # moment the close price became knowable; a period-START ts here would leak up to
    # one full period of look-ahead into every backtest. Kalshi returns end_period_ts;
    # if that field ever disappears, fail loudly rather than guess.
    ts = c.get("end_period_ts")
    if ts is None:
        raise ValueError(
            "candle missing end_period_ts — refusing to guess a timestamp "
            "(period-start would leak look-ahead); inspect API response format"
        )
    price = c.get("price") or {}
    yb = c.get("yes_bid") or {}
    ya = c.get("yes_ask") or {}
    close = price.get("close")
    if close is None and "close" in c:
        close = c.get("close")
    return [
        ts,
        price.get("open"),
        price.get("high"),
        price.get("low"),
        close,
        yb.get("close"),
        ya.get("close"),
        c.get("volume"),
    ]


def fetch_kalshi_candles_for_market(m, interval, fetch_fn=fetch_json, sleep_fn=time.sleep):
    """Fetch one market's candles. Tries live endpoint, falls back to historical on 404/empty.

    Returns (candles, source_endpoint) where source_endpoint is "live" or "historical".
    """
    ticker = str(m.get("id"))
    series = series_ticker_from(ticker)
    end_ts = _parse_iso(m.get("close_time"))
    if end_ts is None:
        # A now-anchored window on an old settled market fetches the wrong (empty)
        # range and silently records a market as "done" with no candles. Skip instead.
        raise ValueError(f"unparseable close_time for {ticker!r}; skipping market")
    start_ts = end_ts - LOOKBACK_SECONDS

    candles = None
    url_live = build_candle_url(ticker, series, start_ts, end_ts, interval, historical=False)
    try:
        resp = fetch_with_retry(url_live, fetch_fn, sleep_fn)
        candles = (resp or {}).get("candlesticks")
    except urllib.error.HTTPError as e:
        if e.code != 404:
            raise
        candles = None

    if not candles:
        url_hist = build_candle_url(ticker, series, start_ts, end_ts, interval, historical=True)
        resp = fetch_with_retry(url_hist, fetch_fn, sleep_fn)
        candles = (resp or {}).get("candlesticks") or []
        return [_flatten_candle(c) for c in candles], "historical"

    return [_flatten_candle(c) for c in candles], "live"


def fetch_kalshi(max_markets, interval=60, fetch_fn=fetch_json, sleep_fn=time.sleep,
                  in_path=KALSHI_SETTLED_IN, out_path=KALSHI_CANDLES_OUT, call_sleep=0.2):
    if not os.path.exists(in_path):
        print(f"no kalshi settled store at {in_path}; run fetch_history.py first")
        return 0, 0
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    done = _load_done_ids(out_path)
    written = err = 0
    with open(out_path, "a", encoding="utf-8") as out:
        for m in _iter_jsonl(in_path):
            if written >= max_markets:
                break
            mid = str(m.get("id"))
            if mid in done:
                continue
            done.add(mid)
            try:
                candles, used = fetch_kalshi_candles_for_market(m, interval, fetch_fn, sleep_fn)
            except Exception:
                err += 1
                continue
            out.write(json.dumps({
                "venue": "kalshi",
                "id": mid,
                "event_ticker": m.get("event_ticker"),
                "period_interval": interval,
                "candles": candles,
                "source_endpoint": used,
                "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }, ensure_ascii=True) + "\n")
            out.flush()
            written += 1
            if written % 100 == 0:
                print(f"  kalshi-candles {written} (err={err})")
            sleep_fn(call_sleep)
    return written, err


# --------------------------------------------------------------------------------------
# Polymarket trades (same store/schema as fetch_prices.py)
# --------------------------------------------------------------------------------------
def _trades_for(cid, fetch_fn=fetch_json, sleep_fn=time.sleep, call_sleep=0.2, cap=5000):
    pts, offset, page = [], 0, 500
    while len(pts) < cap:
        url = f"{POLY_TRADES}?market={cid}&limit={page}&offset={offset}"
        try:
            batch = fetch_with_retry(url, fetch_fn, sleep_fn)
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
        sleep_fn(call_sleep)
    pts.sort(key=lambda x: x[0])
    return pts


def fetch_polymarket(max_markets, fetch_fn=fetch_json, sleep_fn=time.sleep,
                      in_glob=POLY_RESOLVED_GLOB, out_path=POLY_TRADES_OUT, call_sleep=0.2):
    in_files = glob.glob(in_glob)
    if not in_files:
        print("no outcome store yet; run fetch_history.py first")
        return 0, 0, 0
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    done = _load_done_ids(out_path)
    seen_cid = set()
    for row in _iter_jsonl(out_path):
        cid = row.get("condition_id")
        if cid:
            seen_cid.add(str(cid))
    written = thin = err = 0
    out = open(out_path, "a", encoding="utf-8")
    for path in sorted(glob.glob(in_glob)):
        if written >= max_markets:
            break
        for m in _iter_jsonl(path):
            if written >= max_markets:
                break
            mid = str(m.get("id"))
            cid = m.get("condition_id")
            if mid in done or not cid or str(cid) in seen_cid:
                continue
            seen_cid.add(str(cid))
            try:
                points = _trades_for(cid, fetch_fn, sleep_fn, call_sleep)
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
                "outcome_prices": m.get("outcome_prices"),
                "n_trades": len(points),
                "points": points,
                "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }, ensure_ascii=True) + "\n")
            out.flush()
            written += 1
            if written % 100 == 0:
                print(f"  poly-trades {written} (thin<2={thin}, err={err})")
    out.close()
    return written, thin, err


# --------------------------------------------------------------------------------------
# manifest
# --------------------------------------------------------------------------------------
def update_manifest_kalshi_candles(count, path=KALSHI_CANDLES_OUT, manifest_path=MANIFEST_PATH):
    manifest = {}
    if os.path.exists(manifest_path):
        try:
            manifest = json.load(open(manifest_path, "r", encoding="utf-8"))
        except Exception:
            manifest = {}
    total = sum(1 for _ in open(path, encoding="utf-8")) if os.path.exists(path) else 0
    manifest["kalshi_candles"] = {
        "last_fetch": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "added_this_run": count,
        "total_rows": total,
        "file": os.path.relpath(path, os.path.dirname(manifest_path)),
    }
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
    json.dump(manifest, open(manifest_path, "w", encoding="utf-8"), indent=2)
    return manifest


# --------------------------------------------------------------------------------------
# --probe: minimal read-only coverage probe. Writes nothing except the printed report.
# --------------------------------------------------------------------------------------
def probe(fetch_fn=fetch_json, sleep_fn=time.sleep):
    rows = list(_iter_jsonl(KALSHI_SETTLED_IN))
    kalshi_sample = []
    if rows:
        by_cat = {}
        for r in rows:
            by_cat.setdefault(r.get("category") or "unknown", []).append(r)
        cats = list(by_cat.keys())
        i = 0
        guard = 0
        while len(kalshi_sample) < 50 and guard < 10000:
            cat = cats[i % len(cats)]
            bucket = by_cat[cat]
            if bucket:
                kalshi_sample.append(bucket.pop())
            i += 1
            guard += 1
            if all(not v for v in by_cat.values()):
                break
    else:
        print("[probe] no kalshi_settled.jsonl found; skipping kalshi probe")

    status_counter = Counter()
    earliest_ts = None
    has_bidask = 0
    ratelimited = 0
    for m in kalshi_sample:
        ticker = str(m.get("id"))
        series = series_ticker_from(ticker)
        end_ts = _parse_iso(m.get("close_time")) or int(time.time())
        start_ts = end_ts - LOOKBACK_SECONDS
        url = build_candle_url(ticker, series, start_ts, end_ts, 60, historical=False)
        try:
            resp = fetch_with_retry(url, fetch_fn, sleep_fn)
            status_counter["200"] += 1
        except urllib.error.HTTPError as e:
            status_counter[str(e.code)] += 1
            if e.code == 429:
                ratelimited += 1
            continue
        except Exception:
            status_counter["error"] += 1
            continue
        candles = (resp or {}).get("candlesticks") or []
        if candles:
            ts0 = _flatten_candle(candles[0])[0]
            if ts0 is not None and (earliest_ts is None or ts0 < earliest_ts):
                earliest_ts = ts0
            if candles[0].get("yes_bid") or candles[0].get("yes_ask"):
                has_bidask += 1
        sleep_fn(0.2)

    done = _load_done_ids(POLY_TRADES_OUT)
    poly_candidates = []
    for path in sorted(glob.glob(POLY_RESOLVED_GLOB)):
        if len(poly_candidates) >= 200:
            break
        for m in _iter_jsonl(path):
            if str(m.get("id")) not in done and m.get("condition_id"):
                poly_candidates.append(m)
            if len(poly_candidates) >= 200:
                break

    n_checked = n_ge10 = 0
    for m in poly_candidates:
        try:
            pts = _trades_for(m.get("condition_id"), fetch_fn, sleep_fn, call_sleep=0.2, cap=20)
        except Exception:
            continue
        n_checked += 1
        if len(pts) >= 10:
            n_ge10 += 1

    print("=== fetch_prices_v2 --probe report ===")
    print(f"[kalshi] sampled={len(kalshi_sample)} markets, "
          f"{len(set(m.get('category') for m in kalshi_sample))} distinct categories")
    print(f"[kalshi] earliest retrievable candle ts={earliest_ts}")
    print(f"[kalshi] bid/ask present in {has_bidask}/{len(kalshi_sample)} sampled markets")
    print(f"[kalshi] http status distribution: {dict(status_counter)}")
    print(f"[kalshi] rate-limited (429) responses observed: {ratelimited}")
    print(f"[polymarket] sampled={n_checked} unfetched markets")
    frac = (n_ge10 / n_checked) if n_checked else 0.0
    print(f"[polymarket] fraction with >=10 trades: {frac:.2%}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--venue", choices=["kalshi", "polymarket", "all"], default="all")
    ap.add_argument("--max", type=int, default=2000, help="max NEW markets per venue this run")
    ap.add_argument("--interval", type=int, choices=[1, 60, 1440], default=60,
                    help="Kalshi period_interval in minutes")
    ap.add_argument("--sleep", type=float, default=0.2, help="seconds between HTTP calls")
    ap.add_argument("--probe", action="store_true", help="read-only coverage probe; writes nothing")
    args = ap.parse_args()

    if args.probe:
        probe()
        return

    if args.venue in ("kalshi", "all"):
        print(f"[kalshi-candles] fetching candlesticks (interval={args.interval}, max={args.max})...")
        w, err = fetch_kalshi(args.max, interval=args.interval, call_sleep=args.sleep)
        print(f"[kalshi-candles] wrote {w} markets (errors={err})")
        update_manifest_kalshi_candles(w)

    if args.venue in ("polymarket", "all"):
        print(f"[poly-trades] expanding trades (max={args.max})...")
        w, thin, err = fetch_polymarket(args.max, call_sleep=args.sleep)
        print(f"[poly-trades] wrote {w} (thin<2 trades={thin}, errors={err})")


if __name__ == "__main__":
    main()
