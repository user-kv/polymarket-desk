"""Generate the Institute dashboard (static, self-contained HTML).

Reads the gitignored data stores, appends a snapshot row to
data/history/dashboard_runs.jsonl (so growth sparklines accrue run over run),
and writes institute/FABLE5/out/dashboard/index.html with all data inlined
(no fetch/CORS — openable from file://).

Run:  python gen_dashboard.py
"""
import json
import os
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))       # institute/
DATA = os.path.join(ROOT, "data", "history")
MANIFEST = os.path.join(DATA, "manifest.json")
KALSHI_SETTLED = os.path.join(DATA, "kalshi_settled.jsonl")
KALSHI_CANDLES = os.path.join(DATA, "prices", "kalshi_candles.jsonl")
POLY_TRADES = os.path.join(DATA, "prices", "polymarket_trades.jsonl")
RUNS_LOG = os.path.join(DATA, "dashboard_runs.jsonl")
OUT_HTML = os.path.join(HERE, "..", "dashboard", "index.html")


def _iter_jsonl(path):
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except ValueError:
                continue


def collect():
    stats = {"generated_at": time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())}

    manifest = {}
    if os.path.exists(MANIFEST):
        try:
            manifest = json.load(open(MANIFEST, encoding="utf-8"))
        except ValueError:
            manifest = {}
    stats["manifest"] = manifest

    # Kalshi settled: category per market id (for joining candles -> category)
    cat_by_id = {}
    kalshi_total = 0
    for r in _iter_jsonl(KALSHI_SETTLED):
        kalshi_total += 1
        cat_by_id[str(r.get("id"))] = (r.get("category") or "unknown").lower()
    stats["kalshi_settled_total"] = kalshi_total

    # Kalshi candles store
    cand_markets = 0
    cand_rows = 0
    with_bidask = 0
    with_any_candle = 0
    per_cat = {}
    for r in _iter_jsonl(KALSHI_CANDLES):
        cand_markets += 1
        candles = r.get("candles") or []
        cand_rows += len(candles)
        if candles:
            with_any_candle += 1
            if any(c[5] is not None or c[6] is not None for c in candles):
                with_bidask += 1
        cat = cat_by_id.get(str(r.get("id")), "unknown")
        per_cat[cat] = per_cat.get(cat, 0) + 1
    stats["kalshi_candles"] = {
        "markets": cand_markets, "candle_rows": cand_rows,
        "with_any_candle": with_any_candle, "with_bidask": with_bidask,
        "per_category": dict(sorted(per_cat.items(), key=lambda kv: -kv[1])[:10]),
    }

    # Polymarket trades store
    pm_markets = 0
    pm_usable = 0
    pm_points = 0
    for r in _iter_jsonl(POLY_TRADES):
        pm_markets += 1
        n = r.get("n_trades") or 0
        pm_points += n
        if n >= 10:
            pm_usable += 1
    stats["poly"] = {"markets": pm_markets, "usable": pm_usable, "points": pm_points}

    # Run history (append this snapshot, then load all for the sparkline)
    snap = {
        "ts": int(time.time()),
        "kalshi_candle_markets": cand_markets,
        "kalshi_candle_rows": cand_rows,
        "poly_markets": pm_markets,
        "poly_usable": pm_usable,
    }
    os.makedirs(os.path.dirname(RUNS_LOG), exist_ok=True)
    with open(RUNS_LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(snap) + "\n")
    stats["runs"] = list(_iter_jsonl(RUNS_LOG))[-60:]
    return stats


def _c2_cell():
    p = os.path.join(DATA, "c2_verdict.json")
    if not os.path.exists(p):
        return "warning", "Awaiting candle corpus; +2% net-after-costs bar"
    try:
        v = json.load(open(p, encoding="utf-8"))
    except ValueError:
        return "warning", "verdict file unreadable"
    note = (f'{v.get("qualifying_fades", 0)} fades, win {v.get("win_rate", 0)*100:.1f}%, '
            f'net ROI {v.get("mean_net_roi", 0)*100:+.2f}% — {v.get("verdict", "?")}')
    if v.get("bar_pass"):
        return "good", note
    if v.get("deploy_killed"):
        return "critical", note
    return "warning", note


def _c1_cell():
    """Live net-of-fee record from the papertrader ledger (fees already in pnl)."""
    import csv
    bets = os.path.join(os.path.dirname(ROOT), "papertrader", "data", "bets.csv")
    try:
        rows = [r for r in csv.DictReader(open(bets, encoding="utf-8"))
                if r["status"] == "settled" and r.get("is_test", "N") != "Y"]
        w = sum(1 for r in rows if r["result"] == "WON")
        staked = sum(float(r["stake"]) for r in rows)
        pnl = sum(float(r["pnl"]) for r in rows)
        return ("good" if pnl > 0 else "warning",
                f"LIVE paper since 2026-06-20: {len(rows)}/50 settled, {w} wins "
                f"({w/len(rows)*100:.0f}%), {pnl/staked*100:+.1f}% ROI NET of fees "
                f"(${pnl:+.0f}) — >=+10% branch; SPRT + family correction at n>=50")
    except Exception:
        return "warning", "ledger unreadable"


