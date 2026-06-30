"""Tests for the ``research`` baseline in map/baselines.py (A6).

Verifies all betting logic edge-cases and that it scores correctly through
baselines.evaluate without error on a small resolved set.
"""
from institute.map.baselines import research, evaluate, BASELINES


# ── helpers ───────────────────────────────────────────────────────────────────

def _rm(q_yes, y, p_final=None, p_std=None):
    """Build a minimal ResolvedMarket-like dict."""
    meta = {}
    if p_final is not None:
        meta["p_final"] = p_final
    if p_std is not None:
        meta["p_std"] = p_std
    return {"q_yes": q_yes, "y": y, "meta": meta}


# ── research baseline unit tests ──────────────────────────────────────────────

def test_research_yes_bet_when_p_above_q():
    """p_final - q > edge -> YES."""
    rm = _rm(q_yes=0.4, y=1, p_final=0.50, p_std=0.05)
    p, side = research(rm)
    assert side == "YES"
    assert abs(p - 0.50) < 1e-9


def test_research_no_bet_when_q_above_p():
    """q - p_final > edge -> NO."""
    rm = _rm(q_yes=0.6, y=0, p_final=0.50, p_std=0.05)
    p, side = research(rm)
    assert side == "NO"
    assert abs(p - 0.50) < 1e-9


def test_research_abstain_within_edge():
    """|p - q| <= edge -> None (no bet)."""
    rm = _rm(q_yes=0.5, y=1, p_final=0.53, p_std=0.05)  # diff = 0.03 < 0.05
    p, side = research(rm)
    assert side is None


def test_research_abstain_high_std():
    """p_std > std_ceiling -> None (swarm too divided)."""
    rm = _rm(q_yes=0.4, y=1, p_final=0.55, p_std=0.25)  # std above 0.20 default
    p, side = research(rm)
    assert side is None
    assert abs(p - 0.55) < 1e-9  # returns p_final even when abstaining


def test_research_abstain_no_p_final():
    """Missing p_final -> abstain, returns q_yes."""
    rm = _rm(q_yes=0.4, y=1)
    p, side = research(rm)
    assert side is None
    assert abs(p - 0.4) < 1e-9


def test_research_abstain_no_meta():
    """Missing meta dict entirely -> abstain."""
    rm = {"q_yes": 0.4, "y": 1}
    p, side = research(rm)
    assert side is None


def test_research_edge_exactly_at_threshold():
    """p - q == edge exactly -> does NOT trigger (must be strictly greater)."""
    rm = _rm(q_yes=0.45, y=1, p_final=0.50, p_std=0.05)  # diff = 0.05 exactly
    p, side = research(rm)
    # 0.05 > 0.05 is False, so no bet
    assert side is None


def test_research_custom_edge():
    """Custom edge parameter respected."""
    rm = _rm(q_yes=0.4, y=1, p_final=0.43, p_std=0.05)  # diff = 0.03
    p, side = research(rm, edge=0.02)
    assert side == "YES"


def test_research_custom_std_ceiling():
    """Custom std_ceiling parameter respected."""
    rm = _rm(q_yes=0.4, y=1, p_final=0.55, p_std=0.18)  # p_std=0.18 < 0.20 default
    p, side = research(rm, std_ceiling=0.15)  # but above custom ceiling of 0.15
    assert side is None


# ── integration: evaluate through baselines.evaluate ─────────────────────────

def test_research_evaluate_no_error():
    """research scores through baselines.evaluate on a small resolved set."""
    rows = [
        _rm(q_yes=0.4, y=1, p_final=0.52, p_std=0.05),  # YES bet, win
        _rm(q_yes=0.6, y=0, p_final=0.50, p_std=0.05),  # NO bet, win
        _rm(q_yes=0.5, y=1, p_final=0.52, p_std=0.05),  # within edge, abstain
        _rm(q_yes=0.4, y=0),                              # no forecast, abstain
    ]
    fn, kw, _ = BASELINES["research"]
    metrics = evaluate(rows, fn, **kw)

    assert "n" in metrics
    assert "win_pct" in metrics
    assert "mean_S" in metrics
    assert "ev_net" in metrics
    assert metrics["n"] == 2  # two bets placed


def test_research_in_baselines_registry():
    """research is registered in BASELINES with use_realized=True."""
    assert "research" in BASELINES
    fn, kw, use_realized = BASELINES["research"]
    assert callable(fn)
    assert use_realized is True


def test_research_evaluate_all_abstain():
    """All-abstain set -> n=0, no error."""
    rows = [_rm(q_yes=0.5, y=1)]  # no p_final -> abstain
    fn, kw, _ = BASELINES["research"]
    metrics = evaluate(rows, fn, **kw)
    assert metrics["n"] == 0
