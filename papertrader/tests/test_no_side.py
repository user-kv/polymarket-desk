"""
NO-side unit tests (M5).

Covers:
  1. NO qualifies correctly when ask > prob + threshold and ask <= 15c cap
  2. NO blocked by negative edge (ensemble_prob > ask)
  3. NO blocked by ask > 15c cap
  4. Settlement: NO wins when bucket does NOT happen
  5. Settlement: NO loses when bucket DOES happen

Run:  PYTHONPATH=papertrader python -m pytest papertrader/tests/test_no_side.py -q
"""
import lib.forecasts as forecasts
from lib.engine import evaluate_bucket
from lib.settlement import did_bucket_win

# Shared base config — all YES guards tight so only NO path triggers
CFG = {
    "stake_per_bet": 20.0,
    "edge_threshold_pct": 5.0,
    "near_miss_min_pct": 3.0,
    "max_exposure_pct": 100.0,      # wide open so exposure never blocks
    "max_hours_to_resolution": 48,
    "model_agree_max_diff_c": 1.0,
    "buffer_around_mean_f": 2.0,
    "min_ensemble_prob_pct": 0.0,   # disabled so only edge/ask matter here
    "use_kelly_staking": False,
    "allow_no_side": True,
    "no_longshot_max_ask": 0.15,
    "min_ask_for_yes_pct": 0.0,     # disabled — let engine reach NO path naturally
    "nbm_min_member_prob_pct": 0.0, # disabled
}

# Market bucket far from the ensemble mean — bucket won't happen (mean=90F, bucket=105-106F)
MARKET = {
    "ask_price": 0.10,
    "hours_left": 24.0,
    "slug": "test-no-slug",
    "city": "Testville",
    "bucket_low_f": 105.0,
    "bucket_high_f": 106.0,
    "is_open_ended_low": False,
    "is_open_ended_high": False,
}
# Ensemble: all members cluster around 90°F — bucket 105-106 probability is near zero
FORECAST = {
    "all_highs_f": [90.0] * 50,
    "gfs_mean_f": 90.0,
    "ecmwf_mean_f": 90.0,
    "combined_mean_f": 90.0,
}


def _eval(ask, ensemble_prob, monkeypatch, cfg_overrides=None):
    """Run engine evaluation with patched ensemble_prob and given ask."""
    monkeypatch.setattr(forecasts, "bucket_probability_by_model", lambda *a, **k: ensemble_prob)
    m = dict(MARKET)
    m["ask_price"] = ask
    cfg = dict(CFG)
    if cfg_overrides:
        cfg.update(cfg_overrides)
    return evaluate_bucket(m, dict(FORECAST), [], cfg, 2000.0)


def test_no_qualifies_correctly(monkeypatch):
    # ask=0.10, ensemble_prob=0.02 → no_edge=0.08 (> 5% threshold), ask<=0.15 → NO BET
    r = _eval(0.10, 0.02, monkeypatch)
    assert r["action"] == "BET", r
    assert r["side"] == "NO", r
    assert r["edge_pct"] > 0
    assert r["no_entry_price"] == round(1.0 - 0.10, 4)


def test_no_blocked_by_negative_edge(monkeypatch):
    # ask=0.10, ensemble_prob=0.12 → no_edge=-0.02 (negative) → SKIP, not a NO bet
    r = _eval(0.10, 0.12, monkeypatch)
    assert r["action"] in ("SKIP", "NEAR_MISS"), r
    assert r.get("side") != "NO", r


def test_no_blocked_by_ask_above_cap(monkeypatch):
    # ask=0.20 > no_longshot_max_ask=0.15 → NO is blocked by the cap
    r = _eval(0.20, 0.02, monkeypatch)
    # YES also can't win here (ensemble_prob 0.02 < ask 0.20, negative YES edge)
    assert r["action"] in ("SKIP", "NEAR_MISS"), r
    assert r.get("side") != "NO", r


def test_no_settlement_win_when_bucket_does_not_happen():
    # Bucket 105-106°F; actual high = 91°F → bucket did NOT happen → NO wins
    bucket_happened = did_bucket_win(
        actual_high_f=91.0,
        low_f=105.0, high_f=106.0,
        is_oe_low=False, is_oe_high=False,
    )
    assert not bucket_happened, "Bucket should NOT have happened (actual=91, bucket=105-106)"
    # For a NO bet: won = not bucket_happened
    no_won = not bucket_happened
    assert no_won, "NO bet should WIN when bucket does not happen"


def test_no_settlement_loss_when_bucket_happens():
    # Bucket 89-90°F; actual high = 89.5°F → bucket DID happen → NO loses
    bucket_happened = did_bucket_win(
        actual_high_f=89.5,
        low_f=89.0, high_f=90.0,
        is_oe_low=False, is_oe_high=False,
    )
    assert bucket_happened, "Bucket should have happened (actual=89.5, bucket=89-90)"
    no_won = not bucket_happened
    assert not no_won, "NO bet should LOSE when bucket happens"


def test_no_shares_recomputed_after_brain_multiplier(monkeypatch):
    """Regression: when brain scales the NO stake, no_shares must be consistent
    with the POST-brain stake (not the pre-brain value)."""
    import lib.brain as brain_mod

    monkeypatch.setattr(
        forecasts, "bucket_probability_by_model",
        lambda *a, **k: 0.02,
    )
    monkeypatch.setattr(
        brain_mod, "evaluate_bet",
        lambda market, forecast, eval_for_brain, cfg: {
            "vetoed": False,
            "multiplier": 2.0,
            "rationale": "test",
            "backend": "test",
        },
    )

    cfg = dict(CFG)
    cfg["use_brain"] = True

    m = dict(MARKET)  # ask=0.10, produces a qualifying NO bet
    r = evaluate_bucket(m, dict(FORECAST), [], cfg, 2000.0)

    assert r["action"] == "BET", r
    assert r["side"] == "NO", r

    # Core invariant: shares must be stake / (1 - ask)
    expected_shares = round(r["stake"] / (1.0 - r["ask_price"]), 4)
    assert abs(r["shares"] - expected_shares) < 1e-6, (
        f"shares={r['shares']} inconsistent with stake={r['stake']} "
        f"at no_entry={1.0 - r['ask_price']:.4f}; expected {expected_shares}"
    )

    # Confirm the brain multiplier actually inflated the stake vs the base
    base_stake = CFG["stake_per_bet"]
    assert r["stake"] > base_stake, (
        f"brain multiplier 2.0 should have grown stake above {base_stake}, got {r['stake']}"
    )
