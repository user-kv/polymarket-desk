"""Statistical gatekeepers — four independent attempts to DISPROVE edge.

All pure stdlib (math, random, statistics, itertools). No numpy/scipy.
Each function returns a dict so gate1 can log the full picture.
"""
import math
import random
import statistics
import itertools

from institute.scoring import market_relative_S

_SQRT2 = math.sqrt(2.0)
_E = math.e
_EMC = 0.5772156649  # Euler-Mascheroni constant


# ── helpers ───────────────────────────────────────────────────────────────────


def norm_cdf(x):
    """Standard normal CDF via erf identity — exact to stdlib erf precision."""
    return 0.5 * (1.0 + math.erf(x / _SQRT2))


def norm_ppf(p):
    """Inverse normal CDF — Beasley-Springer-Moro rational approximation.

    Uses scipy's tested coefficient set (Moro 1995 / AS241). Accurate to ~1e-7
    across the full range. Pure stdlib, no deps.
    """
    # Coefficients from Moro (1995), used by Glasserman & many quant libs.
    # Central region: |p - 0.5| <= 0.42
    a = [
        2.50662823884,
        -18.61500062529,
        41.39119773534,
        -25.44106049637,
    ]
    b = [
        -8.47351093090,
        23.08336743743,
        -21.06224101826,
        3.13082909833,
    ]
    # Tail region: |p - 0.5| > 0.42
    c = [
        0.3374754822726147,
        0.9761690190917186,
        0.1607979714918209,
        0.0276438810333863,
        0.0038405729373609,
        0.0003951896511349,
        0.0000321767881768,
        0.0000002888167364,
        0.0000003960315187,
    ]

    if p <= 0.0:
        return -math.inf
    if p >= 1.0:
        return math.inf

    r = p - 0.5
    if abs(r) <= 0.42:
        # Central region
        s = r * r
        num = r * (((a[3]*s + a[2])*s + a[1])*s + a[0])
        den = ((((b[3]*s + b[2])*s + b[1])*s + b[0])*s + 1.0)
        return num / den
    else:
        # Tail region
        if r < 0:
            s = math.log(-math.log(p))
        else:
            s = math.log(-math.log(1.0 - p))
        t = c[0] + s*(c[1] + s*(c[2] + s*(c[3] + s*(c[4] + s*(c[5] + s*(c[6] + s*(c[7] + s*c[8])))))))
        return t if r > 0 else -t


def _skew(xs, mu, s):
    """Population skewness (3rd standardised moment)."""
    n = len(xs)
    if n < 2 or s == 0.0:
        return 0.0
    return sum((x - mu) ** 3 for x in xs) / (n * s ** 3)


def _kurt(xs, mu, s):
    """Population standardised 4th moment (normal = 3)."""
    n = len(xs)
    if n < 2 or s == 0.0:
        return 3.0
    return sum((x - mu) ** 4 for x in xs) / (n * s ** 4)


# ── DSR ───────────────────────────────────────────────────────────────────────


def deflated_sharpe(returns, n_trials, sr_benchmark=0.0):
    """Bailey & Lopez de Prado Deflated Sharpe Ratio (CONSTITUTION §6 gate 1a).

    Corrects for the selection bias across n_trials independent strategies
    tested on the same data. A high DSR (>= 0.95) means the Sharpe is
    unlikely to be a false discovery even under the stated search intensity.
    """
    T = len(returns)
    if T < 8:
        return {"sr": None, "sr0": None, "dsr": None, "T": T,
                "passed": False, "reason": "n < 8"}
    mu = sum(returns) / T
    # population std
    var = sum((x - mu) ** 2 for x in returns) / T
    s = math.sqrt(var)
    if s == 0.0:
        return {"sr": None, "sr0": None, "dsr": None, "T": T,
                "passed": False, "reason": "zero variance"}

    sr = mu / s
    g3 = _skew(returns, mu, s)
    g4 = _kurt(returns, mu, s)

    # expected max Sharpe under n_trials independent strategies
    if n_trials >= 2:
        # Var_sr approx per BLP eq. (2): used both for sr0 and standardisation
        var_sr = (1.0 / (T - 1)) * (1.0 - g3 * sr + ((g4 - 1.0) / 4.0) * sr * sr)
        var_sr = max(var_sr, 1e-18)  # clamp; can be tiny but must be positive
        std_sr = math.sqrt(var_sr)
        sr0 = std_sr * (
            (1.0 - _EMC) * norm_ppf(1.0 - 1.0 / n_trials)
            + _EMC * norm_ppf(1.0 - 1.0 / (n_trials * _E))
        )
    else:
        sr0 = sr_benchmark

    # denominator under DSR sqrt
    denom_sq = 1.0 - g3 * sr + ((g4 - 1.0) / 4.0) * sr * sr
    if denom_sq < 0.0:
        return {"sr": round(sr, 4), "sr0": round(sr0, 4), "dsr": None, "T": T,
                "passed": False, "reason": "ill-conditioned"}

    denom = max(math.sqrt(denom_sq), 1e-9)
    dsr = norm_cdf(((sr - sr0) * math.sqrt(T - 1)) / denom)

    return {
        "sr": round(sr, 4),
        "sr0": round(sr0, 4),
        "dsr": round(dsr, 4),
        "T": T,
        "passed": dsr >= 0.95,
        "reason": "ok",
    }


# ── permutation null ──────────────────────────────────────────────────────────


