#!/usr/bin/env python3
"""
desk/export_state.py — write desk/dashboard_state.json, the single snapshot the
standalone Chrome dashboard (desk/dashboard.html) reads.

Stdlib only. FAKE MONEY ONLY: this only *reads* the ledger/memory the desk commits
and writes one JSON file; it never places a bet or touches a wallet.

Why a committed snapshot? The Chrome dashboard runs in the browser and reads the
repo over the GitHub API. The Second Brain's principles live in the gitignored,
rebuildable knowledge.sqlite, and the bets/scans need parsing — so instead of making
the browser do all that, this script flattens everything into one small JSON the page
fetches in a single request.

Run by both GitHub Actions workflows before the commit step, and runnable locally:
    python -m desk.export_state
"""
from __future__ import annotations

import csv
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # repo root
PT = ROOT / "papertrader" / "data"
DESK = ROOT / "desk"
OUT = DESK / "dashboard_state.json"


# --------------------------------------------------------------------------- #
# data readers (defensive: a missing/locked file never crashes the export)     #
# --------------------------------------------------------------------------- #
def _read_json(p: Path, default):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def bankroll_state():
    b = _read_json(PT / "bankroll.json", {})
    bal = b.get("balance")
    start = b.get("start")
    hist = b.get("history", []) or []
    pnl = (bal - start) if (bal is not None and start is not None) else None
    pnl_pct = (pnl / start * 100.0) if (pnl is not None and start) else None
    # curve = flat list of balances (kept for back-compat); curve_points = the same
    # series enriched with date + note so the dashboard can show a tooltip on hover.
    curve, points = [], []
    if start is not None:
        curve.append(float(start))
        points.append({"b": float(start), "ts": (hist[0].get("ts") if hist else None),
                       "note": "starting balance"})
    for h in hist:
        if h.get("balance") is not None:
            curve.append(float(h["balance"]))
            points.append({"b": float(h["balance"]), "ts": h.get("ts"),
                           "note": h.get("note", "")})
    return {
        "balance": bal, "start": start, "pnl": pnl, "pnl_pct": pnl_pct,
        "curve": curve, "curve_points": points, "history": hist[-12:][::-1],
    }


def bets_state():
    p = PT / "bets.csv"
    rows = []
    try:
        with p.open(encoding="utf-8", newline="") as fh:
            rows = list(csv.DictReader(fh))
    except Exception:
        rows = []

    def num(r, k):
        try:
            return float(r.get(k, "") or 0)
        except Exception:
            return 0.0

    settled = [r for r in rows if (r.get("status") == "settled")]
    open_ = [r for r in rows if (r.get("status") != "settled")]
    wins = [r for r in settled if (r.get("result") == "WON")]
    losses = [r for r in settled if (r.get("result") == "LOST")]
    total_pnl = sum(num(r, "pnl") for r in settled)
    win_rate = (len(wins) / len(settled) * 100.0) if settled else None

    cities = {}
    for r in settled:
        c = r.get("city") or "?"
        d = cities.setdefault(c, {"settled": 0, "won": 0, "pnl": 0.0})
        d["settled"] += 1
        d["won"] += 1 if r.get("result") == "WON" else 0
        d["pnl"] += num(r, "pnl")
    for c, d in cities.items():
        d["win_rate"] = (d["won"] / d["settled"] * 100.0) if d["settled"] else None

    def slim(r):
        return {
            "city": r.get("city"), "question": r.get("question"),
            "stake": num(r, "stake"), "ask_price": r.get("ask_price"),
            "edge_pct": r.get("edge_pct"), "status": r.get("status"),
            "result": r.get("result"), "pnl": num(r, "pnl"),
            "timestamp": r.get("timestamp"), "is_test": r.get("is_test"),
        }

    return {
        "total": len(rows), "open": len(open_), "settled": len(settled),
        "wins": len(wins), "losses": len(losses), "win_rate": win_rate,
        "total_pnl": total_pnl, "cities": cities,
        "recent": [slim(r) for r in rows][::-1][:15],
        "open_bets": [slim(r) for r in open_][::-1],
    }


def scans_state():
    d = PT / "scans"
    files = sorted(d.glob("scan_*.json")) if d.exists() else []
    summaries = []
    for f in files[-30:]:
        j = _read_json(f, {})
        summaries.append({
            "file": f.name,
            "ts": j.get("scan_timestamp"),
            "found": j.get("markets_found"),
            "priced": j.get("markets_priced"),
            "placed": j.get("bets_placed"),
            "near_misses": j.get("near_misses"),
            "test_mode": j.get("test_mode"),
        })
    return {
        "count": len(files),
        "latest": summaries[-1] if summaries else None,
        "recent": summaries[::-1][:15],
    }


def _sqlite_rows(db: Path, query: str):
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        con.row_factory = sqlite3.Row
        try:
            return [dict(r) for r in con.execute(query)]
        finally:
            con.close()
    except Exception:
        return []


def brain_state():
    """Read lessons + principles. Caller refreshes the indexes first (see main())."""
    lessons = _sqlite_rows(
        DESK / "memory" / "index.sqlite",
        "select ts,category,outcome,root_cause,rule from lessons order by id desc limit 20",
    )
    principles = _sqlite_rows(
        DESK / "memory" / "knowledge.sqlite",
        "select ts,category,topic,claim,confidence,evidence_count from principles "
        "order by confidence desc, id desc limit 20",
    )
    return {"lessons": lessons, "principles": principles}


def digest_state():
    p = DESK / "digest_latest.md"
    try:
        return {"text": p.read_text(encoding="utf-8")}
    except Exception:
        return {"text": "(no digest yet — runs after the first reflective cycle)"}


def _refresh_indexes():
    """Rebuild the sqlite indexes from the committed lessons markdown so the export is
    correct in any job — including the scan job, where the gitignored sqlite files
    don't exist on a fresh checkout. Mirrors run_cycle.py steps 3 and 3b. Best-effort."""
    try:
        from desk.memory import store, knowledge
        store.rebuild_index()
        knowledge.consolidate()
    except Exception:
        pass  # missing deps / no lessons yet -> brain_state just reads what's there


def build_state():
    _refresh_indexes()
    return {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "bankroll": bankroll_state(),
        "bets": bets_state(),
        "scans": scans_state(),
        "brain": brain_state(),
        "digest": digest_state(),
    }


def main():
    state = build_state()
    OUT.write_text(json.dumps(state, indent=2), encoding="utf-8")
    b, t = state["bankroll"], state["bets"]
    print(f"wrote {OUT.relative_to(ROOT)} "
          f"(balance={b['balance']} pnl={b['pnl']} bets={t['total']} "
          f"lessons={len(state['brain']['lessons'])} "
          f"principles={len(state['brain']['principles'])})")


if __name__ == "__main__":
    main()
