"""A4 portfolio/gate4.py: Gate 4 capital-activation ladder tests."""
import os
import tempfile

from institute.corpus.schema import Strategy
from institute.map.baselines import longshot_fade
from institute.execute import paper
from institute.portfolio import gate4


def _strat(sid="s_test"):
    return Strategy(id=sid, archetype="weather-daily", baseline="longshot_fade")


def test_empty_ledger_is_accumulating():
    with tempfile.TemporaryDirectory() as d:
        ledger = os.path.join(d, "paper.jsonl")
        result = gate4.gate4_status("nonexistent_strategy", ledger_path=ledger)
        assert result["verdict"] == "accumulating"
        assert result["n"] == 0
        assert result["reason"] == "no settled forward outcomes"


def test_sprt_strong_win_streak_graduates():
    """A strong win streak should trigger SPRT accept_H1 and graduate."""
    with tempfile.TemporaryDirectory() as d:
        ledger = os.path.join(d, "paper.jsonl")
        strat = _strat("s_win")
        # Open and settle 25 markets -- all NO bets with q_yes=0.1 (strong wins)
        for i in range(25):
            snap = {"market_id": f"m_win_{i}", "q_yes": 0.1, "t0": f"2026-01-{i+1:02d}T00:00:00Z"}
            pos = paper.open_position(strat, snap, longshot_fade, ledger_path=ledger)
            assert pos is not None, f"expected bet on market {i}"
            paper.settle(f"m_win_{i}", y=0, ledger_path=ledger)  # NO wins when y=0

        result = gate4.gate4_status("s_win", ledger_path=ledger)
        assert result["sprt"] == "accept_H1", f"expected accept_H1, got {result['sprt']}"
        assert result["ev"] > 0
        assert result["verdict"] == "graduated", f"expected graduated, got {result}"


def test_losing_streak_past_n_floor_rejected():
    """A losing streak past N_FLOOR (monkeypatched small) -> rejected."""
    with tempfile.TemporaryDirectory() as d:
        ledger = os.path.join(d, "paper.jsonl")
        strat = _strat("s_lose")

        original_n_floor = gate4.N_FLOOR
        try:
            gate4.N_FLOOR = 6

            # Settle 7 losing NO bets (y=1 means YES resolved -> NO loses)
            for i in range(7):
                snap = {"market_id": f"m_lose_{i}", "q_yes": 0.1, "t0": f"2026-01-{i+1:02d}T00:00:00Z"}
                paper.open_position(strat, snap, longshot_fade, ledger_path=ledger)
                paper.settle(f"m_lose_{i}", y=1, ledger_path=ledger)  # NO loses

            result = gate4.gate4_status("s_lose", ledger_path=ledger)
            assert result["verdict"] == "rejected", f"expected rejected, got {result}"
        finally:
            gate4.N_FLOOR = original_n_floor


def test_accumulating_insufficient_data():
    """A few bets not enough to trigger SPRT either way -> accumulating."""
    with tempfile.TemporaryDirectory() as d:
        ledger = os.path.join(d, "paper.jsonl")
        strat = _strat("s_acc")

        # 3 wins -- not enough to trigger SPRT at default N_FLOOR=50
        for i in range(3):
            snap = {"market_id": f"m_acc_{i}", "q_yes": 0.1, "t0": f"2026-01-{i+1:02d}T00:00:00Z"}
            paper.open_position(strat, snap, longshot_fade, ledger_path=ledger)
            paper.settle(f"m_acc_{i}", y=0, ledger_path=ledger)

        result = gate4.gate4_status("s_acc", ledger_path=ledger)
        assert result["verdict"] == "accumulating"
        assert result["n"] == 3
