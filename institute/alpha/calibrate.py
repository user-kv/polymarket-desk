"""Extremization calibration for the Alpha Engine (A6).

Calibration undoes the RLHF hedge-toward-0.5 bias by pushing probabilities
toward the tails in logit space.

Standing institute rule: do NOT activate until n >= 200 resolved markets
for the research baseline.  Today n is tiny so maybe_calibrate() is a
structural no-op — it just returns p unchanged.  The switch will flip
automatically once the threshold is crossed.

Reference: AIA Forecaster extremization (arXiv 2511.07678), fixed alpha ~1.73.
"""
import math

from institute.scoring import clip

ALPHA = 3 ** 0.5        # ~1.732  AIA fixed extremization coefficient (no overfit)
CALIB_MIN_N = 200       # institute standing rule — do not change without deliberation


def extremize(p, alpha=ALPHA):
    """Push probability p toward the tails in logit space.

    extremize(0.5) == 0.5 (symmetric fixed point).
    extremize(p > 0.5) > p  (pushes toward 1).
    extremize(p < 0.5) < p  (pushes toward 0).
    extremize(p) + extremize(1-p) == 1.0  (symmetry).

    Uses pure math stdlib only.
    """
    p = clip(p)
    z = math.log(p / (1.0 - p))      # logit
    return 1.0 / (1.0 + math.exp(-alpha * z))


def maybe_calibrate(p, n, alpha=ALPHA):
    """Apply extremization calibration only when we have enough data.

    Below CALIB_MIN_N (today) this is a no-op: returns p unchanged.
    This is intentional and correct — calibration requires sufficient n
    to be trustworthy; premature extremization can hurt accuracy.
    """
    if n >= CALIB_MIN_N:
        return extremize(p, alpha)
    return p
