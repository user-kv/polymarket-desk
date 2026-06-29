"""A3 Gate 3: the adversarial battery catches leaks and fragile fills."""
from institute.map.baselines import longshot_fade
from institute.gates import redteam
from institute.resolve import weather_adapter


def _cheat(rm, **kw):
    """A lookahead-leaking baseline: side depends on the outcome y."""
    return rm["q_yes"], ("YES" if rm["y"] == 1 else "NO")


def test_lookahead_flags_cheating_baseline():
    rows = [{"q_yes": 0.3, "y": 0}, {"q_yes": 0.3, "y": 1}]
    f = redteam.attack_lookahead(None, rows, _cheat)
    assert f["fatal"] is True


def test_lookahead_clears_clean_baseline():
    rows = weather_adapter.load_rows()
    f = redteam.attack_lookahead(None, rows, longshot_fade)
    assert f["fatal"] is False


def test_fills_fatal_on_marginal_set():
    # NO bets at q=0.2 (payoff 0.25); 40 wins / 9 losses -> EV just above 0,
    # flips negative under 3% fill stress.
    rows = [{"q_yes": 0.2, "y": 0}] * 40 + [{"q_yes": 0.2, "y": 1}] * 9
    f = redteam.attack_fills(None, rows, longshot_fade)
    assert f["fatal"] is True
    assert f["evidence"]["ev_clean"] > 0 > f["evidence"]["ev_stress"]


def test_fills_survive_on_real_weather():
    rows = weather_adapter.load_rows()
    f = redteam.attack_fills(None, rows, longshot_fade)
    assert f["fatal"] is False


def test_run_aggregates_survival():
    rows = weather_adapter.load_rows()
    res = redteam.run(None, rows, longshot_fade)
    assert "survived" in res and len(res["findings"]) == 3
