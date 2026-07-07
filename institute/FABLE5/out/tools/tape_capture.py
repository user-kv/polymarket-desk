"""Forward-only large-trade tape recorder for BOTH venues (Polymarket + Kalshi).

PURPOSE: this tape cannot be backfilled -- Polymarket/Kalshi trade-history endpoints only
serve recent trades, so every run captures a slice of "now" that is gone tomorrow. It feeds
a future copy-flow / whale-fade strategy. Reliability and append-only honesty matter more
than completeness: better to log a gap than to fake continuity.

Polymarket:
    GET https://data-api.polymarket.com/trades?limit=500&offset=0
    Newest-first. Filter: notional = size*price >= $200 (whale-ish only).
    Paginate by offset up to --max-rows (default 2000) or until we hit a trade we've
    already recorded (dedup via seen-set), whichever comes first.

Kalshi:
    GET https://api.elections.kalshi.com/trade-api/v2/markets/trades?limit=1000
    Public, no auth. Cursor pagination via the response's "cursor" field.
    Filter: count >= 100 contracts (proxy for size).

Storage (append-only, never rewritten):
    institute/data/history/tape/polymarket_tape.jsonl
    institute/data/history/tape/kalshi_tape.jsonl
Dedup:
    Rolling seen-set built from the LAST 5000 rows of each file (by trade id if present,
    else hash of (venue, ts, market, price, size)).
State (best-effort resume, not authoritative):
    institute/data/history/tape/tape_state.json  {venue: {cursor/last_ts, updated_at}}
    Corrupt/missing state = start fresh from most recent. Gaps are logged, never faked.
Log:
    institute/data/history/tape/tape.log  (timestamped lines, append-only)

Field-name assumptions (defensive; see normalize_* functions):
  Polymarket /trades row: proxyWallet, side, size, price, timestamp (unix seconds, may be
    string), conditionId, asset/outcome, transactionHash (used as trade id fallback).
    Trade id: transactionHash if present, else hash of the row.
  Kalshi /markets/trades row: trade_id, ticker, count, yes_price/no_price (cents ints),
    taker_side, created_time (ISO8601). Trade id: trade_id if present, else hash of row.

stdlib only. ASCII output. Windows-safe paths.

Usage:
    python tape_capture.py --venue all --max-rows 2000
    python tape_capture.py --selftest
"""
import argparse
import hashlib
import json
import os
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
# institute/FABLE5/out/tools -> up 3 -> institute -> data/history/tape
DATA = os.path.join(HERE, "..", "..", "..", "data", "history", "tape")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Accept": "application/json"}

POLY_TRADES_URL = "https://data-api.polymarket.com/trades"
KALSHI_TRADES_URL = "https://api.elections.kalshi.com/trade-api/v2/markets/trades"

POLY_OUT = os.path.join(DATA, "polymarket_tape.jsonl")
KALSHI_OUT = os.path.join(DATA, "kalshi_tape.jsonl")
STATE_PATH = os.path.join(DATA, "tape_state.json")
LOG_PATH = os.path.join(DATA, "tape.log")

RETRY_STATUSES = (429, 500, 502, 503, 504)
MAX_RETRIES = 5

POLY_MIN_NOTIONAL = 200.0
KALSHI_MIN_COUNT = 100

SEEN_WINDOW = 5000          # rows scanned from tail of file to build the seen-set
POLY_PAGE_CAP = 2000        # per spec: paginate up to 2000 rows
POLY_PAGE_SIZE = 500


# --------------------------------------------------------------------------------------
# logging
# --------------------------------------------------------------------------------------
def log_line(msg, log_path=LOG_PATH):
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")


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
        except (urllib.error.URLError, TimeoutError):
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


def _tail_rows(path, n=SEEN_WINDOW):
    """Return up to the last n parsed rows of a jsonl file (order preserved)."""
    rows = list(_iter_jsonl(path))
    return rows[-n:] if len(rows) > n else rows


def _row_hash(venue, ts, market, price, size):
    key = f"{venue}|{ts}|{market}|{price}|{size}"
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]


def load_seen_set(path, window=SEEN_WINDOW):
    """Rolling seen-set from the last `window` rows of the output file."""
    seen = set()
    for row in _tail_rows(path, window):
        tid = row.get("trade_id")
        if tid:
            seen.add(str(tid))
    return seen


def load_state(path=STATE_PATH):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {}
        return data
    except Exception:
        # corrupt state = start fresh; log the gap, never fake continuity
        log_line("WARN state file corrupt/unreadable; starting fresh (gap logged)")
        return {}


