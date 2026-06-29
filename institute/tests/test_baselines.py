"""Constitution §2 sanity: copying the price is zero edge; the favorite-longshot
fade shows positive skill on a longshot-biased set."""
from institute.map import baselines as B


def _rm(q, y):
    return {"q_yes": q, "y": y}


def test_price_follow_is_zero_skill():
    rows = [_rm(0.2, 0), _rm(0.8, 1), _rm(0.5, 0), _rm(0.3, 1)]
    m = B.evaluate(rows, B.price_follow)
    assert abs(m["mean_S"]) < 1e-9   # p == q ⇒ market-relative skill exactly 0
    assert m["n"] == 0               # places no bet


def test_longshot_fade_positive_on_biased_set():
    # cheap longshots (q≈0.2) that mostly DON'T happen (y=0) — overpriced tails.
    rows = [_rm(0.2, 0)] * 8 + [_rm(0.2, 1)] * 1
    m = B.evaluate(rows, B.longshot_fade)
    assert m["mean_S"] > 0
    assert m["ev_net"] > 0
    assert m["n"] == 9
