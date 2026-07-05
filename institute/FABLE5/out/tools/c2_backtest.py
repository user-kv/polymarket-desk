"""C2 — Kalshi longshot-fade backtest. PRE-REGISTERED; committed before results seen.

Pre-registration (frozen at git commit time, per ARCHITECTURE v4 sect.5; changing any
of these after results exist voids the study):
  SIGNAL        yes price <= 0.10 at decision time
  DECISION TIME close_time - 24h (last hourly candle STRICTLY before that instant)
  MIN HISTORY   >= 5 candles strictly before decision time (else no-trade)
  TRADE         buy NO at decision: NO price = 1 - yes_bid if bid known,
                else (1 - close) + SPREAD_FLOOR (0.01) haircut
  COSTS         Kalshi taker fee ceil(0.07 * C * P * (1-P)) at a $100 stake,
                P = NO price; settlement free (held to expiry)
  SUCCESS BAR   mean net ROI per bet >= +2.0% across the corpus AND every
                time-ordered fold with >=30 YES-resolving (loss) events is positive
  DEPLOY-KILL   mean net ROI < +1.0% -> C2 never deploys
  FOLDS         4 time-ordered quartiles by close_time; folds lacking 30 loss
                events are reported as UNDERPOWERED, not silently passed
  MIN CORPUS    >= 2,000 qualifying fade opportunities before any verdict is
                labeled more than PRELIMINARY (re-anchored from 10k after the
                2026-07-05 probe: candle history reaches ~Apr 2026 only)

Output: prints a report; writes institute/data/history/c2_verdict.json.
Run:    python c2_backtest.py [--threshold 0.10] (threshold override voids study)
"""
import argparse
import json
import math
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "..", "..", "data", "history"))
CANDLES = os.path.join(DATA, "prices", "kalshi_candles.jsonl")
SETTLED = os.path.join(DATA, "kalshi_settled.jsonl")
VERDICT_OUT = os.path.join(DATA, "c2_verdict.json")

STAKE = 100.0
SPREAD_FLOOR = 0.01
DECISION_LEAD_S = 24 * 3600
MIN_CANDLES = 5
YES_MAX = 0.10
MIN_LOSS_EVENTS_PER_FOLD = 30
MIN_CORPUS = 2000


def _iter_jsonl(path):
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    yield json.loads(line)
                except ValueError:
                    continue


def _parse_iso(s):
    try:
        return int(time.mktime(time.strptime(str(s)[:19] + "Z", "%Y-%m-%dT%H:%M:%SZ"))
                   - time.timezone)
    except Exception:
        return None


def kalshi_fee(contracts, p):
    return math.ceil(0.07 * contracts * p * (1.0 - p) * 100) / 100.0


def evaluate():
    results = {}          # id -> "yes"/"no"
    close_ts = {}
    for m in _iter_jsonl(SETTLED):
        r = (m.get("result") or "").lower()
        if r in ("yes", "no"):
            results[str(m.get("id"))] = r
            close_ts[str(m.get("id"))] = _parse_iso(m.get("close_time"))

    bets = []
    scanned = have_candles = 0
    for row in _iter_jsonl(CANDLES):
        scanned += 1
        mid = str(row.get("id"))
        res = results.get(mid)
        cts = close_ts.get(mid)
        candles = row.get("candles") or []
        if not candles or res is None or cts is None:
            continue
        have_candles += 1
        t_dec = cts - DECISION_LEAD_S
        prior = [c for c in candles if c[0] is not None and c[0] < t_dec
                 and c[4] is not None]
        if len(prior) < MIN_CANDLES:
            continue
        last = prior[-1]
        yes_close, yes_bid = last[4], last[5]
        if yes_close is None or yes_close > YES_MAX or yes_close <= 0:
            continue
        if yes_bid is not None and yes_bid > 0:
            no_price = 1.0 - yes_bid            # we lift what the yes-bidder offers
        else:
            no_price = (1.0 - yes_close) + SPREAD_FLOOR
        if no_price >= 1.0 or no_price <= 0.5:
            continue
        contracts = int(STAKE // no_price)
        if contracts < 1:
            continue
        cost = contracts * no_price + kalshi_fee(contracts, no_price)
        payout = contracts * 1.0 if res == "no" else 0.0
        pnl = payout - cost
        bets.append({"id": mid, "t": cts, "no_price": round(no_price, 4),
                     "won": res == "no", "roi": pnl / cost})

    bets.sort(key=lambda b: b["t"])
    n = len(bets)
    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "preregistration": "frozen at commit; see module docstring",
        "markets_scanned": scanned, "with_candles_and_result": have_candles,
        "qualifying_fades": n,
    }
    if n == 0:
        report["verdict"] = "NO_DATA"
        return report, bets
    wins = sum(1 for b in bets if b["won"])
    mean_roi = sum(b["roi"] for b in bets) / n
    folds = []
    q = max(1, n // 4)
    for i in range(4):
        part = bets[i * q:(i + 1) * q if i < 3 else n]
        if not part:
            continue
        losses = sum(1 for b in part if not b["won"])
        froi = sum(b["roi"] for b in part) / len(part)
        folds.append({"n": len(part), "loss_events": losses,
                      "mean_roi": round(froi, 4),
                      "powered": losses >= MIN_LOSS_EVENTS_PER_FOLD})
    powered = [f for f in folds if f["powered"]]
    all_powered_positive = bool(powered) and all(f["mean_roi"] > 0 for f in powered)
    report.update({
        "wins": wins, "win_rate": round(wins / n, 4),
        "mean_net_roi": round(mean_roi, 4), "folds": folds,
        "corpus_sufficient": n >= MIN_CORPUS,
        "bar_pass": mean_roi >= 0.02 and all_powered_positive and n >= MIN_CORPUS,
        "deploy_killed": (mean_roi < 0.01) and n >= MIN_CORPUS,
    })
    if n < MIN_CORPUS:
        report["verdict"] = "PRELIMINARY (corpus below pre-registered minimum)"
    elif report["bar_pass"]:
        report["verdict"] = "PASS — C2 may seed forward paper (per ARCHITECTURE sect.5)"
    elif report["deploy_killed"]:
        report["verdict"] = "KILLED — net edge < +1%; C2 never deploys"
    else:
        report["verdict"] = "BETWEEN BARS — no deploy; keep corpus growing"
    return report, bets


def main():
    global YES_MAX
    ap = argparse.ArgumentParser()
    ap.add_argument("--threshold", type=float, default=0.10,
                    help="override voids the pre-registration; report will say so")
    a = ap.parse_args()
    if a.threshold != YES_MAX:
        YES_MAX = a.threshold
    report, _ = evaluate()
    if a.threshold != 0.10:
        report["verdict"] = "EXPLORATORY (threshold overridden) — " + report.get("verdict", "")
    print(json.dumps(report, indent=2))
    with open(VERDICT_OUT, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)


if __name__ == "__main__":
    main()
