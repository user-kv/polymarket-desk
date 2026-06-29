"""Cell-lifecycle orchestrator: PROPOSED -> Gate1 -> Gate2 -> Gate3 -> paper-forward.

Runs a candidate cell through the first three gates and reports the furthest
gate it reached. Only a cell that PASSES Gate 1 (not merely 'insufficient') and
survives Gates 2-3 is enqueued for paper-forward (Gate 4 territory, A4). The
optimiser is adversarial, so we never promote on thin evidence.
"""
import uuid
import datetime

from institute.corpus.schema import Strategy
from institute.map import baselines as B
from institute.map import predictability
from institute.resolve import weather_adapter
from institute.strategy import generate
from institute.evidence import gate1
from institute.gates import mechanism, redteam


def _utcnow_iso():
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def run_cell(archetype, baseline_name, rows=None, use_llm=False, log=True) -> dict:
    """Walk one (archetype x baseline) cell through Gates 1-3.

    Gate 1 'insufficient' still runs Gates 2-3 as diagnostics, but the cell
    cannot reach 'paper' until Gate 1 actually passes.
    """
    if rows is None:
        rows = weather_adapter.load_rows()
    arch_rows = [rm for rm in rows if rm.get("archetype") == archetype]

    mech, hyp = generate.BASELINE_MECHANISM.get(baseline_name, ("", ""))
    strat = Strategy(
        id=uuid.uuid4().hex[:12], archetype=archetype, baseline=baseline_name,
        params={}, mechanism=mech, hypothesis=hyp, status="proposed", ts=_utcnow_iso(),
    )

    out = {"strategy": strat, "gate1": None, "gate2": None, "gate3": None,
           "gate1_ok": False, "status": "proposed"}

    g1 = gate1.run_gate(archetype, baseline_name, rows=rows, log=log)
    out["gate1"] = g1
    g1_ok = g1["verdict"] == "pass"
    out["gate1_ok"] = g1_ok
    if g1["verdict"] == "fail":
        out["status"] = strat.status = "rejected_gate1"
        return out

    fn, kw = generate.resolve_baseline(baseline_name)

    g2 = mechanism.check(strat, arch_rows, fn, use_llm=use_llm, **kw)
    out["gate2"] = g2
    if not g2["passed"]:
        out["status"] = strat.status = "held_gate2"
        return out

    g3 = redteam.run(strat, arch_rows, fn, use_llm=use_llm, **kw)
    out["gate3"] = g3
    if not g3["survived"]:
        out["status"] = strat.status = "rejected_gate3"
        return out

    # Gates 2-3 cleared. Promotion to paper requires Gate 1 to have PASSED.
    out["status"] = strat.status = "paper" if g1_ok else "gate1_insufficient"
    return out


def run_all(rows=None, use_llm=False, log=True) -> list:
    """Run every non-null, gate1-resolvable cell from the current map."""
    if rows is None:
        rows = weather_adapter.load_rows()
    cells = predictability.build(rows)
    results = []
    for c in cells:
        if c.baseline == "price_follow":
            continue  # the null carries no edge claim
        if c.baseline not in B.BASELINES:
            continue  # gate1 can only score registered weather baselines for now
        results.append(run_cell(c.archetype, c.baseline, rows=rows, use_llm=use_llm, log=log))
    return results


def render(results) -> str:
    """ASCII table of each cell's gate progress (Windows cp1252 safe)."""
    lines = ["=" * 72,
             f"  {'archetype':<16}{'baseline':<16}{'g1':<13}{'g2':<5}{'g3':<5}{'status'}",
             "-" * 72]
    if not results:
        lines.append("  (no cells to run)")
    for r in results:
        s = r["strategy"]
        g1 = r["gate1"]["verdict"] if r["gate1"] else "-"
        g2 = ("P" if r["gate2"]["passed"] else "F") if r["gate2"] else "-"
        g3 = ("S" if r["gate3"]["survived"] else "X") if r["gate3"] else "-"
        lines.append(f"  {s.archetype:<16}{s.baseline:<16}{g1:<13}{g2:<5}{g3:<5}{r['status']}")
    lines.append("=" * 72)
    return "\n".join(lines)
