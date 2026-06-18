"""
lib/tuning.py — self-correcting threshold tuning for the weather paper-trader.

Run periodically by `papertrader.py self_correct`. Never touches bets.csv or
bankroll.json — it only reads scan snapshots (data/scans/*.json) that
cmd_scan already wrote during normal/live scanning, and (optionally) writes
new threshold values into config.json (global and/or per-city) plus an audit
row to data/tuning_log.csv.

KEY DESIGN CHANGE FROM v1 (2026-06-16, same day): the first version gated
EVERY grid combo on "5+ qualifying bets after applying edge_threshold AND
buffer AND model_agree all at once" — with only ~75 scored markets across 11
cities, almost no combo could ever clear that bar, so the loop ran for hours
finding nothing to tune. v2 decomposes the three knobs by what they're
actually deciding:

  - model_agree_max_diff_c and buffer_around_mean_f are FORECAST-QUALITY
    filters — "is this specific market's forecast trustworthy enough to act
    on at all?" That's a calibration question (does the model's stated
    probability match the real outcome rate?), which can be scored with
    Brier score across EVERY evaluated market that passes the filter — no
    minimum bet count tied to a price edge required. This is "stage 1".

  - edge_threshold_pct is an ECONOMIC decision — "given a trustworthy
    forecast, how much mispricing do I need to see before risking money?"
    That's scored with simulated P&L, but only needs a per-bet-count gate on
    THIS one threshold, applied AFTER the (now-fixed) stage-1 filter — a
    much bigger and more representative pool than the old 3-way intersection.

Both stages still use a chronological 70/30 walk-forward split and both still
require a minimum sample size before trusting a result, and both are skipped
(not silently applied) when there isn't enough evidence — same honesty
contract as v1, just less needlessly conservative about what counts as
"enough".

A third, OPTIONAL stage tunes edge_threshold_pct per-city instead of
globally, but only for a city that individually clears CITY_MIN_ROWS scored
markets — with ~7 rows/city today this will not fire yet, but the mechanism
is in place so it activates automatically as more days of scanning accrue
(it does NOT require a code change later).
"""

import os
import csv
import json
import glob
import logging
from datetime import datetime, timezone

from lib import backtest, settlement, forecasts

logger = logging.getLogger("tuning")

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
TUNING_LOG = os.path.join(DATA_DIR, "tuning_log.csv")

EDGE_GRID = [3.0, 5.0, 7.0, 10.0]
BUFFER_GRID = [2.0, 3.0, 4.0]
AGREE_GRID = [1.0, 1.5, 2.0]

MIN_FILTER_ROWS = 10     # stage 1 (Brier, no edge gate): rows needed per filter combo
MIN_EDGE_BETS = 5        # stage 2 (P&L): qualifying bets needed per edge candidate
CITY_MIN_ROWS = 20       # stage 3 (per-city): total scored rows needed before a city
                          # gets its own threshold instead of the global one

LOG_FIELDS = [
    "timestamp", "scope", "n_train", "n_validate",
    "old_edge_pct", "old_buffer_f", "old_agree_c",
    "new_edge_pct", "new_buffer_f", "new_agree_c",
    "old_val_metric", "old_val_n", "new_val_metric", "new_val_n",
    "applied", "reason",
]


# ──────────────────────────────────────────────────────────────────────────────
# extended snapshot loader — same as backtest._load_snapshot_rows but also
# carries the per-model means needed to re-evaluate buffer/agreement rules
# without re-fetching any forecast.
# ──────────────────────────────────────────────────────────────────────────────
def _load_rows():
    rows = []
    for path in sorted(glob.glob(os.path.join(backtest.SCANS_DIR, "scan_*.json"))):
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
                "end_date": m.get("end_date", ""),
                "bucket_low_f": m.get("bucket_low_f"),
                "bucket_high_f": m.get("bucket_high_f"),
                "is_oe_low": bool(m.get("is_open_ended_low", False)),
                "is_oe_high": bool(m.get("is_open_ended_high", False)),
                "ask_price": float(ask),
                "ensemble_prob": float(ev.get("ensemble_prob", 0.0)),
                "gfs_mean_f": ev.get("gfs_mean_f"),
                "ecmwf_mean_f": ev.get("ecmwf_mean_f"),
                "combined_mean_f": ev.get("combined_mean_f"),
                "scan_ts": scan_ts,
            })
    return rows


