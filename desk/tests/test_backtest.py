"""Tests for the walk-forward backtest: ordering, embargo, transaction costs, fitness."""
import sys
import csv
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from desk import backtest_wf as bt
from desk.memory import store
from desk.memory.store import Lesson


def _mk_bets(path, n=12, win_every=2):
    cols = ["city", "result", "ensemble_prob", "pnl", "settled_at", "timestamp"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for i in range(n):
            won = (i % win_every == 0)
            w.writerow({
                "city": "Dallas",
                "result": "WON" if won else "LOST",
                "ensemble_prob": 0.6 if won else 0.55,
                "pnl": 30.0 if won else -5.0,
                "settled_at": f"2026-06-{1+i:02d}T00:00:00Z",
                "timestamp": f"2026-06-{1+i:02d}T00:00:00Z",
            })


def test_ordered_and_walk_forward_runs():
    tmp = Path(tempfile.mkdtemp()) / "bets.csv"
    _mk_bets(tmp, n=12)
    res = bt.walk_forward(n_folds=3, bets_csv=tmp)
    assert res["n_bets"] == 12
    assert res["n_folds"] >= 1
    # pooled OOS fitness present with a finite Brier
    assert res["oos_fitness"]["n_bets"] > 0


def test_embargo_blocks_future_leak():
    bets = [{"settled_at": "2026-06-10T00:00:00Z"},
            {"settled_at": "2026-06-20T00:00:00Z"}]
    # asof BEFORE the second bet -> that bet must be flagged as a leak
    assert bt._embargo_ok(bets, "2026-06-15T00:00:00Z") is False
    assert bt._embargo_ok(bets[:1], "2026-06-15T00:00:00Z") is True


def test_recall_asof_excludes_future_lessons():
    tmpdir = Path(tempfile.mkdtemp())
    od, odb = store.LESSONS_DIR, store.INDEX_DB
    store.LESSONS_DIR, store.INDEX_DB = tmpdir, tmpdir / "i.sqlite"
    try:
        store.append_lesson(Lesson("2026-06-01T00:00:00Z", "dallas", "b1", "LOST",
                                    "t", "rc", "old rule", "x"))
        store.append_lesson(Lesson("2026-06-20T00:00:00Z", "dallas", "b2", "WON",
                                    "t", "rc", "future rule", "x"))
        store.rebuild_index(store.INDEX_DB)
        got = store.recall_asof("dallas", "2026-06-10T00:00:00Z", db_path=store.INDEX_DB)
        rules = [g["rule"] for g in got]
        assert "old rule" in rules
        assert "future rule" not in rules    # embargoed
    finally:
        store.LESSONS_DIR, store.INDEX_DB = od, odb


def test_slippage_reduces_pnl():
    tmp = Path(tempfile.mkdtemp()) / "bets.csv"
    _mk_bets(tmp, n=12)
    base = bt.walk_forward(n_folds=3, slippage_pct=0.0, bets_csv=tmp)
    slipped = bt.walk_forward(n_folds=3, slippage_pct=10.0, bets_csv=tmp)
    assert slipped["oos_fitness"]["pnl"] <= base["oos_fitness"]["pnl"]


def test_insufficient_history_degrades_safely():
    tmp = Path(tempfile.mkdtemp()) / "bets.csv"
    _mk_bets(tmp, n=1)
    res = bt.walk_forward(bets_csv=tmp)
    assert res["folds"] == []
    assert "oos_fitness" in res


def _run():
    passed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  PASS {name}")
            passed += 1
    print(f"\n{passed} backtest tests passed.")


if __name__ == "__main__":
    _run()
