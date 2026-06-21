"""
lib/walkforward.py — honest OUT-OF-SAMPLE evaluation for the weather trader.

The snapshot backtest (lib/backtest.py) scores every market in-sample: it uses
the whole history at once, so its calibration table and P&L flatter the model —
it has effectively "seen the answers". This module is the truth machine the
v2 roadmap (M1) calls for: a WALK-FORWARD harness that never lets a fold see its
own future.

How a fold works (expanding window, split by resolution day):
  - Order all scored markets by the day they resolved.
  - For each test day D, fit the probability calibrator (lib/prob_calibration)
    on ONLY the markets that resolved strictly before D (minus an optional
    embargo of E days, to defend against same-synoptic-regime leakage between
    adjacent days).
  - Predict the test day's markets with that calibrator. The calibrated prob for
    every test market is therefore produced by a model that never saw it.
  - Pool all such out-of-sample predictions and score them once.

What it answers, with evidence, on unseen data:
  1. Does probability calibration actually help?  (OOS Brier / log-loss / ECE,
     raw vs calibrated.)
  2. Four strategies, pooled OOS P&L:
       yes_raw          - current bot: buy YES when raw edge >= threshold
       yes_cal          - same, but on CALIBRATED probabilities
       both_cal         - allow the NO side too (buy whichever side is +EV)
       no_longshot_cal  - ONLY buy NO on cheap longshots the model says are
                          overpriced — the favorite-longshot hypothesis, isolated
     This tells us whether calibration helps the current approach, and whether
     betting the *other* side of overpriced longshots beats buy-YES — the thing
     the research said we were getting backwards.

Pure read-only — never touches bets.csv or bankroll.json. FAKE MONEY.
"""

import logging
import os
from datetime import datetime, timezone

from lib import backtest, prob_calibration as pc

_BASE_DIR = os.path.dirname(os.path.dirname(__file__))
_WALKFORWARD_HTML = os.path.join(_BASE_DIR, "walkforward.html")

logger = logging.getLogger("walkforward")

# A fold needs at least this many resolved markets in its training window before
# we trust a calibrator fitted on it; below that we skip the day (reported).
MIN_TRAIN_MARKETS = 20
LONGSHOT_MAX_ASK = 0.15  # "cheap longshot" cut for the favorite-longshot test


def _day(end_date):
    return (end_date or "")[:10]


def _simulate(rows, prob_key, stake, fee, thr,
              allow_yes=True, allow_no=True, no_longshot_max=None):
    """
    Flat-stake simulation over already-out-of-sample rows. For each row at most
    one side can qualify (YES needs q-a>=thr, NO needs a-q>=thr; mutually
    exclusive for thr>0). Buying NO at price (1-a) wins when the bucket does NOT
    happen. Returns a P&L scorecard.
    """
    n = wins = 0
    pnl = 0.0
    staked = 0.0
    for r in rows:
        q = r[prob_key]
        a = r["ask_price"]
        won = r["won"]
        if not (0.0 < a < 1.0):
            continue
        side = None
        if allow_yes and (q - a) >= thr:
            side = "yes"
        elif allow_no and (a - q) >= thr:
            if no_longshot_max is None or a <= no_longshot_max:
                side = "no"
        if side is None:
            continue
        n += 1
        staked += stake
        if side == "yes":
            shares = stake / a
            if won:
                wins += 1
                pnl += shares * (1.0 - fee) - stake
            else:
                pnl -= stake
        else:  # NO side, entry price (1 - a)
            shares = stake / (1.0 - a)
            if not won:
                wins += 1
                pnl += shares * (1.0 - fee) - stake
            else:
                pnl -= stake
    return {
        "bets": n,
        "wins": wins,
        "win_rate": round(wins / n * 100.0, 1) if n else 0.0,
        "pnl": round(pnl, 2),
        "roi": round(pnl / staked * 100.0, 1) if staked else 0.0,
    }


