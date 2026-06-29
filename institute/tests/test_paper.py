"""A3 paper executor: open -> settle -> forward_count, on a temp ledger only."""
import os
import tempfile

from institute.corpus.schema import Strategy
from institute.map.baselines import longshot_fade
from institute.execute import paper


def _strat():
    return Strategy(id="s1", archetype="weather-daily", baseline="longshot_fade")


def test_open_settle_count_roundtrip():
    with tempfile.TemporaryDirectory() as d:
        ledger = os.path.join(d, "paper.jsonl")
        snap = {"market_id": "m1", "q_yes": 0.2, "t0": "2026-06-29T00:00:00Z"}
        pos = paper.open_position(_strat(), snap, longshot_fade, ledger_path=ledger)
        assert pos is not None and pos["side"] == "NO" and pos["status"] == "open"
        assert paper.forward_count("s1", ledger_path=ledger) == 0

        settled = paper.settle("m1", y=0, ledger_path=ledger)  # NO wins when y=0
        assert settled["status"] == "settled" and settled["pnl"] > 0
        assert paper.forward_count("s1", ledger_path=ledger) == 1
        assert paper.open_positions(ledger_path=ledger) == []


def test_no_bet_returns_none():
    with tempfile.TemporaryDirectory() as d:
        ledger = os.path.join(d, "paper.jsonl")
        # q_yes above the longshot cap -> longshot_fade places no bet
        snap = {"market_id": "m2", "q_yes": 0.8, "t0": "t"}
        assert paper.open_position(_strat(), snap, longshot_fade, ledger_path=ledger) is None
