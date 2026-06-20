"""
lib/backtest.py — READ-ONLY backtesting for the weather paper-trader.

Two modes, neither of which touches bets.csv, bankroll.json, or places any order:

  Mode 1  run_snapshot_backtest()    — replays the scan snapshots already on disk
          (data/scans/*.json). Each snapshot captured the model probability AND the
          real market ask price at scan time, so cross-referencing with the actual
          observed high gives an honest model-vs-market-vs-reality scorecard plus a
          simulated P&L threshold sweep. This is the instant "how did my calls do?".

  Mode 2  run_historical_backtest()  — reconstructs archived ensemble forecasts over
          the past N days and compares them to the observed high, measuring the
          weather model's bias / MAE / RMSE and P10-P90 spread coverage. No market
          price is involved, so this validates the FORECAST, not the strategy.

Both render a console summary and write backtest.html.
"""

import os
import csv
import glob
import json
import math
import time
import logging
from datetime import datetime, timezone, timedelta, date

from lib import settlement, forecasts

logger = logging.getLogger("backtest")

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SCANS_DIR = os.path.join(DATA_DIR, "scans")
BACKTEST_HTML = os.path.join(BASE_DIR, "backtest.html")

# Edge thresholds (in percentage points) for the P&L sweep
THRESHOLD_SWEEP_PT = [5.0, 7.0, 10.0, 15.0]


# ──────────────────────────────────────────────────────────────────────────────
# small stats helpers
# ──────────────────────────────────────────────────────────────────────────────
def _percentile(sorted_vals, q):
    """Linear-interpolated percentile (q in 0..1) of a pre-sorted list."""
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = q * (len(sorted_vals) - 1)
    lo = int(math.floor(pos))
    hi = int(math.ceil(pos))
    if lo == hi:
        return sorted_vals[lo]
    frac = pos - lo
    return sorted_vals[lo] + (sorted_vals[hi] - sorted_vals[lo]) * frac


def _mean(vals):
    return sum(vals) / len(vals) if vals else 0.0


# ──────────────────────────────────────────────────────────────────────────────
# observed-high cache (one fetch per city+date, shared across both modes)
# ──────────────────────────────────────────────────────────────────────────────
def _make_actual_cache():
    cache = {}

    def get_actual(city_cfg, date_str):
        key = (city_cfg["name"], date_str)
        if key not in cache:
            high, source, diff = settlement.fetch_observed_high(city_cfg, date_str)
            cache[key] = high
        return cache[key]

    return get_actual


# ──────────────────────────────────────────────────────────────────────────────
# Mode 1 — snapshot replay
# ──────────────────────────────────────────────────────────────────────────────
def _load_snapshot_rows():
    """Flatten every scan snapshot into per-bucket evaluation rows."""
    rows = []
    for path in sorted(glob.glob(os.path.join(SCANS_DIR, "scan_*.json"))):
        try:
            with open(path, encoding="utf-8") as f:
                snap = json.load(f)
        except Exception as e:
            logger.warning(f"Could not read snapshot {path}: {e}")
            continue
        scan_ts = snap.get("scan_timestamp", "")
        for r in snap.get("results", []):
            m = r.get("market", {})
            ev = r.get("evaluation", {})
            ask = m.get("ask_price")
            if ask is None:
                continue
            rows.append({
                "slug": m.get("slug", ""),
                "city": m.get("city", ""),
                "question": m.get("question", ""),
                "end_date": m.get("end_date", ""),
                "bucket_low_f": m.get("bucket_low_f"),
                "bucket_high_f": m.get("bucket_high_f"),
                "is_oe_low": bool(m.get("is_open_ended_low", False)),
                "is_oe_high": bool(m.get("is_open_ended_high", False)),
                "ask_price": float(ask),
                "ensemble_prob": float(ev.get("ensemble_prob", 0.0)),
                "scan_ts": scan_ts,
            })
    return rows


