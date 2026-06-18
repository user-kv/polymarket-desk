"""
desk/brief.py — the Research Desk's pre-trade reasoning layer.

Produces a Research Brief (recommendation + confidence + rationale) for a market by
combining three inputs:
  1. the deterministic engine's verdict (papertrader/lib/engine.py) — GROUND TRUTH,
  2. relevant past lessons recalled from the Second Brain (recency-weighted),
  3. an LLM judgement (single-agent baseline by default; an optional <=2-round
     Bull/Bear/Risk debate that is only switched on if it BEATS the baseline in
     backtest — research round 2's diminishing-returns finding).

GROUND-TRUTH AUTHORITY (research round 5): the LLM may only CONFIRM or VETO a bet
the engine already approved, or lower its confidence. It can NEVER turn a SKIP into
a BET. The deterministic discipline rules cannot be overridden by reasoning.
"""

from __future__ import annotations
import json
import argparse
from pathlib import Path
from dataclasses import dataclass, asdict

from desk.memory.store import recall
from desk.agents import llm
from desk import risk

DEBATE_ENABLED = False           # default: single-agent baseline (cheaper, see R2)
MAX_DEBATE_ROUNDS = 2            # hard cap — gains saturate by round 2/3 (R2)


@dataclass
class Brief:
    slug: str
    city: str
    question: str
    engine_action: str          # the ground-truth verdict (BET/NEAR_MISS/SKIP)
    recommendation: str         # may only be == engine_action or a downgrade to SKIP
    confidence: float           # 0..1
    rationale: str
    lessons_applied: list
    mode: str                   # 'single' | 'debate'

    def as_dict(self) -> dict:
        return asdict(self)


def _category(market: dict) -> str:
    return (market.get("city") or "general").strip().lower().replace(" ", "-")


def _models_disagree_now(fc: dict) -> float:
    gfs, ecmwf = fc.get("gfs_mean_f"), fc.get("ecmwf_mean_f")
    if gfs is None or ecmwf is None:
        return 0.0
    return abs(float(gfs) - float(ecmwf))


def _baseline_confidence(evaluation: dict, fc: dict, lessons: list) -> tuple[float, str]:
    """
    Deterministic confidence used by the MOCK backend (and as a safety floor under
    the real LLM). Starts from the edge, then applies recalled lessons as discounts —
    this is where past mistakes actually change present behaviour.
    """
    edge = float(evaluation.get("edge_pct", 0.0))
    conf = max(0.0, min(1.0, 0.5 + edge / 40.0))   # 10pt edge -> 0.75
    notes = [f"edge={edge:.1f}pt -> base conf {conf:.2f}"]

    disagree = _models_disagree_now(fc)
    # If we hold a recent lesson about losing on model disagreement and the models
    # disagree now, discount confidence (closing the Reflexion loop).
    has_disagree_lesson = any("model_disagreement" in (l.get("tags") or "")
                              and l.get("outcome") == "LOST" for l in lessons)
    if disagree >= 2.0 and has_disagree_lesson:
        conf *= 0.5
        notes.append(f"models disagree {disagree:.1f}F + prior loss-lesson -> conf x0.5")
    elif disagree >= 2.0:
        conf *= 0.8
        notes.append(f"models disagree {disagree:.1f}F -> conf x0.8")

    has_latency_lesson = any("latency" in (l.get("tags") or "") for l in lessons)
    if has_latency_lesson:
        notes.append("latency lesson on file: prefer fresh model-run scans")
    return round(conf, 3), "; ".join(notes)


