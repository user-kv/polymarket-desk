"""Dumb baselines for the predictability map (A1_PLAN). No predictors yet —
these measure where edge plausibly lives, cheaply.

Each baseline maps a ResolvedMarket(-dict) to a forecast p(YES) and a bet
decision. EV uses executable prices (NO price ≈ 1 - q_yes), never mid of a
strategy it doesn't take. Realized ledger PnL is used as ground truth when the
row carries it (the weather +$68 anchor).
"""
from institute.scoring import clip, market_relative_S

# ── individual baselines: return (p_forecast, side|None) ──────────────────────


def price_follow(rm):
    """Sanity null: trust the price exactly. p == q → market-relative skill 0."""
    return rm["q_yes"], None  # takes no directional bet; pure score anchor


def longshot_fade(rm, cap=0.35, shrink=0.5):
    """Our proven mechanism: cheap longshots are overpriced → fade them (bet NO)."""
    q = rm["q_yes"]
    if q <= cap:
        return q * shrink, "NO"
    return q, None


def base_rate(rm, rate):
    """Bet toward the archetype's empirical base rate vs the price."""
    side = "YES" if rate > q_of(rm) else "NO"
    return rate, side


def q_of(rm):
    return rm["q_yes"]


# ── scoring a baseline over a set of resolved markets ─────────────────────────


def _sim_profit(side, q_yes, y, cost=0.0):
    """Realistic-ish payoff per $1 staked at executable price (§3). NO buys at
    ~ (1 - q_yes); YES buys at ~ q_yes. Win pays 1/price - 1, loss pays -1."""
    if side == "NO":
        price = clip(1.0 - q_yes)
        won = (y == 0)
    else:  # YES
        price = clip(q_yes)
        won = (y == 1)
    return (1.0 / price - 1.0 - cost) if won else -1.0


def evaluate(rows, baseline_fn, use_realized=False, **kw):
    """rows: list[ResolvedMarket dict]. Returns metrics dict."""
    n = 0
    wins = 0
    s_vals = []
    pnl = 0.0
    staked = 0.0
    for rm in rows:
        p, side = baseline_fn(rm, **kw)
        s_vals.append(market_relative_S(p, rm["q_yes"], rm["y"]))
        if side is None:
            continue  # scores S but places no bet (e.g. price_follow)
        n += 1
        if use_realized and rm.get("realized_pnl") is not None and rm.get("realized_side") == side:
            prof = rm["realized_pnl"] / max(rm.get("stake", 1.0), 1e-9)
            staked += 1.0
            pnl += prof
            wins += 1 if rm["realized_pnl"] > 0 else 0
        else:
            prof = _sim_profit(side, rm["q_yes"], rm["y"])
            staked += 1.0
            pnl += prof
            wins += 1 if prof > 0 else 0
    return {
        "n": n,
        "win_pct": round(100.0 * wins / n, 1) if n else 0.0,
        "mean_S": round(sum(s_vals) / len(s_vals), 4) if s_vals else 0.0,
        "ev_net": round(pnl / staked, 4) if staked else 0.0,
        "naive_roi": round(pnl / staked, 4) if staked else 0.0,
    }


def research(rm, edge=0.05, std_ceiling=0.20):
    """Bet our model's edge vs the market, but only when confident and decisive.

    Reads the point-in-time forecast frozen at snapshot.  No forecast -> abstain.
    std_ceiling: if the swarm is too divided (high p_std) we abstain.
    edge: minimum divergence |p_final - q_yes| required to place a bet.
    """
    meta = rm.get("meta", {})
    p = meta.get("p_final")
    if p is None:
        return rm["q_yes"], None                # never forecast -> abstain
    if meta.get("p_std", 1.0) > std_ceiling:
        return p, None                          # swarm too divided -> abstain
    q = rm["q_yes"]
    if p - q > edge:
        return p, "YES"
    if q - p > edge:
        return p, "NO"
    return p, None


BASELINES = {
    "price_follow": (price_follow, {}, False),
    "longshot_fade": (longshot_fade, {}, True),
    "research": (research, {}, True),
}
