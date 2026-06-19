"""Tests for the self-modification guardrails: overseer, sandbox, promotion gate."""
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from desk import overseer, sandbox, promote
from desk.kernel import fitness as fit


# ---- overseer ----------------------------------------------------------------
def test_overseer_frozen_by_default():
    # selfmod_config ships with self_modification_enabled=false (kill switch)
    allowed, reason = overseer.gate()
    assert allowed is False
    assert "FROZEN" in reason or "NOT READY" in reason or "FREEZE" in reason


def test_scan_proposal_blocks_bad():
    ok, _ = overseer.scan_proposal("def run(): return real money wallet")
    assert ok is False
    ok, _ = overseer.scan_proposal("import os\nos.system('x')")
    assert ok is False
    ok, _ = overseer.scan_proposal("fetch https://evil.example.com/x")
    assert ok is False


def test_scan_proposal_allows_clean_allowlisted():
    ok, why = overseer.scan_proposal(
        "fetch https://ensemble-api.open-meteo.com/v1/ensemble?x=1")
    assert ok is True


# ---- sandbox static analysis -------------------------------------------------
def test_static_rejects_banned_import():
    ok, _ = sandbox.static_analyze("import os\ndef run(): return 1")
    assert ok is False
    ok, _ = sandbox.static_analyze("import socket\ndef run(): return 1")
    assert ok is False


def test_static_rejects_banned_call():
    ok, _ = sandbox.static_analyze("def run(): return eval('1+1')")
    assert ok is False
    ok, _ = sandbox.static_analyze("def run(): return open('x','w')")
    assert ok is False


def test_static_allows_clean():
    ok, _ = sandbox.static_analyze("import math\ndef run(): return math.sqrt(4)")
    assert ok is True


# ---- sandbox execution -------------------------------------------------------
def test_sandbox_runs_clean_tool():
    r = sandbox.run_tool("def run():\n    import math\n    return math.sqrt(81)\n")
    assert r["ok"] is True
    assert "9.0" in r["stdout"]


def test_sandbox_rejects_dirty_tool():
    r = sandbox.run_tool("import os\ndef run():\n    return os.system('echo x')\n")
    assert r["ok"] is False
    assert r.get("rejected") is True


# ---- promotion gate ----------------------------------------------------------
def test_promote_blocked_when_frozen():
    champ = fit.FitnessReport(2.0, 0.2, 0.05, 0.1, 0.0, 40, 20)
    chall = fit.FitnessReport(1.5, 0.2, 0.04, 0.11, 0.0, 40, 20)
    res = promote.evaluate_and_promote(
        "t", "def run(): return 1", "run", champ, chall)
    assert res["promoted"] is False
    assert res["stage"] == "overseer"


def test_promote_success_path_when_allowed(monkeypatch=None):
    # repoint side-effecting paths to temp + stub overseer/git so the test is hermetic
    tmp = Path(tempfile.mkdtemp())
    orig_gate, orig_git = overseer.gate, promote._git_commit
    orig_live, orig_arc, orig_log = promote.LIVE, promote.ARCHIVE, overseer.PROMOTIONS_LOG
    overseer.gate = lambda proposal_text=None: (True, "test-allowed")
    promote._git_commit = lambda paths, message: None
    promote.LIVE = tmp / "live"
    promote.ARCHIVE = tmp / "archive"
    overseer.PROMOTIONS_LOG = tmp / "promotions.log"
    try:
        champ = fit.FitnessReport(2.0, 0.2, 0.05, 0.10, 0.0, 40, 20)
        chall = fit.FitnessReport(1.5, 0.2, 0.04, 0.11, 0.0, 40, 20)  # better CRPS
        src = "def run():\n    import math\n    return math.sqrt(64)\n"
        res = promote.evaluate_and_promote("good_tool", src, "run", champ, chall)
        assert res["promoted"] is True, res
        assert (promote.LIVE / "good_tool.py").exists()

        # a challenger that only improves PnL (reward-hack) must be rejected at fitness
        hack = fit.FitnessReport(2.0, 0.2, 0.05, 0.10, 999.0, 40, 20)
        res2 = promote.evaluate_and_promote("hack_tool", src, "run", champ, hack)
        assert res2["promoted"] is False
        assert res2["stage"] == "fitness"
    finally:
        overseer.gate, promote._git_commit = orig_gate, orig_git
        promote.LIVE, promote.ARCHIVE, overseer.PROMOTIONS_LOG = orig_live, orig_arc, orig_log


def _run():
    passed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  PASS {name}")
            passed += 1
    print(f"\n{passed} selfmod tests passed.")


if __name__ == "__main__":
    _run()
