"""Gate 1: four independent attempts to DISPROVE a cell's edge (CONSTITUTION §6).

A cell only earns the 'pass' verdict when it survives all applicable tests.
The optimiser is assumed adversarial, so DSR deflates against the full trial
registry and permutation tests the null hard.
"""
import os
import uuid
import datetime

from institute.resolve import weather_adapter
from institute.map.baselines import BASELINES
from institute.corpus.schema import Trial
from institute.corpus import registry

from institute.evidence.backtest import returns_series, win_loss_stream
from institute.evidence.stats import (
    deflated_sharpe, permutation_pvalue, pbo_cscv, sprt
)

# Registry path mirrors cli.MAP_OUT convention — data/ is gitignored.
REGISTRY = os.path.join(os.path.dirname(__file__), "..", "data", "trials.jsonl")
REGISTRY = os.path.normpath(REGISTRY)


def _utcnow_iso():
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _mean_price(rows, baseline_fn):
    """Mean executable price for the cell — used as SPRT p0 (break-even)."""
    prices = []
    for rm in rows:
        _, side = baseline_fn(rm)
        if side is None:
            continue
        if side == "NO":
            prices.append(1.0 - rm["q_yes"])
        else:
            prices.append(rm["q_yes"])
    return sum(prices) / len(prices) if prices else 0.5


def run_gate(archetype, baseline_name, rows=None, log=True):
    """Run all four Gate-1 tests and return a unified result dict.

    rows: inject synthetic rows for tests; None -> load from weather_adapter.
    log:  write Trial to REGISTRY when True (set False in unit tests).
    """
    if rows is None:
        rows = weather_adapter.load_rows()

    # filter to requested archetype
    rows = [rm for rm in rows if rm.get("archetype") == archetype]

    # resolve baseline function
    if baseline_name not in BASELINES:
        raise ValueError(f"unknown baseline '{baseline_name}'; know {list(BASELINES)}")
    baseline_fn, kw, _use_realized = BASELINES[baseline_name]

    rets = returns_series(rows, baseline_fn, **kw)
    wl = win_loss_stream(rows, baseline_fn, **kw)

    # trial count before this run — used to deflate DSR
    n_prev = registry.trial_count(REGISTRY)
    n_trials = max(2, n_prev + 1)  # this run counts as one more

    dsr = deflated_sharpe(rets, n_trials)
    perm = permutation_pvalue(rows, baseline_fn, B=2000, seed=42, **kw)
    pbo = pbo_cscv([rets])  # single config -> N/A; multi-config arrives in A3

    # SPRT: p0 = mean executable price (break-even); p1 = p0 + 0.10 (target edge)
    p0 = _mean_price(rows, baseline_fn)
    p1 = min(0.98, p0 + 0.10)
    sp = sprt(wl, p0=p0, p1=p1)

    # Verdict logic per spec
    if dsr["passed"] and perm["passed"] and sp["decision"] == "accept_H1":
        verdict = "pass"
    elif sp["decision"] == "continue":
        verdict = "insufficient"
    else:
        verdict = "fail"

    result = {
        "archetype": archetype,
        "baseline": baseline_name,
        "n_bets": len(rets),
        "verdict": verdict,
        "dsr": dsr,
        "perm": perm,
        "pbo": pbo,
        "sprt": sp,
    }

    if log:
        trial = Trial(
            id=str(uuid.uuid4()),
            archetype=archetype,
            strategy_id=baseline_name,
            metrics={
                "dsr": dsr,
                "perm": perm,
                "pbo": pbo,
                "sprt": sp,
                "n_bets": len(rets),
            },
            verdict=verdict,
            ts=_utcnow_iso(),
        )
        registry.log_trial(REGISTRY, trial)

    return result


def render(result):
    """One-screen ASCII summary table (no unicode — Windows cp1252 safe)."""
    lines = []
    lines.append("=" * 60)
    lines.append(f"  Gate 1 | archetype: {result['archetype']}  baseline: {result['baseline']}")
    lines.append(f"  n_bets : {result['n_bets']}")
    lines.append("=" * 60)

    dsr = result["dsr"]
    lines.append(f"  [DSR]  sr={dsr.get('sr')}  sr0={dsr.get('sr0')}  "
                 f"dsr={dsr.get('dsr')}  T={dsr.get('T')}")
    lines.append(f"         passed={dsr['passed']}  reason={dsr.get('reason', '')}")

    perm = result["perm"]
    lines.append(f"  [PERM] stat_obs={perm['stat_obs']}  p_value={perm['p_value']}  "
                 f"B={perm['B']}")
    lines.append(f"         passed={perm['passed']}")

    pbo = result["pbo"]
    lines.append(f"  [PBO]  pbo={pbo.get('pbo')}  n_splits={pbo.get('n_splits')}  "
                 f"passed={pbo['passed']}")
    if pbo.get("reason"):
        lines.append(f"         reason={pbo['reason']}")

    sp = result["sprt"]
    lines.append(f"  [SPRT] decision={sp['decision']}  llr={sp['llr']}  "
                 f"n_used={sp['n_used']}  p0={sp['p0']:.3f}  p1={sp['p1']:.3f}")

    lines.append("-" * 60)
    verdict_sym = "PASS" if result["verdict"] == "pass" else result["verdict"].upper()
    lines.append(f"  VERDICT: {verdict_sym}")
    lines.append("=" * 60)
    return "\n".join(lines)
