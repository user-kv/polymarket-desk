"""Regression: bets.csv header migration (2026-07-06 verifier BLOCKER).

An old 34-column file must be atomically rewritten with the new header and
metric backfilled to "high" BEFORE any new-schema row is appended — otherwise
a low-temp bet's metric lands in DictReader's restkey and the bet settles
against the daily HIGH."""
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from lib import ledger  # noqa: E402


def _write_old_file(path, n_rows=2):
    old_cols = [c for c in ledger.BETS_COLS if c != "metric"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=old_cols)
        w.writeheader()
        for i in range(n_rows):
            row = {c: "" for c in old_cols}
            row.update({"bet_id": f"old{i}", "stake": "100.0", "status": "settled",
                        "result": "WON", "is_test": "N"})
            w.writerow(row)


def test_migration_backfills_metric(tmp_path, monkeypatch):
    p = str(tmp_path / "bets.csv")
    _write_old_file(p)
    monkeypatch.setattr(ledger, "BETS_PATH", p)
    rows = ledger.load_bets()
    # header rewritten on disk
    with open(p, newline="", encoding="utf-8") as f:
        header = next(csv.reader(f))
    assert header == ledger.BETS_COLS
    assert all(r.get("metric") == "high" for r in rows)
    assert [r["bet_id"] for r in rows] == ["old0", "old1"]


def test_append_after_migration_keeps_metric(tmp_path, monkeypatch):
    p = str(tmp_path / "bets.csv")
    _write_old_file(p)
    monkeypatch.setattr(ledger, "BETS_PATH", p)
    monkeypatch.setattr(ledger, "update_bankroll", lambda *a, **k: None)
    new_bet = {c: "" for c in ledger.BETS_COLS}
    new_bet.update({"bet_id": "new1", "stake": "50.0", "metric": "low",
                    "status": "open", "is_test": "Y"})
    ledger.append_bet(new_bet)
    rows = ledger.load_bets()
    got = {r["bet_id"]: r.get("metric") for r in rows}
    assert got == {"old0": "high", "old1": "high", "new1": "low"}


def test_migration_refuses_unknown_columns(tmp_path, monkeypatch):
    p = str(tmp_path / "bets.csv")
    with open(p, "w", newline="", encoding="utf-8") as f:
        f.write("bet_id,mystery_col\nx,1\n")
    monkeypatch.setattr(ledger, "BETS_PATH", p)
    ledger.load_bets()  # must not crash and must not rewrite
    with open(p, newline="", encoding="utf-8") as f:
        header = next(csv.reader(f))
    assert header == ["bet_id", "mystery_col"]  # untouched
