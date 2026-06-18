"""
desk/kernel/fitness.py — IMMUTABLE fitness definition.

"Better" is defined here and ONLY here. The self-modification loop optimises
against these numbers, so they live in the protected kernel: if the loop could
edit the ruler, it would reward-hack the ruler instead of improving the trading.

Three strictly-proper / objective measures (research round 5):
  * CRPS  — Continuous Ranked Probability Score on the ensemble forecast vs the
            observed high. Jointly rewards calibration AND sharpness. Lower better.
  * Brier — mean squared error of the bucket YES-probabilities vs outcomes, with
            Murphy's decomposition into reliability / resolution / uncertainty.
            Lower better.
  * PnL   — realised fake-dollar profit. Higher better, but noisy and gameable,
            so it is the tie-breaker, never the sole objective.

A challenger only beats the champion if it improves the proper scores out-of-sample
(see desk/backtest_wf.py). PnL alone can never promote a change.
"""

from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Sequence
import math


# --------------------------------------------------------------------------- #
# CRPS for an ensemble (empirical / sample form).
#   CRPS = (1/m) Σ|x_i - y|  -  1/(2 m²) ΣΣ|x_i - x_j|
# where x_i are the m ensemble member highs and y is the observed high.
# --------------------------------------------------------------------------- #
def crps_ensemble(members_f: Sequence[float], observed_f: float) -> float:
    m = len(members_f)
    if m == 0:
        raise ValueError("CRPS needs at least one ensemble member")
    term1 = sum(abs(x - observed_f) for x in members_f) / m
    # mean absolute pairwise difference
    s = 0.0
    for xi in members_f:
        for xj in members_f:
            s += abs(xi - xj)
    term2 = s / (2.0 * m * m)
    return term1 - term2


def mean_crps(cases: Sequence[tuple[Sequence[float], float]]) -> float:
    """cases: list of (member_highs, observed_high). Returns mean CRPS (lower better)."""
    if not cases:
        return float("nan")
    return sum(crps_ensemble(mem, obs) for mem, obs in cases) / len(cases)


# --------------------------------------------------------------------------- #
# Brier score + Murphy decomposition.
#   forecasts p_i in [0,1], outcomes o_i in {0,1}
#   BS = mean( (p_i - o_i)^2 )
#   With K probability bins: BS = reliability - resolution + uncertainty
# --------------------------------------------------------------------------- #
@dataclass
class BrierReport:
    brier: float
    reliability: float   # lower = better calibrated
    resolution: float    # higher = sharper / more discriminating
    uncertainty: float   # base-rate variance (property of the data, not the model)
    n: int

    def as_dict(self) -> dict:
        return asdict(self)


def brier_decomposition(probs: Sequence[float], outcomes: Sequence[int],
                        n_bins: int = 10) -> BrierReport:
    if len(probs) != len(outcomes):
        raise ValueError("probs and outcomes length mismatch")
    n = len(probs)
    if n == 0:
        return BrierReport(float("nan"), float("nan"), float("nan"), float("nan"), 0)

    brier = sum((p - o) ** 2 for p, o in zip(probs, outcomes)) / n
    base_rate = sum(outcomes) / n
    uncertainty = base_rate * (1.0 - base_rate)

    # bin by forecast probability
    bins: list[list[tuple[float, int]]] = [[] for _ in range(n_bins)]
    for p, o in zip(probs, outcomes):
        idx = min(int(p * n_bins), n_bins - 1)
        bins[idx].append((p, o))

    reliability = 0.0
    resolution = 0.0
    for b in bins:
        if not b:
            continue
        nk = len(b)
        mean_p = sum(p for p, _ in b) / nk
        obs_freq = sum(o for _, o in b) / nk
        reliability += nk * (mean_p - obs_freq) ** 2
        resolution += nk * (obs_freq - base_rate) ** 2
    reliability /= n
    resolution /= n
    return BrierReport(brier, reliability, resolution, uncertainty, n)


# --------------------------------------------------------------------------- #
# Realised PnL (fake dollars) from settled bet records.
# --------------------------------------------------------------------------- #
def realised_pnl(settled_bets: Sequence[dict]) -> float:
    total = 0.0
    for b in settled_bets:
        pnl = b.get("pnl", "")
        if pnl == "" or pnl is None:
            continue
        try:
            total += float(pnl)
        except (TypeError, ValueError):
            continue
    return total


# --------------------------------------------------------------------------- #
# Composite fitness — the single object the promotion gate compares.
# --------------------------------------------------------------------------- #
@dataclass
class FitnessReport:
    crps: float            # lower better
    brier: float           # lower better
    reliability: float     # lower better
    resolution: float      # higher better
    pnl: float             # higher better (tie-breaker only)
    n_forecasts: int
    n_bets: int

    def as_dict(self) -> dict:
        return asdict(self)


def compute_fitness(crps_cases, prob_outcome_pairs, settled_bets) -> FitnessReport:
    crps = mean_crps(crps_cases) if crps_cases else float("nan")
    probs = [p for p, _ in prob_outcome_pairs]
    outs = [o for _, o in prob_outcome_pairs]
    br = brier_decomposition(probs, outs) if prob_outcome_pairs else BrierReport(
        float("nan"), float("nan"), float("nan"), float("nan"), 0)
    return FitnessReport(
        crps=crps, brier=br.brier, reliability=br.reliability,
        resolution=br.resolution, pnl=realised_pnl(settled_bets),
        n_forecasts=len(crps_cases), n_bets=len(settled_bets),
    )


def challenger_beats_champion(champion: FitnessReport, challenger: FitnessReport,
                              eps: float = 1e-6) -> tuple[bool, str]:
    """
    Promotion rule. A challenger must IMPROVE a proper score (CRPS or Brier)
    out-of-sample without worsening the other beyond noise, AND not lose money.
    PnL can only break ties — it can never, alone, promote a change. This is the
    anti-reward-hacking gate.
    """
    def better(a, b):   # lower is better, NaN-safe
        if math.isnan(a) or math.isnan(b):
            return False
        return a < b - eps
    def not_worse(a, b):
        if math.isnan(a) or math.isnan(b):
            return True
        return a <= b + eps

    crps_better = better(challenger.crps, champion.crps)
    brier_better = better(challenger.brier, champion.brier)
    crps_ok = not_worse(challenger.crps, champion.crps)
    brier_ok = not_worse(challenger.brier, champion.brier)
    pnl_ok = challenger.pnl >= champion.pnl - eps

    if not pnl_ok:
        return False, f"rejected: PnL regressed ({challenger.pnl:.2f} < {champion.pnl:.2f})"
    if crps_better and brier_ok:
        return True, f"promoted: CRPS {champion.crps:.3f}->{challenger.crps:.3f}"
    if brier_better and crps_ok:
        return True, f"promoted: Brier {champion.brier:.4f}->{challenger.brier:.4f}"
    return False, "rejected: no out-of-sample improvement in a proper score"