def run_walkforward(cfg, scored=None, n_bins=pc.DEFAULT_BINS, kappa=pc.DEFAULT_KAPPA,
                    embargo_days=0, min_train=MIN_TRAIN_MARKETS,
                    longshot_max_ask=LONGSHOT_MAX_ASK):
    """
    Returns a results dict. If `scored` is given (list of scored rows from
    backtest.score_markets), it is used directly — handy for tests; otherwise
    the snapshots are scored fresh (one network pass for actuals).
    """
    stake = cfg.get("stake_per_bet", 5.0)
    fee = cfg.get("fee_on_winnings_pct", 2.0) / 100.0
    thr = cfg.get("edge_threshold_pct", 5.0) / 100.0

    if scored is None:
        scored, _ = backtest.score_markets(cfg)

    # usable = valid market price + a resolution day
    usable = [r for r in scored if _day(r.get("end_date")) and 0.0 < r.get("ask_price", -1) < 1.0]
    usable.sort(key=lambda r: _day(r["end_date"]))
    days = sorted({_day(r["end_date"]) for r in usable})

    oos = []                 # pooled out-of-sample rows (raw_prob, cal_prob, ask, won)
    folds = []               # per-test-day bookkeeping
    skipped_days = 0
    for d in days:
        train = [r for r in usable if _day(r["end_date"]) < d
                 and (embargo_days == 0 or _days_before(_day(r["end_date"]), d) > embargo_days)]
        test = [r for r in usable if _day(r["end_date"]) == d]
        if len(train) < min_train:
            skipped_days += 1
            continue
        model = pc.fit([(r["ensemble_prob"], 1.0 if r["won"] else 0.0) for r in train],
                       n_bins=n_bins, kappa=kappa)
        for r in test:
            raw = r["ensemble_prob"]
            oos.append({
                "raw_prob": raw,
                "cal_prob": pc.apply(model, raw),
                "ask_price": r["ask_price"],
                "won": r["won"],
                "city": r.get("city", ""),
                "end_date": r["end_date"],
            })
        folds.append({"day": d, "n_train": len(train), "n_test": len(test)})

    out = {
        "n_scored": len(scored),
        "n_usable": len(usable),
        "n_days": len(days),
        "n_folds": len(folds),
        "skipped_days": skipped_days,
        "n_oos": len(oos),
        "min_train": min_train,
        "embargo_days": embargo_days,
        "folds": folds,
    }
    if not oos:
        out["insufficient"] = True
        return out

    raw_probs = [r["raw_prob"] for r in oos]
    cal_probs = [r["cal_prob"] for r in oos]
    outcomes = [1.0 if r["won"] else 0.0 for r in oos]

    out["metrics"] = {
        "brier_raw": round(pc.brier(raw_probs, outcomes), 4),
        "brier_cal": round(pc.brier(cal_probs, outcomes), 4),
        "logloss_raw": round(pc.log_loss(raw_probs, outcomes), 4),
        "logloss_cal": round(pc.log_loss(cal_probs, outcomes), 4),
        "ece_raw": round(pc.expected_calibration_error(raw_probs, outcomes, n_bins), 4),
        "ece_cal": round(pc.expected_calibration_error(cal_probs, outcomes, n_bins), 4),
        "base_rate_pct": round(sum(outcomes) / len(outcomes) * 100.0, 1),
    }
    out["metrics"]["calibration_helps"] = out["metrics"]["brier_cal"] < out["metrics"]["brier_raw"]

    out["strategies"] = {
        "yes_raw": _simulate(oos, "raw_prob", stake, fee, thr, allow_no=False),
        "yes_cal": _simulate(oos, "cal_prob", stake, fee, thr, allow_no=False),
        "both_raw": _simulate(oos, "raw_prob", stake, fee, thr),
        "both_cal": _simulate(oos, "cal_prob", stake, fee, thr),
        "no_longshot_raw": _simulate(oos, "raw_prob", stake, fee, thr,
                                     allow_yes=False, no_longshot_max=longshot_max_ask),
        "no_longshot_cal": _simulate(oos, "cal_prob", stake, fee, thr,
                                     allow_yes=False, no_longshot_max=longshot_max_ask),
        # NO-only with NO ask cap — measures what the ask<=longshot_max cap costs
        # vs no_longshot_raw (same but capped). Decision input for tuning the cap;
        # NOT a deployed strategy.
        "no_raw": _simulate(oos, "raw_prob", stake, fee, thr,
                            allow_yes=False, no_longshot_max=None),
    }
    out["reliability_raw"] = pc.reliability_table(list(zip(raw_probs, outcomes)), n_bins=n_bins)
    out["stake"] = stake
    return out


