"""
desk/deploy/flow_prefect.py — Prefect wrapper for the expensive reflective loop.

Research round 4: plain cron is fine for the cheap, idempotent reactive scan, but the
expensive LLM cycle benefits from Prefect's retries, durable scheduling, and
observability — without Temporal's heavyweight server. systemd still runs the cheap
loop; this runs the reflective one.

Run a one-off:        python desk/deploy/flow_prefect.py
Serve on a schedule:  python desk/deploy/flow_prefect.py --serve   (needs `pip install prefect`)
"""
from __future__ import annotations
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:
    from prefect import flow, task
    from prefect.tasks import exponential_backoff
    HAVE_PREFECT = True
except ImportError:
    HAVE_PREFECT = False
    def flow(*a, **k):
        def deco(fn): return fn
        return deco
    def task(*a, **k):
        def deco(fn): return fn
        return deco

from desk import run_cycle


@task(retries=3, retry_delay_seconds=30) if HAVE_PREFECT else task()
def _cycle_task(use_debate: bool):
    return run_cycle.run_cycle(do_brief=True, use_debate=use_debate)


@flow(name="desk-reflective-cycle", log_prints=True)
def reflective_cycle(use_debate: bool = False):
    """One reflective cycle with retries. Fake money only; self-mod stays gated."""
    report = _cycle_task(use_debate)
    print("cycle report:", report)
    return report


if __name__ == "__main__":
    if "--serve" in sys.argv and HAVE_PREFECT:
        # daily at 14:15 UTC, matching the systemd timer cadence
        reflective_cycle.serve(name="daily-desk-cycle", cron="15 14 * * *")
    else:
        reflective_cycle()
