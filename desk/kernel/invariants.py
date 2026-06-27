"""
desk/kernel/invariants.py  — IMMUTABLE protected core.

These are the non-negotiable invariants the autonomous self-modification loop may
NEVER edit or override. They exist to prevent the two documented failure modes of
self-modifying agents (reward-hacking and goal/safety drift):

  * FAKE MONEY ONLY. No real orders, no wallet, no API keys to any exchange.
  * The five discipline rules define what "a disciplined bet" means. A self-written
    tool may add NEW information, but may not loosen these to manufacture wins.
  * The fitness definition (see fitness.py) is what "better" means. If the loop
    could edit it, it would optimise the ruler instead of the trading.

The kernel guards itself by hashing its own source. `verify_kernel_integrity()` is
called by the overseer and the promotion gate; if the hash drifts without a
deliberate re-baseline, self-modification is frozen.
"""

from __future__ import annotations
import hashlib
import json
from pathlib import Path

# --------------------------------------------------------------------------- #
# Hard safety invariants — must always hold, everywhere.
# --------------------------------------------------------------------------- #
FAKE_MONEY_ONLY = True          # No real money is ever placed. Ever.
ALLOW_REAL_ORDERS = False       # There is no code path that submits a live order.
ALLOW_WALLET = False            # No wallet/private key is ever loaded.
MAX_BANKROLL_USD = 0.0          # Real-dollar exposure ceiling. Zero by design.

# Network the sandboxed self-written tools may reach (read-only data only).
NETWORK_ALLOWLIST = (
    "ensemble-api.open-meteo.com",
    "api.open-meteo.com",
    "archive-api.open-meteo.com",
    "gamma-api.polymarket.com",
    "clob.polymarket.com",
)

# --------------------------------------------------------------------------- #
# The five discipline rules (parameters live in config; the RULE SET is fixed).
# A self-written tool may supply better inputs to these rules; it may not delete
# a rule or invert its direction.
# --------------------------------------------------------------------------- #
DISCIPLINE_RULES = (
    "edge_gte_threshold",     # model prob must beat the ask by >= threshold
    "within_max_hours",       # only short-lead markets (forecast skill exists)
    "models_agree",           # cross-model agreement required
    "outside_mean_buffer",    # skip coin-flip buckets straddling the mean
    "bankroll_ok",            # exposure / no-duplicate / liquidity guard
)

# Config keys the self-mod loop is NOT allowed to widen past these bounds.
# (Promotion gate rejects any proposed config delta that breaches a bound.)
PARAM_BOUNDS = {
    "edge_threshold_pct":     {"min": 3.0,  "max": 30.0},   # cannot bet on <3pt edge
    "max_hours_to_resolution":{"min": 1,    "max": 72},     # cannot bet >72h lead
    "model_agree_max_diff_c": {"min": 0.25, "max": 3.0},
    "max_exposure_pct":       {"min": 1.0,  "max": 25.0},   # cannot risk >25% bankroll
    "stake_per_bet":          {"min": 0.0,  "max": 50.0},
    "max_stake":              {"min": 0.0,  "max": 100.0},  # 5% of the $2000 fake bankroll (user-approved 2026-06-20)
}

KERNEL_DIR = Path(__file__).resolve().parent
_HASH_FILE = KERNEL_DIR / "kernel.hash.json"
# Files whose bytes define the protected core. Drift here freezes self-mod.
_PROTECTED_FILES = ("invariants.py", "fitness.py")


def assert_fake_money_only() -> None:
    """Called at every entry point. Hard-stops if any real-money flag is flipped."""
    if not FAKE_MONEY_ONLY or ALLOW_REAL_ORDERS or ALLOW_WALLET or MAX_BANKROLL_USD != 0.0:
        raise SystemExit(
            "KERNEL VIOLATION: real-money safety invariant breached. Refusing to run."
        )


def param_within_bounds(key: str, value: float) -> bool:
    """True if a proposed config value is inside the protected bound (or unbounded)."""
    b = PARAM_BOUNDS.get(key)
    if b is None:
        return True
    return b["min"] <= value <= b["max"]


def _compute_hash() -> str:
    h = hashlib.sha256()
    for name in _PROTECTED_FILES:
        h.update((KERNEL_DIR / name).read_bytes())
    return h.hexdigest()


def baseline_hash(write: bool = True) -> str:
    """Record the current kernel hash as the trusted baseline."""
    digest = _compute_hash()
    if write:
        _HASH_FILE.write_text(json.dumps({"sha256": digest}, indent=2))
    return digest


def verify_kernel_integrity() -> tuple[bool, str]:
    """
    (ok, message). ok=False means the protected core changed without a deliberate
    re-baseline — the overseer treats this as grounds to FREEZE self-modification.
    """
    if not _HASH_FILE.exists():
        return False, "No kernel baseline recorded. Run --rebaseline once you trust the core."
    expected = json.loads(_HASH_FILE.read_text())["sha256"]
    actual = _compute_hash()
    if actual != expected:
        return False, f"KERNEL DRIFT: expected {expected[:12]} got {actual[:12]} — self-mod FROZEN."
    return True, "kernel intact"


if __name__ == "__main__":
    import sys
    if "--rebaseline" in sys.argv:
        print("New kernel baseline:", baseline_hash(write=True))
    else:
        ok, msg = verify_kernel_integrity()
        print(("OK: " if ok else "FAIL: ") + msg)
        assert_fake_money_only()
        print("fake-money-only invariant: held")
