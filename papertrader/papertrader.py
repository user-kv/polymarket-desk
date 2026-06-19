"""
papertrader.py — PaperTrader CLI (FAKE MONEY ONLY)
Usage:
  python papertrader.py scan              # Scan markets, evaluate edges, place paper bets
  python papertrader.py scan --test       # Force a bet with lowered threshold (for testing)
  python papertrader.py settle            # Settle resolved markets, update bankroll
  python papertrader.py report            # Regenerate dashboard.html + tracker.xlsx
  python papertrader.py status            # Quick summary: bankroll, open bets, last scan
  python papertrader.py cities            # Rebuild cities list from live Polymarket data
  python papertrader.py self_correct --hours 2   # Live scan/settle/tune/calibrate loop

HARD GUARDRAIL: This system NEVER places real orders. No wallet keys. Read-only public APIs only.
"""

import sys
import os
import json
import logging
import argparse
from datetime import datetime, timezone, date

# ── path setup so lib/ is importable ──────────────────────────────────────────
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from lib import polymarket, forecasts, engine, ledger, settlement, report, backtest, calibration, notify, tuning, cities as cities_lib

# ── logging ──────────────────────────────────────────────────────────────────
LOG_DIR = os.path.join(HERE, "logs")
os.makedirs(LOG_DIR, exist_ok=True)
log_file = os.path.join(LOG_DIR, f"papertrader_{datetime.now().strftime('%Y%m%d')}.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler(log_file, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("main")


def load_config():
    cfg_path = os.path.join(HERE, "config.json")
    with open(cfg_path) as f:
        return json.load(f)


def cmd_scan(cfg, test_mode=False):
    """
    Scan Polymarket for weather markets, fetch ensemble forecasts,
    evaluate edges, and paper-bet anything that passes all rules.
    """
    log.info("=" * 60)
    log.info("SCAN starting" + (" [TEST MODE — lowered threshold]" if test_mode else ""))
    log.info("=" * 60)

    # If test mode, temporarily lower edge threshold AND disable buffer/agreement rules
    scan_cfg = dict(cfg)
    if test_mode:
        scan_cfg["edge_threshold_pct"] = -50.0  # accept any edge (even negative) to force a bet
        scan_cfg["model_agree_max_diff_c"] = 999.0   # always agree in test mode
        scan_cfg["buffer_around_mean_f"] = -999.0    # never in buffer zone in test mode
        log.info("TEST MODE: all discipline rules relaxed to force exactly one bet placement")

    # Step 1: Fetch markets
    log.info("Fetching weather markets from Gamma API...")
    markets = polymarket.fetch_weather_markets(scan_cfg)
    log.info(f"Found {len(markets)} weather markets within {scan_cfg.get('max_hours_to_resolution', 48)}h")

    if not markets:
        log.warning("No markets found. Either no weather markets exist for tracked cities today, or the API is slow.")
        return

    # Step 2: Enrich with CLOB ask prices
    log.info("Fetching CLOB ask prices...")
    markets = polymarket.enrich_markets_with_prices(markets, scan_cfg)
    priced = [m for m in markets if m.get("ask_price") is not None]
    log.info(f"{len(priced)}/{len(markets)} markets have a valid ask price")

    # Step 3: Group by city to fetch one raw ensemble per city
    city_groups = {}
    for m in priced:
        city = m["city"]
        city_groups.setdefault(city, []).append(m)

    log.info(f"Fetching ensemble forecasts for {len(city_groups)} cities...")

    # Step 4: Load open bets and bankroll
    open_bets = ledger.get_open_bets()
    br = ledger.load_bankroll(cfg.get("bankroll_start", 500))
    bankroll = br["balance"]

    # Step 5: Evaluate each market
    scan_results = []
    bets_placed = []
    near_misses = []

    city_cfg_lookup = {c["name"]: c for c in cfg["cities"]}

    for city, city_markets in city_groups.items():
        city_cfg = city_cfg_lookup.get(city)
        if city_cfg is None:
            log.warning(f"No config for city {city}, skipping")
            continue

        # Fetch raw ensembles ONCE per city
        try:
            log.info(f"  Fetching raw ensembles for {city}...")
            raw_ensembles = forecasts.fetch_raw_ensembles_for_city(city_cfg, scan_cfg)
        except Exception as e:
            log.error(f"  Raw ensemble fetch failed for {city}: {e}")
            continue

        # Per-city edge_threshold_pct override (set by lib/tuning.py's stage-3
        # per-city pass once a city has enough of its own data — see
        # CITY_MIN_ROWS there). Falls back to the global threshold otherwise.
        city_eval_cfg = scan_cfg
        override = city_cfg.get("edge_threshold_pct_override")
        if override is not None and not test_mode:
            city_eval_cfg = dict(scan_cfg)
            city_eval_cfg["edge_threshold_pct"] = override

        for m in city_markets:
            end_date_str = m["end_date"][:10]  # YYYY-MM-DD
            try:
                # Compute daily high ensemble using the cached raw ensembles
                fc = forecasts.get_forecast_for_city(city_cfg, end_date_str, scan_cfg, raw_ensembles=raw_ensembles)
                log.info(
                    f"  {city} on {end_date_str}: GFS mean={fc['gfs_mean_f']:.1f}°F  "
                    f"ECMWF mean={fc['ecmwf_mean_f']:.1f}°F  "
                    f"n_members={len(fc['all_highs_f'])}"
                )
            except Exception as e:
                log.error(f"  Forecast extraction failed for {city} {end_date_str}: {e}")
                continue

            try:
                eval_result = engine.evaluate_bucket(
                    m, fc, open_bets, city_eval_cfg, bankroll
                )
            except Exception as e:
                log.error(f"  Evaluation error for {m.get('question','')}: {e}")
                continue

            action = eval_result["action"]
            log.info(
                f"  {action:10s} | {m['question'][:70]} | "
                f"edge={eval_result['edge_pct']:.1f}pt | "
                f"prob={eval_result['ensemble_prob']:.1%} | "
                f"ask={m.get('ask_price', 'N/A')}"
            )

            scan_entry = {
                "market": m,
                "forecast_summary": {
                    "gfs_mean_f": fc["gfs_mean_f"],
                    "ecmwf_mean_f": fc["ecmwf_mean_f"],
                    "combined_mean_f": fc["combined_mean_f"],
                    "n_members": len(fc["all_highs_f"]),
                },
                "evaluation": eval_result,
            }
            scan_results.append(scan_entry)

            if action == "BET":
                bet_record = engine.simulate_fill(m, eval_result, scan_cfg)
                if test_mode:
                    bet_record["is_test"] = "Y"
                    bet_record["bet_id"] = "TEST__" + bet_record["bet_id"]
                ledger.append_bet(bet_record)
                open_bets.append(bet_record)  # update local list for dup check
                bankroll -= float(bet_record["stake"])
                bets_placed.append(bet_record)
                log.info(f"  >>> BET PLACED: {bet_record['bet_id']}")
                if test_mode:
                    break  # In test mode, place exactly one bet then stop
            elif action == "NEAR_MISS":
                near_misses.append(scan_entry)

        if test_mode and bets_placed:
            break  # Stop after first city's first bet in test mode

    # Step 6: Save scan snapshot
    snapshot = {
        "scan_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "test_mode": test_mode,
        "markets_found": len(markets),
        "markets_priced": len(priced),
        "bets_placed": len(bets_placed),
        "near_misses": len(near_misses),
        "results": scan_results,
    }
    snap_path = ledger.save_scan_snapshot(snapshot)

    log.info("=" * 60)
    log.info(f"SCAN COMPLETE: {len(markets)} markets | {len(bets_placed)} bets placed | {len(near_misses)} near-misses")
    log.info(f"Snapshot: {snap_path}")
    log.info("=" * 60)

    # Notify only on real (non-test) bets — a scan with zero qualifying edges
    # shouldn't ping you every 2 hours, but an actual bet is worth knowing about.
    real_bets_placed = [b for b in bets_placed if not test_mode]
    if real_bets_placed:
        lines = "; ".join(
            f"{b['city']} {b['question'][:40]}... edge {b['edge_pct']}pt"
            for b in real_bets_placed
        )
        notify.send_toast(
            "PaperTrader: bet placed",
            f"{len(real_bets_placed)} new paper bet(s) — {lines}",
        )

    if test_mode and bets_placed:
        log.info("")
        log.info("TEST BET VERIFICATION:")
        for b in bets_placed:
            ask = float(b["ask_price"])
            stake = float(b["stake"])
            shares = float(b["shares"])
            fee_if_win = float(b["fee_if_win"])
            net_if_win = float(b["net_profit_if_win"])
            log.info(f"  Market  : {b['question']}")
            log.info(f"  Ask     : ${ask:.4f}  (fill price)")
            log.info(f"  Stake   : ${stake:.2f}")
            log.info(f"  Shares  : {shares:.4f}  (= ${stake} / ${ask:.4f})")
            log.info(f"  Win pays: ${shares:.4f} × $1 = ${shares:.4f} gross")
            log.info(f"  Fee     : ${fee_if_win:.4f} (2% of gross)")
            log.info(f"  Net win : ${net_if_win:.4f} profit  (or -${stake:.2f} if lost)")
            log.info(f"  bet_id  : {b['bet_id']}")
        log.info("")
        log.info("IMPORTANT: Test bet is marked is_test=Y in bets.csv.")
        log.info("Remove it by deleting the row in data/bets.csv if desired.")


def cmd_settle(cfg):
    """Settle all open bets whose markets have resolved."""
    log.info("=" * 60)
    log.info("SETTLE starting")
    city_lookup = {c["name"]: c for c in cfg["cities"]}
    results = settlement.settle_all(cfg, city_lookup)
    if not results:
        log.info("Nothing to settle (no resolved open bets yet)")
    else:
        for r in results:
            log.info(
                f"  {r['result']:4s} | {r['question'][:60]} | "
                f"actual={r['actual_high_f']}°F | P&L={r['pnl']:+.2f}"
            )
        wins = sum(1 for r in results if r["result"] == "WON")
        total_pnl = sum(float(r["pnl"]) for r in results)
        notify.send_toast(
            "PaperTrader: bets settled",
            f"{len(results)} settled — {wins}W/{len(results)-wins}L, P&L ${total_pnl:+.2f}",
        )
    log.info(f"SETTLE COMPLETE: {len(results)} bets settled")
    log.info("=" * 60)


def cmd_report(cfg):
    """Generate dashboard.html and tracker.xlsx."""
    log.info("Generating dashboard and tracker...")
    d, t = report.generate_all()
    log.info(f"Dashboard: {d}")
    log.info(f"Tracker  : {t}")
    print(f"\nDashboard saved: {d}")
    print(f"Tracker saved  : {t}")
    print("Open dashboard.html in your browser to view your paper-trading results.")
    print("Open tracker.xlsx in Excel for the full ledger + Sports CLV template.")


def cmd_backtest(cfg, args):
    """
    READ-ONLY backtest. Never modifies bets.csv or bankroll.json.
      python papertrader.py backtest                  # Mode 1: snapshot replay
      python papertrader.py backtest --historical     # + Mode 2: model accuracy
      python papertrader.py backtest --historical --days 45
    """
    log.info("=" * 60)
    log.info("BACKTEST starting (read-only — live bankroll/ledger untouched)")
    log.info("=" * 60)

    snapshot_res = backtest.run_snapshot_backtest(cfg)
    backtest.print_snapshot_summary(snapshot_res)

    historical_res = None
    if getattr(args, "historical", False):
        days = getattr(args, "days", 30)
        log.info(f"Running historical model-accuracy backtest ({days} days)...")
        historical_res = backtest.run_historical_backtest(cfg, days=days)
        backtest.print_historical_summary(historical_res)

    path = backtest.write_html(snapshot_res, historical_res)
    print(f"\nBacktest report saved: {path}")
    print("Open backtest.html in your browser for the full breakdown.")


def cmd_calibrate(cfg, args):
    """
    Measure each city's recent forecast bias (forecast vs actual) and save a
    damped correction to data/calibration.json. The next scan automatically
    applies it. Re-run this periodically (e.g. weekly) as more data comes in —
    the correction strengthens the more days back it up.
    """
    log.info("=" * 60)
    log.info("CALIBRATE starting")
    log.info("=" * 60)
    days = getattr(args, "days", 14)
    cal = calibration.compute_and_save(cfg, days=days)
    calibration.print_summary(cal)


def _days_until_real_money(cfg):
    target_str = cfg.get("real_money_target_date")
    if not target_str:
        return None
    try:
        target = datetime.strptime(target_str, "%Y-%m-%d").date()
        today = datetime.now(timezone.utc).date()
        return (target - today).days
    except Exception:
        return None


def cmd_weekly(cfg):
    """
    Weekly digest: refresh calibration, regenerate reports, and send ONE
    consolidated notification — bankroll, win rate, calibration deltas, and a
    countdown to the real-money target date. Meant to run automatically once a
    week so you get a check-in without anything being noisy in between.
    """
    log.info("=" * 60)
    log.info("WEEKLY DIGEST starting")
    log.info("=" * 60)

    cal = calibration.compute_and_save(cfg, days=14)
    calibration.print_summary(cal)

    d, t = report.generate_all()
    log.info(f"Dashboard: {d}")
    log.info(f"Tracker  : {t}")

    br = ledger.load_bankroll(cfg.get("bankroll_start", 500))
    all_bets = ledger.load_bets()
    real = [b for b in all_bets if b.get("is_test", "N") != "Y"]
    settled = [b for b in real if b.get("status") == "settled"]
    won = [b for b in settled if b.get("result") == "WON"]
    win_rate = f"{len(won)/len(settled)*100:.0f}%" if settled else "n/a"

    days_left = _days_until_real_money(cfg)
    countdown = f"{days_left} days until your real-money target" if days_left is not None else ""

    cal_str = "; ".join(
        f"{city} {c['correction_f']:+.1f}°F" for city, c in cal.items()
    ) or "no calibration data yet"

    message = (
        f"Bankroll ${br.get('balance', 500):.2f} | "
        f"{len(settled)} settled ({win_rate} win rate) | "
        f"calibration: {cal_str}"
        + (f" | {countdown}" if countdown else "")
    )
    log.info(message)
    notify.send_toast("PaperTrader: weekly digest", message)

    log.info("=" * 60)
    log.info("WEEKLY DIGEST COMPLETE")
    log.info("=" * 60)


def cmd_cities(cfg, args):
    """Rebuild the cities list from live Polymarket data (see lib/cities.py)."""
    cfg_path = os.path.join(HERE, "config.json")
    log.info("Rescanning Polymarket for supported-format cities...")
    new_cities = cities_lib.build_and_apply(cfg, cfg_path)
    print(f"\nWrote {len(new_cities)} cities to config.json:")
    for c in new_cities:
        print(f"  {c['name']:20s} station={c['station']:6s} lat={c['lat']:8.4f} lon={c['lon']:9.4f}")
    print(
        "\nNote: only Fahrenheit highest-temp range/open-ended bucket markets are "
        "supported right now. Celsius/single-value/lowest-temp markets are skipped "
        "(see config.json's _cities_note)."
    )


def cmd_self_correct(cfg, args):
    """
    Live self-correcting loop (FAKE MONEY ONLY): repeatedly scan -> settle ->
    walk-forward tune thresholds -> recalibrate, for --hours wall-clock time.
    Each cycle is the same scan/settle path the scheduled tasks already use —
    this just runs it more frequently and re-tunes engine.py's thresholds
    between cycles based on real accumulated evidence (see lib/tuning.py).
    """
    import time as _time

    hours = getattr(args, "hours", 2.0)
    interval_min = getattr(args, "interval", 12)
    cfg_path = os.path.join(HERE, "config.json")
    end_time = _time.time() + hours * 3600

    log.info("=" * 60)
    log.info(f"SELF-CORRECT starting: {hours}h, cycling every {interval_min}min")
    log.info("FAKE MONEY ONLY — same guardrails as scan/settle.")
    log.info("=" * 60)

    cycles = 0
    applied_changes = []
    while True:
        cycles += 1
        log.info(f"\n--- Self-correct cycle {cycles} ---")
        cfg = load_config()  # reload in case a previous cycle changed it
        try:
            cmd_scan(cfg)
        except Exception as e:
            log.error(f"scan failed in self-correct cycle {cycles}: {e}")
        try:
            cmd_settle(load_config())
        except Exception as e:
            log.error(f"settle failed in self-correct cycle {cycles}: {e}")
        try:
            cfg = load_config()
            result = tuning.run_tuning_cycle(cfg, cfg_path)
            if result.get("applied"):
                applied_changes.append({"cycle": cycles, **result})
        except Exception as e:
            log.error(f"tuning failed in self-correct cycle {cycles}: {e}")
        try:
            calibration.compute_and_save(load_config(), days=14)
        except Exception as e:
            log.error(f"calibration failed in self-correct cycle {cycles}: {e}")

        remaining = end_time - _time.time()
        if remaining <= 0:
            break
        sleep_s = min(interval_min * 60, remaining)
        log.info(f"Cycle {cycles} done. Sleeping {sleep_s/60:.1f}min "
                  f"({remaining/60:.1f}min left in run)...")
        _time.sleep(sleep_s)

    log.info("=" * 60)
    log.info(f"SELF-CORRECT COMPLETE: {cycles} cycles, {len(applied_changes)} config change(s) applied")
    for c in applied_changes:
        log.info(f"  cycle {c['cycle']}: {c['reason']}")
    log.info("=" * 60)

    notify.send_toast(
        "PaperTrader: self-correct loop finished",
        f"{cycles} cycles run, {len(applied_changes)} threshold change(s) applied. "
        f"See data/tuning_log.csv.",
    )


def cmd_status(cfg):
    """Quick status: bankroll, open bets, last scan time."""
    br = ledger.load_bankroll(cfg.get("bankroll_start", 500))
    open_bets = ledger.get_open_bets()
    all_bets = ledger.load_bets()
    # Test bets stay visible in lists but never count toward stats
    real = [b for b in all_bets if b.get("is_test", "N") != "Y"]
    settled = [b for b in real if b.get("status") == "settled"]
    won = [b for b in settled if b.get("result") == "WON"]
    total_pnl = sum(float(b.get("pnl", 0)) for b in settled)

    # Last scan
    scans_dir = os.path.join(HERE, "data", "scans")
    scans = sorted([f for f in os.listdir(scans_dir) if f.startswith("scan_")]) if os.path.exists(scans_dir) else []
    last_scan = scans[-1] if scans else "none"

    print("\n" + "=" * 55)
    print("  PAPERTRADER STATUS  (FAKE MONEY — PAPER TRADING ONLY)")
    print("=" * 55)
    print(f"  Bankroll start : ${br.get('start', 500):.2f}")
    print(f"  Current balance: ${br.get('balance', 500):.2f}  ({total_pnl:+.2f} total P&L)")
    print(f"  Open bets      : {len(open_bets)}")
    print(f"  Settled bets   : {len(settled)}  ({len(won)}W / {len(settled)-len(won)}L)")
    win_rate = f"{len(won)/len(settled)*100:.0f}%" if settled else "n/a"
    print(f"  Win rate       : {win_rate}")
    print(f"  Last scan file : {last_scan}")
    print(f"  Dashboard      : {os.path.join(HERE, 'dashboard.html')}")
    print(f"  Tracker        : {os.path.join(HERE, 'tracker.xlsx')}")
    days_left = _days_until_real_money(cfg)
    if days_left is not None:
        print(f"  Real-money in  : {days_left} days (target {cfg.get('real_money_target_date')})")
    print("=" * 55)

    if open_bets:
        print(f"\n  Open bets:")
        for b in open_bets:
            test_tag = " [TEST]" if b.get("is_test") == "Y" else ""
            print(f"    - {b.get('question', '')[:65]}{test_tag}")
            print(f"      Edge={b.get('edge_pct')}pt | Ask=${b.get('ask_price')} | Stake=${b.get('stake')} | Resolves {b.get('end_date','')[:10]}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="PaperTrader — Weather paper-trading system (FAKE money only)"
    )
    sub = parser.add_subparsers(dest="command")

    p_scan = sub.add_parser("scan", help="Scan markets and place paper bets")
    p_scan.add_argument("--test", action="store_true",
                        help="Force a bet (lower threshold) for testing purposes")

    sub.add_parser("settle", help="Settle resolved markets")
    sub.add_parser("report", help="Generate dashboard.html and tracker.xlsx")
    sub.add_parser("status", help="Show quick status summary")

    p_bt = sub.add_parser("backtest", help="Read-only backtest (no money moves)")
    p_bt.add_argument("--historical", action="store_true",
                      help="Also run the multi-week model-accuracy backtest")
    p_bt.add_argument("--days", type=int, default=14,
                      help="Days to look back for --historical (default 14). "
                           "NOTE: Open-Meteo's ensemble API only retains ~5-6 days "
                           "of actual history regardless of this value — see backtest.html.")

    p_cal = sub.add_parser("calibrate", help="Measure & save the self-correcting forecast bias")
    p_cal.add_argument("--days", type=int, default=14,
                       help="Days of history to measure bias from (default 14)")

    sub.add_parser("weekly", help="Weekly digest: calibrate + reports + one notification")

    sub.add_parser("cities", help="Rebuild cities list from live Polymarket data (lib/cities.py)")

    p_sc = sub.add_parser("self_correct", help="Live self-correcting loop: scan/settle/tune/calibrate on a timer")
    p_sc.add_argument("--hours", type=float, default=2.0,
                      help="Total wall-clock hours to run (default 2.0)")
    p_sc.add_argument("--interval", type=float, default=12,
                      help="Minutes between scan/settle/tune cycles (default 12)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    cfg = load_config()

    if args.command == "scan":
        cmd_scan(cfg, test_mode=getattr(args, "test", False))
    elif args.command == "settle":
        cmd_settle(cfg)
    elif args.command == "report":
        cmd_report(cfg)
    elif args.command == "status":
        cmd_status(cfg)
    elif args.command == "backtest":
        cmd_backtest(cfg, args)
    elif args.command == "calibrate":
        cmd_calibrate(cfg, args)
    elif args.command == "weekly":
        cmd_weekly(cfg)
    elif args.command == "cities":
        cmd_cities(cfg, args)
    elif args.command == "self_correct":
        cmd_self_correct(cfg, args)


if __name__ == "__main__":
    main()
