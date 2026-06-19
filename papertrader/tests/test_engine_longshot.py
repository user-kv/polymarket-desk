"""
Regression test for the favorite-longshot guard (engine rule 6), added 2026-06-20.

The first 5 paper bets all LOST — every one a deep-tail bucket the ensemble itself
gave < 15% probability. This test pins the lesson into code: a low-probability bucket
must be SKIPped (not bet, not even logged as a near-miss), while a healthy-probability
bucket with the same edge must still BET. If someone weakens the floor and reintroduces
the longshot mistake, this fails.

Run:  PYTHONPATH=papertrader python -m pytest papertrader/tests/test_engine_longshot.py -q
"""
import lib.forecasts as forecasts
from lib.engine import evaluate_bucket

CFG = {
    "stake_per_bet": 20.0, "edge_threshold_pct": 5.0, "near_miss_min_pct": 3.0,
    "max_exposure_pct": 20.0, "max_hours_to_resolution": 48,
    "model_agree_max_diff_c": 1.0, "buffer_around_mean_f": 2.0,
    "min_ensemble_prob_pct": 15.0, "use_kelly_staking": False,
}

# A market/forecast where everything EXCEPT the bucket probability is fine:
# short lead, models agree tightly, bucket well outside the mean buffer.
MARKET = {"ask_price": 0.01, "hours_left": 24.0, "slug": "x", "city": "Testville",
          "bucket_low_f": 96.0, "bucket_high_f": 97.0}
FORECAST = {"all_highs_f": [90.0] * 50, "gfs_mean_f": 90.5, "ecmwf_mean_f": 90.6,
            "combined_mean_f": 90.55}


def _eval(prob, monkeypatch):
    monkeypatch.setattr(forecasts, "bucket_probability_by_model", lambda *a, **k: prob)
    return evaluate_bucket(dict(MARKET), dict(FORECAST), [], dict(CFG), 2000.0)


def test_longshot_tail_is_skipped(monkeypatch):
    # 6% model prob over a 1% ask = +5pt "edge", but it's a longshot. Must SKIP.
    r = _eval(0.06, monkeypatch)
    assert r["action"] == "SKIP", r
    assert "longshot" in r["reason"].lower()
    assert any(name == "min_ensemble_prob" and not ok for name, ok, _ in r["all_rules"])


def test_all_five_historical_losers_blocked(monkeypatch):
    # The actual ensemble_prob of the 5 first paper losses — every one must be blocked.
    for prob in (0.0, 0.0511, 0.06, 0.0856, 0.135):
        assert _eval(prob, monkeypatch)["action"] == "SKIP", prob


def test_healthy_probability_still_bets(monkeypatch):
    # Same edge structure but the model gives a real 25% — this is the kind of bet
    # the guard is meant to KEEP. Must still BET.
    r = _eval(0.25, monkeypatch)
    assert r["action"] == "BET", r
    assert all(ok for _, ok, _ in r["all_rules"]), r["all_rules"]