def _dedupe_latest(rows):
    """
    Keep one row per market (slug): the latest scan AT OR BEFORE its end_date
    (the most-informed forecast). Records how many times it was observed.
    """
    by_slug = {}
    counts = {}
    for r in rows:
        slug = r["slug"]
        counts[slug] = counts.get(slug, 0) + 1
        end = r["end_date"]
        # only consider scans that happened before resolution
        if end and r["scan_ts"] and r["scan_ts"] > end:
            continue
        cur = by_slug.get(slug)
        if cur is None or r["scan_ts"] > cur["scan_ts"]:
            by_slug[slug] = r
    for slug, r in by_slug.items():
        r["n_observations"] = counts.get(slug, 1)
    return list(by_slug.values())


def _simulate_threshold(scored, threshold_pt, stake, fee_pct):
    """
    Simulate placing a flat-stake bet on every scored market whose edge >= threshold.
    Returns dict: bets, wins, win_rate, total_pnl, roi.
    """
    n = wins = 0
    total_pnl = 0.0
    staked = 0.0
    for s in scored:
        edge_pt = (s["ensemble_prob"] - s["ask_price"]) * 100.0
        ask = s["ask_price"]
        if edge_pt < threshold_pt or ask <= 0 or ask >= 1:
            continue
        n += 1
        staked += stake
        shares = stake / ask
        if s["won"]:
            wins += 1
            fee = shares * fee_pct
            total_pnl += shares - fee - stake
        else:
            total_pnl += -stake
    return {
        "threshold_pt": threshold_pt,
        "bets": n,
        "wins": wins,
        "win_rate": (wins / n * 100.0) if n else 0.0,
        "total_pnl": round(total_pnl, 2),
        "roi": (total_pnl / staked * 100.0) if staked else 0.0,
    }


def _calibration_bins(scored, value_key):
    """Bin a probability field into deciles; report actual YES-rate per bin."""
    bins = {}  # decile index 0..9 -> [yes, total]
    for s in scored:
        p = s[value_key]
        idx = min(int(p * 10), 9)
        e = bins.setdefault(idx, [0, 0])
        e[1] += 1
        if s["won"]:
            e[0] += 1
    out = []
    for idx in sorted(bins):
        yes, total = bins[idx]
        out.append({
            "range": f"{idx*10}-{idx*10+10}%",
            "n": total,
            "actual_pct": round(yes / total * 100.0, 1) if total else 0.0,
        })
    return out


def score_markets(cfg, get_actual=None):
    """
    Replay every scan snapshot, keep the most-informed forecast per market, and
    score each against the actual observed high. Returns a list of scored rows
    (each carries raw ensemble_prob, ask_price, won, end_date, city, lead_h).

    This is the shared scoring substrate: run_snapshot_backtest aggregates it,
    and the walk-forward harness (lib/walkforward.py) splits it out-of-sample.
    Pure read-only — never touches the ledger or places a bet. Returns
    (scored, skipped_no_actual).
    """
    city_lookup = {c["name"]: c for c in cfg["cities"]}
    if get_actual is None:
        get_actual = _make_actual_cache()

    rows = _dedupe_latest(_load_snapshot_rows())
    logger.info(f"Snapshot replay: {len(rows)} unique markets across all scans")

    scored = []
    skipped_no_actual = 0
    for r in rows:
        city_cfg = city_lookup.get(r["city"])
        if city_cfg is None:
            continue
        target_date = r["end_date"][:10]
        if not target_date:
            continue
        actual = get_actual(city_cfg, target_date)
        if actual is None:
            skipped_no_actual += 1
            continue
        won = settlement.did_bucket_win(
            actual, float(r["bucket_low_f"]), float(r["bucket_high_f"]),
            r["is_oe_low"], r["is_oe_high"],
        )
        # lead time (hours) between the chosen scan and resolution
        lead_h = None
        try:
            st = datetime.fromisoformat(r["scan_ts"].replace("Z", "+00:00"))
            en = datetime.fromisoformat(r["end_date"].replace("Z", "+00:00"))
            lead_h = round((en - st).total_seconds() / 3600.0, 1)
        except Exception:
            pass
        scored.append({**r, "actual_high_f": actual, "won": won, "lead_h": lead_h})
    return scored, skipped_no_actual