def _debate(market, evaluation, fc, lessons) -> tuple[float, str]:
    """Lean Bull/Bear/Risk debate, <=2 rounds (R2). Uses the LLM seam (Opus tier)."""
    facts = {"market": market.get("question"), "edge_pct": evaluation.get("edge_pct"),
             "models_disagree_f": round(_models_disagree_now(fc), 2),
             "lessons": [l.get("rule") for l in lessons[:3]]}
    sys = ("Three analysts (Bull, Bear, Risk) debate a FAKE-MONEY weather bet for at "
           "most two rounds, then output a confidence 0..1. You cannot turn a SKIP "
           "into a BET. Output strict JSON {\"confidence\":float,\"rationale\":str}.")
    user = "```facts\n" + json.dumps(facts, indent=2) + "\n```"
    try:
        raw = llm.complete(sys, user, want_json=True, tier="deep")
        data = json.loads(raw)
        if data.get("_backend") == "mock" or "confidence" not in data:
            c, note = _baseline_confidence(evaluation, fc, lessons)
            return c, "debate(mock->baseline): " + note
        return float(data["confidence"]), data.get("rationale", "debate")
    except Exception:
        c, note = _baseline_confidence(evaluation, fc, lessons)
        return c, "debate(error->baseline): " + note


def build_brief(market: dict, forecast_summary: dict, evaluation: dict,
                debate: bool = DEBATE_ENABLED) -> Brief:
    engine_action = evaluation.get("action", "SKIP")
    lessons = recall(_category(market), limit=5)

    if debate:
        conf, rationale = _debate(market, evaluation, forecast_summary, lessons)
        mode = "debate"
    else:
        conf, rationale = _baseline_confidence(evaluation, forecast_summary, lessons)
        mode = "single"

    # GROUND-TRUTH AUTHORITY: never upgrade. Only confirm or VETO an engine BET.
    recommendation = engine_action
    if engine_action == "BET":
        if conf < 0.5:
            recommendation = "SKIP"
            rationale += " | VETO: confidence below 0.5, engine BET downgraded to SKIP."
        else:
            # Phase 2 risk guards — either can veto a confident bet, neither can create one.
            decline, dmsg = risk.should_decline_category(_category(market))
            liquid, lmsg = risk.passes_liquidity(market)
            if decline:
                recommendation = "SKIP"
                rationale += f" | VETO(risk): {dmsg}"
            elif not liquid:
                recommendation = "SKIP"
                rationale += f" | VETO(liquidity): {lmsg}"

    return Brief(
        slug=market.get("slug", ""), city=market.get("city", ""),
        question=market.get("question", ""), engine_action=engine_action,
        recommendation=recommendation, confidence=conf, rationale=rationale,
        lessons_applied=[{"rule": l.get("rule"), "weight": l.get("_weight")} for l in lessons],
        mode=mode,
    )


def brief_scan(scan_path: Path, debate: bool = DEBATE_ENABLED, only_actionable=True) -> list[dict]:
    data = json.loads(Path(scan_path).read_text(encoding="utf-8"))
    out = []
    for entry in data.get("results", []):
        market = entry.get("market", {})
        ev = entry.get("evaluation", {})
        fc = entry.get("forecast_summary", {})
        if only_actionable and ev.get("action") == "SKIP" and float(ev.get("edge_pct", -99)) < 3:
            continue   # don't waste reasoning on clearly-dead markets
        out.append(build_brief(market, fc, ev, debate).as_dict())
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--scan", required=True, help="path to a data/scans/*.json snapshot")
    ap.add_argument("--debate", action="store_true", help="enable the lean debate layer")
    ap.add_argument("--all", action="store_true", help="include near-dead markets too")
    args = ap.parse_args()
    briefs = brief_scan(Path(args.scan), debate=args.debate, only_actionable=not args.all)
    print(f"backend={llm.backend()} mode={'debate' if args.debate else 'single'} "
          f"briefs={len(briefs)}\n")
    for b in briefs:
        print(f"[{b['recommendation']:9}] conf={b['confidence']:.2f} "
              f"engine={b['engine_action']:9} {b['city']:14} {b['question'][:54]}")
        if b["lessons_applied"]:
            print(f"           lessons: {[l['rule'][:60] for l in b['lessons_applied'][:2]]}")
