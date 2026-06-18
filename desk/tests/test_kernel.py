"""Tests for the immutable kernel: invariants + fitness math."""
import math
import sys
from pathlib import Path

# allow `import desk...` when run directly
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from desk.kernel import invariants as inv
from desk.kernel import fitness as fit


def test_fake_money_invariant_holds():
    assert inv.FAKE_MONEY_ONLY is True
    assert inv.ALLOW_REAL_ORDERS is False
    assert inv.ALLOW_WALLET is False
    assert inv.MAX_BANKROLL_USD == 0.0
    inv.assert_fake_money_only()  # must not raise


def test_param_bounds_reject_loosening():
    # cannot lower the edge threshold below the protected floor
    assert inv.param_within_bounds("edge_threshold_pct", 5.0) is True
    assert inv.param_within_bounds("edge_threshold_pct", 1.0) is False
    # cannot bet on > 72h lead
    assert inv.param_within_bounds("max_hours_to_resolution", 48) is True
    assert inv.param_within_bounds("max_hours_to_resolution", 200) is False
    # unknown key is unconstrained
    assert inv.param_within_bounds("some_new_param", 999) is True


def test_crps_perfect_forecast_is_zero():
    # all members equal the observation -> CRPS 0
    assert abs(fit.crps_ensemble([70.0] * 10, 70.0)) < 1e-9


def test_crps_rewards_closeness():
    obs = 80.0
    tight = fit.crps_ensemble([79, 80, 81], obs)
    wide = fit.crps_ensemble([60, 80, 100], obs)
    assert tight < wide  # sharper, well-placed ensemble scores better (lower)


def test_brier_decomposition_identity():
    # BS == reliability - resolution + uncertainty (Murphy)
    probs = [0.1, 0.4, 0.6, 0.9, 0.2, 0.8, 0.5, 0.3]
    outs = [0, 0, 1, 1, 0, 1, 0, 1]
    r = fit.brier_decomposition(probs, outs, n_bins=10)
    recon = r.reliability - r.resolution + r.uncertainty
    assert abs(recon - r.brier) < 1e-9


def test_promotion_requires_proper_score_improvement():
    champ = fit.FitnessReport(crps=2.0, brier=0.20, reliability=0.05,
                              resolution=0.10, pnl=10.0, n_forecasts=50, n_bets=20)
    # challenger improves CRPS, doesn't worsen Brier, keeps PnL -> promote
    better = fit.FitnessReport(crps=1.5, brier=0.20, reliability=0.04,
                               resolution=0.11, pnl=10.0, n_forecasts=50, n_bets=20)
    ok, _ = fit.challenger_beats_champion(champ, better)
    assert ok is True

    # challenger only improves PnL (reward-hack attempt) -> reject
    hack = fit.FitnessReport(crps=2.0, brier=0.20, reliability=0.05,
                             resolution=0.10, pnl=999.0, n_forecasts=50, n_bets=20)
    ok, msg = fit.challenger_beats_champion(champ, hack)
    assert ok is False

    # challenger improves CRPS but loses money -> reject
    loser = fit.FitnessReport(crps=1.0, brier=0.20, reliability=0.05,
                              resolution=0.10, pnl=-5.0, n_forecasts=50, n_bets=20)
    ok, msg = fit.challenger_beats_champion(champ, loser)
    assert ok is False


def _run():
    passed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  PASS {name}")
            passed += 1
    print(f"\n{passed} kernel tests passed.")


if __name__ == "__main__":
    _run()
