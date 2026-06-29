"""End-to-end Gate 1 tests (CONSTITUTION §6).

Structural checks only — the live dataset is small so we never assert 'pass'.
We assert: correct shape, that perm.stat_obs > 0 matches the +EV anchor, and
that trial logging increments the registry correctly.
"""
import os
import tempfile

import pytest

from institute.evidence import gate1
from institute.corpus import registry


# ── helpers ───────────────────────────────────────────────────────────────────


def _synth_rows(n=40, q=0.2, win_rate=0.1):
    """Synthetic longshot-biased rows (mostly NO wins) for fast smoke tests."""
    import random
    rng = random.Random(0)
    rows = []
    for i in range(n):
        y = 1 if rng.random() < win_rate else 0
        rows.append({
            "q_yes": q,
            "y": y,
            "archetype": "weather-daily",
            "realized_pnl": None,
            "realized_side": None,
            "stake": 1.0,
            "market_id": f"synth_{i}",
            "t0": "2024-01-01T00:00:00Z",
            "meta": {},
        })
    return rows


# ── structure tests ───────────────────────────────────────────────────────────


def test_run_gate_returns_required_keys():
    rows = _synth_rows(40)
    result = gate1.run_gate("weather-daily", "longshot_fade", rows=rows, log=False)

    assert "verdict" in result
    assert result["verdict"] in {"pass", "insufficient", "fail"}
    assert "dsr" in result
    assert "perm" in result
    assert "sprt" in result
    assert "pbo" in result
    assert "n_bets" in result


def test_run_gate_dsr_has_required_keys():
    rows = _synth_rows(40)
    result = gate1.run_gate("weather-daily", "longshot_fade", rows=rows, log=False)
    dsr = result["dsr"]
    for key in ("sr", "sr0", "dsr", "T", "passed", "reason"):
        assert key in dsr, f"missing dsr key: {key}"


def test_run_gate_perm_stat_obs_positive_on_biased_set():
    """With 8:1 NO wins on q=0.2 longshots, longshot_fade should show +EV (stat_obs > 0)."""
    rows = _synth_rows(n=40, q=0.2, win_rate=0.1)
    result = gate1.run_gate("weather-daily", "longshot_fade", rows=rows, log=False)
    perm = result["perm"]
    assert perm["stat_obs"] > 0, (
        f"expected positive market-relative S on biased anchor, got {perm['stat_obs']}"
    )


def test_run_gate_sprt_keys():
    rows = _synth_rows(40)
    result = gate1.run_gate("weather-daily", "longshot_fade", rows=rows, log=False)
    sp = result["sprt"]
    for key in ("decision", "llr", "n_used", "p0", "p1"):
        assert key in sp, f"missing sprt key: {key}"


def test_run_gate_real_rows_structure():
    """Smoke test against actual weather data (may return 0 rows — still must not crash)."""
    result = gate1.run_gate("weather-daily", "longshot_fade", log=False)
    assert "verdict" in result
    assert result["verdict"] in {"pass", "insufficient", "fail"}


# ── trial logging ─────────────────────────────────────────────────────────────


def test_run_gate_logs_trial(tmp_path):
    """log=True must append one Trial and increment trial_count."""
    reg_path = str(tmp_path / "trials.jsonl")

    # monkeypatch REGISTRY inside gate1 module
    original = gate1.REGISTRY
    gate1.REGISTRY = reg_path
    try:
        assert registry.trial_count(reg_path) == 0
        rows = _synth_rows(40)
        gate1.run_gate("weather-daily", "longshot_fade", rows=rows, log=True)
        assert registry.trial_count(reg_path) == 1
        # second run increments
        gate1.run_gate("weather-daily", "longshot_fade", rows=rows, log=True)
        assert registry.trial_count(reg_path) == 2
    finally:
        gate1.REGISTRY = original


def test_trial_has_required_fields(tmp_path):
    reg_path = str(tmp_path / "trials.jsonl")
    original = gate1.REGISTRY
    gate1.REGISTRY = reg_path
    try:
        rows = _synth_rows(40)
        gate1.run_gate("weather-daily", "longshot_fade", rows=rows, log=True)
        trials = registry.all_trials(reg_path)
        assert len(trials) == 1
        t = trials[0]
        for field in ("id", "archetype", "strategy_id", "metrics", "verdict", "ts"):
            assert field in t, f"missing trial field: {field}"
        assert t["archetype"] == "weather-daily"
        assert t["strategy_id"] == "longshot_fade"
    finally:
        gate1.REGISTRY = original
