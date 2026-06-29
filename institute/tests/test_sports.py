"""A3 sports archetype: external-signal baselines + positive skill on a biased set."""
from institute.classify import sports
from institute.map.baselines import evaluate


def _rm(q, y, book=None, model=None):
    meta = {}
    if book is not None:
        meta["book_prob"] = book
    if model is not None:
        meta["model_prob"] = model
    return {"q_yes": q, "y": y, "meta": meta}


def test_odds_follow_directions():
    assert sports.odds_follow(_rm(0.5, 1, book=0.8))[1] == "YES"
    assert sports.odds_follow(_rm(0.5, 0, book=0.2))[1] == "NO"
    assert sports.odds_follow(_rm(0.5, 1, book=0.5))[1] is None
    assert sports.odds_follow(_rm(0.5, 1))[1] is None   # no book_prob -> no bet


def test_power_rating_fade_uses_model_prob():
    assert sports.power_rating_fade(_rm(0.5, 1, model=0.7))[1] == "YES"
    assert sports.power_rating_fade(_rm(0.5, 0, model=0.3))[1] == "NO"
    assert sports.power_rating_fade(_rm(0.5, 1, model=0.52))[1] is None


def test_odds_follow_has_skill_when_book_is_sharper():
    # PM mispriced at 0.5; the sharp book (0.8) is right (y=1) more often.
    rows = [_rm(0.5, 1, book=0.8)] * 8 + [_rm(0.5, 0, book=0.8)] * 2
    m = evaluate(rows, sports.odds_follow)
    assert m["mean_S"] > 0
    assert m["n"] == 10
