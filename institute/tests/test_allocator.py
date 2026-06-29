"""A4 portfolio/allocator.py: Kelly sizing, clustering, and cap tests."""
from institute.portfolio.allocator import (
    kelly_fraction, allocate,
    CELL_CAP, CLUSTER_CAP, ARCHETYPE_CAP, TOTAL_CAP,
)


def _cell(cid, archetype, baseline, ev_net, win_pct, mean_s=0.08, mean_price=0.15):
    return {
        "id": cid,
        "archetype": archetype,
        "baseline": baseline,
        "metrics": {
            "n": 50,
            "win_pct": win_pct,
            "mean_S": mean_s,
            "ev_net": ev_net,
            "naive_roi": ev_net,
        },
        "mean_price": mean_price,
    }


# ── Kelly tests ───────────────────────────────────────────────────────────────

def test_kelly_positive_ev_cell():
    """High win rate, good payoff -> positive Kelly, clipped <= CELL_CAP."""
    f = kelly_fraction(win_prob=0.9, payoff_b=4.0, calib=1.0)
    assert f > 0.0
    assert f <= CELL_CAP


def test_kelly_negative_ev_cell():
    """p=0.2, b=1.0 -> f_star = 0.2 - 0.8 = -0.6 < 0 -> 0."""
    f = kelly_fraction(win_prob=0.2, payoff_b=1.0, calib=1.0)
    assert f == 0.0


def test_kelly_zero_payoff():
    f = kelly_fraction(win_prob=0.9, payoff_b=0.0, calib=1.0)
    assert f == 0.0


def test_kelly_zero_calib():
    """Zero calibration quality -> zero allocation (§7: gets cut not trusted less)."""
    f = kelly_fraction(win_prob=0.9, payoff_b=4.0, calib=0.0)
    assert f == 0.0


# ── Clustering and Gate 5 tests ───────────────────────────────────────────────

def test_two_identical_weather_cells_cluster_together():
    """Two weather cells (corr=1.0) must end up in the same cluster."""
    c1 = _cell("w1", "weather-daily", "longshot_fade", ev_net=0.20, win_pct=80.0)
    c2 = _cell("w2", "weather-daily", "longshot_fade", ev_net=0.05, win_pct=55.0)
    result = allocate([c1, c2], bankroll=10000.0)
    # Cluster sum weight must not exceed CLUSTER_CAP
    total_w = sum(a["weight"] for a in result["allocations"])
    assert total_w <= CLUSTER_CAP + 1e-9, f"cluster sum {total_w} > CLUSTER_CAP {CLUSTER_CAP}"


def test_dominated_cell_gets_gate5_wait():
    """Lower ev_net cell that is below MARGINAL_FLOOR_FRAC * anchor.ev_net -> gate5_wait."""
    # c1 anchor ev=0.20; c2 ev=0.02 < 0.5*0.20=0.10 -> gate5_wait
    c1 = _cell("w1", "weather-daily", "longshot_fade", ev_net=0.20, win_pct=80.0)
    c2 = _cell("w2", "weather-daily", "longshot_fade", ev_net=0.02, win_pct=52.0)
    result = allocate([c1, c2], bankroll=10000.0)
    statuses = {a["id"]: a["status"] for a in result["allocations"]}
    assert statuses["w2"] == "gate5_wait", f"w2 should be gate5_wait, got {statuses['w2']}"


# ── Cross-archetype allocation tests ─────────────────────────────────────────

def test_weather_and_crypto_form_two_clusters():
    """Weather and crypto cells have zero correlation -> separate clusters."""
    c1 = _cell("w1", "weather-daily", "longshot_fade", ev_net=0.20, win_pct=80.0)
    c2 = _cell("k1", "crypto-daily",  "longshot_fade", ev_net=0.15, win_pct=65.0)
    result = allocate([c1, c2], bankroll=10000.0)
    assert len(result["clusters"]) == 2, f"expected 2 clusters, got {len(result['clusters'])}"


def test_total_deployed_within_total_cap():
    c1 = _cell("w1", "weather-daily", "longshot_fade", ev_net=0.30, win_pct=85.0)
    c2 = _cell("k1", "crypto-daily",  "longshot_fade", ev_net=0.25, win_pct=75.0)
    result = allocate([c1, c2], bankroll=10000.0)
    total_w = sum(a["weight"] for a in result["allocations"])
    assert total_w <= TOTAL_CAP + 1e-9


def test_reserve_equals_bankroll_minus_deployed():
    c1 = _cell("w1", "weather-daily", "longshot_fade", ev_net=0.20, win_pct=80.0)
    c2 = _cell("k1", "crypto-daily",  "longshot_fade", ev_net=0.15, win_pct=65.0)
    result = allocate([c1, c2], bankroll=10000.0)
    assert abs(result["reserve"] - (result["bankroll"] - result["deployed"])) < 0.02


def test_reserve_at_least_one_minus_total_cap():
    c1 = _cell("w1", "weather-daily", "longshot_fade", ev_net=0.20, win_pct=80.0)
    result = allocate([c1], bankroll=10000.0)
    min_reserve = result["bankroll"] * (1.0 - TOTAL_CAP)
    assert result["reserve"] >= min_reserve - 0.02


def test_empty_cells_full_reserve():
    result = allocate([], bankroll=5000.0)
    assert result["deployed"] == 0.0
    assert result["reserve"] == 5000.0
    assert result["allocations"] == []
