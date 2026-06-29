from institute.classify.archetype import classify, in_initial_universe


def test_known_markets_classify():
    assert classify("Will the highest temperature in Dallas be between 96-97F on June 13?") == "weather-daily"
    assert classify("Will Bitcoin close above $70,000 on June 28?") == "crypto-daily"
    assert classify("Will the Fed cut interest rate in July?") == "econ-release"
    assert classify("Lakers vs Celtics: will the Lakers win the game?") == "sports-game"
    assert classify("Will it rain tacos tomorrow?") == "other"


def test_initial_universe():
    assert in_initial_universe("weather-daily")
    assert in_initial_universe("crypto-daily")
    assert not in_initial_universe("other")