def _c3_cell():
    p = os.path.join(DATA, "c3_verdict.json")
    if not os.path.exists(p):
        return "warning", "Not yet run"
    try:
        b = json.load(open(p, encoding="utf-8"))["buckets"]
        b1, b2 = b["B1_longshot_fade"], b["B2_favorite_buy"]
        return "warning", (
            f'longshot n={b1["n"]} ({b1.get("mean_net_roi_forward", 0)*100:+.1f}%), '
            f'favorite n={b2["n"]} ({b2.get("mean_net_roi_forward", 0)*100:+.1f}%) — '
            f'both UNDERPOWERED (need 500/bucket); PM long tail too thin, grows ~7/day')
    except Exception:
        return "warning", "verdict file unreadable"


def _s1_cell():
    p = os.path.join(DATA, "s1_forecasts.jsonl")
    if not os.path.exists(p):
        return "neutral", ("Wired to Groq free tier ($0) — waiting for GROQ_API_KEY "
                           "to start capturing forecasts")
    n = fro = setl = 0
    for r in _iter_jsonl(p):
        n += 1
        if "settle_for" in r:
            setl += 1
        else:
            fro += 1
    return "good", f"{fro} frozen forecasts, {setl} settled — forward record accruing"


# Cell status — all data-driven from ledgers/verdict files.
_c1s, _c1n = _c1_cell()
_c2s, _c2n = _c2_cell()
_c3s, _c3n = _c3_cell()
_s1s, _s1n = _s1_cell()
CELLS = [
    {"id": "C1", "name": "Weather ensemble", "stage": "Graduation candidate",
     "status": _c1s, "note": _c1n},
    {"id": "C2", "name": "Kalshi longshot fade", "stage": "Backtest study + forward seed",
     "status": _c2s, "note": _c2n},
    {"id": "C3", "name": "PM behavioral validation", "stage": "Pre-registered study",
     "status": _c3s, "note": _c3n},
    {"id": "S1", "name": "Geopolitics news (0% fee)", "stage": "Forward-only seed",
     "status": _s1s, "note": _s1n},
    {"id": "S2", "name": "CPI / macro", "stage": "Forward-only seed",
     "status": "neutral", "note": "Monthly cadence; cannot graduate in-window"},
]


