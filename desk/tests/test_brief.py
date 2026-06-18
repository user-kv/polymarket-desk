"""Tests for the brief layer — especially the ground-truth-authority invariant."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from desk import brief


def _market(city="dallas"):
    return {"slug": "s1", "city": city, "question": "Will Dallas high be 96-97F?"}


def test_skip_is_never_upgraded():
    # engine says SKIP with a big positive edge — brief must still output SKIP.
    ev = {"action": "SKIP", "edge_pct": 25.0}
    fc = {"gfs_mean_f": 96.0, "ecmwf_mean_f": 96.2}
    b = brief.build_brief(_market(), fc, ev, debate=False)
    assert b.engine_action == "SKIP"
    assert b.recommendation == "SKIP"   # never upgraded


def test_bet_confirmed_when_confident():
    ev = {"action": "BET", "edge_pct": 20.0}        # high edge -> high conf
    fc = {"gfs_mean_f": 96.0, "ecmwf_mean_f": 96.1}  # models agree
    b = brief.build_brief(_market(), fc, ev, debate=False)
    assert b.recommendation == "BET"
    assert b.confidence >= 0.5


def test_bet_vetoed_when_low_confidence():
    # tiny edge -> confidence below 0.5 -> engine BET downgraded to SKIP (veto allowed)
    ev = {"action": "BET", "edge_pct": -5.0}
    fc = {"gfs_mean_f": 90.0, "ecmwf_mean_f": 90.0}
    b = brief.build_brief(_market(), fc, ev, debate=False)
    assert b.engine_action == "BET"
    assert b.recommendation == "SKIP"
    assert "VETO" in b.rationale


def _run():
    passed = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            print(f"  PASS {name}")
            passed += 1
    print(f"\n{passed} brief tests passed.")


if __name__ == "__main__":
    _run()
