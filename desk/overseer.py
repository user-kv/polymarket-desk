"""
desk/overseer.py — the independent overseer (research round 3 / SICA).

Because you chose fuller autonomy (no human approval gate), this is the autonomous
stand-in: an independent check that runs BEFORE any self-modification and has the
authority to FREEZE the loop. It does not trust the loop's own judgement.

It enforces, in order:
  1. Kernel integrity — the protected core (invariants + fitness) must match its
     baseline hash. Drift => freeze.
  2. Fake-money invariant — hard assert.
  3. Kill switch — selfmod_config.self_modification_enabled must be true.
  4. Readiness — enough resolved bets for the backtest to be a fair judge.
  5. Daily promotion budget — no more than max_promotions_per_day.
  6. Pathology heuristics — obviously bad proposals (kernel edits, real-money
     strings, network beyond the allowlist) are refused.

`gate()` returns (allowed, reason). Anything other than allowed=True means the loop
must not modify itself this run.
"""

from __future__ import annotations
import json
from pathlib import Path
from datetime import datetime, timezone

from desk.kernel import invariants as inv

DESK = Path(__file__).resolve().parent
CONFIG = DESK / "selfmod_config.json"
PROMOTIONS_LOG = DESK / "tools" / "promotions.log"


def load_config() -> dict:
    return json.loads(CONFIG.read_text(encoding="utf-8"))


def _promotions_today() -> int:
    if not PROMOTIONS_LOG.exists():
        return 0
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    n = 0
    for line in PROMOTIONS_LOG.read_text(encoding="utf-8").splitlines():
        if line.startswith(today):
            n += 1
    return n


def _resolved_bet_count() -> int:
    import csv
    bets = DESK.parent / "papertrader" / "data" / "bets.csv"
    if not bets.exists():
        return 0
    n = 0
    with bets.open(encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if (r.get("result") or "").upper() in ("WON", "LOST"):
                n += 1
    return n


# crude content pathology scan for a proposed change (defense in depth; the real
# enforcement is sandbox static-analysis + the kernel hash)
_PATHOLOGY = ("real money", "private key", "wallet", "os.system", "subprocess",
             "eval(", "exec(", "rm -rf", "import socket")


def scan_proposal(text: str) -> tuple[bool, str]:
    low = (text or "").lower()
    for bad in _PATHOLOGY:
        if bad in low:
            return False, f"pathology: proposal contains '{bad}'"
    for host_token in ("http://", "https://"):
        idx = low.find(host_token)
        while idx != -1:
            rest = low[idx + len(host_token):]
            host = rest.split("/")[0].split(":")[0]
            if host and not any(host == a or host.endswith("." + a) for a in inv.NETWORK_ALLOWLIST):
                return False, f"pathology: non-allowlisted host '{host}'"
            idx = low.find(host_token, idx + 1)
    return True, "no pathology detected"


def gate(proposal_text: str | None = None) -> tuple[bool, str]:
    """The master pre-flight. allowed=True only if every guard passes."""
    ok, msg = inv.verify_kernel_integrity()
    if not ok:
        return False, f"FREEZE (kernel): {msg}"
    try:
        inv.assert_fake_money_only()
    except SystemExit as e:
        return False, f"FREEZE (safety): {e}"

    cfg = load_config()
    if not cfg.get("self_modification_enabled", False):
        return False, "FROZEN: kill switch is off (self_modification_enabled=false)"

    need = cfg.get("min_resolved_bets_before_selfmod", 30)
    have = _resolved_bet_count()
    if have < need:
        return False, f"NOT READY: {have}/{need} resolved bets before self-mod is allowed"

    cap = cfg.get("max_promotions_per_day", 2)
    if _promotions_today() >= cap:
        return False, f"DAILY CAP: {cap} promotions already today"

    if proposal_text is not None:
        clean, why = scan_proposal(proposal_text)
        if not clean:
            return False, f"REFUSE: {why}"

    return True, "overseer: all guards passed"


def record_promotion(tool_name: str, detail: str) -> None:
    PROMOTIONS_LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    with PROMOTIONS_LOG.open("a", encoding="utf-8") as f:
        f.write(f"{ts} | {tool_name} | {detail}\n")


if __name__ == "__main__":
    allowed, reason = gate()
    print(("ALLOWED: " if allowed else "BLOCKED: ") + reason)
