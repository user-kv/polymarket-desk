"""Forward-paper executor: institute-side ledger feeding Gate 4.

NOT the papertrader bets.csv -- this is a thin institute jsonl recording
positions opened by strategies that have passed gates 1-3. Gate 4 reads
forward_count() to assess whether a strategy has enough live OOS resolutions.
"""
import os
import uuid
import datetime

from institute.map.baselines import _sim_profit
from institute.corpus.store import append_jsonl, load_jsonl, overwrite_jsonl

_DATA = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
PAPER_LEDGER = os.path.join(_DATA, "paper_ledger.jsonl")


def _utcnow_iso():
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def open_position(strategy, market_snapshot, baseline_fn, ledger_path=PAPER_LEDGER, **kw) -> dict | None:
    """Open a forward paper position for strategy on this market snapshot.

    market_snapshot must contain {market_id, q_yes, t0, ...}.
    Calls baseline_fn to get (p, side); if side is None returns None (no bet).
    Appends an open position record to the ledger and returns it.
    """
    q_yes = market_snapshot["q_yes"]
    rm_like = {"q_yes": q_yes, "y": 0, **market_snapshot}  # y placeholder; not used for decision
    p, side = baseline_fn(rm_like, **kw)

    if side is None:
        return None

    strategy_id = strategy.id if hasattr(strategy, "id") else strategy.get("id", "")
    archetype = strategy.archetype if hasattr(strategy, "archetype") else strategy.get("archetype", "")
    baseline = strategy.baseline if hasattr(strategy, "baseline") else strategy.get("baseline", "")

    pos = {
        "id": uuid.uuid4().hex[:12],
        "strategy_id": strategy_id,
        "archetype": archetype,
        "baseline": baseline,
        "market_id": market_snapshot["market_id"],
        "t0": market_snapshot.get("t0", _utcnow_iso()),
        "q_yes_entry": q_yes,
        "side": side,
        "status": "open",
        "y": None,
        "pnl": None,
        "settled_ts": None,
    }
    append_jsonl(ledger_path, [pos])
    return pos


def settle(market_id, y, ledger_path=PAPER_LEDGER) -> dict | None:
    """Settle all open positions for market_id with outcome y.

    Computes pnl via _sim_profit, sets status='settled', overwrites ledger.
    Returns the last settled position (or None if none found).
    """
    positions = load_jsonl(ledger_path)
    settled = None
    updated = []
    for pos in positions:
        if pos["market_id"] == market_id and pos["status"] == "open":
            pos = dict(pos)
            pos["y"] = y
            pos["pnl"] = round(_sim_profit(pos["side"], pos["q_yes_entry"], y), 6)
            pos["status"] = "settled"
            pos["settled_ts"] = _utcnow_iso()
            settled = pos
        updated.append(pos)
    if settled is not None:
        overwrite_jsonl(ledger_path, updated)
    return settled


def forward_count(strategy_id, ledger_path=PAPER_LEDGER) -> int:
    """Number of settled positions for this strategy — the Gate-4 counter."""
    positions = load_jsonl(ledger_path)
    return sum(
        1 for p in positions
        if p.get("strategy_id") == strategy_id and p.get("status") == "settled"
    )


def open_positions(ledger_path=PAPER_LEDGER) -> list:
    """All currently open positions."""
    return [p for p in load_jsonl(ledger_path) if p.get("status") == "open"]
