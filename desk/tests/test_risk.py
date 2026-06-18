"""Tests for the Phase 2 risk guards: category decline + liquidity, and brief wiring."""
import sys
import csv
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from desk import risk, brief


def _write_bets(path, rows):
    cols = ["city", "result", "settled_at", "timestamp"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def test_decline_losing_category():
    tmp = Path(tempfile.mkdtemp()) / "bets.csv"
    rows = [{"city": "Dallas", "result": "LOST",
             "settled_at": "2026-06-18T00:00:00Z", "timestamp": ""} for _ in range(10)]
    _write_bets(tmp, rows)
    decline, msg = risk.should_decline_category("dallas", bets_csv=tmp)
    assert decline is True


def test_winning_category_not_declined():
    tmp = Path(tempfile.mkdtemp()) / "bets.csv"
    rows = [{"city": "Miami", "result": "WON",
             "settled_at": "2026-06-18T00:00:00Z", "timestamp": ""} for _ in range(10)]
    _write_bets(tmp, rows)
    decline, msg = risk.should_decline_category("miami", bets_csv=tmp)
    assert decline is False


def test_insufficient_history_not_declined():
    tmp = Path(tempfile.mkdtemp()) / "bets.csv"
    rows = [{"city": "Austin", "result": "LOST",
             "settled_at": "2026-06-18T00:00:00Z", "timestamp": ""} for _ in range(3)]
    _write_bets(tmp, rows)
    decline, _ = risk.should_decline_category("austin", bets_csv=tmp)
    assert decline is False   # only 3 samples < MIN_SAMPLES_TO_JUDGE


def test_liquidity_veto():
    ok, _ = risk.passes_liquidity({"volume_num": 100.0})
    assert ok is False
    ok, _ = risk.passes_liquidity({"volume_num": 50_000.0})
    assert ok is True
    ok, msg = risk.passes_liquidity({})       # unknown -> graceful pass
    assert ok is True


def test_brief_liquidity_veto_cannot_create_bet():
    # illiquid market + engine BET + high edge -> brief must VETO to SKIP
    m = {"slug": "s", "city": "nowhere", "question": "q?", "volume_num": 10.0}
    ev = {"action": "BET", "edge_pct": 25.0}
    fc = {"gfs_mean_f": 90.0, "ecmwf_mean_f": 90.0}
    b = brief.build_brief(m, fc, ev, debate=False)
    assert b.recommendation == "SKIP"
    assert "liquidity" in b.rationale.lower()


def _run():
    passed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  PASS {name}")
            passed += 1
    print(f"\n{passed} risk tests passed.")


if __name__ == "__main__":
    _run()