def permutation_pvalue(rows, baseline_fn, B=2000, seed=0, **kw):
    """Non-parametric permutation test on mean market-relative skill S.

    Shuffles outcome labels (y) across rows, keeping q_yes fixed. If our
    signal is real, the observed statistic should be in the extreme right
    tail of the null distribution. p < 0.05 passes.
    """
    rng = random.Random(seed)

    # rows where a bet is placed
    bet_rows = [rm for rm in rows if baseline_fn(rm, **kw)[1] is not None]
    if not bet_rows:
        return {"stat_obs": 0.0, "p_value": 1.0, "B": B, "passed": False}

    def _stat(rs):
        # mean market-relative S for placed-bet rows under given y values
        vals = [market_relative_S(baseline_fn(rm, **kw)[0], rm["q_yes"], rm["y"])
                for rm in rs]
        return sum(vals) / len(vals)

    stat_obs = _stat(bet_rows)
    ys = [rm["y"] for rm in bet_rows]

    count_gte = 0
    for _ in range(B):
        rng.shuffle(ys)
        perm_rows = [{**rm, "y": y} for rm, y in zip(bet_rows, ys)]
        if _stat(perm_rows) >= stat_obs:
            count_gte += 1

    p_value = (count_gte + 1) / (B + 1)
    return {
        "stat_obs": round(stat_obs, 6),
        "p_value": round(p_value, 6),
        "B": B,
        "passed": p_value < 0.05,
    }


# ── PBO / CSCV ────────────────────────────────────────────────────────────────


def _sharpe(vec):
    """Mean / std Sharpe; returns -inf when std == 0 to avoid tie-break weirdness."""
    n = len(vec)
    if n < 2:
        return -math.inf
    mu = sum(vec) / n
    var = sum((x - mu) ** 2 for x in vec) / (n - 1)
    if var == 0.0:
        return -math.inf
    return mu / math.sqrt(var)


def pbo_cscv(returns_matrix, S=8):
    """Probability of Backtest Overfitting via Combinatorially Symmetric CV.

    returns_matrix: list of C configs, each a list of T returns (time-aligned).
    Splits T into S blocks; for each combination of S/2 blocks as IS, picks the
    best IS config and records its OOS rank. PBO = fraction of splits where the
    winner ranked last or worse OOS (logit <= 0). pbo < 0.5 passes.
    """
    C = len(returns_matrix)
    if C < 2:
        return {"pbo": None, "n_splits": 0, "passed": True,
                "reason": "single config -- PBO N/A"}

    T = len(returns_matrix[0])
    block_size = T // S
    if block_size < 1:
        return {"pbo": None, "n_splits": 0, "passed": True,
                "reason": "too few rows for S blocks"}

    blocks = list(range(S))
    half = S // 2
    splits = list(itertools.combinations(blocks, half))

    logit_vals = []
    for is_blocks in splits:
        oos_blocks = [b for b in blocks if b not in is_blocks]

        # compute per-config IS and OOS Sharpes
        is_sharpes = []
        oos_sharpes = []
        for c_vec in returns_matrix:
            is_slice = []
            oos_slice = []
            for bi in is_blocks:
                is_slice.extend(c_vec[bi * block_size: (bi + 1) * block_size])
            for bi in oos_blocks:
                oos_slice.extend(c_vec[bi * block_size: (bi + 1) * block_size])
            is_sharpes.append(_sharpe(is_slice))
            oos_sharpes.append(_sharpe(oos_slice))

        # winner = best IS Sharpe config
        best_idx = max(range(C), key=lambda i: is_sharpes[i])
        winner_oos = oos_sharpes[best_idx]

        # rank = how many configs the winner beats OOS (0-based count)
        rank = sum(1 for s in oos_sharpes if winner_oos > s)
        omega = (rank + 1) / (C + 1)  # fraction of configs beaten (with smoothing)
        # guard against omega = 0 or 1 for logit
        omega = max(1e-9, min(1.0 - 1e-9, omega))
        lam = math.log(omega / (1.0 - omega))
        logit_vals.append(lam)

    pbo = sum(1 for lam in logit_vals if lam <= 0.0) / len(logit_vals)
    return {
        "pbo": round(pbo, 4),
        "n_splits": len(logit_vals),
        "passed": pbo < 0.5,
        "reason": "ok",
    }


# ── SPRT ──────────────────────────────────────────────────────────────────────


def sprt(win_loss, p0, p1, alpha=0.05, beta=0.05):
    """Wald Sequential Probability Ratio Test on a Bernoulli win/loss stream.

    Stops as soon as evidence is strong enough to reject H0 (edge = p0) in
    favour of H1 (edge = p1) or to accept H0. 'continue' means data are
    consistent with both — collect more.
    """
    log_A = math.log((1.0 - beta) / alpha)   # accept H1 boundary
    log_B = math.log(beta / (1.0 - alpha))   # accept H0 boundary

    llr = 0.0
    decision = "continue"
    n_used = 0
    for w in win_loss:
        n_used += 1
        if w == 1:
            llr += math.log(p1 / p0)
        else:
            llr += math.log((1.0 - p1) / (1.0 - p0))
        if llr >= log_A:
            decision = "accept_H1"
            break
        if llr <= log_B:
            decision = "accept_H0"
            break

    return {
        "decision": decision,
        "llr": round(llr, 6),
        "n_used": n_used,
        "p0": p0,
        "p1": p1,
    }