def render(stats):
    kc = stats["kalshi_candles"]
    pm = stats["poly"]
    cats = kc["per_category"]
    cat_max = max(cats.values()) if cats else 1
    runs = stats["runs"]

    def spark(points, key):
        vals = [r.get(key, 0) for r in points] or [0]
        vmax = max(vals) or 1
        w, h = 120, 28
        if len(vals) == 1:
            vals = vals * 2
        step = w / (len(vals) - 1)
        pts = " ".join(f"{i*step:.1f},{h - (v/vmax)*(h-4) - 2:.1f}" for i, v in enumerate(vals))
        return (f'<svg class="spark" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
                f'role="img" aria-label="trend"><polyline points="{pts}" fill="none" '
                f'stroke="var(--series-1)" stroke-width="2" stroke-linejoin="round" '
                f'stroke-linecap="round"/></svg>')

    cat_bars = "\n".join(
        f'<div class="barrow"><span class="barlabel">{c}</span>'
        f'<span class="bartrack"><span class="bar" style="width:{(n/cat_max)*100:.1f}%"></span></span>'
        f'<span class="barval">{n:,}</span></div>'
        for c, n in cats.items()
    ) or '<p class="muted">No candle data yet — run fetch_prices_v2.py --venue kalshi</p>'

    status_dot = {"good": "var(--status-good)", "warning": "var(--status-warning)",
                  "critical": "var(--status-critical)", "neutral": "var(--muted)"}
    cell_rows = "\n".join(
        f'<tr><td class="mono">{c["id"]}</td><td>{c["name"]}</td>'
        f'<td><span class="dot" style="background:{status_dot[c["status"]]}"></span>{c["stage"]}</td>'
        f'<td class="muted">{c["note"]}</td></tr>'
        for c in CELLS
    )

    pct_usable = (pm["usable"] / pm["markets"] * 100) if pm["markets"] else 0
    pct_bidask = (kc["with_bidask"] / kc["markets"] * 100) if kc["markets"] else 0

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Institute — Data &amp; Cell Dashboard</title>
<style>
  :root {{
    --page: #f9f9f7; --surface: #fcfcfb; --ink: #0b0b0b; --ink-2: #52514e;
    --muted: #898781; --grid: #e1e0d9; --border: rgba(11,11,11,0.10);
    --series-1: #2a78d6;
    --status-good: #0ca30c; --status-warning: #fab219; --status-critical: #d03b3b;
  }}
  @media (prefers-color-scheme: dark) {{ :root {{
    --page: #0d0d0d; --surface: #1a1a19; --ink: #ffffff; --ink-2: #c3c2b7;
    --grid: #2c2c2a; --border: rgba(255,255,255,0.10); --series-1: #3987e5;
  }} }}
  * {{ box-sizing: border-box; margin: 0; }}
  body {{ background: var(--page); color: var(--ink);
    font: 14px/1.5 system-ui, -apple-system, "Segoe UI", sans-serif; padding: 24px; }}
  h1 {{ font-size: 18px; margin-bottom: 2px; }}
  .sub {{ color: var(--muted); margin-bottom: 20px; font-size: 12px; }}
  .grid {{ display: grid; gap: 12px; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); margin-bottom: 20px; }}
  .tile {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 14px 16px; }}
  .tile .k {{ color: var(--ink-2); font-size: 12px; }}
  .tile .v {{ font-size: 26px; font-weight: 650; margin: 2px 0; }}
  .tile .d {{ color: var(--muted); font-size: 12px; }}
  .spark {{ display: block; margin-top: 6px; }}
  .panel {{ background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 16px; margin-bottom: 16px; }}
  .panel h2 {{ font-size: 13px; color: var(--ink-2); font-weight: 600; margin-bottom: 12px; }}
  .barrow {{ display: flex; align-items: center; gap: 10px; margin: 6px 0; }}
  .barlabel {{ width: 110px; color: var(--ink-2); font-size: 12px; text-align: right;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
  .bartrack {{ flex: 1; background: transparent; }}
  .bar {{ display: block; height: 14px; background: var(--series-1); border-radius: 0 4px 4px 0; min-width: 2px; }}
  .barval {{ width: 64px; font-variant-numeric: tabular-nums; font-size: 12px; color: var(--ink-2); }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ text-align: left; color: var(--muted); font-size: 11px; font-weight: 600;
    text-transform: uppercase; letter-spacing: .04em; padding: 6px 8px; border-bottom: 1px solid var(--grid); }}
  td {{ padding: 8px; border-bottom: 1px solid var(--grid); vertical-align: top; }}
  tr:last-child td {{ border-bottom: none; }}
  .mono {{ font-family: ui-monospace, Consolas, monospace; }}
  .muted {{ color: var(--muted); }}
  .dot {{ display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 7px; }}
  .foot {{ color: var(--muted); font-size: 11px; margin-top: 18px; }}
  @media (max-width: 640px) {{ body {{ padding: 12px; }} .barlabel {{ width: 84px; }} }}
</style></head><body>
<h1>The Institute — data &amp; cell dashboard</h1>
<p class="sub">Generated {stats["generated_at"]} · paper only · ARCHITECTURE v4 (converged)</p>

<div class="grid">
  <div class="tile"><div class="k">Kalshi candle histories</div>
    <div class="v">{kc["markets"]:,}</div>
    <div class="d">{kc["candle_rows"]:,} hourly candles · {pct_bidask:.0f}% with bid/ask</div>
    {spark(runs, "kalshi_candle_markets")}</div>
  <div class="tile"><div class="k">PM decision-time series</div>
    <div class="v">{pm["markets"]:,}</div>
    <div class="d">{pm["usable"]:,} usable (&ge;10 trades, {pct_usable:.0f}%) · {pm["points"]:,} trade points</div>
    {spark(runs, "poly_markets")}</div>
  <div class="tile"><div class="k">Kalshi settled outcomes</div>
    <div class="v">{stats["kalshi_settled_total"]:,}</div>
    <div class="d">backtest ground truth (labels)</div></div>
  <div class="tile"><div class="k">Candle coverage of settled</div>
    <div class="v">{(kc["markets"]/stats["kalshi_settled_total"]*100 if stats["kalshi_settled_total"] else 0):.1f}%</div>
    <div class="d">grows with each scheduled fetch</div></div>
</div>

<div class="panel"><h2>Kalshi candle histories by category (markets)</h2>{cat_bars}</div>

<div class="panel"><h2>Cell / study status (ARCHITECTURE &sect;2, &sect;5)</h2>
<table><thead><tr><th>ID</th><th>Cell</th><th>Stage</th><th>Note</th></tr></thead>
<tbody>{cell_rows}</tbody></table></div>

<p class="foot">Data stores are local &amp; gitignored (re-fetchable). This page regenerates after every
scheduled fetch via gen_dashboard.py. Kill criteria and pre-registration live in
institute/FABLE5/out/ARCHITECTURE.md; go-live bar in GO_LIVE_TRIGGER.md.</p>
</body></html>"""


def main():
    stats = collect()
    out = os.path.abspath(OUT_HTML)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(render(stats))
    print(f"dashboard written: {out}")
    print(json.dumps({k: v for k, v in stats.items() if k != "runs"}, indent=2)[:800])


if __name__ == "__main__":
    main()
