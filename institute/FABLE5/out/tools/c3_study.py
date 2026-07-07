"""C3 — Polymarket favorite-longshot behavioral-bias study. PRE-REGISTERED;
committed before results seen. Companion to C2 (Kalshi longshot-fade backtest);
same discipline applies — changing any of these after results exist voids the
study.

Pre-registration (frozen at git commit time, per ARCHITECTURE v4 sect.5):
  DECISION TIME     close_time - 24h. Decision price = last trade STRICTLY
                    before that instant; require >=5 trades strictly before it
                    AND n_trades >= 10 for the market to qualify at all.
  BUCKET B1         "longshot_fade": decision yes_price <= 0.10 -> buy NO at
                    (1 - yes_price) + 0.02 adverse-fill haircut.
  BUCKET B2         "favorite_buy": decision yes_price >= 0.70 -> buy YES at
                    yes_price + 0.02 adverse-fill haircut.
  BUCKET B3         "horizon_compression" — DROPPED as untestable on
                    trades-only data (no clean point-in-time horizon
                    snapshot exists in this corpus; see report field
                    b3_dropped_reason).
  FEES              regime-aware, conservative. Per-share fee formula:
                    fee = 0.05 * p * (1 - p), p = fill price of the share
                    bought (worst-case category coefficient: econ/culture/
                    weather at $1.25 per 100 shares at p=0.50 -> 0.05*0.5*0.5
                    = 0.0125/share * 100 = $1.25, matches).
                    (a) historical-actual: fee = 0 if start_date is before
                        2026-03-30 (Polymarket fee go-live), else the formula
                        above.
                    (b) forward-basis: fee always on (the formula above,
                        unconditionally). THE VERDICT USES FORWARD-BASIS.
  STAKE             $100 per bet. shares = STAKE / fill_price. cost =
                    STAKE + shares * fee_per_share. Win: payout =
                    shares * $1. pnl = payout - cost (win) or -cost (loss).
                    ROI per bet = pnl / cost.
  SUCCESS BAR       per bucket: mean forward-basis net ROI > 0 AND its 97.5%
                    CI (normal approx, Bonferroni x2 correction for two
                    buckets -> z = 2.24) excludes 0, with n >= 500 in the
                    bucket. Below 500 -> verdict UNDERPOWERED for that bucket.
  FOLDS             4 time-ordered quartiles by decision time, per bucket.
                    powered = >= 30 LOSS events (bets that lost) in the fold;
                    folds below that are reported UNDERPOWERED, not silently
                    passed.

Output: prints a report; writes institute/data/history/c3_verdict.json.
Run:    python c3_study.py (no args; a threshold override would void the
        pre-registration, so none is exposed).
"""
import calendar
import json
import math
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.abspath(os.path.join(HERE, "..", "..", "..", "data", "history"))
TRADES = os.path.join(DATA, "prices", "polymarket_trades.jsonl")
RESOLVED_A = os.path.join(DATA, "polymarket_resolved.jsonl")
RESOLVED_B = os.path.join(DATA, "polymarket_clob_resolved.jsonl")
VERDICT_OUT = os.path.join(DATA, "c3_verdict.json")

STAKE = 100.0
HAIRCUT = 0.02
DECISION_LEAD_S = 24 * 3600
MIN_TRADES_PRIOR = 5
MIN_N_TRADES = 10
B1_MAX = 0.10
B2_MIN = 0.70
# calendar.timegm, not mktime-timezone: the latter assumes local STANDARD time,
# so under DST every parsed timestamp shifted by 3600s depending on run date —
# a reproducibility hole in a frozen protocol (2026-07-07 fix; thresholds untouched).
FEE_CUTOVER_TS = int(calendar.timegm(time.strptime("2026-03-30T00:00:00Z", "%Y-%m-%dT%H:%M:%SZ")))
MIN_LOSS_EVENTS_PER_FOLD = 30
MIN_BUCKET_N = 500
Z_BONFERRONI = 2.24  # 97.5th percentile, Bonferroni x2 for two buckets

B3_DROPPED_REASON = (
    "horizon_compression requires a point-in-time snapshot of the market's "
    "remaining horizon (time-to-close) paired with a probability estimate at "
    "that instant, independent of trade activity. The trades-only corpus "
    "(polymarket_trades.jsonl) has no such snapshot -- only trade events -- "
    "so any horizon-compression signal built from it would be conflated with "
    "trade-timing/liquidity effects. Untestable on this data; dropped rather "
    "than approximated."
)


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
    if not s:
        return None
    try:
        return int(calendar.timegm(time.strptime(str(s)[:19] + "Z", "%Y-%m-%dT%H:%M:%SZ")))
    except Exception:
        return None


