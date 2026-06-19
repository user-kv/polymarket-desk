"""Integration tests for the orchestrator: idempotent autopsy + safe full cycle."""
import sys
import csv
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from desk import autopsy, run_cycle
from desk.memory import store


def _isolate_memory():
    tmp = Path(tempfile.mkdtemp())
    store.LESSONS_DIR = tmp / "lessons"
    store.LESSONS_DIR.mkdir(parents=True)
    store.INDEX_DB = tmp / "index.sqlite"
    return tmp


def test_autopsy_is_idempotent(monkeypatch=None):
    tmp = _isolate_memory()
    # point autopsy at a temp ledger with 3 resolved bets
    ledger = tmp / "bets.csv"
    cols = ["bet_id", "slug", "city", "result", "edge_pct", "ensemble_prob",
            "ask_price", "gfs_mean_f", "ecmwf_mean_f", "actual_high_f",
            "bucket_low_f", "bucket_high_f", "settled_at", "timestamp"]
    with open(ledger, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        for i in range(3):
            w.writerow({"bet_id": f"b{i}", "slug": f"slug-{i}", "city": "Dallas",
                        "result": "LOST", "edge_pct": "12", "ensemble_prob": "0.4",
                        "ask_price": "0.3", "gfs_mean_f": "95", "ecmwf_mean_f": "91",
                        "actual_high_f": "88", "bucket_low_f": "95", "bucket_high_f": "96",
                        "settled_at": f"2026-06-1{i}T00:00:00Z", "timestamp": ""})
    orig = autopsy.BETS_CSV
    autopsy.BETS_CSV = ledger
    try:
        r1 = autopsy.run_autopsies()
        assert r1["lessons_stored"] == 3
        r2 = autopsy.run_autopsies()
        assert r2["lessons_stored"] == 0          # idempotent
        assert r2["skipped_already_done"] == 3
        assert store.rebuild_index(store.INDEX_DB) == 3
    finally:
        autopsy.BETS_CSV = orig


def test_full_cycle_runs_and_is_safe():
    # the real cycle must run without error and must never enable real money / self-mod
    rep = run_cycle.run_cycle(do_brief=True, use_debate=False)
    assert rep["kernel_intact"] is True
    assert rep["self_mod"]["allowed"] is False    # frozen by default
    assert "autopsy" in rep and "digest" in rep


def _run():
    passed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  PASS {name}")
            passed += 1
    print(f"\n{passed} cycle tests passed.")


if __name__ == "__main__":
    _run()
