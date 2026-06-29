"""A4 portfolio/decay.py: Gate 7 decay detector tests."""
from institute.portfolio.decay import detect


def test_flat_profitable_stream_no_decay():
    """Consistent positive pnl throughout -> not decayed."""
    series = [0.10] * 30
    result = detect(series)
    assert result["decayed"] is False


def test_edge_collapse_to_negative_decayed():
    """Early positive stream, then recent collapses to negative -> decay detected."""
    # 20 early wins, then 10 recent losses
    early = [0.20] * 20
    recent = [-0.30] * 10
    series = early + recent
    result = detect(series, recent_frac=0.4, alpha=0.05)
    assert result["decayed"] is True, f"expected decay, got {result}"
    assert result["p_value"] < 0.05


def test_short_stream_insufficient_history():
    """Stream shorter than 2*min_window -> always False, reason 'insufficient history'."""
    series = [0.10] * 10  # 2*8 = 16, so 10 < 16
    result = detect(series, min_window=8)
    assert result["decayed"] is False
    assert result["reason"] == "insufficient history"
    assert result["p_value"] is None


def test_mildly_weaker_recent_no_decay():
    """Recent slightly weaker but still profitable and not material -> not decayed."""
    early = [0.20] * 20
    recent = [0.15] * 10
    series = early + recent
    result = detect(series)
    # recent_ev > 0 and > 0.5*early_ev, so material clause fails -> not decayed
    assert result["decayed"] is False


def test_exactly_at_2x_min_window_boundary():
    """Stream of exactly 2*min_window should be processed (not insufficient)."""
    series = [0.10] * 8 + [-0.50] * 8  # n=16, 2*8=16 -> processes
    result = detect(series, min_window=8)
    # n == 2*min_window -> not insufficient
    assert result["p_value"] is not None, "should compute p_value at exact boundary"


def test_keys_present_in_result():
    series = [0.1] * 30
    result = detect(series)
    for key in ("decayed", "reason", "p_value", "early_ev", "recent_ev", "n"):
        assert key in result, f"missing key: {key}"
