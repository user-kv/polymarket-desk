"""Scheduled incremental fetch + dashboard refresh.

Designed to run unattended (Windows Task Scheduler, daily). Both fetchers are
append-only and resumable, so a fixed per-run budget steadily grows coverage:
newly-settled markets are picked up first on each pass through the settled store.

Timing rationale: most Kalshi daily markets settle around midnight-2am ET
(= ~14:00-16:00 AEST). A ~16:30 local run captures each day's fresh settlements
while their candle history is warm.

Run:  python scheduled_fetch.py [--kalshi-max N] [--poly-max N]
Logs: institute/data/history/scheduled_fetch.log
"""
import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.abspath(os.path.join(HERE, "..", "..", "..", "data", "history",
                                   "scheduled_fetch.log"))


def log(msg):
    line = f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}"
    print(line)
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def run(args_list):
    p = subprocess.run([sys.executable] + args_list, cwd=HERE,
                       capture_output=True, text=True, timeout=3 * 3600)
    tail = (p.stdout or "").strip().splitlines()[-3:]
    log(f"exit={p.returncode} cmd={' '.join(args_list)} | " + " / ".join(tail))
    if p.returncode != 0:
        log("stderr: " + (p.stderr or "").strip()[-400:])
    return p.returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--kalshi-max", type=int, default=2000)
    ap.add_argument("--poly-max", type=int, default=200)
    a = ap.parse_args()
    log("=== scheduled fetch start ===")
    run(["fetch_prices_v2.py", "--venue", "kalshi", "--max", str(a.kalshi_max),
         "--interval", "60"])
    run(["fetch_prices_v2.py", "--venue", "polymarket", "--max", str(a.poly_max)])
    run(["c2_backtest.py"])          # pre-registered; re-runs as the corpus grows
    run(["gen_dashboard.py"])
    log("=== scheduled fetch done ===")


if __name__ == "__main__":
    main()