def _double_parse(v):
    """outcomes/outcome_prices are JSON-encoded strings; parse twice."""
    if v is None:
        return None
    if isinstance(v, list):
        return v
    try:
        parsed = json.loads(v)
    except (ValueError, TypeError):
        return None
    if isinstance(parsed, str):
        try:
            parsed = json.loads(parsed)
        except (ValueError, TypeError):
            return None
    return parsed if isinstance(parsed, list) else None


def load_market_meta(paths):
    """condition_id -> {"close_ts": int, "start_ts": int|None}"""
    meta = {}
    for path in paths:
        for row in _iter_jsonl(path):
            cid = row.get("condition_id") or row.get("id")
            if not cid:
                continue
            cid = str(cid)
            close_ts = _parse_iso(row.get("closed_time")) or _parse_iso(row.get("end_date"))
            if close_ts is None:
                continue
            start_ts = _parse_iso(row.get("start_date"))
            if cid not in meta:
                meta[cid] = {"close_ts": close_ts, "start_ts": start_ts}
    return meta


def fee_per_share(p):
    return 0.05 * p * (1.0 - p)


def resolve_outcome(outcome_prices):
    """Return True if YES won, False if NO won, None if non-binary/unclear."""
    if not outcome_prices or len(outcome_prices) != 2:
        return None
    try:
        a, b = float(outcome_prices[0]), float(outcome_prices[1])
    except (TypeError, ValueError):
        return None
    if a == 1.0 and b == 0.0:
        return True
    if a == 0.0 and b == 1.0:
        return False
    return None


def evaluate_bet(fill_price, stake, start_ts, close_ts):
    """Given fill price and stake, compute both fee regimes' cost/roi denominator
    components. Returns dict with keys: cost_forward, cost_historical, shares.
    Actual pnl/roi filled in by caller once win/loss is known."""
    shares = stake / fill_price
    fee_fwd = shares * fee_per_share(fill_price)
    charge_historical = (start_ts is None) or (start_ts >= FEE_CUTOVER_TS)
    fee_hist = fee_fwd if charge_historical else 0.0
    return {
        "shares": shares,
        "cost_forward": stake + fee_fwd,
        "cost_historical": stake + fee_hist,
    }


