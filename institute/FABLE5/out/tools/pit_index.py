"""Point-in-time index over the two decision-time price stores (Kalshi candles + Polymarket
trades) written by fetch_prices_v2.py / fetch_prices.py.

The one honesty invariant that matters for backtesting: price_at(market_id, t) must return the
LAST known price STRICTLY BEFORE t -- never at or after t. An exact match (ts == t) does not
count as "known before t" and must be excluded, otherwise a backtest sees the future.

Loads lazily (first call to price_at/spread_at reads the underlying JSONL files once) and
caches per market id in memory for the life of the PitIndex instance.

stdlib only. Windows-safe paths.
"""
import glob
import json
import os
from collections import namedtuple

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "..", "..", "data", "history")
KALSHI_CANDLES = os.path.join(DATA, "prices", "kalshi_candles.jsonl")
POLY_TRADES = os.path.join(DATA, "prices", "polymarket_trades.jsonl")

PricePoint = namedtuple("PricePoint", ["ts", "price", "venue"])
SpreadPoint = namedtuple("SpreadPoint", ["ts", "yes_bid", "yes_ask"])

_GLOB_CHARS = set("*?[")


class PitIndex:
    """Lazy, cached point-in-time index. Safe to keep one instance around per process."""

    def __init__(self, kalshi_path=KALSHI_CANDLES, poly_path=POLY_TRADES):
        self.kalshi_path = kalshi_path
        self.poly_path = poly_path
        self._kalshi_cache = {}  # id -> sorted [(ts, close, yes_bid, yes_ask), ...]
        self._poly_cache = {}    # id -> sorted [(ts, price), ...]
        self._kalshi_loaded = False
        self._poly_loaded = False

    # -- loading -------------------------------------------------------------------
    def _load_kalshi(self):
        if self._kalshi_loaded:
            return
        self._kalshi_loaded = True
        if not os.path.exists(self.kalshi_path):
            return
        with open(self.kalshi_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                mid = str(row.get("id"))
                series = self._kalshi_cache.setdefault(mid, [])
                for c in row.get("candles") or []:
                    if not c or c[0] is None:
                        continue
                    ts = c[0]
                    close = c[4] if len(c) > 4 else None
                    ybid = c[5] if len(c) > 5 else None
                    yask = c[6] if len(c) > 6 else None
                    series.append((ts, close, ybid, yask))
        for mid, series in self._kalshi_cache.items():
            series.sort(key=lambda x: x[0])

    def _load_poly(self):
        if self._poly_loaded:
            return
        self._poly_loaded = True
        if any(ch in self.poly_path for ch in _GLOB_CHARS):
            paths = sorted(glob.glob(self.poly_path))
        else:
            paths = [self.poly_path] if os.path.exists(self.poly_path) else []
        for path in paths:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        row = json.loads(line)
                    except Exception:
                        continue
                    mid = str(row.get("id"))
                    pts = self._poly_cache.setdefault(mid, [])
                    for p in row.get("points") or []:
                        if not p or p[0] is None:
                            continue
                        pts.append((p[0], p[1]))
        for mid, pts in self._poly_cache.items():
            pts.sort(key=lambda x: x[0])

    # -- queries -------------------------------------------------------------------
    def price_at(self, market_id, t):
        """Last known price STRICTLY before t. Checks Kalshi candle closes, then PM trades."""
        mid = str(market_id)

        self._load_kalshi()
        series = self._kalshi_cache.get(mid)
        if series:
            best = None
            for ts, close, _, _ in series:
                if ts >= t:
                    break
                if close is not None:
                    best = (ts, close)
            if best is not None:
                return PricePoint(ts=best[0], price=best[1], venue="kalshi")

        self._load_poly()
        pts = self._poly_cache.get(mid)
        if pts:
            best = None
            for ts, price in pts:
                if ts >= t:
                    break
                best = (ts, price)
            if best is not None:
                return PricePoint(ts=best[0], price=best[1], venue="polymarket")

        return None

    def spread_at(self, market_id, t):
        """Kalshi only: (yes_bid, yes_ask) strictly before t, as a SpreadPoint, else None."""
        mid = str(market_id)
        self._load_kalshi()
        series = self._kalshi_cache.get(mid)
        if not series:
            return None
        best = None
        for ts, _, ybid, yask in series:
            if ts >= t:
                break
            best = (ts, ybid, yask)
        if best is None:
            return None
        return SpreadPoint(ts=best[0], yes_bid=best[1], yes_ask=best[2])


# module-level convenience wrappers over a shared default index
_default_index = None


def _index():
    global _default_index
    if _default_index is None:
        _default_index = PitIndex()
    return _default_index


def price_at(market_id, t):
    return _index().price_at(market_id, t)


def spread_at(market_id, t):
    return _index().spread_at(market_id, t)
