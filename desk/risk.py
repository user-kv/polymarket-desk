"""
desk/risk.py — risk self-awareness (Phase 2).

Two guards the brief consults before confirming a bet:

  1. Category track record. Using the settled ledger, compute a recency-weighted
     win-rate per category (city). If a category has enough resolved bets and a
     losing record, the desk DECLINES it — the system learns which kinds of markets
     it is bad at and stops feeding them (research round 1: risk self-awareness;
     round 5: regime-aware weighting so a fixed-then-recovered category can recover).

  2. Liquidity. Skip markets too thin to realistically fill, and (optionally) the
     hyper-saturated ones where pro bots already closed the latency window
     (research round 5). Reads volume/liquidity now captured by the scanner.

Both are advisory inputs to the brief; the deterministic engine remains authority.
"""

from __future__ import annotations
import csv
from pathlib import Path
from datetime import datetime, timezone

PAPERTRADER = Path(__file__).resolve().parents[1] / "papertrader"
BETS_CSV = PAPERTRADER / "data" / "bets.csv"

WINRATE_HALFLIFE_DAYS = 45.0
MIN_SAMPLES_TO_JUDGE = 8       # below this, not enough data to decline a category
DECLINE_BELOW_WINRATE = 0.45   # weighted win-rate under this => decline the category

# Liquidity bounds (fake-money paper trades, but we model realistic fillability).
MIN_VOLUME_USD = 5_000.0       # below: too illiquid to trust the ask
MAX_VOLUME_USD = None          # set e.g. 5_000_000 to also avoid hyper-saturated books


def _category(city: str) -> str:
    return (city or "general").strip().lower().replace(" ", "-")


def _age_days(ts: str) -> float:
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            t = datetime.strptime(ts, fmt)
            if t.tzinfo is None:
                t = t.replace(tzinfo=timezone.utc)
            return max(0.0, (datetime.now(timezone.utc) - t).total_seconds() / 86400.0)
        except ValueError:
            continue
    return 9999.0


def category_winrate(category: str, bets_csv: Path = BETS_CSV) -> dict:
    """Recency-weighted win-rate for a category. Returns {n, winrate, weighted_n}."""
    if not bets_csv.exists():
        return {"n": 0, "winrate": None, "weighted_n": 0.0}
    wins = total = 0.0
    n = 0
    with bets_csv.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if _category(r.get("city", "")) != category:
                continue
            res = (r.get("result") or "").upper()
            if res not in ("WON", "LOST"):
                continue
            w = 0.5 ** (_age_days(r.get("settled_at") or r.get("timestamp", "")) / WINRATE_HALFLIFE_DAYS)
            total += w
            wins += w if res == "WON" else 0.0
            n += 1
    return {"n": n, "winrate": (wins / total) if total else None,
            "weighted_n": round(total, 3)}


def should_decline_category(category: str, bets_csv: Path = BETS_CSV) -> tuple[bool, str]:
    stats = category_winrate(category, bets_csv)
    if stats["n"] < MIN_SAMPLES_TO_JUDGE or stats["winrate"] is None:
        return False, f"insufficient history (n={stats['n']})"
    if stats["winrate"] < DECLINE_BELOW_WINRATE:
        return True, (f"DECLINE {category}: weighted win-rate {stats['winrate']:.0%} "
                      f"over n={stats['n']} < {DECLINE_BELOW_WINRATE:.0%}")
    return False, f"ok: win-rate {stats['winrate']:.0%} (n={stats['n']})"


def passes_liquidity(market: dict) -> tuple[bool, str]:
    """True if the market is liquid enough to trust/fill. Graceful if volume unknown."""
    vol = market.get("volume_num")
    if vol is None:
        return True, "liquidity unknown (scanner pre-dates volume capture) — not vetoing"
    if vol < MIN_VOLUME_USD:
        return False, f"too illiquid: volume ${vol:,.0f} < ${MIN_VOLUME_USD:,.0f}"
    if MAX_VOLUME_USD is not None and vol > MAX_VOLUME_USD:
        return False, f"hyper-saturated: volume ${vol:,.0f} > ${MAX_VOLUME_USD:,.0f}"
    return True, f"liquidity ok: ${vol:,.0f}"


def all_category_winrates(bets_csv: Path = BETS_CSV) -> dict:
    cats = set()
    if bets_csv.exists():
        with bets_csv.open(encoding="utf-8") as f:
            for r in csv.DictReader(f):
                cats.add(_category(r.get("city", "")))
    return {c: category_winrate(c, bets_csv) for c in sorted(cats) if c}


if __name__ == "__main__":
    import json
    print(json.dumps(all_category_winrates(), indent=2))