def _score_rows(cfg):
    """Dedupe to one row per market, resolve actual outcomes. Returns scored list
    sorted by scan_ts (oldest first) — ready for a chronological train/validate split.
    Includes EVERY evaluated market (bets, near-misses, and plain skips alike) —
    not just markets that were actually bet on — since stage 1 needs the full
    population to measure calibration."""
    city_lookup = {c["name"]: c for c in cfg["cities"]}
    get_actual = backtest._make_actual_cache()
    rows = backtest._dedupe_latest(_load_rows())

    scored = []
    for r in rows:
        if r["gfs_mean_f"] is None or r["ecmwf_mean_f"] is None or r["combined_mean_f"] is None:
            continue  # older snapshot format, missing means — skip rather than guess
        city_cfg = city_lookup.get(r["city"])
        if city_cfg is None:
            continue
        target_date = r["end_date"][:10]
        if not target_date:
            continue
        actual = get_actual(city_cfg, target_date)
        if actual is None:
            continue
        won = settlement.did_bucket_win(
            actual, float(r["bucket_low_f"]), float(r["bucket_high_f"]),
            r["is_oe_low"], r["is_oe_high"],
        )
        scored.append({**r, "actual_high_f": actual, "won": won})

    scored.sort(key=lambda s: s["scan_ts"])
    return scored


def _filter_pass(s, buffer_f, agree_c):
    """Stage-1 filter only: model agreement + outside-mean-buffer. No edge/price
    logic — this is purely 'is the forecast itself trustworthy for this market'."""
    if not forecasts.models_agree(s["gfs_mean_f"], s["ecmwf_mean_f"], agree_c):
        return False
    if buffer_f > 0:
        in_buffer = forecasts.near_mean_buffer(
            s["bucket_low_f"], s["bucket_high_f"], s["combined_mean_f"], buffer_f
        )
        if in_buffer:
            return False
    return True


def _brier(rows):
    if not rows:
        return None
    return sum((s["ensemble_prob"] - (1.0 if s["won"] else 0.0)) ** 2 for s in rows) / len(rows)


def _simulate_pnl(rows, edge_pct, stake, fee_pct):
    """P&L sweep over rows ALREADY filtered by stage 1; only edge_pct gates here."""
    n = wins = 0
    total_pnl = 0.0
    for s in rows:
        ask = s["ask_price"]
        if ask <= 0 or ask >= 1:
            continue
        edge = (s["ensemble_prob"] - ask) * 100.0
        if edge < edge_pct:
            continue
        n += 1
        shares = stake / ask
        if s["won"]:
            wins += 1
            fee = shares * fee_pct
            total_pnl += shares - fee - stake
        else:
            total_pnl -= stake
    return {"bets": n, "wins": wins, "total_pnl": round(total_pnl, 2)}


def _append_log(row):
    os.makedirs(DATA_DIR, exist_ok=True)
    write_header = not os.path.exists(TUNING_LOG)
    with open(TUNING_LOG, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=LOG_FIELDS)
        if write_header:
            w.writeheader()
        w.writerow(row)


def _tune_stage1(train, validate, old_buffer, old_agree):
    """Pick buffer_f/agree_c by lowest validation Brier score (no edge gate)."""
    old_val_rows = [s for s in validate if _filter_pass(s, old_buffer, old_agree)]
    old_brier = _brier(old_val_rows)

    best = None
    for buffer_f in BUFFER_GRID:
        for agree_c in AGREE_GRID:
            train_rows = [s for s in train if _filter_pass(s, buffer_f, agree_c)]
            if len(train_rows) < MIN_FILTER_ROWS:
                continue
            val_rows = [s for s in validate if _filter_pass(s, buffer_f, agree_c)]
            if len(val_rows) < MIN_FILTER_ROWS:
                continue
            brier = _brier(val_rows)
            if best is None or brier < best["brier"]:
                best = {"buffer_f": buffer_f, "agree_c": agree_c, "brier": brier,
                        "n_train": len(train_rows), "n_val": len(val_rows)}

    result = {
        "old_brier": old_brier, "old_n": len(old_val_rows),
        "best": best, "applied": False, "reason": "",
    }
    if best is None:
        result["reason"] = (
            f"no buffer/agree combo reached {MIN_FILTER_ROWS} rows on both train "
            f"and validate — stay at buffer={old_buffer}, agree={old_agree}"
        )
        return result
    if old_brier is not None and best["brier"] >= old_brier:
        result["reason"] = (
            f"current settings (buffer={old_buffer}, agree={old_agree}) already "
            f"have validation Brier {old_brier:.4f} <= best candidate's "
            f"{best['brier']:.4f} — keeping current"
        )
        return result
    if best["buffer_f"] == old_buffer and best["agree_c"] == old_agree:
        result["reason"] = "best combo matches current config already — no change needed"
        return result
    result["applied"] = True
    result["reason"] = (
        f"validation Brier improved {old_brier:.4f} -> {best['brier']:.4f} "
        f"({best['n_val']} rows passing filter, {best['n_train']} in train)"
    )
    return result