def run_snapshot_backtest(cfg):
    """Mode 1. Returns a results dict (also used to render HTML)."""
    stake = cfg.get("stake_per_bet", 5.0)
    fee_pct = cfg.get("fee_on_winnings_pct", 2.0) / 100.0

    scored, skipped_no_actual = score_markets(cfg)

    n = len(scored)
    outcomes = [1.0 if s["won"] else 0.0 for s in scored]
    brier_model = _mean([(s["ensemble_prob"] - o) ** 2 for s, o in zip(scored, outcomes)])
    brier_market = _mean([(s["ask_price"] - o) ** 2 for s, o in zip(scored, outcomes)])
    base_rate = _mean(outcomes)
    brier_base = _mean([(base_rate - o) ** 2 for o in outcomes])

    sweep = [_simulate_threshold(scored, t, stake, fee_pct) for t in THRESHOLD_SWEEP_PT]
    calibration = _calibration_bins(scored, "ensemble_prob")

    avg_lead = _mean([s["lead_h"] for s in scored if s["lead_h"] is not None])

    result = {
        "n_markets": n,
        "n_yes": int(sum(outcomes)),
        "base_rate": round(base_rate * 100.0, 1),
        "skipped_no_actual": skipped_no_actual,
        "avg_lead_h": round(avg_lead, 1),
        "brier_model": round(brier_model, 4),
        "brier_market": round(brier_market, 4),
        "brier_base": round(brier_base, 4),
        "model_beats_market": brier_model < brier_market,
        "sweep": sweep,
        "calibration": calibration,
        "markets": sorted(scored, key=lambda s: (s["city"], s["end_date"], s["bucket_low_f"])),
        "stake": stake,
    }
    return result


# ──────────────────────────────────────────────────────────────────────────────
# Mode 2 — historical model-accuracy
# ──────────────────────────────────────────────────────────────────────────────
def run_historical_backtest(cfg, days=30):
    """
    Mode 2. Returns a results dict keyed by city.

    IMPORTANT DATA LIMITATION: Open-Meteo's ensemble API is a rolling forecast
    window, not a true archive — it only retains the last ~5-6 days of ensemble
    member data. Older dates return HTTP 200 but with every member null. We
    detect that (raise inside get_historical_forecast_for_city) and stop walking
    further back for a city once we hit a few consecutive misses, rather than
    silently burning API calls on dates that can never have data. requested
    `days` is therefore a ceiling, not a guarantee — see `window_limited` in the
    returned per-city dict.
    """
    get_actual = _make_actual_cache()
    today = datetime.now(timezone.utc).date()
    # leave a 1-day buffer so the observed high is finalised
    dates = [(today - timedelta(days=d)).isoformat() for d in range(2, days + 2)]

    per_city = {}
    for city_cfg in cfg["cities"]:
        name = city_cfg["name"]
        day_rows = []
        consecutive_misses = 0
        window_limited = False
        for ds in dates:
            if consecutive_misses >= 2:
                window_limited = True
                break  # archive window exhausted for this city — stop early
            actual = get_actual(city_cfg, ds)
            if actual is None:
                continue
            try:
                fc = forecasts.get_historical_forecast_for_city(city_cfg, ds, cfg)
            except Exception as e:
                logger.warning(f"Historical forecast failed for {name} {ds}: {e}")
                consecutive_misses += 1
                continue
            consecutive_misses = 0
            time.sleep(0.4)  # pace requests so the ensemble API doesn't rate-limit
            highs = sorted(fc.get("all_highs_f", []))
            if not highs:
                continue
            mean_f = fc["combined_mean_f"]
            p10 = _percentile(highs, 0.10)
            p90 = _percentile(highs, 0.90)
            in_band = p10 <= actual <= p90
            day_rows.append({
                "date": ds,
                "forecast_mean_f": round(mean_f, 1),
                "actual_high_f": actual,
                "error_f": round(mean_f - actual, 1),
                "p10_f": round(p10, 1),
                "p90_f": round(p90, 1),
                "in_band": in_band,
                "n_members": len(highs),
            })

        if day_rows:
            errors = [r["error_f"] for r in day_rows]
            per_city[name] = {
                "n_days": len(day_rows),
                "bias_f": round(_mean(errors), 2),
                "mae_f": round(_mean([abs(e) for e in errors]), 2),
                "rmse_f": round(math.sqrt(_mean([e ** 2 for e in errors])), 2),
                "coverage_pct": round(
                    sum(1 for r in day_rows if r["in_band"]) / len(day_rows) * 100.0, 1),
                "days": sorted(day_rows, key=lambda r: r["date"], reverse=True),
                "window_limited": window_limited,
            }
        else:
            per_city[name] = {"n_days": 0, "days": [], "window_limited": window_limited}
    return {"days_requested": days, "per_city": per_city}


