"""A3: strategy-gen proposes real cells with a mechanism; never the null."""
from institute.strategy import generate


def test_proposes_longshot_fade_with_mechanism():
    strategies = generate.propose()
    assert strategies, "expected at least one proposal from the weather map"
    fade = [s for s in strategies if s.baseline == "longshot_fade"]
    assert fade, "weather longshot_fade should be proposed"
    assert fade[0].mechanism == "favorite_longshot_bias"
    assert fade[0].archetype == "weather-daily"


def test_null_baseline_not_proposed():
    strategies = generate.propose()
    assert all(s.baseline != "price_follow" for s in strategies)


def test_budget_caps_proposals():
    # synthetic map with many positive cells must respect the budget
    class C:
        def __init__(self, b):
            self.archetype = "x"; self.baseline = b
            self.mean_S = 0.1; self.ev_net = 0.1; self.n = 5
    cells = [C(f"odds_follow") for _ in range(20)]
    out = generate.propose_from_map(cells, budget=3)
    assert len(out) == 3