def _tune_stage2(train, validate, buffer_f, agree_c, old_edge, stake, fee_pct):
    """Pick edge_threshold_pct by highest validation P&L, scoped to rows that pass
    the (possibly just-updated) stage-1 filter."""
    train_f = [s for s in train if _filter_pass(s, buffer_f, agree_c)]
    val_f = [s for s in validate if _filter_pass(s, buffer_f, agree_c)]

    old_val = _simulate_pnl(val_f, old_edge, stake, fee_pct)

    best = None
    for edge_pct in EDGE_GRID:
        train_res = _simulate_pnl(train_f, edge_pct, stake, fee_pct)
        if train_res["bets"] < MIN_EDGE_BETS:
            continue
        val_res = _simulate_pnl(val_f, edge_pct, stake, fee_pct)
        if val_res["bets"] < MIN_EDGE_BETS:
            continue
        if best is None or val_res["total_pnl"] > best["val"]["total_pnl"]:
            best = {"edge_pct": edge_pct, "train": train_res, "val": val_res}

    result = {"old_val": old_val, "best": best, "applied": False, "reason": ""}
    if best is None:
        result["reason"] = (
            f"no edge threshold reached {MIN_EDGE_BETS} bets on both train and "
            f"validate ({len(val_f)} rows available after stage-1 filter) — "
            f"keeping edge={old_edge}"
        )
        return result
    if best["edge_pct"] == old_edge:
        result["reason"] = "best edge threshold matches current config already — no change needed"
        return result
    if best["val"]["total_pnl"] <= old_val["total_pnl"]:
        result["reason"] = (
            f"candidate edge={best['edge_pct']} validation P&L ${best['val']['total_pnl']:.2f} "
            f"does not beat current edge={old_edge}'s ${old_val['total_pnl']:.2f} — keeping current"
        )
        return result
    result["applied"] = True
    result["reason"] = (
        f"validation P&L improved ${old_val['total_pnl']:.2f} -> ${best['val']['total_pnl']:.2f} "
        f"on {best['val']['bets']} validation bets (train had {best['train']['bets']} bets)"
    )
    return result


def run_tuning_cycle(cfg, config_path):
    """
    One walk-forward tuning cycle (global scope), followed by an optional
    per-city pass (see run_city_tuning). Returns a summary dict. May rewrite
    config.json in place. Always appends at least one row to tuning_log.csv.
    """
    stake = cfg.get("stake_per_bet", 5.0)
    fee_pct = cfg.get("fee_on_winnings_pct", 2.0) / 100.0
    old_edge = cfg.get("edge_threshold_pct", 5.0)
    old_buffer = cfg.get("buffer_around_mean_f", 3.0)
    old_agree = cfg.get("model_agree_max_diff_c", 1.5)

    scored = _score_rows(cfg)
    n = len(scored)
    split = int(n * 0.7)
    train, validate = scored[:split], scored[split:]

    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    applied_any = False
    reasons = []

    if n < (MIN_FILTER_ROWS * 2):
        reason = f"only {n} scored markets total — too few to tune yet (need {MIN_FILTER_ROWS*2}+)"
        _append_log({
            "timestamp": ts, "scope": "global", "n_train": len(train), "n_validate": len(validate),
            "old_edge_pct": old_edge, "old_buffer_f": old_buffer, "old_agree_c": old_agree,
            "new_edge_pct": old_edge, "new_buffer_f": old_buffer, "new_agree_c": old_agree,
            "old_val_metric": "", "old_val_n": 0, "new_val_metric": "", "new_val_n": 0,
            "applied": False, "reason": reason,
        })
        logger.info(f"TUNING: no change — {reason}")
        return {"applied": False, "reason": reason, "n_scored": n}

    # Stage 1: forecast-quality filter (buffer/agree) via Brier score.
    s1 = _tune_stage1(train, validate, old_buffer, old_agree)
    new_buffer, new_agree = old_buffer, old_agree
    if s1["applied"]:
        new_buffer, new_agree = s1["best"]["buffer_f"], s1["best"]["agree_c"]
        applied_any = True
    reasons.append(f"stage1(buffer/agree): {s1['reason']}")

    # Stage 2: economic edge threshold via P&L, scoped to the (possibly new) filter.
    s2 = _tune_stage2(train, validate, new_buffer, new_agree, old_edge, stake, fee_pct)
    new_edge = old_edge
    if s2["applied"]:
        new_edge = s2["best"]["edge_pct"]
        applied_any = True
    reasons.append(f"stage2(edge): {s2['reason']}")

    log_row = {
        "timestamp": ts, "scope": "global", "n_train": len(train), "n_validate": len(validate),
        "old_edge_pct": old_edge, "old_buffer_f": old_buffer, "old_agree_c": old_agree,
        "new_edge_pct": new_edge, "new_buffer_f": new_buffer, "new_agree_c": new_agree,
        "old_val_metric": f"brier={s1['old_brier']}", "old_val_n": s1["old_n"],
        "new_val_metric": f"brier={s1['best']['brier'] if s1['best'] else ''};pnl={s2['best']['val']['total_pnl'] if s2['best'] else ''}",
        "new_val_n": s2["best"]["val"]["bets"] if s2["best"] else 0,
        "applied": applied_any, "reason": " | ".join(reasons),
    }
    _append_log(log_row)

    if applied_any:
        cfg["edge_threshold_pct"] = new_edge
        cfg["buffer_around_mean_f"] = new_buffer
        cfg["model_agree_max_diff_c"] = new_agree
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        logger.info(
            f"TUNING: APPLIED edge={old_edge}->{new_edge} "
            f"buffer={old_buffer}->{new_buffer} agree={old_agree}->{new_agree}"
        )
        for r in reasons:
            logger.info(f"  {r}")
    else:
        logger.info("TUNING: no change this cycle")
        for r in reasons:
            logger.info(f"  {r}")

    result = {
        "applied": applied_any, "reason": " | ".join(reasons), "n_scored": n,
        "old": {"edge_pct": old_edge, "buffer_f": old_buffer, "agree_c": old_agree},
        "new": {"edge_pct": new_edge, "buffer_f": new_buffer, "agree_c": new_agree},
    }

    # Stage 3: optional per-city edge override, only for cities with enough of
    # their own data. Uses the (possibly updated) global buffer/agree as the
    # filter — per-city tuning here is scoped to the economic threshold only,
    # since splitting buffer/agree per city needs even more data than this.
    city_result = run_city_tuning(cfg, config_path, scored, new_buffer, new_agree, stake, fee_pct)
    result["city_changes"] = city_result
    return result