def _days_before(d_earlier, d_later):
    """Whole days between two YYYY-MM-DD strings (d_later - d_earlier)."""
    a = datetime.strptime(d_earlier, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    b = datetime.strptime(d_later, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    return (b - a).days


# ──────────────────────────────────────────────────────────────────────────────
# console rendering
# ──────────────────────────────────────────────────────────────────────────────
def print_summary(res):
    print("\n" + "=" * 68)
    print("  WALK-FORWARD BACKTEST  (out-of-sample — FAKE money)")
    print("=" * 68)
    print(f"  Scored markets        : {res['n_scored']}  (usable: {res['n_usable']})")
    print(f"  Resolution days       : {res['n_days']}  -> {res['n_folds']} test folds "
          f"({res['skipped_days']} skipped: < {res['min_train']} train markets)")
    print(f"  Out-of-sample markets : {res['n_oos']}")
    if res.get("insufficient"):
        print("-" * 68)
        print("  NOT ENOUGH DATA YET for an out-of-sample fold. Need more resolution")
        print(f"  days each with >= {res['min_train']} prior scored markets. Keep scanning.")
        print("=" * 68)
        return
    m = res["metrics"]
    print(f"  Base YES rate         : {m['base_rate_pct']}%")
    print("-" * 68)
    print("  Probability accuracy (OUT-OF-SAMPLE, lower = better):")
    print(f"    {'':14}{'raw':>10}{'calibrated':>14}")
    print(f"    {'Brier':14}{m['brier_raw']:>10}{m['brier_cal']:>14}")
    print(f"    {'Log-loss':14}{m['logloss_raw']:>10}{m['logloss_cal']:>14}")
    print(f"    {'ECE':14}{m['ece_raw']:>10}{m['ece_cal']:>14}")
    print(f"    => calibration {'HELPS' if m['calibration_helps'] else 'does NOT help'} out-of-sample")
    print("-" * 68)
    print(f"  Strategy P&L (pooled OOS, flat ${res['stake']:.0f}/bet, {res.get('embargo_days',0)}d embargo):")
    print(f"    {'strategy':18}{'bets':>5}{'win%':>7}{'P&L$':>10}{'ROI%':>8}")
    labels = {
        "yes_raw": "yes_raw (current)",
        "yes_cal": "yes_cal",
        "both_raw": "both_raw",
        "both_cal": "both_cal",
        "no_longshot_raw": "no_longshot_raw (LIVE)",
        "no_longshot_cal": "no_longshot_cal",
        "no_raw": "no_raw (uncapped)",
    }
    for key in ("yes_raw", "yes_cal", "both_raw", "both_cal", "no_longshot_raw", "no_longshot_cal", "no_raw"):
        s = res["strategies"][key]
        print(f"    {labels[key]:18}{s['bets']:>5}{s['win_rate']:>6.0f}%"
              f"{s['pnl']:>10.2f}{s['roi']:>7.1f}%")
    print("-" * 68)
    if res["n_oos"] < 30:
        print(f"  NOTE: only {res['n_oos']} OOS markets — directional, not yet significant.")
    print("=" * 68)


# ──────────────────────────────────────────────────────────────────────────────
# HTML report
# ──────────────────────────────────────────────────────────────────────────────
def write_html(res):
    from lib.backtest import _CSS  # reuse styling
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if res.get("insufficient"):
        body = f"""
<div class="warning">Not enough data yet for an out-of-sample fold.
Need at least {res['min_train']} resolved markets in the training window.
Keep scanning — more resolution days will unlock this report.</div>"""
    else:
        m = res["metrics"]
        cal_verdict = ("HELPS" if m["calibration_helps"] else "does NOT help")
        cal_cls = "good" if m["calibration_helps"] else "bad"

        metric_rows = "".join(
            f"<tr><td>{name}</td><td>{m[raw_k]}</td><td>{m[cal_k]}</td></tr>"
            for name, raw_k, cal_k in [
                ("Brier (lower = better)", "brier_raw", "brier_cal"),
                ("Log-loss (lower = better)", "logloss_raw", "logloss_cal"),
                ("ECE (lower = better)", "ece_raw", "ece_cal"),
            ]
        )

        strat_rows = ""
        labels = {
            "yes_raw": "yes_raw (current bot)",
            "yes_cal": "yes_cal",
            "both_raw": "both_raw",
            "both_cal": "both_cal",
            "no_longshot_raw": "no_longshot_raw (LIVE — deployed path)",
            "no_longshot_cal": "no_longshot_cal",
            "no_raw": "no_raw (uncapped, not deployed)",
        }
        for key in ("yes_raw", "yes_cal", "both_raw", "both_cal", "no_longshot_raw", "no_longshot_cal", "no_raw"):
            s = res["strategies"][key]
            pnl_cls = "good" if s["pnl"] >= 0 else "bad"
            strat_rows += (
                f"<tr><td>{labels[key]}</td><td>{s['bets']}</td>"
                f"<td>{s['win_rate']:.0f}%</td>"
                f"<td class='{pnl_cls}'>${s['pnl']:.2f}</td>"
                f"<td>{s['roi']:.1f}%</td></tr>"
            )

        fold_rows = "".join(
            f"<tr><td>{f['day']}</td><td>{f['n_train']}</td><td>{f['n_test']}</td></tr>"
            for f in res["folds"]
        )

        small_sample = (
            f'<div class="warning">Only {res["n_oos"]} OOS markets — '
            f'directional signal, not yet statistically significant.</div>'
            if res["n_oos"] < 30 else ""
        )

        body = f"""
<div class="stats">
  <div class="stat"><div class="num">{res['n_scored']}</div><div class="lbl">Markets Scored</div></div>
  <div class="stat"><div class="num">{res['n_oos']}</div><div class="lbl">OOS Markets</div></div>
  <div class="stat"><div class="num">{res['n_folds']}</div><div class="lbl">Test Folds</div></div>
  <div class="stat"><div class="num">{res['skipped_days']}</div><div class="lbl">Folds Skipped (&lt;{res['min_train']} train)</div></div>
  <div class="stat"><div class="num">{m['base_rate_pct']}%</div><div class="lbl">Base YES Rate</div></div>
</div>
{small_sample}
<h2>Probability Accuracy (out-of-sample)</h2>
<div class="warning">Calibration <span class="{cal_cls}">{cal_verdict}</span> out-of-sample (Brier: raw {m['brier_raw']} → calibrated {m['brier_cal']}). Embargo: {res['embargo_days']}d.</div>
<table>
  <tr><th>Metric</th><th>Raw</th><th>Calibrated</th></tr>
  {metric_rows}
</table>

<h2>Strategy P&amp;L (pooled OOS, flat ${res['stake']:.0f}/bet)</h2>
<table>
  <tr><th>Strategy</th><th>Bets</th><th>Win%</th><th>P&amp;L</th><th>ROI</th></tr>
  {strat_rows}
</table>

<h2>Fold Detail</h2>
<table>
  <tr><th>Test Day</th><th>Train Markets</th><th>Test Markets</th></tr>
  {fold_rows}
</table>"""

    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>PaperTrader Walk-Forward Backtest</title><style>{_CSS}</style></head>
<body>
<h1>Walk-Forward Backtest <small style="font-size:14px;color:#888;">— FAKE MONEY / OUT-OF-SAMPLE —</small></h1>
<p style="color:#888;font-size:13px;">Generated: {now}. Read-only — live bankroll and ledger untouched.</p>
{body}
</body></html>"""

    with open(_WALKFORWARD_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    logger.info(f"Walk-forward report written: {_WALKFORWARD_HTML}")
    return _WALKFORWARD_HTML
