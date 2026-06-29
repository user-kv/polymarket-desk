"""Weather → ResolvedMarket rows from the papertrader settled ledger.

This is the real-data anchor: the live +$68 NO-side longshot fade. No network —
reads the committed bets.csv. (Sports/crypto adapters arrive next; they need a
live sensor collecting resolved history over time — see A1_PLAN out-of-scope.)
"""
import os
import csv

from institute.corpus.schema import ResolvedMarket

BASE = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
BETS = os.path.join(BASE, "papertrader", "data", "bets.csv")


def load_rows(bets_path=BETS):
    rows = []
    if not os.path.exists(bets_path):
        return rows
    with open(bets_path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("status") != "settled" or r.get("is_test") == "Y":
                continue
            side = r.get("side", "")
            result = r.get("result", "")
            # YES bucket resolved iff: a YES bet WON, or a NO bet LOST.
            if side == "YES":
                y = 1 if result == "WON" else 0
            else:  # NO
                y = 0 if result == "WON" else 1
            try:
                q_yes = float(r.get("ask_price", 0) or 0)
                pnl = float(r.get("pnl", 0) or 0)
                stake = float(r.get("stake", 0) or 0) or 1.0
            except ValueError:
                continue
            rows.append(ResolvedMarket(
                market_id=r.get("bet_id", ""),
                archetype="weather-daily",
                t0=r.get("timestamp", ""),
                q_yes=q_yes,
                y=y,
                realized_pnl=pnl,
                realized_side=side,
                stake=stake,
                meta={"city": r.get("city", ""), "station": r.get("station", "")},
            ).dict())
    return rows
