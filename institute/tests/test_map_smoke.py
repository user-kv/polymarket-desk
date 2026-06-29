"""End-to-end map on the real settled weather ledger — the +$68 reality anchor.
The weather × longshot_fade cell must show positive EV_net, matching the live
NO-side result. If this regresses, the map has drifted from reality."""
from institute.resolve import weather_adapter
from institute.map import predictability


def test_map_runs_and_weather_fade_is_positive():
    rows = weather_adapter.load_rows()
    assert rows, "no settled weather rows found in papertrader/data/bets.csv"
    cells = predictability.build(rows)
    assert cells
    fade = [c for c in cells if c.archetype == "weather-daily" and c.baseline == "longshot_fade"]
    assert fade, "weather-daily × longshot_fade cell missing"
    assert fade[0].ev_net > 0, f"expected +EV anchor, got {fade[0].ev_net}"