def run_city_tuning(cfg, config_path, scored, buffer_f, agree_c, stake, fee_pct):
    """
    Per-city edge_threshold_pct override. Only fires for a city once it has
    CITY_MIN_ROWS of its own scored markets — with today's ~7 rows/city this
    will not activate yet, but requires no further code changes once it does;
    it'll just start firing on its own as more days of scans accumulate.
    """
    by_city = {}
    for s in scored:
        by_city.setdefault(s["city"], []).append(s)

    changes = []
    cities_by_name = {c["name"]: c for c in cfg["cities"]}
    global_edge = cfg.get("edge_threshold_pct", 5.0)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    for city, rows in by_city.items():
        if len(rows) < CITY_MIN_ROWS:
            continue  # not enough city-specific evidence yet — use the global threshold
        rows = sorted(rows, key=lambda s: s["scan_ts"])
        split = int(len(rows) * 0.7)
        train, validate = rows[:split], rows[split:]
        city_cfg = cities_by_name.get(city)
        old_edge = (city_cfg or {}).get("edge_threshold_pct_override", global_edge)

        s2 = _tune_stage2(train, validate, buffer_f, agree_c, old_edge, stake, fee_pct)
        log_row = {
            "timestamp": ts, "scope": f"city:{city}", "n_train": len(train), "n_validate": len(validate),
            "old_edge_pct": old_edge, "old_buffer_f": buffer_f, "old_agree_c": agree_c,
            "new_edge_pct": s2["best"]["edge_pct"] if s2["applied"] else old_edge,
            "new_buffer_f": buffer_f, "new_agree_c": agree_c,
            "old_val_metric": f"pnl={s2['old_val']['total_pnl']}", "old_val_n": s2["old_val"]["bets"],
            "new_val_metric": f"pnl={s2['best']['val']['total_pnl']}" if s2["best"] else "",
            "new_val_n": s2["best"]["val"]["bets"] if s2["best"] else 0,
            "applied": s2["applied"], "reason": s2["reason"],
        }
        _append_log(log_row)
        if s2["applied"] and city_cfg is not None:
            city_cfg["edge_threshold_pct_override"] = s2["best"]["edge_pct"]
            changes.append({"city": city, "old_edge": old_edge, "new_edge": s2["best"]["edge_pct"],
                             "reason": s2["reason"]})
            logger.info(f"TUNING ({city}): edge override {old_edge} -> {s2['best']['edge_pct']} "
                        f"— {s2['reason']}")

    if changes:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    return changes
