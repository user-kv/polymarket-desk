"""Proper scoring per CONSTITUTION §2/§11A. EV_net is the gate; S is a diagnostic."""
import math

EPS = 0.01


def clip(p, eps=EPS):
    return max(eps, min(1.0 - eps, float(p)))


def log_score(p, y):
    """Log score of forecast p against binary outcome y in {0,1}."""
    p = clip(p)
    return y * math.log(p) + (1 - y) * math.log(1.0 - p)


def market_relative_S(p, q, y):
    """Incremental log-skill of forecast p over the market prior q (§2).

    Copying the price (p == q) scores exactly 0 — by design.
    """
    return log_score(p, y) - log_score(clip(q), y)


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0