# ──────────────────────────────────────────────────────────────────────────────
# console rendering
# ──────────────────────────────────────────────────────────────────────────────
def print_snapshot_summary(res):
    print("\n" + "=" * 64)
    print("  SNAPSHOT BACKTEST  (model vs market vs reality — FAKE money)")
    print("=" * 64)
    print(f"  Unique markets scored : {res['n_markets']}  "
          f"({res['n_yes']} resolved YES, base rate {res['base_rate']}%)")
    if res["skipped_no_actual"]:
        print(f"  Skipped (no actual yet): {res['skipped_no_actual']}")
    print(f"  Avg forecast lead time : {res['avg_lead_h']}h before resolution")
    print("-" * 64)
    print("  Brier score (lower = more accurate):")
    print(f"    Model  : {res['brier_model']}")
    print(f"    Market : {res['brier_market']}")
    print(f"    Naive  : {res['brier_base']}  (always-predict-base-rate)")
    verdict = ("MODEL BEATS THE MARKET" if res["model_beats_market"]
               else "market is at least as accurate as the model")
    print(f"    => {verdict}")
    print("-" * 64)
    print("  Simulated P&L by edge threshold:")
    print(f"    {'thresh':>7} {'bets':>5} {'wins':>5} {'win%':>6} {'P&L($)':>9} {'ROI%':>7}")
    for s in res["sweep"]:
        print(f"    {s['threshold_pt']:>6.0f}p {s['bets']:>5} {s['wins']:>5} "
              f"{s['win_rate']:>5.0f}% {s['total_pnl']:>9.2f} {s['roi']:>6.1f}%")
    print("-" * 64)
    if res["n_markets"] < 30:
        print(f"  NOTE: only {res['n_markets']} markets — indicative, not yet")
        print("        statistically significant. Keep scanning to grow the sample.")
    print("=" * 64)


def print_historical_summary(res):
    print("\n" + "=" * 64)
    print(f"  HISTORICAL MODEL-ACCURACY BACKTEST  (requested {res['days_requested']} days)")
    print("=" * 64)
    any_limited = False
    for city, c in res["per_city"].items():
        if not c["n_days"]:
            print(f"  {city}: no data available")
            continue
        bias_dir = "warm" if c["bias_f"] > 0 else "cold"
        print(f"  {city}  ({c['n_days']} days actually available)")
        print(f"    Bias    : {c['bias_f']:+.2f}°F ({bias_dir})")
        print(f"    MAE     : {c['mae_f']}°F     RMSE: {c['rmse_f']}°F")
        print(f"    P10-P90 coverage: {c['coverage_pct']}%  (ideal ~80%)")
        any_limited = any_limited or c.get("window_limited")
    print("-" * 64)
    if any_limited:
        print("  DATA LIMIT: Open-Meteo's ensemble API is a rolling forecast window,")
        print("  not a true archive — it only retains ~5-6 days of ensemble history.")
        print("  Older dates return HTTP 200 with null data, so fewer days came back")
        print("  than requested. This is a hard ceiling on Mode 2, not a bug.")
    print("  CAVEAT: archived ensemble runs are short-lead, so this is an")
    print("          optimistic bound on true 2-day-ahead skill.")
    print("=" * 64)


