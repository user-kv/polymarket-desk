"""
settle_all per-bet write isolation (regression).

A malformed bet row or a single failed ledger write must NOT abort settlement
of the remaining open bets in the same cycle. Before the fix, an exception in
settle_bet/update_bet propagated out of the loop and starved every later bet.

Run:  PYTHONPATH=papertrader python -m pytest papertrader/tests/test_settle_isolation.py -q
"""
import lib.settlement as settlement
import lib.ledger as ledger


CITY = {"name": "Dallas", "lat": 32.8471, "lon": -96.8518, "station": "KDAL", "tz": "America/Chicago"}


def test_one_bad_bet_does_not_block_others(monkeypatch):
    bets = [
        {"bet_id": "BAD", "city": "Dallas"},
        {"bet_id": "GOOD", "city": "Dallas"},
    ]
    monkeypatch.setattr(ledger, "get_open_bets", lambda: bets)
    monkeypatch.setattr(ledger, "update_bankroll", lambda *a, **k: None)

    updated = []
    monkeypatch.setattr(ledger, "update_bet", lambda bid, res: updated.append(bid))

    def fake_settle(bet, city_cfg, cfg):
        if bet["bet_id"] == "BAD":
            raise ValueError("malformed bucket bounds")
        return {
            "status": "settled", "result": "WON", "actual_high_f": 95.0,
            "pnl": 78.0, "bankroll_delta": 98.0,
            "settlement_source": "nws", "cross_check_diff_f": None,
        }

    monkeypatch.setattr(settlement, "settle_bet", fake_settle)

    settled = settlement.settle_all({}, {"Dallas": CITY})

    ids = [s["bet_id"] for s in settled]
    assert "GOOD" in ids, "the healthy bet must still settle despite the bad one"
    assert "BAD" not in ids
    assert updated == ["GOOD"]
