"""A3 Gate 2: mechanism must be stated AND consistent with the error pattern."""
from institute.corpus.schema import Strategy
from institute.map.baselines import longshot_fade
from institute.gates import mechanism
from institute.resolve import weather_adapter


def _strat(mech):
    return Strategy(id="t", archetype="weather-daily", baseline="longshot_fade",
                    mechanism=mech, hypothesis="x")


def test_flb_passes_on_real_weather():
    rows = [rm for rm in weather_adapter.load_rows() if rm["archetype"] == "weather-daily"]
    res = mechanism.check(_strat("favorite_longshot_bias"), rows, longshot_fade)
    assert res["passed"] is True
    assert res["mechanism"] == "favorite_longshot_bias"


def test_empty_mechanism_is_held():
    rows = weather_adapter.load_rows()
    res = mechanism.check(_strat(""), rows, longshot_fade)
    assert res["passed"] is False
    assert "no stated mechanism" in res["reason"]


def test_unknown_mechanism_rejected():
    rows = weather_adapter.load_rows()
    res = mechanism.check(_strat("vibes"), rows, longshot_fade)
    assert res["passed"] is False
