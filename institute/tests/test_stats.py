"""Unit tests for institute.evidence.stats — one test per statistical primitive.

All pure stdlib, deterministic (fixed seeds). Tests assert mathematical
properties rather than exact floats to stay robust under minor impl tweaks.
"""
import random

from institute.evidence.stats import (
    norm_cdf, norm_ppf, deflated_sharpe, permutation_pvalue,
    pbo_cscv, sprt,
)
from institute.map.baselines import longshot_fade


# ── shared helpers ─────────────────────────────────────────────────────────────

def _moderate_returns(n=40, base=0.04, noise=0.12, seed=7):
    """Moderate consistent positive returns — DSR passes at n_trials=2 but
    is visibly deflated at n_trials=1000 (not saturated at 1.0)."""
    rng = random.Random(seed)
    return [base + rng.gauss(0, noise) for _ in range(n)]


def _make_correlated_rows(seed=0):
    """Synthetic dataset for the permutation test.

    High-q rows (near the longshot_fade cap=0.35) are strongly biased toward
    y=0 (NO resolves) — they are the most overpriced longshots.
    Low-q rows (less overpriced) sometimes resolve YES.
    This correlation between price level and outcome is the detectable signal;
    permuting y destroys it and shifts the null distribution left.
    """
    rng = random.Random(seed)
    rows = []
    # High-q, mostly y=0 (overpriced, strong NO bias)
    for _ in range(20):
        rows.append({"q_yes": 0.30 + rng.uniform(0.0, 0.04), "y": 0})
    rows.append({"q_yes": 0.32, "y": 1})  # one YES at high q
    # Low-q, mixed outcomes (less overpriced, more y=1)
    for _ in range(8):
        rows.append({"q_yes": 0.10 + rng.uniform(0.0, 0.05), "y": 0})
    for _ in range(5):
        rows.append({"q_yes": 0.10 + rng.uniform(0.0, 0.05), "y": 1})
    return rows


def _make_random_rows(seed=99):
    """50/50 random outcomes across a range of q — no detectable signal."""
    rng = random.Random(seed)
    return [
        {"q_yes": 0.10 + rng.uniform(0.0, 0.24), "y": rng.choice([0, 1])}
        for _ in range(40)
    ]


# ── norm_cdf / norm_ppf ───────��───────────────────────────────────────────────


def test_norm_cdf_midpoint():
    assert abs(norm_cdf(0.0) - 0.5) < 1e-10


def test_norm_ppf_975():
    # 1.96 is the canonical 97.5th percentile; BSM approx is within 0.01
    assert abs(norm_ppf(0.975) - 1.96) < 0.01


def test_norm_ppf_roundtrip():
    for p in [0.01, 0.1, 0.5, 0.9, 0.99]:
        assert abs(norm_cdf(norm_ppf(p)) - p) < 1e-6


# ── deflated_sharpe ───────────────────────────────────────────────────────────


def test_dsr_high_on_strong_series():
    """Moderate positive series with low n_trials should score high DSR."""
    rets = _moderate_returns()
    r = deflated_sharpe(rets, n_trials=2)
    assert r["passed"], f"expected pass, got dsr={r['dsr']}"
    assert r["dsr"] >= 0.9


def test_dsr_deflation_monotonic():
    """More trials tested -> lower DSR (deflation bites harder)."""
    rets = _moderate_returns()
    r2 = deflated_sharpe(rets, n_trials=2)
    r1000 = deflated_sharpe(rets, n_trials=1000)
    assert r2["dsr"] > r1000["dsr"], (
        f"expected DSR(2)={r2['dsr']} > DSR(1000)={r1000['dsr']}"
    )


def test_dsr_low_n_returns_skip():
    r = deflated_sharpe([0.1, 0.2, 0.3], n_trials=2)
    assert not r["passed"]
    assert r["reason"] == "n < 8"


def test_dsr_zero_variance():
    r = deflated_sharpe([0.5] * 20, n_trials=2)
    assert not r["passed"]


# ── permutation_pvalue ────────────────────────────────────────────────────────


def test_permutation_passes_on_biased_set():
    """High-q rows are biased toward y=0; permuting y destroys this correlation
    and pushes stat_obs into the right tail of the null -> p < 0.05."""
    rows = _make_correlated_rows(seed=0)
    r = permutation_pvalue(rows, longshot_fade, B=2000, seed=0)
    assert r["passed"], f"p_value={r['p_value']} expected < 0.05 on correlated biased set"


def test_permutation_fails_on_random_y():
    """Random outcomes have no detectable correlation with q -> p NOT < 0.05."""
    rows = _make_random_rows(seed=99)
    r = permutation_pvalue(rows, longshot_fade, B=2000, seed=0)
    assert not r["passed"], f"p_value={r['p_value']} expected >= 0.05 on random set"


# ── pbo_cscv ───────���───────────────────────────���─────────────────────────────���


def test_pbo_single_config_na():
    rets = [0.1, -0.05, 0.2, 0.15] * 10
    r = pbo_cscv([rets])
    assert r["passed"] is True
    assert r["pbo"] is None


def test_pbo_two_configs_returns_value():
    rng = random.Random(42)
    c1 = [rng.gauss(0.1, 0.1) for _ in range(64)]
    c2 = [rng.gauss(-0.1, 0.1) for _ in range(64)]
    r = pbo_cscv([c1, c2])
    assert r["pbo"] is not None
    assert 0.0 <= r["pbo"] <= 1.0


# ── sprt ───────────��──────────────────────────────────────────────────────────


def test_sprt_mostly_wins_accepts_h1():
    stream = [1] * 25 + [0] * 5
    r = sprt(stream, p0=0.5, p1=0.7)
    assert r["decision"] == "accept_H1", f"got {r['decision']}"


def test_sprt_mostly_losses_accepts_h0():
    stream = [0] * 25 + [1] * 3
    r = sprt(stream, p0=0.5, p1=0.7)
    assert r["decision"] == "accept_H0", f"got {r['decision']}"


def test_sprt_returns_continue_on_mixed():
    # Near-50/50 stream — ambiguous evidence, should not accept H1
    stream = [1, 0, 1, 0, 1, 0]
    r = sprt(stream, p0=0.5, p1=0.7)
    assert r["decision"] in ("continue", "accept_H0")
