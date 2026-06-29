"""Gate 7 significance-gated decay detector (CONSTITUTION Gate 7 + Appendix F).

Fires ONLY on statistically significant edge degradation, never on a normal
drawdown. Monitors a live cell's chronological per-bet pnl stream.
Symmetric: the same detector, run continuously, reports recent_ev for re-promotion
monitoring (acting on that is out of scope here).
"""
import math

from institute.evidence.stats import norm_cdf


def _sample_variance(xs):
    """Sample variance with ddof=1. Returns 0.0 for n < 2."""
    n = len(xs)
    if n < 2:
        return 0.0
    mu = sum(xs) / n
    return sum((x - mu) ** 2 for x in xs) / (n - 1)


def detect(pnl_series, recent_frac=0.4, alpha=0.05, min_window=8):
    """Detect statistically significant edge decay in a pnl stream.

    pnl_series: chronological list of per-bet pnl values.
    recent_frac: fraction of the tail treated as 'recent'.
    alpha: significance level for one-sided test.
    min_window: minimum observations required in each split.

    Returns dict with keys: decayed, reason, p_value, early_ev, recent_ev, n,
    and (when computable) z.
    """
    n = len(pnl_series)

    if n < 2 * min_window:
        return {
            "decayed": False,
            "reason": "insufficient history",
            "p_value": None,
            "early_ev": None,
            "recent_ev": None,
            "n": n,
        }

    k = max(min_window, int(round(n * recent_frac)))
    # Guard: ensure early slice is also at least min_window
    # DEVIATION: spec says guard len(early) >= min_window but doesn't say what to do
    # if the guard fails. We fall back to a 50/50 split to maintain validity.
    if (n - k) < min_window:
        k = n - min_window

    early = pnl_series[:n - k]
    recent = pnl_series[n - k:]

    me = sum(early) / len(early)
    mr = sum(recent) / len(recent)
    ne = len(early)
    nr = len(recent)
    ve = _sample_variance(early)
    vr = _sample_variance(recent)

    se_sq = ve / ne + vr / nr
    if se_sq <= 0.0:
        # Zero standard error: deterministic comparison
        decayed = mr < me
        p_value = 0.0 if decayed else 1.0
        return {
            "decayed": decayed,
            "reason": "deterministic (zero variance)" if decayed else "no decay (zero variance)",
            "p_value": p_value,
            "early_ev": round(me, 6),
            "recent_ev": round(mr, 6),
            "z": 0.0,
            "n": n,
        }

    se = math.sqrt(se_sq)
    z = (mr - me) / se
    p_value = norm_cdf(z)  # left tail = P(recent worse than early)

    # Material erosion check: recent edge collapsed toward/below zero.
    material = (mr <= 0) or (mr < 0.5 * me)
    decayed = (p_value < alpha) and (mr < me) and material

    if decayed:
        reason = f"edge decay detected: early_ev={round(me,4)}, recent_ev={round(mr,4)}, p={round(p_value,4)}"
    else:
        reason = "no significant decay"

    return {
        "decayed": decayed,
        "reason": reason,
        "p_value": round(p_value, 4),
        "early_ev": round(me, 6),
        "recent_ev": round(mr, 6),
        "z": round(z, 4),
        "n": n,
    }
