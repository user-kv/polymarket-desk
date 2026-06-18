"""
desk/autopsy.py — the Capability (Four C's) implemented as a Reflexion loop.

Reflexion (research round 3): convert the binary WON/LOST signal from a resolved
trade into a verbal "semantic gradient" — a generalized, reusable rule written into
episodic memory so the next run avoids the same mistake. This is the engine of the
self-improvement.

The reasoning step is pluggable (desk/agents/llm.py): MOCK by default (deterministic
heuristic, zero-cost, CI-safe), Claude Opus when DESK_LLM=claude. Every produced
lesson must pass the Write Gate before it is stored.
"""

from __future__ import annotations
import csv
import json
from pathlib import Path

from desk.memory.store import Lesson, append_lesson, _now_iso
from desk.memory.write_gate import WriteGateError
from desk.agents import llm

PAPERTRADER = Path(__file__).resolve().parents[1] / "papertrader"
BETS_CSV = PAPERTRADER / "data" / "bets.csv"

_SYSTEM = (
    "You are the Autopsy analyst for a FAKE-MONEY weather prediction-market paper "
    "trader. Given a resolved bet and its original thesis, find the single most "
    "likely root cause and state ONE generalized, reusable rule. You may never "
    "advocate real money, wallets, ignoring model disagreement, or betting the whole "
    "bankroll. Output strict JSON: {\"root_cause\":..., \"rule\":..., \"tags\":[...]}"
)


def _category_of(bet: dict) -> str:
    return (bet.get("city") or "general").strip().lower().replace(" ", "-")


def _heuristic_reason(bet: dict) -> dict:
    """Deterministic fallback root-cause used by the MOCK backend (and as a guard)."""
    result = (bet.get("result") or "").upper()
    edge = _f(bet.get("edge_pct"))
    gfs, ecmwf = _f(bet.get("gfs_mean_f")), _f(bet.get("ecmwf_mean_f"))
    disagree_f = abs(gfs - ecmwf) if (gfs and ecmwf) else 0.0
    actual = _f(bet.get("actual_high_f"))
    lo, hi = _f(bet.get("bucket_low_f")), _f(bet.get("bucket_high_f"))

    if result == "LOST":
        if disagree_f >= 2.0:
            return {"root_cause": f"Models disagreed by {disagree_f:.1f}F yet the bet "
                    "was placed; the disagreement signalled low forecast skill.",
                    "rule": "When GFS and ECMWF means diverge, shrink stake or skip — "
                            "treat disagreement as a confidence discount, not noise.",
                    "tags": ["model_disagreement", "lost"]}
        if actual and (actual < lo or actual >= hi):
            miss = min(abs(actual - lo), abs(actual - hi))
            return {"root_cause": f"Actual high {actual:.0f}F missed bucket "
                    f"[{lo:.0f},{hi:.0f}] by {miss:.0f}F — ensemble was confident but off.",
                    "rule": "Widen the mean-buffer near steep parts of the day's "
                            "temperature distribution; confident ensembles still miss tails.",
                    "tags": ["forecast_miss", "lost"]}
        return {"root_cause": "Lost despite a clean signal — likely normal variance "
                "or stale pricing before our scan.",
                "rule": "Trigger scans on model-run publish times (00/06/12/18Z) so we "
                        "price fresh runs before the market repriced.",
                "tags": ["variance", "latency", "lost"]}
    if result == "WON":
        return {"root_cause": f"Edge of {edge:.0f}pt converted as expected.",
                "rule": "Edges with model agreement and short lead remain the core "
                        "repeatable source of value; keep sizing disciplined.",
                "tags": ["won", "edge_confirmed"]}
    return {"root_cause": "Bet not yet resolved or voided.",
            "rule": "Only autopsy resolved bets to keep lessons grounded in outcomes.",
            "tags": ["unresolved"]}


def _f(v) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def reason_about(bet: dict) -> dict:
    """Produce {root_cause, rule, tags}. Uses the LLM seam; falls back to heuristic."""
    facts = {k: bet.get(k) for k in ("city", "question", "result", "edge_pct",
             "gfs_mean_f", "ecmwf_mean_f", "actual_high_f", "bucket_low_f",
             "bucket_high_f", "ensemble_prob", "ask_price")}
    user = ("Resolved bet to autopsy:\n```facts\n" + json.dumps(facts, indent=2) +
            "\n```\nReturn the JSON described in the system prompt.")
    try:
        raw = llm.complete(_SYSTEM, user, want_json=True, tier="deep")
        data = json.loads(raw)
        # MOCK backend returns echo-only; detect and use the heuristic instead.
        if data.get("_backend") == "mock" or "rule" not in data:
            return _heuristic_reason(bet)
        if isinstance(data.get("tags"), list):
            data["tags"] = data["tags"]
        return data
    except Exception:
        return _heuristic_reason(bet)


def autopsy_bet(bet: dict) -> dict:
    """Full Reflexion step for one resolved bet -> stored lesson. Returns a summary."""
    reasoning = reason_about(bet)
    lesson = Lesson(
        ts=_now_iso(),
        category=_category_of(bet),
        bet=bet.get("slug", bet.get("bet_id", "unknown")),
        outcome=(bet.get("result") or "UNRESOLVED").upper(),
        thesis=f"edge={bet.get('edge_pct')}pt prob={bet.get('ensemble_prob')} "
               f"ask={bet.get('ask_price')}",
        root_cause=reasoning.get("root_cause", ""),
        rule=reasoning.get("rule", ""),
        tags=",".join(reasoning.get("tags", [])) if isinstance(reasoning.get("tags"), list)
             else str(reasoning.get("tags", "")),
    )
    try:
        path = append_lesson(lesson)
        return {"stored": True, "category": lesson.category, "file": path.name,
                "rule": lesson.rule}
    except WriteGateError as e:
        return {"stored": False, "reason": str(e), "rule": lesson.rule}


def load_settled_bets(limit: int | None = None) -> list[dict]:
    """Read resolved (won/lost) bets from the papertrader ledger."""
    if not BETS_CSV.exists():
        return []
    rows = []
    with BETS_CSV.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if (r.get("result") or "").upper() in ("WON", "LOST"):
                rows.append(r)
    return rows[-limit:] if limit else rows


def run_autopsies(limit: int | None = None) -> dict:
    """Autopsy every resolved bet; returns counts. (Cadence calls this on resolve.)"""
    bets = load_settled_bets(limit)
    stored, blocked = 0, 0
    for b in bets:
        res = autopsy_bet(b)
        stored += 1 if res.get("stored") else 0
        blocked += 0 if res.get("stored") else 1
    return {"resolved_bets": len(bets), "lessons_stored": stored,
            "blocked_by_write_gate": blocked, "backend": llm.backend()}


if __name__ == "__main__":
    print(json.dumps(run_autopsies(), indent=2))