def save_state(state, path=STATE_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    os.replace(tmp, path)


def append_rows(path, rows):
    """Append-only write; never touches existing bytes."""
    if not rows:
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=True) + "\n")
            f.flush()


# --------------------------------------------------------------------------------------
# Polymarket
# --------------------------------------------------------------------------------------
def normalize_poly_trade(tr):
    """Normalize one Polymarket /trades row. Returns dict or None if malformed/unfilterable."""
    if not isinstance(tr, dict):
        return None
    try:
        price = float(tr.get("price"))
        size = float(tr.get("size"))
    except (TypeError, ValueError):
        return None
    try:
        ts = int(tr.get("timestamp"))
    except (TypeError, ValueError):
        return None
    notional = price * size
    trade_id = tr.get("transactionHash") or tr.get("id")
    market = tr.get("conditionId") or tr.get("asset")
    if not trade_id:
        trade_id = _row_hash("polymarket", ts, market, price, size)
    return {
        "venue": "polymarket",
        "trade_id": str(trade_id),
        "ts": ts,
        "condition_id": tr.get("conditionId"),
        "asset": tr.get("asset"),
        "proxy_wallet": tr.get("proxyWallet"),
        "side": tr.get("side"),
        "outcome": tr.get("outcome"),
        "price": price,
        "size": size,
        "notional": notional,
        "raw": tr,
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def fetch_polymarket_tape(max_rows=POLY_PAGE_CAP, fetch_fn=fetch_json, sleep_fn=time.sleep,
                           out_path=POLY_OUT, call_sleep=0.2, state=None):
    state = state if state is not None else {}
    seen = load_seen_set(out_path)
    appended = []
    offset = 0
    hit_seen = False
    skipped_malformed = 0
    while offset < max_rows and not hit_seen:
        url = f"{POLY_TRADES_URL}?limit={POLY_PAGE_SIZE}&offset={offset}"
        try:
            batch = fetch_with_retry(url, fetch_fn, sleep_fn)
        except Exception as e:
            log_line(f"ERROR polymarket fetch failed at offset={offset}: {e}")
            break
        if not isinstance(batch, list) or not batch:
            break
        for tr in batch:
            norm = normalize_poly_trade(tr)
            if norm is None:
                skipped_malformed += 1
                continue
            if norm["trade_id"] in seen:
                # newest-first feed: once we hit an already-seen trade, everything
                # after it in this run is old news.
                hit_seen = True
                break
            if norm["notional"] < POLY_MIN_NOTIONAL:
                continue
            seen.add(norm["trade_id"])
            appended.append(norm)
            if len(appended) >= max_rows:
                break
        if len(batch) < POLY_PAGE_SIZE:
            break
        offset += POLY_PAGE_SIZE
        if len(appended) >= max_rows:
            break
        sleep_fn(call_sleep)
    append_rows(out_path, appended)
    if appended:
        state["polymarket"] = {
            "last_trade_id": appended[0]["trade_id"],
            "last_ts": max(r["ts"] for r in appended),
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    if skipped_malformed:
        log_line(f"polymarket: skipped {skipped_malformed} malformed rows")
    log_line(f"polymarket: appended {len(appended)} rows (offset reached={offset})")
    return len(appended)


# --------------------------------------------------------------------------------------
# Kalshi
# --------------------------------------------------------------------------------------
def normalize_kalshi_trade(tr):
    """Normalize one Kalshi /markets/trades row. Returns dict or None if malformed."""
    if not isinstance(tr, dict):
        return None
    # Live API (2026-07) serves count_fp (string) + yes/no_price_dollars (string
    # dollars); older/numeric shape is count + yes/no_price (integer cents).
    # Same dual-shape trap as candlesticks: unit decided by KEY, never magnitude.
    raw_count = tr.get("count_fp", tr.get("count"))
    try:
        count = float(raw_count)
    except (TypeError, ValueError):
        return None
    ticker = tr.get("ticker")
    created = tr.get("created_time")
    trade_id = tr.get("trade_id")
    if not trade_id:
        trade_id = _row_hash("kalshi", created, ticker,
                             tr.get("yes_price_dollars", tr.get("yes_price")), count)

    def price(key):
        v = tr.get(f"{key}_dollars")
        if v is not None:
            try:
                return float(v)
            except (TypeError, ValueError):
                return None
        v = tr.get(key)
        try:
            return float(v) / 100.0
        except (TypeError, ValueError):
            return None

    return {
        "venue": "kalshi",
        "trade_id": str(trade_id),
        "ts": created,
        "ticker": ticker,
        "count": count,
        "yes_price": price("yes_price"),
        "no_price": price("no_price"),
        "taker_side": tr.get("taker_side"),
        "raw": tr,
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def fetch_kalshi_tape(max_rows=2000, fetch_fn=fetch_json, sleep_fn=time.sleep,
                       out_path=KALSHI_OUT, call_sleep=0.2, state=None):
    state = state if state is not None else {}
    seen = load_seen_set(out_path)
    appended = []
    skipped_malformed = 0
    # Always start from the TOP of the tape (no cursor): Kalshi's trades cursor
    # pages toward OLDER trades, so resuming from a saved cursor walks further
    # into history every run and never captures new trades. The seen-set
    # (hit_seen) is the real resume mechanism — page newest→older until we
    # reach trades already on disk. (2026-07-07 fix; saved cursors ignored.)
    cursor = None
    hit_seen = False
    guard = 0
    while len(appended) < max_rows and not hit_seen and guard < 50:
        guard += 1
        url = f"{KALSHI_TRADES_URL}?limit=1000"
        if cursor:
            url += f"&cursor={cursor}"
        try:
            resp = fetch_with_retry(url, fetch_fn, sleep_fn)
        except Exception as e:
            log_line(f"ERROR kalshi fetch failed (cursor={cursor}): {e}")
            break
        if not isinstance(resp, dict):
            break
        batch = resp.get("trades") or []
        if not batch:
            break
        for tr in batch:
            norm = normalize_kalshi_trade(tr)
            if norm is None:
                skipped_malformed += 1
                continue
            if norm["trade_id"] in seen:
                hit_seen = True
                break
            if norm["count"] < KALSHI_MIN_COUNT:
                continue
            seen.add(norm["trade_id"])
            appended.append(norm)
            if len(appended) >= max_rows:
                break
        next_cursor = resp.get("cursor")
        if not next_cursor or next_cursor == cursor:
            break
        cursor = next_cursor
        if len(appended) >= max_rows:
            break
        sleep_fn(call_sleep)
    append_rows(out_path, appended)
    state["kalshi"] = {
        "cursor": None,  # never reused as a start point — see comment above
        "last_ts": appended[0]["ts"] if appended else (state.get("kalshi") or {}).get("last_ts"),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if skipped_malformed:
        log_line(f"kalshi: skipped {skipped_malformed} malformed rows")
    log_line(f"kalshi: appended {len(appended)} rows (cursor={cursor})")
    return len(appended)


# --------------------------------------------------------------------------------------
# selftest (offline, injected fakes)
# --------------------------------------------------------------------------------------
def _selftest():
    import shutil
    import tempfile

    tmpdir = tempfile.mkdtemp(prefix="tape_selftest_")
    ok = True

    def check(name, cond):
        nonlocal ok
        status = "PASS" if cond else "FAIL"
        if not cond:
            ok = False
        print(f"[selftest] {name}: {status}")

    # ---------------- (a) dedup across two runs + (b) append-only ----------------
    poly_out = os.path.join(tmpdir, "polymarket_tape.jsonl")

    page1 = [
        {"transactionHash": "0xaaa", "timestamp": "1000", "price": "0.50", "size": "1000",
         "conditionId": "c1", "asset": "a1", "proxyWallet": "w1", "side": "BUY", "outcome": "Yes"},
        {"transactionHash": "0xbbb", "timestamp": "999", "price": "0.10", "size": "5",
         "conditionId": "c1", "asset": "a1", "proxyWallet": "w2", "side": "SELL", "outcome": "No"},
        # malformed: missing price
        {"transactionHash": "0xbad", "timestamp": "998", "size": "10", "conditionId": "c1"},
    ]

    def fake_poly_fetch_run1(url):
        if "offset=0" in url:
            return page1
        return []

    n1 = fetch_polymarket_tape(max_rows=2000, fetch_fn=fake_poly_fetch_run1,
                                sleep_fn=lambda s: None, out_path=poly_out, call_sleep=0)
    check("polymarket run1 appended whale-only (notional>=200)", n1 == 1)

    with open(poly_out, "r", encoding="utf-8") as f:
        bytes_after_run1 = f.read()

    # run 2: same page1 (newest-first feed unchanged) plus one genuinely new whale trade
    page2 = [
        {"transactionHash": "0xccc", "timestamp": "1100", "price": "0.60", "size": "2000",
         "conditionId": "c1", "asset": "a1", "proxyWallet": "w3", "side": "BUY", "outcome": "Yes"},
    ] + page1

    def fake_poly_fetch_run2(url):
        if "offset=0" in url:
            return page2
        return []

    n2 = fetch_polymarket_tape(max_rows=2000, fetch_fn=fake_poly_fetch_run2,
                                sleep_fn=lambda s: None, out_path=poly_out, call_sleep=0)
    check("polymarket run2 appended only the new trade (dedup)", n2 == 1)

    with open(poly_out, "r", encoding="utf-8") as f:
        bytes_after_run2 = f.read()
    check("append-only: run1 bytes untouched by run2", bytes_after_run2.startswith(bytes_after_run1))

    check("notional filter excluded 0xbbb (0.10*5=$0.50 < $200)",
          "0xbbb" not in bytes_after_run2)
    check("malformed row 0xbad skipped without crashing",
          "0xbad" not in bytes_after_run2)

    lines = [json.loads(l) for l in bytes_after_run2.strip().split("\n")]
    ids = [r["trade_id"] for r in lines]
    check("polymarket tape has exactly 2 rows total (dedup across runs)", len(ids) == 2)
    check("no duplicate trade_ids in tape", len(ids) == len(set(ids)))

    # ---------------- (d) cursor resume passes cursor from state ----------------
    kalshi_out = os.path.join(tmpdir, "kalshi_tape.jsonl")
    state = {"kalshi": {"cursor": "resume-cursor-123"}}
    seen_urls = []

    def fake_kalshi_fetch(url):
        seen_urls.append(url)
        return {"trades": [], "cursor": None}

    fetch_kalshi_tape(max_rows=100, fetch_fn=fake_kalshi_fetch, sleep_fn=lambda s: None,
                       out_path=kalshi_out, call_sleep=0, state=state)
    check("kalshi resume: request used cursor from state",
          any("cursor=resume-cursor-123" in u for u in seen_urls))

    # ---------------- (c) count filter + (e) malformed rows on kalshi ----------------
    kalshi_out2 = os.path.join(tmpdir, "kalshi_tape2.jsonl")
    kalshi_page = {
        "trades": [
            {"trade_id": "k1", "ticker": "KX-A", "count": 500, "yes_price": 60,
             "no_price": 40, "taker_side": "yes", "created_time": "2026-07-01T00:00:00Z"},
            {"trade_id": "k2", "ticker": "KX-A", "count": 5, "yes_price": 60,
             "no_price": 40, "taker_side": "no", "created_time": "2026-07-01T00:00:01Z"},
            # malformed: missing count
            {"trade_id": "k3", "ticker": "KX-A", "yes_price": 60, "created_time": "bad"},
        ],
        "cursor": None,
    }

    def fake_kalshi_fetch2(url):
        return kalshi_page

    n3 = fetch_kalshi_tape(max_rows=100, fetch_fn=fake_kalshi_fetch2, sleep_fn=lambda s: None,
                            out_path=kalshi_out2, call_sleep=0, state={})
    check("kalshi count filter: only count>=100 kept", n3 == 1)
    with open(kalshi_out2, "r", encoding="utf-8") as f:
        content2 = f.read()
    check("kalshi malformed row (k3) skipped without crashing", "k3" not in content2)
    check("kalshi low-count row (k2) filtered out", "k2" not in content2)
    check("kalshi whale row (k1) present", '"k1"' in content2)

    shutil.rmtree(tmpdir, ignore_errors=True)

    print(f"[selftest] overall: {'PASS' if ok else 'FAIL'}")
    return ok


# --------------------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--venue", choices=["all", "polymarket", "kalshi"], default="all")
    ap.add_argument("--max-rows", type=int, default=2000)
    ap.add_argument("--selftest", action="store_true", help="offline selftest; touches no network")
    args = ap.parse_args()

    if args.selftest:
        ok = _selftest()
        raise SystemExit(0 if ok else 1)

    state = load_state()
    summary = {}

    if args.venue in ("polymarket", "all"):
        n = fetch_polymarket_tape(max_rows=args.max_rows, out_path=POLY_OUT, state=state)
        summary["polymarket"] = n

    if args.venue in ("kalshi", "all"):
        n = fetch_kalshi_tape(max_rows=args.max_rows, out_path=KALSHI_OUT, state=state)
        summary["kalshi"] = n

    save_state(state)
    print(json.dumps(summary, indent=2))
    log_line(f"run summary: {summary}")


if __name__ == "__main__":
    main()
