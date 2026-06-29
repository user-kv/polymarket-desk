"""Gate 4 capital-activation ladder / forward lockbox (CONSTITUTION Gate 4 + Appendix B).

A strategy earns graduation off paper only when forward OOS evidence is
statistically convincing (SPRT accept_H1 OR n >= N_FLOOR with positive EV).
Nothing graduates on thin data.
"""
import datetime

from institute.execute import paper
from institute.corpus.store import load_jsonl
from institute.evidence.stats import sprt

# Changeable params per CONSTITUTION §10 -- define at top, do not hardcode inline.
N_FLOOR = 50          # moderate-effect sample floor
WEEKS_MIN = 4         # minimum forward span
P0 = 0.50             # SPRT null: no edge (break-even win rate baseline)
P1_LIFT = 0.10        # SPRT alt: p0 + lift, capped 0.98


def settled_for(strategy_id, ledger_path=None):
    """Return strategy's status=='settled' ledger rows sorted by settled_ts."""
    if ledger_path is None:
        ledger_path = paper.PAPER_LEDGER
    rows = load_jsonl(ledger_path)
    settled = [r for r in rows
               if r.get("strategy_id") == strategy_id and r.get("status") == "settled"]
    settled.sort(key=lambda r: r.get("settled_ts", ""))
    return settled


def gate4_status(strategy_id, ledger_path=None):
    """Assess whether a strategy has earned graduation off paper.

    Returns a dict with keys: strategy_id, n, ev, span_weeks, sprt, verdict, reason.
    """
    if ledger_path is None:
        ledger_path = paper.PAPER_LEDGER

    rows = settled_for(strategy_id, ledger_path)
    n = len(rows)

    if n == 0:
        return {
            "strategy_id": strategy_id,
            "n": 0,
            "ev": 0.0,
            "span_weeks": 0.0,
            "sprt": None,
            "verdict": "accumulating",
            "reason": "no settled forward outcomes",
        }

    # Win/loss stream in chronological order
    stream = [1 if row["pnl"] > 0 else 0 for row in rows]

    # Forward EV = mean pnl per $1 staked
    ev = sum(row["pnl"] for row in rows) / n

    # Span in weeks
    span_weeks = 0.0
    try:
        fmt = "%Y-%m-%dT%H:%M:%SZ"
        first_ts = datetime.datetime.strptime(rows[0]["settled_ts"], fmt)
        last_ts = datetime.datetime.strptime(rows[-1]["settled_ts"], fmt)
        span_days = (last_ts - first_ts).total_seconds() / 86400.0
        span_weeks = span_days / 7.0
    except (ValueError, TypeError, KeyError):
        span_weeks = 0.0

    # SPRT early-stop
    p1 = min(0.98, P0 + P1_LIFT)
    s = sprt(stream, P0, p1)
    sprt_decision = s["decision"]

    # Verdict logic
    if (sprt_decision == "accept_H1" and ev > 0) or (
        n >= N_FLOOR and span_weeks >= WEEKS_MIN and ev > 0
    ):
        verdict = "graduated"
        if sprt_decision == "accept_H1" and ev > 0 and n < N_FLOOR:
            reason = "SPRT accept_H1 with positive EV (early graduation)"
        else:
            reason = f"n={n} >= {N_FLOOR}, span={round(span_weeks,2)}w >= {WEEKS_MIN}w, EV > 0"
    elif sprt_decision == "accept_H0" or (n >= N_FLOOR and ev <= 0):
        verdict = "rejected"
        if sprt_decision == "accept_H0":
            reason = "SPRT accept_H0 (no edge detected)"
        else:
            reason = f"n={n} >= {N_FLOOR} but EV <= 0"
    else:
        verdict = "accumulating"
        reason = f"n={n}, SPRT={sprt_decision}, EV={round(ev,6)}"

    return {
        "strategy_id": strategy_id,
        "n": n,
        "ev": round(ev, 6),
        "span_weeks": round(span_weeks, 2),
        "sprt": sprt_decision,
        "verdict": verdict,
        "reason": reason,
    }
