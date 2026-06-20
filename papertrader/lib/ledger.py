"""
lib/ledger.py
Manages the append-only bets.csv and bankroll.json.

bets.csv columns (M4 adds side, brain_multiplier, brain_rationale):
  bet_id, timestamp, city, station, question, slug, market_id, yes_token,
  end_date, bucket_low_f, bucket_high_f, is_open_ended_low, is_open_ended_high,
  side, ask_price, stake, shares, gross_if_win, fee_if_win, net_profit_if_win,
  net_loss_if_lose, ensemble_prob, edge_pct, gfs_mean_f, ecmwf_mean_f,
  n_members, brain_multiplier, brain_rationale,
  status, result, actual_high_f, settled_at, pnl, is_test

  side: "YES" (buy YES token) | "NO" (buy NO token at 1-ask)
  brain_multiplier: Kelly multiplier set by brain (1.0 = no change; 0.0 = vetoed)
  brain_rationale: one-line reason from the brain (empty if brain disabled)

bankroll.json:
  {"balance": 500.00, "start": 500.00, "history": [{"ts": ..., "balance": ...}]}
"""

import csv
import json
import os
import logging
from datetime import datetime, timezone

logger = logging.getLogger("ledger")

BETS_COLS = [
    "bet_id", "timestamp", "city", "station", "question", "slug", "market_id",
    "yes_token", "end_date", "bucket_low_f", "bucket_high_f",
    "is_open_ended_low", "is_open_ended_high",
    "side",                                          # M4: "YES" or "NO"
    "ask_price", "stake", "shares", "gross_if_win", "fee_if_win",
    "net_profit_if_win", "net_loss_if_lose",
    "ensemble_prob", "edge_pct", "gfs_mean_f", "ecmwf_mean_f", "n_members",
    "brain_multiplier", "brain_rationale",           # M3: brain sizing metadata
    "status", "result", "actual_high_f", "settled_at", "pnl", "is_test",
]

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
BETS_PATH = os.path.join(DATA_DIR, "bets.csv")
BANKROLL_PATH = os.path.join(DATA_DIR, "bankroll.json")


def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "scans"), exist_ok=True)


def load_bankroll(start=500.0):
    """Load or initialise bankroll.json. Returns dict."""
    _ensure_data_dir()
    if os.path.exists(BANKROLL_PATH):
        with open(BANKROLL_PATH) as f:
            return json.load(f)
    br = {"balance": start, "start": start, "history": []}
    _save_bankroll(br)
    return br


def _save_bankroll(br):
    with open(BANKROLL_PATH, "w") as f:
        json.dump(br, f, indent=2)


def update_bankroll(delta, note=""):
    """Add delta to balance, record in history. Returns new balance."""
    br = load_bankroll()
    br["balance"] = round(br["balance"] + delta, 4)
    br["history"].append({
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "delta": delta,
        "balance": br["balance"],
        "note": note,
    })
    _save_bankroll(br)
    return br["balance"]


_FLOAT_COLS = {
    "ask_price", "stake", "shares", "gross_if_win", "fee_if_win",
    "net_profit_if_win", "net_loss_if_lose", "ensemble_prob", "edge_pct",
    "gfs_mean_f", "ecmwf_mean_f", "bucket_low_f", "bucket_high_f", "pnl",
    "actual_high_f",
}
_INT_COLS = {"n_members"}


def _cast_bet(row):
    """Coerce numeric CSV strings to float/int so callers can do arithmetic."""
    out = dict(row)
    for col in _FLOAT_COLS:
        v = out.get(col, "")
        if v not in ("", None):
            try:
                out[col] = float(v)
            except (ValueError, TypeError):
                pass
    for col in _INT_COLS:
        v = out.get(col, "")
        if v not in ("", None):
            try:
                out[col] = int(v)
            except (ValueError, TypeError):
                pass
    return out


def load_bets():
    """Return list of bet dicts from bets.csv. Empty list if file doesn't exist."""
    _ensure_data_dir()
    if not os.path.exists(BETS_PATH):
        return []
    with open(BETS_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [_cast_bet(row) for row in reader]


def append_bet(bet_dict):
    """
    Append one bet to bets.csv (creates file with header if needed).
    Also deducts stake from bankroll immediately.
    """
    _ensure_data_dir()
    file_exists = os.path.exists(BETS_PATH)
    with open(BETS_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=BETS_COLS, extrasaction="ignore")
        if not file_exists:
            writer.writeheader()
        writer.writerow(bet_dict)

    stake = float(bet_dict.get("stake", 0))
    if bet_dict.get("is_test", "N") != "Y":
        update_bankroll(-stake, note=f"paper_bet {bet_dict.get('bet_id','')}")
    logger.info(f"Bet placed: {bet_dict.get('question', '')} | edge={bet_dict.get('edge_pct')}pt | stake=${stake}")


def update_bet(bet_id, updates):
    """
    Update fields on a specific bet (settlement). Rewrites the whole CSV.
    updates: dict of field->value to update.
    """
    bets = load_bets()
    found = False
    for b in bets:
        if b.get("bet_id") == bet_id:
            b.update(updates)
            found = True
            break
    if not found:
        logger.warning(f"update_bet: bet_id {bet_id} not found")
        return False

    with open(BETS_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=BETS_COLS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(bets)
    return True


def get_open_bets():
    """Return only bets with status=='open'."""
    return [b for b in load_bets() if b.get("status") == "open"]


def save_scan_snapshot(scan_data, scans_dir=None):
    """Save the full scan result as a JSON file for audit trail."""
    if scans_dir is None:
        scans_dir = os.path.join(DATA_DIR, "scans")
    os.makedirs(scans_dir, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    path = os.path.join(scans_dir, f"scan_{ts}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(scan_data, f, indent=2, default=str)
    logger.info(f"Scan snapshot saved: {path}")
    return path