def evaluate():
    meta = load_market_meta([RESOLVED_A, RESOLVED_B])

    buckets = {"B1_longshot_fade": [], "B2_favorite_buy": []}
    scanned = 0
    usable = 0

    for row in _iter_jsonl(TRADES):
        scanned += 1
        cid = row.get("condition_id") or row.get("id")
        if not cid:
            continue
        cid = str(cid)
        m = meta.get(cid)
        if m is None:
            continue
        outcome_prices = _double_parse(row.get("outcome_prices"))
        won_yes = resolve_outcome(outcome_prices)
        if won_yes is None:
            continue
        n_trades_field = row.get("n_trades")
        try:
            n_trades_field = int(n_trades_field)
        except (TypeError, ValueError):
            n_trades_field = 0
        if n_trades_field < MIN_N_TRADES:
            continue
        points = row.get("points") or []
        points = sorted(
            [p for p in points if isinstance(p, (list, tuple)) and len(p) >= 2
             and p[0] is not None and p[1] is not None],
            key=lambda p: p[0],
        )
        if not points:
            continue

        close_ts = m["close_ts"]
        start_ts = m["start_ts"]
        t_dec = close_ts - DECISION_LEAD_S
        prior = [p for p in points if p[0] < t_dec]
        if len(prior) < MIN_TRADES_PRIOR:
            continue
        usable += 1

        yes_price = float(prior[-1][1])
        if yes_price <= 0.0 or yes_price >= 1.0:
            continue

        bucket = None
        fill_price = None
        won_bet = None
        if yes_price <= B1_MAX:
            bucket = "B1_longshot_fade"
            fill_price = (1.0 - yes_price) + HAIRCUT
            won_bet = (won_yes is False)
        elif yes_price >= B2_MIN:
            bucket = "B2_favorite_buy"
            fill_price = yes_price + HAIRCUT
            won_bet = (won_yes is True)
        else:
            continue

        if fill_price is None or fill_price <= 0.0 or fill_price >= 1.0:
            continue

        calc = evaluate_bet(fill_price, STAKE, start_ts, close_ts)
        shares = calc["shares"]
        cost_fwd = calc["cost_forward"]
        cost_hist = calc["cost_historical"]
        payout = shares * 1.0 if won_bet else 0.0
        pnl_fwd = payout - cost_fwd
        pnl_hist = payout - cost_hist

        buckets[bucket].append({
            "cid": cid,
            "t": t_dec,
            "won": won_bet,
            "fill_price": round(fill_price, 4),
            "roi_forward": pnl_fwd / cost_fwd,
            "roi_historical": pnl_hist / cost_hist,
        })

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "preregistration": "frozen at commit; see module docstring",
        "markets_scanned": scanned,
        "markets_usable_decision_point": usable,
        "b3_horizon_compression": "DROPPED",
        "b3_dropped_reason": B3_DROPPED_REASON,
        "buckets": {},
    }

    for name, bets in buckets.items():
        bets.sort(key=lambda b: b["t"])
        n = len(bets)
        bucket_report = {"n": n}
        if n == 0:
            bucket_report["verdict"] = "NO_DATA"
            report["buckets"][name] = bucket_report
            continue

        wins = sum(1 for b in bets if b["won"])
        rois_fwd = [b["roi_forward"] for b in bets]
        rois_hist = [b["roi_historical"] for b in bets]
        mean_fwd = sum(rois_fwd) / n
        mean_hist = sum(rois_hist) / n

        if n > 1:
            var_fwd = sum((r - mean_fwd) ** 2 for r in rois_fwd) / (n - 1)
            sem_fwd = math.sqrt(var_fwd / n)
        else:
            sem_fwd = 0.0
        ci_lo = mean_fwd - Z_BONFERRONI * sem_fwd
        ci_hi = mean_fwd + Z_BONFERRONI * sem_fwd

        folds = []
        q = max(1, n // 4)
        for i in range(4):
            part = bets[i * q:(i + 1) * q if i < 3 else n]
            if not part:
                continue
            losses = sum(1 for b in part if not b["won"])
            fmean = sum(b["roi_forward"] for b in part) / len(part)
            folds.append({
                "n": len(part),
                "loss_events": losses,
                "mean_roi_forward": round(fmean, 4),
                "powered": losses >= MIN_LOSS_EVENTS_PER_FOLD,
            })

        underpowered = n < MIN_BUCKET_N
        ci_excludes_zero = (ci_lo > 0) or (ci_hi < 0)
        bar_pass = (not underpowered) and (mean_fwd > 0) and ci_excludes_zero

        if underpowered:
            verdict = "UNDERPOWERED (n < {})".format(MIN_BUCKET_N)
        elif bar_pass:
            verdict = "PASS — net edge positive, CI excludes zero"
        elif mean_fwd > 0:
            verdict = "BETWEEN BARS — positive mean but CI includes zero"
        else:
            verdict = "FAIL — mean forward-basis net ROI <= 0"

        bucket_report.update({
            "win_rate": round(wins / n, 4),
            "mean_net_roi_forward": round(mean_fwd, 6),
            "mean_net_roi_historical": round(mean_hist, 6),
            "ci95_lo": round(ci_lo, 6),
            "ci95_hi": round(ci_hi, 6),
            "z_bonferroni": Z_BONFERRONI,
            "folds": folds,
            "verdict": verdict,
        })
        report["buckets"][name] = bucket_report

    return report


def main():
    report = evaluate()
    print(json.dumps(report, indent=2))
    tmp = VERDICT_OUT + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    os.replace(tmp, VERDICT_OUT)  # atomic: a truncated verdict reads as "no data"


# --------------------------------------------------------------------------- #
# Self-test: synthetic smoke test only. Does NOT touch real data. Asserts the
# core semantics called out in the pre-registration: strictly-before decision
# time, double-parse of outcome_prices, fee-regime switch, bucket assignment.
# --------------------------------------------------------------------------- #
def _selftest():
    import tempfile

    tmp = tempfile.mkdtemp(prefix="c3_selftest_")
    trades_path = os.path.join(tmp, "trades.jsonl")
    resolved_path = os.path.join(tmp, "resolved.jsonl")

    closed_time_str = "2027-01-15T00:00:00Z"
    close_ts = _parse_iso(closed_time_str)
    t_dec = close_ts - DECISION_LEAD_S

    def ts(offset_s):
        return t_dec + offset_s

    rows = [
        # B1 candidate: longshot fade, YES loses (NO wins) -> win for NO bet.
        # last trade strictly before t_dec has yes_price 0.05.
        # fee cutover: start_date before 2026-03-30 -> historical fee = 0.
        {
            "id": "m1", "condition_id": "cid1", "question": "m1",
            "outcomes": json.dumps(json.dumps(["Yes", "No"])),
            "outcome_prices": json.dumps(json.dumps(["0", "1"])),  # NO won
            "n_trades": 12,
            "points": [
                [ts(-500), 0.06, 10], [ts(-400), 0.05, 10], [ts(-300), 0.05, 5],
                [ts(-200), 0.05, 5], [ts(-100), 0.05, 5],
                [ts(1), 0.99, 5],  # AFTER decision time -- must be excluded
            ],
        },
        # B2 candidate: favorite buy, YES wins -> win for YES bet.
        # start_date after cutover -> historical fee charged (same as forward).
        {
            "id": "m2", "condition_id": "cid2", "question": "m2",
            "outcomes": json.dumps(json.dumps(["Yes", "No"])),
            "outcome_prices": json.dumps(json.dumps(["1", "0"])),  # YES won
            "n_trades": 15,
            "points": [
                [ts(-500), 0.80, 10], [ts(-400), 0.81, 10], [ts(-300), 0.82, 5],
                [ts(-200), 0.83, 5], [ts(-100), 0.85, 5],
            ],
        },
        # Not enough prior trades -> must be skipped.
        {
            "id": "m3", "condition_id": "cid3", "question": "m3",
            "outcomes": json.dumps(json.dumps(["Yes", "No"])),
            "outcome_prices": json.dumps(json.dumps(["1", "0"])),
            "n_trades": 12,
            "points": [[ts(-100), 0.05, 5], [ts(-50), 0.05, 5]],
        },
        # Non-binary resolution -> must be skipped.
        {
            "id": "m4", "condition_id": "cid4", "question": "m4",
            "outcomes": json.dumps(json.dumps(["A", "B", "C"])),
            "outcome_prices": json.dumps(json.dumps(["0.3", "0.3", "0.4"])),
            "n_trades": 12,
            "points": [
                [ts(-500), 0.05, 10], [ts(-400), 0.05, 10], [ts(-300), 0.05, 5],
                [ts(-200), 0.05, 5], [ts(-100), 0.05, 5],
            ],
        },
    ]
    with open(trades_path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r) + "\n")

    resolved_rows = [
        {"condition_id": "cid1", "closed_time": closed_time_str,
         "start_date": "2026-01-01T00:00:00Z"},  # pre-cutover -> historical fee=0
        {"condition_id": "cid2", "closed_time": closed_time_str,
         "start_date": "2026-06-01T00:00:00Z"},  # post-cutover -> historical fee on
        {"condition_id": "cid3", "closed_time": closed_time_str,
         "start_date": "2026-01-01T00:00:00Z"},
        {"condition_id": "cid4", "closed_time": closed_time_str,
         "start_date": "2026-01-01T00:00:00Z"},
    ]
    with open(resolved_path, "w", encoding="utf-8") as f:
        for r in resolved_rows:
            f.write(json.dumps(r) + "\n")

    global TRADES, RESOLVED_A, RESOLVED_B
    TRADES, RESOLVED_A, RESOLVED_B = trades_path, resolved_path, resolved_path + ".missing"

    report = evaluate()

    assert report["markets_scanned"] == 4, report
    # only cid1 and cid2 qualify (>=5 prior trades, n_trades>=10, binary resolution)
    assert report["markets_usable_decision_point"] == 2, report

    b1 = report["buckets"]["B1_longshot_fade"]
    b2 = report["buckets"]["B2_favorite_buy"]
    assert b1["n"] == 1, b1
    assert b2["n"] == 1, b2

    # strictly-before semantics: decision yes_price for m1 must be 0.05 (last
    # prior trade), NOT 0.99 (the point after t_dec). If the later trade leaked
    # in, yes_price would exceed B1_MAX and the bucket would be empty.
    assert b1["n"] == 1, "strictly-before-decision-time filter failed"

    # double-parse + bucket assignment: cid1 resolved NO -> NO-bet wins.
    assert b1["win_rate"] == 1.0, b1

    # fee-regime switch: cid1 pre-cutover -> historical roi should differ from
    # (equal or better than) forward roi since historical fee is zero there.
    assert b1["mean_net_roi_historical"] >= b1["mean_net_roi_forward"], b1

    # cid2 post-cutover -> historical fee == forward fee -> rois should match.
    assert abs(b2["mean_net_roi_historical"] - b2["mean_net_roi_forward"]) < 1e-9, b2

    # underpowered verdict fires below MIN_BUCKET_N (500) with n=1.
    assert b1["verdict"].startswith("UNDERPOWERED"), b1
    assert b2["verdict"].startswith("UNDERPOWERED"), b2

    print("SELFTEST OK")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
    else:
        main()
