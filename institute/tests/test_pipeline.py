"""A3 pipeline: cells walk the gates; thin evidence never reaches 'paper'."""
from institute import pipeline
from institute.resolve import weather_adapter


def test_weather_cell_not_promoted_at_low_n():
    rows = weather_adapter.load_rows()
    res = pipeline.run_cell("weather-daily", "longshot_fade", rows=rows, log=False)
    assert {"strategy", "gate1", "gate2", "gate3", "status"} <= set(res)
    assert res["gate1"]["verdict"] == "insufficient"   # n=13 is too thin
    assert res["status"] != "paper"                    # cannot promote on insufficient


def test_run_all_returns_weather_cells():
    results = pipeline.run_all(log=False)
    assert results
    assert any(r["strategy"].archetype == "weather-daily" for r in results)
    # render must not crash and stays ASCII
    txt = pipeline.render(results)
    assert txt.isascii()
