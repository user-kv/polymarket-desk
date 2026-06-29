"""Return series from a baseline over resolved rows.

Mirrors baselines.evaluate's realized-PnL branch: when the ledger already
recorded the actual outcome for this exact side, use it (ground truth anchor).
Otherwise simulate from executable prices. Rows where the baseline passes
(side=None) are silently dropped — they carry no bet.
"""
from institute.map.baselines import _sim_profit


def returns_series(rows, baseline_fn, cost=0.0, **kw) -> list:
    """Per-bet net return vector (one float per placed bet).

    Prefer realized_pnl/stake when the row is the real anchor and the
    realized_side matches the signal — same logic as baselines.evaluate.
    """
    out = []
    for rm in rows:
        p, side = baseline_fn(rm, **kw)
        if side is None:
            continue
        use_real = (
            rm.get("realized_pnl") is not None
            and rm.get("realized_side") == side
        )
        if use_real:
            stake = max(rm.get("stake", 1.0) or 1.0, 1e-9)
            out.append(rm["realized_pnl"] / stake)
        else:
            out.append(_sim_profit(side, rm["q_yes"], rm["y"], cost))
    return out


def win_loss_stream(rows, baseline_fn, **kw) -> list:
    """Binary 1/0 win/loss per placed bet — feeds SPRT."""
    return [1 if r > 0 else 0 for r in returns_series(rows, baseline_fn, **kw)]
