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


NTFY_TOPIC = "kavee-institute-x7q2m9"   # private-ish: unguessable topic name; paper
                                        # stats only, nothing sensitive travels here.


def notify_phone():
    """Push a one-line daily summary to the user's phone via ntfy.sh.

    The user subscribes to the topic in the ntfy app (iOS/Android). Free, no
    account, no credentials on disk. Failure is logged, never fatal.
    """
    import csv
    import json
    import urllib.request
    data = os.path.abspath(os.path.join(HERE, "..", "..", "..", "data", "history"))
    parts = []
    try:
        v = json.load(open(os.path.join(data, "c2_verdict.json"), encoding="utf-8"))
        tag = "VERDICT!" if (v.get("bar_pass") or v.get("deploy_killed")) else "prelim"
        parts.append(f'Kalshi test [{tag}]: {v.get("qualifying_fades", 0)}/2000 bets, '
                     f'net {v.get("mean_net_roi", 0)*100:+.2f}%')
    except Exception:
        parts.append("Kalshi test: no data")
    try:
        bets = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..",
                                            "papertrader", "data", "bets.csv"))
        rows = [r for r in csv.DictReader(open(bets, encoding="utf-8"))
                if r["status"] == "settled" and r.get("is_test", "N") != "Y"]
        if rows:
            w = sum(1 for r in rows if r["result"] == "WON")
            pnl = sum(float(r["pnl"]) for r in rows)
            staked = sum(float(r["stake"]) for r in rows)
            parts.append(f"Weather bot: {len(rows)}/50 bets, {w} wins, "
                         f"{pnl/staked*100:+.1f}% net (${pnl:+.0f})")
    except Exception:
        parts.append("Weather bot: ledger unreadable")
    msg = " | ".join(parts)
    try:
        req = urllib.request.Request(
            f"https://ntfy.sh/{NTFY_TOPIC}", data=msg.encode("utf-8"),
            headers={"Title": "Institute daily (paper)", "Tags": "chart_with_upwards_trend"})
        urllib.request.urlopen(req, timeout=20).read()
        log(f"phone notify sent: {msg}")
    except Exception as e:
        log(f"phone notify FAILED (non-fatal): {e}")


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
    notify_phone()
    log("=== scheduled fetch done ===")


if __name__ == "__main__":
    main()
