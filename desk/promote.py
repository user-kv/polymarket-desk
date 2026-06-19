"""
desk/promote.py — benchmark-gated, evolutionary promotion (research round 3 / DGM).

A self-written tool is promoted to the live loop ONLY if it survives this pipeline:

  overseer.gate -> static analysis -> sandbox execution -> walk-forward fitness must
  BEAT the champion (kernel.challenger_beats_champion) -> git commit + archive.

Like the Darwin Gödel Machine: every variant (promoted or rejected) is kept in an
archive, and selection is empirical — a change is kept only if it is *measurably*
better out-of-sample. PnL alone can never promote (the kernel forbids it), so the
loop cannot reward-hack its way in.
"""

from __future__ import annotations
import shutil
import subprocess
from pathlib import Path
from datetime import datetime, timezone

from desk import overseer, sandbox
from desk.kernel import fitness as fit

DESK = Path(__file__).resolve().parent
TOOLS = DESK / "tools"
LIVE = TOOLS / "live"
ARCHIVE = TOOLS / "archive"


def _ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _archive(name: str, source: str, verdict: str, reason: str) -> Path:
    sub = ARCHIVE / ("promoted" if verdict == "promoted" else "rejected")
    sub.mkdir(parents=True, exist_ok=True)
    path = sub / f"{_ts()}__{name}.py"
    path.write_text(f"# verdict: {verdict}\n# reason: {reason}\n\n{source}", encoding="utf-8")
    return path


def _git_commit(paths: list[Path], message: str) -> None:
    """One isolated commit per promotion (guardrail #2: instant revert)."""
    try:
        subprocess.run(["git", "add", *[str(p) for p in paths]], cwd=str(DESK.parent),
                       check=True, capture_output=True)
        subprocess.run(["git", "commit", "-q", "-m", message], cwd=str(DESK.parent),
                       check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        # never let a git hiccup crash the loop; the archive is the backup record
        print(f"[promote] git commit skipped: {e}")


def evaluate_and_promote(name: str, source: str, entry: str,
                         champion: fit.FitnessReport, challenger: fit.FitnessReport,
                         args_json: str = "{}") -> dict:
    """
    Full gate for one proposed tool. champion/challenger are FitnessReports from the
    walk-forward backtest (with and without the tool). Returns a verdict dict.
    """
    # 1. overseer pre-flight (kernel intact, kill switch, readiness, pathology)
    allowed, why = overseer.gate(proposal_text=source)
    if not allowed:
        _archive(name, source, "rejected", why)
        return {"promoted": False, "stage": "overseer", "reason": why}

    # 2. static analysis
    ok, sreason = sandbox.static_analyze(source)
    if not ok:
        _archive(name, source, "rejected", f"static: {sreason}")
        return {"promoted": False, "stage": "static", "reason": sreason}

    # 3. sandboxed execution must succeed
    run = sandbox.run_tool(source, entry=entry, args_json=args_json,
                           timeout=overseer.load_config().get("max_tool_runtime_seconds", 20))
    if not run.get("ok"):
        _archive(name, source, "rejected", f"sandbox: {run.get('reason') or run.get('stderr')}")
        return {"promoted": False, "stage": "sandbox", "reason": run}

    # 4. benchmark-gated: challenger must beat champion on a proper score, OOS
    better, breason = fit.challenger_beats_champion(champion, challenger)
    if not better:
        _archive(name, source, "rejected", f"fitness: {breason}")
        return {"promoted": False, "stage": "fitness", "reason": breason}

    # 5. promote: write live, archive, commit, record
    LIVE.mkdir(parents=True, exist_ok=True)
    live_path = LIVE / f"{name}.py"
    live_path.write_text(source, encoding="utf-8")
    arc = _archive(name, source, "promoted", breason)
    overseer.record_promotion(name, breason)
    _git_commit([live_path, arc, overseer.PROMOTIONS_LOG],
                f"self-mod: promote tool '{name}' ({breason})\n\n"
                f"Auto-promoted by desk/promote.py after passing overseer + static + "
                f"sandbox + walk-forward fitness gate. Revert with: git revert HEAD")
    return {"promoted": True, "stage": "live", "reason": breason,
            "live": str(live_path.name), "archive": str(arc.name)}


if __name__ == "__main__":
    # demo: a clean tool that genuinely improves CRPS gets promoted
    src = "def run():\n    import math\n    return math.sqrt(49)\n"
    champ = fit.FitnessReport(crps=2.0, brier=0.2, reliability=0.05, resolution=0.1,
                              pnl=0.0, n_forecasts=40, n_bets=20)
    chall = fit.FitnessReport(crps=1.6, brier=0.2, reliability=0.04, resolution=0.11,
                              pnl=0.0, n_forecasts=40, n_bets=20)
    import json
    print(json.dumps(evaluate_and_promote("demo_tool", src, "run", champ, chall), indent=2))