# ──────────────────────────────────────────────────────────────────────────────
# HTML rendering
# ──────────────────────────────────────────────────────────────────────────────
_CSS = """
  body { font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; color:#222; }
  h1 { color: #333; } h2 { color: #555; margin-top: 30px; }
  .stats { display: flex; flex-wrap: wrap; gap: 12px; margin: 20px 0; }
  .stat { background: white; border-radius: 8px; padding: 16px 24px; box-shadow: 0 1px 3px rgba(0,0,0,.1); }
  .stat .num { font-size: 26px; font-weight: bold; color: #007bff; }
  .stat .lbl { color: #888; font-size: 12px; }
  table { border-collapse: collapse; width: 100%; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,.1); margin-bottom: 20px; }
  th { background: #007bff; color: white; padding: 8px 12px; text-align: left; font-size: 13px; }
  td { padding: 7px 12px; font-size: 12px; border-bottom: 1px solid #eee; }
  .warning { background: #fff3cd; border: 1px solid #ffc107; border-radius: 6px; padding: 10px 16px; margin: 10px 0; font-size: 13px; }
  .good { color:#1a7f37; font-weight:bold; } .bad { color:#b42318; font-weight:bold; }
"""


def _snapshot_html(res):
    if res is None:
        return ""
    verdict = ('<span class="good">Model beats the market</span>' if res["model_beats_market"]
               else '<span class="bad">Market is as accurate as the model</span>')
    sweep_rows = "".join(
        f"<tr><td>{s['threshold_pt']:.0f}pt</td><td>{s['bets']}</td><td>{s['wins']}</td>"
        f"<td>{s['win_rate']:.0f}%</td>"
        f"<td class='{'good' if s['total_pnl']>=0 else 'bad'}'>${s['total_pnl']:.2f}</td>"
        f"<td>{s['roi']:.1f}%</td></tr>"
        for s in res["sweep"]
    )
    calib_rows = "".join(
        f"<tr><td>{c['range']}</td><td>{c['n']}</td><td>{c['actual_pct']}%</td></tr>"
        for c in res["calibration"]
    ) or '<tr><td colspan="3" style="color:#888;text-align:center">Not enough data</td></tr>'

    def bucket_str(m):
        if m["is_oe_low"]:
            return f"≤{m['bucket_high_f']:.0f}°F"
        if m["is_oe_high"]:
            return f"≥{m['bucket_low_f']:.0f}°F"
        return f"{m['bucket_low_f']:.0f}–{m['bucket_high_f']:.0f}°F"

    mkt_rows = "".join(
        f"<tr style='background:{'#d4edda' if m['won'] else '#f8d7da'}'>"
        f"<td>{m['city']}</td><td>{m['end_date'][:10]}</td><td>{bucket_str(m)}</td>"
        f"<td>{m['ensemble_prob']*100:.0f}%</td><td>${m['ask_price']:.2f}</td>"
        f"<td>{(m['ensemble_prob']-m['ask_price'])*100:+.1f}pt</td>"
        f"<td>{m['actual_high_f']:.1f}°F</td>"
        f"<td>{'HIT' if m['won'] else 'MISS'}</td></tr>"
        for m in res["markets"]
    ) or '<tr><td colspan="8" style="color:#888;text-align:center">No scored markets</td></tr>'

    return f"""
<h2>Mode 1 — Snapshot Replay</h2>
<p style="font-size:12px;color:#888;">Replays the model probability + real market price captured in every past scan, scored against the actual recorded high. Avg forecast lead: {res['avg_lead_h']}h before resolution.</p>
<div class="stats">
  <div class="stat"><div class="num">{res['n_markets']}</div><div class="lbl">Markets Scored</div></div>
  <div class="stat"><div class="num">{res['base_rate']}%</div><div class="lbl">Base YES Rate</div></div>
  <div class="stat"><div class="num">{res['brier_model']}</div><div class="lbl">Model Brier (lower=better)</div></div>
  <div class="stat"><div class="num">{res['brier_market']}</div><div class="lbl">Market Brier</div></div>
</div>
<div class="warning">Accuracy verdict: {verdict}. Brier compares predicted probability to outcome — model &lt; market means the forecast carries information the price didn't.</div>

<h3>Simulated P&amp;L by Edge Threshold (flat ${res['stake']:.0f}/bet, 2% win fee)</h3>
<table>
  <tr><th>Threshold</th><th>Bets</th><th>Wins</th><th>Win %</th><th>P&amp;L</th><th>ROI</th></tr>
  {sweep_rows}
</table>

<h3>Model Calibration (did "X%" actually win X%?)</h3>
<table>
  <tr><th>Model Prob</th><th>Markets</th><th>Actual YES %</th></tr>
  {calib_rows}
</table>

<h3>Per-Market Detail</h3>
<table>
  <tr><th>City</th><th>Resolved</th><th>Bucket</th><th>Model</th><th>Ask</th><th>Edge</th><th>Actual High</th><th>Result</th></tr>
  {mkt_rows}
</table>
"""


