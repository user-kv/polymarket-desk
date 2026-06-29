"""Gate 2: mechanism consistency check (CONSTITUTION §6 gate 2).

A strategy must name a known causal mechanism AND the observed error pattern
must be consistent with that claim. This is where "why" lives — a positive
EV with no stated mechanism is a coincidence, not an edge.
"""
from institute.map.baselines import evaluate, _sim_profit
from institute.agents import llm

MECHANISMS = {
    "favorite_longshot_bias": "tails systematically overpriced (behavioural)",
    "recency_overreaction":   "crowd overweights latest event",
    "liquidity_vacuum":       "thin book -> stale/whippy price",
    "model_vs_crowd":         "quant model has info the crowd's price lacks",
    "market_consensus":       "sharper external market (sportsbook) leads PM price",
}


def _check_favorite_longshot_bias(rows, baseline_fn, **kw):
    """Validate the FLB mechanism: bets must be NO on cheap longshots and
    the realised win rate must beat the implied break-even rate.

    Break-even for a NO bet at executable price (1 - q_yes) is q_yes itself
    (the implied YES probability). If we win more than q_yes fraction of the
    time when betting NO, we beat break-even — consistent with overpriced tails.
    """
    bet_rows = []
    costs = []
    wins = 0
    for rm in rows:
        p, side = baseline_fn(rm, **kw)
        if side is None:
            continue
        if side != "NO":
            # FLB should only place NO bets; a YES bet is inconsistent.
            return False, "FLB baseline placed YES bets (inconsistent)"
        bet_rows.append(rm)
        costs.append(rm["q_yes"])  # cost of the NO position = q_yes
        prof = _sim_profit(side, rm["q_yes"], rm["y"])
        if prof > 0:
            wins += 1

    if not bet_rows:
        return False, "no bets placed"

    mean_cost = sum(costs) / len(costs)
    win_pct = 100.0 * wins / len(bet_rows)

    # mean_cost < 0.5: we are betting NO on cheap (sub-50%) longshots.
    # win_pct > 100 * mean_cost: beating break-even (implied rate).
    if mean_cost >= 0.5:
        return False, f"mean executable cost {mean_cost:.3f} >= 0.5 (not longshots)"
    if win_pct <= 100 * mean_cost:
        return (
            False,
            f"win_pct {win_pct:.1f}% <= break-even {100*mean_cost:.1f}% (no FLB edge)",
        )
    return True, f"ok: mean_cost={mean_cost:.3f} win_pct={win_pct:.1f}% > break-even={100*mean_cost:.1f}%"


def _check_generic(rows, baseline_fn, **kw):
    """Generic consistency: mean market-relative skill > 0 on placed bets."""
    m = evaluate(rows, baseline_fn, **kw)
    if m["mean_S"] > 0:
        return True, f"mean_S={m['mean_S']} > 0"
    return False, f"mean_S={m['mean_S']} <= 0 (no skill signal)"


def check(strategy, rows, baseline_fn, use_llm=False, **kw) -> dict:
    """Gate 2: verify mechanism stated AND its pattern is consistent with data.

    Returns {passed, mechanism, reason, evidence}.
    passed=True only if a known mechanism is stated AND its consistency holds.
    """
    mech = strategy.mechanism if hasattr(strategy, "mechanism") else strategy.get("mechanism", "")

    if not mech:
        return {
            "passed": False,
            "mechanism": "",
            "reason": "no stated mechanism (held at Gate 2)",
            "evidence": {},
        }

    if mech not in MECHANISMS:
        return {
            "passed": False,
            "mechanism": mech,
            "reason": f"unknown mechanism '{mech}'; not in taxonomy",
            "evidence": {},
        }

    # Consistency check — mechanism-specific logic.
    if mech == "favorite_longshot_bias":
        ok, detail = _check_favorite_longshot_bias(rows, baseline_fn, **kw)
    else:
        ok, detail = _check_generic(rows, baseline_fn, **kw)

    m = evaluate(rows, baseline_fn, **kw)
    evidence = {
        "n": m["n"],
        "win_pct": m["win_pct"],
        "mean_S": m["mean_S"],
        "ev_net": m["ev_net"],
        "mechanism_desc": MECHANISMS[mech],
        "detail": detail,
    }

    advisory = ""
    if use_llm:
        prompt = (
            f"Mechanism: {mech}\nDescription: {MECHANISMS[mech]}\n"
            f"Evidence: {evidence}\nIs this evidence consistent with the mechanism? "
            f"Reply yes/no with one sentence rationale."
        )
        advisory = " [LLM advisory: " + llm.complete(prompt, role="judge") + "]"

    return {
        "passed": ok,
        "mechanism": mech,
        "reason": detail + advisory,
        "evidence": evidence,
    }
