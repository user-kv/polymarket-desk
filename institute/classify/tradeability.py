"""Tradeability & integrity preconditions (CONSTITUTION §4 + §11 D/E + Seam 1).

A market enters the universe only if resolvable, exitable, freshly priced, and
not obviously insider-toxic. An edge on a market failing any of these is fake.
"""


def crude_toxicity(meta):
    """Seam-1 starter: the classic insider signature (new wallet, one big one-sided
    bet) + sharp price move with no public news. Rules only in A1; matures later.
    Expects optional meta keys: new_wallet_one_sided(bool), price_jump_no_news(bool).
    Returns (score 0..1, flag bool).
    """
    score = 0.0
    if meta.get("new_wallet_one_sided"):
        score += 0.6
    if meta.get("price_jump_no_news"):
        score += 0.4
    return score, score >= 0.6


def check(snapshot, k=3, intended_position=1.0, stale_window_s=86400, toxicity_cut=0.6):
    """snapshot: dict with optional keys
        resolvable(bool), exit_depth(float), last_trade_age_s(float),
        two_sided(bool), meta(dict).
    Returns (tradeable: bool, reasons: list[str]).
    """
    reasons = []
    if not snapshot.get("resolvable", True):
        reasons.append("unresolvable")
    if snapshot.get("exit_depth", float("inf")) < k * intended_position:
        reasons.append("thin-depth")
    # §11D: a stale or one-sided quote is not a valid baseline price
    if snapshot.get("last_trade_age_s", 0) > stale_window_s or not snapshot.get("two_sided", True):
        reasons.append("stale-price")
    tox, flag = crude_toxicity(snapshot.get("meta", {}))
    if flag:
        reasons.append("toxic")
    return (len(reasons) == 0, reasons)