def _historical_html(res):
    if res is None:
        return ""
    blocks = ""
    any_limited = False
    for city, c in res["per_city"].items():
        any_limited = any_limited or c.get("window_limited")
        if not c["n_days"]:
            blocks += f"<h3>{city}</h3><p style='color:#888'>No data available.</p>"
            continue
        bias_dir = "warm" if c["bias_f"] > 0 else "cold"
        day_rows = "".join(
            f"<tr style='background:{'#d4edda' if d['in_band'] else '#fff'}'>"
            f"<td>{d['date']}</td><td>{d['forecast_mean_f']}°F</td>"
            f"<td>{d['actual_high_f']}°F</td><td>{d['error_f']:+.1f}°F</td>"
            f"<td>{d['p10_f']}–{d['p90_f']}°F</td>"
            f"<td>{'✓' if d['in_band'] else '✗'}</td></tr>"
            for d in c["days"]
        )
        blocks += f"""
<h3>{city}</h3>
<div class="stats">
  <div class="stat"><div class="num">{c['bias_f']:+.2f}°F</div><div class="lbl">Bias ({bias_dir})</div></div>
  <div class="stat"><div class="num">{c['mae_f']}°F</div><div class="lbl">MAE</div></div>
  <div class="stat"><div class="num">{c['rmse_f']}°F</div><div class="lbl">RMSE</div></div>
  <div class="stat"><div class="num">{c['coverage_pct']}%</div><div class="lbl">P10–P90 Coverage (ideal ~80%)</div></div>
</div>
<table>
  <tr><th>Date</th><th>Forecast Mean</th><th>Actual High</th><th>Error</th><th>P10–P90</th><th>In Band</th></tr>
  {day_rows}
</table>
"""
    limit_note = ("""<div class="warning"><strong>Data limit:</strong> Open-Meteo's ensemble API is a rolling forecast window, not a true archive — it only retains ~5-6 days of ensemble history. Older dates return HTTP 200 with null data, so fewer days came back than requested. This is a hard ceiling on Mode 2, not a bug.</div>"""
                  if any_limited else "")
    return f"""
<h2>Mode 2 — Historical Model Accuracy (requested {res['days_requested']} days)</h2>
{limit_note}
<div class="warning">Archived ensemble runs are short-lead, so these numbers are an optimistic bound on true 2-day-ahead skill. No market price is involved — this measures the forecast, not the betting strategy.</div>
{blocks}
"""


def write_html(snapshot_res=None, historical_res=None):
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    body = _snapshot_html(snapshot_res) + _historical_html(historical_res)
    html = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>PaperTrader Backtest</title><style>{_CSS}</style></head>
<body>
<h1>PaperTrader Backtest <small style="font-size:14px;color:#888;">— FAKE MONEY ONLY —</small></h1>
<p style="color:#888;font-size:13px;">Generated: {now}. Read-only analysis — the live bankroll and ledger are untouched.</p>
{body}
</body></html>"""
    with open(BACKTEST_HTML, "w", encoding="utf-8") as f:
        f.write(html)
    logger.info(f"Backtest report written: {BACKTEST_HTML}")
    return BACKTEST_HTML
