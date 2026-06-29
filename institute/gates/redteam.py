"""Gate 3: adversarial red-team battery (CONSTITUTION §6 gate 3).

Each attack tries to break a strategy. A cell survives only when zero attacks
are fatal. Non-fatal warnings are informational only.
"""
from institute.map.baselines import evaluate, _sim_profit
from institute.agents import llm


def _finding(name, fatal, reason, evidence=None):
    return {
        "attack": name,
        "fatal": fatal,
        "reason": reason,
        "evidence": evidence or {},
    }


def attack_lookahead(strategy, rows, baseline_fn, **kw):
    """Leak check: decisions must depend only on q_yes (knowable at t0).

    Detects lookahead bias by perturbing y in a copy of each row and checking
    whether the side (decision) changes. If the baseline uses rm['y'] to pick
    a side it is cheating — fatal, as the strategy cannot be executed forward.
    """
    for rm in rows:
        _, side_orig = baseline_fn(rm, **kw)
        # Flip y: 0 -> 1, 1 -> 0.
        perturbed = dict(rm)
        perturbed["y"] = 1 - rm["y"]
        _, side_pert = baseline_fn(perturbed, **kw)
        if side_orig != side_pert:
            return _finding(
                "lookahead",
                fatal=True,
                reason="decision changes when outcome y is altered -- lookahead leak detected",
                evidence={"example_q_yes": rm["q_yes"], "y_orig": rm["y"],
                          "side_orig": side_orig, "side_pert": side_pert},
            )
    return _finding(
        "lookahead",
        fatal=False,
        reason="all decisions stable under y perturbation -- no lookahead leak",
    )


def attack_regime(strategy, rows, baseline_fn, **kw):
    """Regime fragility: edge must not be carried by a single time slice.

    Splits rows into 3 contiguous thirds and checks ev_net per third.
    Fatal when >= 2 thirds show ev_net <= 0 while overall ev_net > 0
    (edge is illusory — regime-dependent).
    Warn (non-fatal) when exactly 1 third shows ev_net <= 0.
    """
    if len(rows) < 3:
        return _finding(
            "regime",
            fatal=False,
            reason=f"too few rows ({len(rows)}) to split into thirds -- skipped",
        )

    n = len(rows)
    chunk = n // 3
    thirds = [
        rows[:chunk],
        rows[chunk: 2 * chunk],
        rows[2 * chunk:],
    ]

    ev_thirds = []
    for t in thirds:
        m = evaluate(t, baseline_fn, **kw)
        ev_thirds.append(m["ev_net"])

    overall = evaluate(rows, baseline_fn, **kw)["ev_net"]
    neg_count = sum(1 for ev in ev_thirds if ev <= 0)

    evidence = {
        "ev_thirds": ev_thirds,
        "ev_overall": overall,
        "neg_thirds": neg_count,
    }

    if overall > 0 and neg_count >= 2:
        return _finding(
            "regime",
            fatal=True,
            reason=f"edge fragile: {neg_count}/3 thirds have ev_net<=0 while overall>0",
            evidence=evidence,
        )
    if neg_count == 1:
        return _finding(
            "regime",
            fatal=False,
            reason=f"regime warn: 1/3 thirds has ev_net<=0 (non-fatal)",
            evidence=evidence,
        )
    return _finding(
        "regime",
        fatal=False,
        reason="edge present in >= 2 thirds -- regime stable",
        evidence=evidence,
    )


def attack_fills(strategy, rows, baseline_fn, **kw):
    """Fill-cost stress: apply 3% friction and check whether EV flips negative.

    Real-world fills are worse than mid. A strategy must survive plausible
    slippage (3 cents per dollar staked) to be operationally viable.
    """
    # Baseline EV without stress.
    m_clean = evaluate(rows, baseline_fn, **kw)
    ev_clean = m_clean["ev_net"]

    # Stressed EV: re-simulate with cost=0.03.
    n_stress = 0
    pnl_stress = 0.0
    for rm in rows:
        p, side = baseline_fn(rm, **kw)
        if side is None:
            continue
        n_stress += 1
        pnl_stress += _sim_profit(side, rm["q_yes"], rm["y"], cost=0.03)

    ev_stress = pnl_stress / n_stress if n_stress else 0.0

    evidence = {
        "ev_clean": round(ev_clean, 4),
        "ev_stress": round(ev_stress, 4),
        "n_bets": n_stress,
        "cost_applied": 0.03,
    }

    if ev_stress < 0:
        return _finding(
            "fills",
            fatal=True,
            reason=f"EV flips negative under 3% fill stress: {ev_clean:.4f} -> {ev_stress:.4f}",
            evidence=evidence,
        )
    return _finding(
        "fills",
        fatal=False,
        reason=f"EV survives fill stress: {ev_clean:.4f} -> {ev_stress:.4f}",
        evidence=evidence,
    )


def run(strategy, rows, baseline_fn, use_llm=False, **kw) -> dict:
    """Run the full red-team battery; survived = no fatal findings."""
    findings = [
        attack_lookahead(strategy, rows, baseline_fn, **kw),
        attack_regime(strategy, rows, baseline_fn, **kw),
        attack_fills(strategy, rows, baseline_fn, **kw),
    ]

    survived = not any(f["fatal"] for f in findings)

    advisory = ""
    if use_llm:
        summary = "; ".join(f["reason"] for f in findings)
        prompt = (
            f"Red-team findings for strategy '{getattr(strategy, 'baseline', strategy)}':\n"
            f"{summary}\nAny additional risks the quant analyst should flag?"
        )
        advisory = llm.complete(prompt, role="reason")

    return {
        "survived": survived,
        "findings": findings,
        "advisory": advisory,
    }
