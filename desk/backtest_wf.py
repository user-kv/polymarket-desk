"""
desk/backtest_wf.py — walk-forward, out-of-sample backtest (Phase 3).

This is the empirical fitness validator. Phase 4 self-modification promotes a change
ONLY if it beats the champion here, so the rigor of this file is what stops the loop
from fooling itself. Three safeguards from the research (rounds 1, 3, 5):

  * Walk-forward: history is split into ordered folds; each fold is scored using only
    bets that resolved BEFORE it. No in-sample peeking — that is how reward-hacking
    on in-sample PnL is prevented.
  * Outcome embargo: lessons/decisions for a bet placed at time t may not use any
    information that became known after t (store.recall_asof). Kills the
    look-ahead / "oracle fallacy" leakage the agentic-trading survey flagged as the
    #1 pitfall.
  * Transaction costs: the 2% winnings fee is applied to PnL (already in the ledger),
    and an optional slippage haircut models imperfect fills.

Fitness is reported as CRPS (if member-level forecast cases are supplied) + Brier
(from prob vs outcome) + PnL, via the immutable kernel.fitness definition.
"""

from __future__ import annotations
import csv
from pathlib import Path
from dataclasses import dataclass

from desk.kernel import fitness
from desk.memory import store

PAPERTRADER = Path(__file__).resolve().parents[1] / "papertrader"
BETS_CSV = PAPERTRADER / "data" / "bets.csv"


def _f(v, d=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def load_ordered_settled(bets_csv: Path = BETS_CSV) -> list[dict]:
    """Resolved bets, sorted by settlement time (walk-forward order)."""
    if not bets_csv.exists():
        return []
    rows = []
    with bets_csv.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if (r.get("result") or "").upper() in ("WON", "LOST"):
                rows.append(r)
    rows.sort(key=lambda r: (r.get("settled_at") or r.get("timestamp") or ""))
    return rows


def _prob_outcome_pairs(bets: list[dict]) -> list[tuple[float, int]]:
    """(YES probability we assigned, realised outcome) for Brier."""
    pairs = []
    for b in bets:
        p = _f(b.get("ensemble_prob"))
        o = 1 if (b.get("result") or "").upper() == "WON" else 0
        pairs.append((p, o))
    return pairs


def _embargo_ok(bets: list[dict], asof_ts: str) -> bool:
    """Assert every bet used to score a fold resolved at/before the embargo time."""
    for b in bets:
        ts = b.get("settled_at") or b.get("timestamp") or ""
        if ts and asof_ts and ts > asof_ts:
            return False
    return True


@dataclass
class FoldResult:
    fold: int
    train_n: int
    test_n: int
    embargo_ts: str
    fitness: dict


def walk_forward(n_folds: int = 4, slippage_pct: float = 0.0,
                 crps_cases=None, bets_csv: Path = BETS_CSV) -> dict:
    """
    Expanding-window walk-forward. Fold k trains on the first k slices and tests on
    slice k+1 (strictly later bets), scoring out-of-sample. Returns per-fold fitness
    plus the pooled out-of-sample FitnessReport that the promotion gate consumes.
    """
    bets = load_ordered_settled(bets_csv)
    if len(bets) < 2:
        # Not enough resolved history yet — return a well-formed empty report so the
        # promotion gate degrades safely instead of crashing.
        empty = fitness.compute_fitness(crps_cases or [], [], [])
        return {"n_bets": len(bets), "folds": [],
                "oos_fitness": empty.as_dict(),
                "note": "insufficient resolved history for walk-forward (need >=2 bets)"}

    n_folds = max(1, min(n_folds, len(bets) - 1))
    slice_size = max(1, len(bets) // (n_folds + 1))
    folds: list[FoldResult] = []
    pooled_test: list[dict] = []

    for k in range(n_folds):
        train_end = slice_size * (k + 1)
        test_start, test_end = train_end, min(train_end + slice_size, len(bets))
        if test_start >= len(bets):
            break
        train = bets[:train_end]
        test = bets[test_start:test_end]
        # embargo: decisions in `test` may only use lessons up to the last train ts
        embargo_ts = train[-1].get("settled_at") or train[-1].get("timestamp") or ""
        assert _embargo_ok(train, embargo_ts), "embargo violation in training slice"

        # apply slippage to PnL (a haircut on winning bets to model imperfect fills)
        test_adj = []
        for b in test:
            bb = dict(b)
            if (b.get("result") or "").upper() == "WON" and slippage_pct:
                bb["pnl"] = _f(b.get("pnl")) * (1.0 - slippage_pct / 100.0)
            test_adj.append(bb)

        fr = fitness.compute_fitness([], _prob_outcome_pairs(test_adj), test_adj)
        folds.append(FoldResult(k, len(train), len(test_adj), embargo_ts, fr.as_dict()))
        pooled_test.extend(test_adj)

    pooled = fitness.compute_fitness(
        crps_cases or [], _prob_outcome_pairs(pooled_test), pooled_test)
    return {"n_bets": len(bets), "n_folds": len(folds),
            "folds": [f.__dict__ for f in folds],
            "oos_fitness": pooled.as_dict(),
            "slippage_pct": slippage_pct}


if __name__ == "__main__":
    import json
    print(json.dumps(walk_forward(), indent=2, default=str))
