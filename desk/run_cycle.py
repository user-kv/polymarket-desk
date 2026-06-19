"""
desk/run_cycle.py — the orchestrator (Cadence). The single entry point the scheduler
(systemd timer / Prefect / cron) calls. It ties the Four C's together for one cycle:

  1. Context   — verify the kernel, read the router's authority chain.
  2. Capability— autopsy every newly-resolved bet (Reflexion -> lessons).
  3. Connections—reconcile the markdown lessons into the SQLite index.
  4. Reason    — produce briefs for the latest scan snapshot (ground-truth-bounded).
  5. Self-mod  — run the overseer gate (frozen by default; no-op unless you enable it).
  6. Digest    — write the daily change digest for after-the-fact review.

Every step is safe to run repeatedly and degrades gracefully if data is missing, so
it is cron-safe. It never places a real order — fake money only.
"""

from __future__ import annotations
import json
import argparse
from pathlib import Path

from desk.kernel import invariants as inv
from desk import autopsy, brief, overseer, digest
from desk.memory import store, knowledge
from desk.agents import llm

DESK = Path(__file__).resolve().parent
SCANS = DESK.parent / "papertrader" / "data" / "scans"


def _latest_scan() -> Path | None:
    scans = sorted(SCANS.glob("scan_*.json"))
    return scans[-1] if scans else None


def run_cycle(do_brief: bool = True, use_debate: bool = False) -> dict:
    report = {"backend": llm.backend()}

    # 1. Context: kernel must be intact before anything reasons.
    inv.assert_fake_money_only()
    ok, kmsg = inv.verify_kernel_integrity()
    report["kernel_intact"] = ok
    report["kernel_msg"] = kmsg

    # 2. Capability: autopsy resolved bets -> lessons (Reflexion).
    report["autopsy"] = autopsy.run_autopsies()

    # 3. Connections: reconcile markdown -> index (bounds drift).
    report["lessons_indexed"] = store.rebuild_index()

    # 3b. Reflection: distil episodic lessons -> semantic principles (Second Brain
    #     upper tier). Idempotent; converges instead of growing without bound.
    report["consolidate"] = knowledge.consolidate()

    # 4. Reason: briefs on the latest scan (advisory; engine stays authority).
    if do_brief:
        scan = _latest_scan()
        if scan:
            briefs = brief.brief_scan(scan, debate=use_debate, only_actionable=True)
            actionable = [b for b in briefs if b["recommendation"] == "BET"]
            report["brief"] = {"scan": scan.name, "n_briefs": len(briefs),
                               "n_recommend_bet": len(actionable)}
        else:
            report["brief"] = {"scan": None, "note": "no scan snapshots yet"}

    # 5. Self-mod: overseer gate. Frozen by default -> reports the block reason.
    allowed, why = overseer.gate()
    report["self_mod"] = {"allowed": allowed, "reason": why}
    # (When you enable it, the propose->promote step plugs in here, behind `allowed`.)

    # 6. Digest: legibility for after-the-fact review.
    d = digest.build_digest()
    (DESK / "digest_latest.md").write_text(digest.render(d), encoding="utf-8")
    report["digest"] = {"lessons_added": d["lessons_added"],
                        "tools_promoted": len(d["tools_promoted"])}
    return report


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Run one reflective desk cycle (fake money only).")
    ap.add_argument("--debate", action="store_true", help="use the lean debate layer for briefs")
    ap.add_argument("--no-brief", action="store_true", help="skip the brief step")
    args = ap.parse_args()
    rep = run_cycle(do_brief=not args.no_brief, use_debate=args.debate)
    print(json.dumps(rep, indent=2))
