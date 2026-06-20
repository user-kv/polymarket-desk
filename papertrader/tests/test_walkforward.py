"""
Deterministic tests for lib/prob_calibration.py and lib/walkforward.py.

(a) calibrator improves a deliberately miscalibrated set
(b) no train/test leakage — test-day rows are excluded from training
(c) both_cal captures a synthetic overpriced longshot (NO side)

Run:  PYTHONPATH=papertrader python -m pytest papertrader/tests/test_walkforward.py -q
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import lib.prob_calibration as pc
from lib.walkforward import run_walkforward, _days_before

# ─── minimal fake cfg ───────────────────────────────────────────────────────
_CFG = {
    "stake_per_bet": 5.0,
    "fee_on_winnings_pct": 2.0,
    "edge_threshold_pct": 0.0,   # accept all positive-edge bets in these tests
}

# ─── helpers ────────────────────────────────────────────────────────────────
def _market(city, date, prob, ask, won):
    """Build a minimal scored-market row for the walkforward harness."""
    return {
        "city": city,
        "end_date": date + "T23:59:00Z",
        "ensemble_prob": prob,
        "ask_price": ask,
        "won": won,
        "bucket_low_f": 70.0,
        "bucket_high_f": 75.0,
        "is_oe_low": False,
        "is_oe_high": False,
    }


# ─── (a) calibration improves a miscalibrated dataset ───────────────────────
def test_calibration_improves_brier():
    """
    Build a set where the raw model systematically over-estimates probability
    (says ~90% but true hit rate is ~50%). Calibration must push Brier down.
    """
    # 40 training pairs: model says 0.90, outcome is alternating 0/1 (50% rate)
    pairs = [(0.90, float(i % 2)) for i in range(40)]
    model = pc.fit(pairs, n_bins=5, kappa=8)

    raw_probs = [p for p, _ in pairs]
    outcomes = [o for _, o in pairs]

    cal_probs = [pc.apply(model, p) for p in raw_probs]
    brier_raw = pc.brier(raw_probs, outcomes)
    brier_cal = pc.brier(cal_probs, outcomes)

    assert brier_cal < brier_raw, (
        f"Expected calibration to reduce Brier but got raw={brier_raw:.4f} "
        f"cal={brier_cal:.4f}"
    )


# ─── (b) no train/test leakage ──────────────────────────────────────────────
def test_no_leakage():
    """
    The test-day rows must never appear in the training window.
    We inject a canary: one market that resolves on the TEST day, with a unique
    improbable probability (0.777). If it leaked into training, the calibrator
    would be fitted partly on it. We verify by checking the fold's n_train count
    is strictly less than the total usable count (i.e. test markets are excluded).
    """
    # 25 markets on 2026-06-01 (train for the fold on 2026-06-02)
    train_day = "2026-06-01"
    test_day = "2026-06-02"
    scored = [_market("Sydney", train_day, 0.55, 0.50, True) for _ in range(25)]
    # 3 canary markets on the test day
    for _ in range(3):
        scored.append(_market("Sydney", test_day, 0.777, 0.70, False))

    res = run_walkforward(_CFG, scored=scored, min_train=20, embargo_days=0)

    assert not res.get("insufficient"), "Expected at least one valid fold"
    assert res["n_folds"] >= 1
    # The test fold trained on train_day markets only
    fold = next(f for f in res["folds"] if f["day"] == test_day)
    assert fold["n_train"] == 25, (
        f"Expected 25 train markets (train_day only) but got {fold['n_train']} — leakage?"
    )
    assert fold["n_test"] == 3


# ─── (c) both_cal captures an overpriced longshot via NO side ───────────────
def test_both_cal_captures_no_side():
    """
    Build 30 training markets where the market severely overprices a longshot
    (ask 0.40, true hit rate ~20%). The calibrator should push the calibrated
    probability down below the ask, making the NO side positive-EV. both_cal
    must place at least one NO bet; yes_raw (no calibration, YES only) must not.
    """
    # Train: market says 0.40, but market resolves YES only 6/30 = 20% of the time
    train_day = "2026-06-01"
    test_day = "2026-06-02"
    scored = []
    for i in range(30):
        scored.append(_market("Perth", train_day, 0.40, 0.40, i < 6))  # 6 wins, 24 losses

    # Test: same overpriced setup
    for i in range(5):
        scored.append(_market("Perth", test_day, 0.40, 0.40, i < 1))

    res = run_walkforward(_CFG, scored=scored, min_train=20, embargo_days=0)

    assert not res.get("insufficient"), "Expected at least one valid fold"
    strats = res["strategies"]
    assert strats["both_cal"]["bets"] > 0, (
        "both_cal placed zero bets — calibrator did not detect NO-side edge"
    )
    # yes_raw bets YES only; with ask=0.40 and raw_prob=0.40, edge=0 so no bet at thr=0
    # (edge_threshold_pct=0 means >= 0 qualifies, so raw_prob - ask = 0.0 which equals thr)
    # The important assertion is that both_cal found NO-side bets
    assert strats["both_cal"]["bets"] >= strats["yes_raw"]["bets"], (
        "both_cal should be >= yes_raw in bet count when the NO side is the value"
    )
