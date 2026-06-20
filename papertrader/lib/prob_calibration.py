"""
lib/prob_calibration.py — PROBABILITY calibration for the weather paper-trader.

NOT to be confused with lib/calibration.py, which corrects the forecast
*temperature* bias (shifts every member's high by N°F). This module corrects the
*probability* itself: it answers "when the ensemble says 20%, does the event
actually happen 20% of the time?" — and if not, learns the mapping that makes it
so. Calibrated probabilities are the foundation for honest edge and Kelly sizing
(see weather-bot-v2-roadmap M1).

Method — reliability binning shrunk toward the identity line:

    cal(p) = (n_b * empirical_rate_b + KAPPA * p) / (n_b + KAPPA)

where bin b is the equal-width probability bin containing p, empirical_rate_b is
the observed YES-frequency of training markets that landed in b, and n_b is how
many there were. With no data in a bin (n_b = 0) the calibrator returns p
unchanged (the raw forecast is the prior); as evidence accumulates it bends
toward the observed frequency. KAPPA is the pseudo-count that controls how much
data it takes to overrule the prior.

Why this and not isotonic regression: isotonic overfits badly on a few hundred
points (it can carve the curve into noise-driven steps). Shrink-to-identity
binning degrades gracefully — at low n it does almost nothing, so it can never
fabricate a phantom edge from noise. That conservatism is exactly what we want
before risking money. It is also trivially serialisable and reproducible.

The model is a plain dict (JSON-serialisable); fit/apply are pure functions so
the walk-forward harness can fit one calibrator per fold without side effects.
"""

import math

# Pseudo-count: with KAPPA "prior observations" pinned on the identity line, a
# bin needs ~KAPPA real markets before it meaningfully moves the probability.
# 8 keeps small samples honest; lower it as the dataset grows.
DEFAULT_KAPPA = 8.0
DEFAULT_BINS = 5  # equal-width bins over [0,1]; 5 -> 20%-wide buckets

_EPS = 1e-3  # clamp so log-loss / Kelly never see exactly 0 or 1


def _clamp(p):
    return max(_EPS, min(1.0 - _EPS, p))


def _bin_index(p, n_bins):
    return min(int(p * n_bins), n_bins - 1)


def fit(pairs, n_bins=DEFAULT_BINS, kappa=DEFAULT_KAPPA):
    """
    pairs: iterable of (raw_prob, outcome) where outcome is 1 (YES) or 0 (NO).
    Returns a JSON-serialisable model dict. Empty input -> identity calibrator.
    """
    wins = [0.0] * n_bins
    tot = [0.0] * n_bins
    n = 0
    for p, y in pairs:
        b = _bin_index(p, n_bins)
        tot[b] += 1.0
        wins[b] += 1.0 if y else 0.0
        n += 1
    rates = [(wins[b] / tot[b]) if tot[b] else None for b in range(n_bins)]
    return {
        "n_bins": n_bins,
        "kappa": kappa,
        "counts": tot,
        "rates": rates,   # None where no training data fell in the bin
        "n": n,
    }


def apply(model, p):
    """Map a raw probability through the fitted calibrator. Pure; clamped."""
    if not model or not model.get("n"):
        return _clamp(p)
    n_bins = model["n_bins"]
    kappa = model["kappa"]
    b = _bin_index(p, n_bins)
    n_b = model["counts"][b]
    rate_b = model["rates"][b]
    if not n_b or rate_b is None:
        return _clamp(p)                       # empty bin -> trust the raw prob
    cal = (n_b * rate_b + kappa * p) / (n_b + kappa)
    return _clamp(cal)


# ──────────────────────────────────────────────────────────────────────────────
# scoring metrics (lower = better for all three)
# ──────────────────────────────────────────────────────────────────────────────
def brier(probs, outcomes):
    if not probs:
        return None
    return sum((p - y) ** 2 for p, y in zip(probs, outcomes)) / len(probs)


def log_loss(probs, outcomes):
    if not probs:
        return None
    s = 0.0
    for p, y in zip(probs, outcomes):
        p = _clamp(p)
        s += -(y * math.log(p) + (1 - y) * math.log(1 - p))
    return s / len(probs)


def expected_calibration_error(probs, outcomes, n_bins=DEFAULT_BINS):
    """Mean |confidence - accuracy| weighted by bin population (ECE)."""
    if not probs:
        return None
    wins = [0.0] * n_bins
    conf = [0.0] * n_bins
    tot = [0.0] * n_bins
    for p, y in zip(probs, outcomes):
        b = _bin_index(p, n_bins)
        tot[b] += 1.0
        conf[b] += p
        wins[b] += 1.0 if y else 0.0
    n = len(probs)
    ece = 0.0
    for b in range(n_bins):
        if tot[b]:
            acc = wins[b] / tot[b]
            avg_conf = conf[b] / tot[b]
            ece += (tot[b] / n) * abs(avg_conf - acc)
    return ece


def reliability_table(pairs, model=None, n_bins=DEFAULT_BINS):
    """
    Build a reliability diagram as rows: predicted-prob bucket -> observed YES%.
    If `model` is given, also shows the calibrated mean per bucket so you can see
    the correction the calibrator would apply.
    """
    wins = [0.0] * n_bins
    raw_sum = [0.0] * n_bins
    cal_sum = [0.0] * n_bins
    tot = [0.0] * n_bins
    for p, y in pairs:
        b = _bin_index(p, n_bins)
        tot[b] += 1.0
        raw_sum[b] += p
        wins[b] += 1.0 if y else 0.0
        if model:
            cal_sum[b] += apply(model, p)
    rows = []
    width = 100.0 / n_bins
    for b in range(n_bins):
        if not tot[b]:
            continue
        rows.append({
            "range": f"{b*width:.0f}-{(b+1)*width:.0f}%",
            "n": int(tot[b]),
            "raw_mean_pct": round(raw_sum[b] / tot[b] * 100.0, 1),
            "actual_pct": round(wins[b] / tot[b] * 100.0, 1),
            "calibrated_pct": (round(cal_sum[b] / tot[b] * 100.0, 1) if model else None),
        })
    return rows
