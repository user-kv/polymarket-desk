"""Tests for institute.alpha.engine — offline, deterministic, no network (A6)."""
from institute.alpha.engine import (
    swarm_forecast,
    reconcile,
    blend,
    forecast_market,
    _parse_prob,
    _mock_p,
)
from institute.alpha.personas import PERSONAS
from institute.scoring import clip


# ── fixtures ──────────────────────────────────────────────────────────────────

def _market(q=0.4, market_id="test-market-001"):
    return {"market_id": market_id, "question": "Will BTC close above $50k?", "q_yes": q, "meta": {}}


# ── _parse_prob ───────────────────────────────────────────────────────────────

def test_parse_prob_decimal():
    assert abs(_parse_prob("I think 0.73 is right") - 0.73) < 1e-6


def test_parse_prob_percent():
    assert abs(_parse_prob("About 65% likely") - 0.65) < 1e-6


def test_parse_prob_bare_dot():
    assert abs(_parse_prob(".42") - 0.42) < 1e-6


def test_parse_prob_garbage_returns_none():
    assert _parse_prob("no numbers here at all") is None


def test_parse_prob_none_input():
    assert _parse_prob(None) is None


def test_parse_prob_empty():
    assert _parse_prob("") is None


# ── swarm_forecast (mock=True) ────────────────────────────────────────────────

def test_swarm_forecast_returns_one_per_persona():
    m = _market()
    results = swarm_forecast(m, mock=True)
    assert len(results) == len(PERSONAS)


def test_swarm_forecast_all_p_in_range():
    m = _market()
    results = swarm_forecast(m, mock=True)
    for r in results:
        assert 0 < r["p"] < 1, f"p out of range: {r}"


def test_swarm_forecast_deterministic():
    m = _market()
    r1 = swarm_forecast(m, mock=True)
    r2 = swarm_forecast(m, mock=True)
    for a, b in zip(r1, r2):
        assert a["persona"] == b["persona"]
        assert a["p"] == b["p"]


def test_swarm_forecast_different_markets_differ():
    """Different market IDs should produce different jitter values."""
    m1 = _market(market_id="aaa")
    m2 = _market(market_id="bbb")
    r1 = swarm_forecast(m1, mock=True)
    r2 = swarm_forecast(m2, mock=True)
    ps1 = [r["p"] for r in r1]
    ps2 = [r["p"] for r in r2]
    # At least one persona should differ
    assert ps1 != ps2


def test_swarm_forecast_persona_ids():
    m = _market()
    results = swarm_forecast(m, mock=True)
    ids = [r["persona"] for r in results]
    expected_ids = [p["id"] for p in PERSONAS]
    assert ids == expected_ids


# ── swarm_forecast mock=False with injectable _complete ───────────────────────

def _fake_complete_good(prompt, role="reason", mock=True, **kw):
    """Fake LLM that always returns a parseable probability."""
    return "I estimate 0.73 probability."


def _fake_complete_garbage(prompt, role="reason", mock=True, **kw):
    """Fake LLM that returns unparseable text."""
    return "absolutely no idea whatsoever"


def test_swarm_forecast_mock_false_good_response():
    m = _market()
    results = swarm_forecast(m, _complete=_fake_complete_good, mock=False)
    assert len(results) == len(PERSONAS)
    for r in results:
        assert abs(r["p"] - 0.73) < 1e-6, f"Expected 0.73, got {r['p']}"


def test_swarm_forecast_mock_false_garbage_falls_back_no_raise():
    """Parse failure must fall back to deterministic mock, not raise."""
    m = _market()
    results = swarm_forecast(m, _complete=_fake_complete_garbage, mock=False)
    # Should not raise; should return one entry per persona
    assert len(results) == len(PERSONAS)
    # Values should match the deterministic mock
    mock_results = swarm_forecast(m, mock=True)
    for real, expected in zip(results, mock_results):
        assert abs(real["p"] - expected["p"]) < 1e-9


# ── reconcile ─────────────────────────────────────────────────────────────────

def test_reconcile_mock_equals_mean():
    m = _market()
    forecasts = [{"persona": "a", "p": 0.5}, {"persona": "b", "p": 0.7}]
    result = reconcile(forecasts, m, mock=True)
    assert abs(result["p_model"] - 0.6) < 1e-9


def test_reconcile_p_std_zero_when_all_equal():
    m = _market()
    forecasts = [{"persona": str(i), "p": 0.5} for i in range(5)]
    result = reconcile(forecasts, m, mock=True)
    assert result["p_std"] == 0.0


def test_reconcile_n_matches_forecast_count():
    m = _market()
    forecasts = [{"persona": str(i), "p": 0.4 + i * 0.05} for i in range(4)]
    result = reconcile(forecasts, m, mock=True)
    assert result["n"] == 4


def test_reconcile_empty_forecasts():
    m = _market()
    result = reconcile([], m, mock=True)
    assert result["n"] == 0
    assert result["p_model"] == 0.5  # safe default


# ── blend ─────────────────────────────────────────────────────────────────────

def test_blend_spec_value():
    """blend(0.8, 0.4, 0.7) == clip(0.7*0.8 + 0.3*0.4) == clip(0.68) == 0.68."""
    result = blend(0.8, 0.4, 0.70)
    assert abs(result - clip(0.68)) < 1e-9


def test_blend_equal_inputs():
    assert abs(blend(0.5, 0.5, 0.7) - 0.5) < 1e-9


def test_blend_clips_extremes():
    # Should stay in (0,1) even with extreme inputs
    r = blend(1.0, 1.0, 1.0)
    assert 0 < r < 1


# ── forecast_market ───────────────────────────────────────────────────────────

def test_forecast_market_returns_required_keys():
    m = _market()
    result = forecast_market(m, mock=True)
    for key in ("p_model", "p_std", "p_final", "n_agents", "w"):
        assert key in result, f"Missing key: {key}"


def test_forecast_market_p_final_equals_blend():
    m = _market(q=0.4)
    result = forecast_market(m, w=0.70, mock=True)
    expected = blend(result["p_model"], m["q_yes"], w=0.70)
    assert abs(result["p_final"] - expected) < 1e-9


def test_forecast_market_n_agents_matches_personas():
    m = _market()
    result = forecast_market(m, personas=PERSONAS, mock=True)
    assert result["n_agents"] == len(PERSONAS)


def test_forecast_market_w_stored():
    m = _market()
    result = forecast_market(m, w=0.65, mock=True)
    assert result["w"] == 0.65
