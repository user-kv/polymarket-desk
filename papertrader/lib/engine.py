"""
lib/engine.py
Applies the discipline rules and decides whether to paper-bet each bucket.

All five rules must pass for a bet to be placed:
 1. Edge >= threshold (ensemble_prob - ask_price >= edge_threshold_pct / 100)
 2. <=48h to resolution
 3. GFS/ECMWF means agree within 1.5°C
 4. Bucket not in the 3°F buffer zone around the ensemble mean
 5. Open exposure check (no dup, and total open bets < 20% of bankroll)

Near-misses (edge 5-10 pts) are logged to the scan snapshot but NOT bet.
"""

import logging
from datetime import datetime, timezone

logger = logging.getLogger("engine")


def evaluate_bucket(market, forecast, current_open_bets, cfg, bankroll):
    """
    Evaluate a single market bucket against all discipline rules.

    Args:
        market: dict from polymarket.py (includes ask_price, hours_left, etc.)
        forecast: dict from forecasts.py compute_daily_high_ensemble
        current_open_bets: list of open bet dicts from ledger (to check exposure)
        cfg: config dict
        bankroll: current fake bankroll float

    Returns dict with:
        action: 'BET' | 'NEAR_MISS' | 'SKIP'
        reason: human-readable string
        edge_pct: float (ensemble_prob - ask) * 100
        ensemble_prob: float
        all_rules: list of (rule_name, passed, detail) tuples
        shares: float (stake/ask) -- only meaningful if action=='BET'
        stake: float
    """
    stake = cfg.get("stake_per_bet", 5.0)
    edge_threshold = cfg.get("edge_threshold_pct", 10.0) / 100.0
    near_miss_min = cfg.get("near_miss_min_pct", 5.0) / 100.0
    max_exposure_pct = cfg.get("max_exposure_pct", 20.0) / 100.0
    max_hours = cfg.get("max_hours_to_resolution", 48)
    model_agree_c = cfg.get("model_agree_max_diff_c", 1.5)
    buffer_f = cfg.get("buffer_around_mean_f", 3.0)

    ask = market.get("ask_price")
    hours_left = market.get("hours_left", 999)
    slug = market.get("slug", "")
    city = market.get("city", "")

    rules = []
    all_pass = True

    # --- Rule 1: Ask price available ---
    if ask is None or ask <= 0:
        return {
            "action": "SKIP",
            "reason": "No valid ask price from CLOB",
            "edge_pct": 0.0,
            "ensemble_prob": 0.0,
            "all_rules": [("ask_price_available", False, "ask=None")],
            "shares": 0.0,
            "stake": stake,
        }

    # --- Compute ensemble probability for this bucket ---
    # Equal-weighted by MODEL (GFS/ECMWF/ICON/AIFS each get one vote), not by
    # raw member count — pooling raw members let ECMWF's 100 combined members
    # (IFS+AIFS) outweigh GFS's 30 for no meteorological reason. See
    # lib/forecasts.bucket_probability_by_model.
    from lib.forecasts import bucket_probability_by_model, models_agree, near_mean_buffer
    all_highs = forecast.get("all_highs_f", [])
    ensemble_prob = bucket_probability_by_model(
        forecast,
        market["bucket_low_f"],
        market["bucket_high_f"],
    )
    edge = ensemble_prob - ask
    edge_pct = edge * 100.0

    if cfg.get("use_kelly_staking", False) and edge > 0 and ask < 1.0:
        f_star = edge / (1.0 - ask)
        proposed_stake = bankroll * cfg.get("kelly_fraction", 0.25) * f_star
        stake = max(cfg.get("min_stake", 1.0), min(proposed_stake, cfg.get("max_stake", 25.0)))

    # Rule 1: Edge threshold
    r1 = edge >= edge_threshold
    rules.append(("edge_gte_threshold", r1,
                  f"prob={ensemble_prob:.3f} ask={ask:.3f} edge={edge_pct:.1f}pt threshold={edge_threshold*100:.0f}pt"))
    all_pass = all_pass and r1

    # Rule 2: Time to resolution
    r2 = 0 < hours_left <= max_hours
    rules.append(("within_48h", r2,
                  f"hours_left={hours_left:.1f}"))
    all_pass = all_pass and r2

    # Rule 3: Model agreement
    gfs_m = forecast.get("gfs_mean_f", 0)
    ecmwf_m = forecast.get("ecmwf_mean_f", 0)
    r3 = models_agree(gfs_m, ecmwf_m, model_agree_c)
    diff_f = abs(gfs_m - ecmwf_m)
    diff_c = diff_f * 5 / 9
    rules.append(("models_agree", r3,
                  f"gfs={gfs_m:.1f}F ecmwf={ecmwf_m:.1f}F diff={diff_c:.2f}C (max {model_agree_c}C)"))
    all_pass = all_pass and r3

    # Rule 4: Not in coin-flip middle
    combined_mean = forecast.get("combined_mean_f", (gfs_m + ecmwf_m) / 2)
    # buffer_f <= 0 means rule disabled (used in test mode)
    if buffer_f <= 0:
        in_buffer = False
    else:
        in_buffer = near_mean_buffer(
            market["bucket_low_f"], market["bucket_high_f"],
            combined_mean, buffer_f
        )
    r4 = not in_buffer
    rules.append(("outside_mean_buffer", r4,
                  f"bucket=[{market['bucket_low_f']},{market['bucket_high_f']}] "
                  f"mean={combined_mean:.1f}F buf±{buffer_f}F"))
    all_pass = all_pass and r4

    # Rule 5: No duplicate open bet for this bucket; exposure check
    dup = any(b.get("slug") == slug for b in current_open_bets
              if b.get("status") == "open")
    exposure = sum(b.get("stake", 0) for b in current_open_bets
                   if b.get("status") == "open")
    max_exposure = bankroll * max_exposure_pct
    r5 = not dup and (exposure + stake) <= max_exposure
    dup_reason = "duplicate slug" if dup else ""
    exp_reason = f"exposure ${exposure:.2f}+${stake:.2f} > ${max_exposure:.2f}" if (exposure + stake) > max_exposure else ""
    rules.append(("bankroll_ok", r5,
                  f"dup={dup} exposure=${exposure:.2f} max=${max_exposure:.2f} {dup_reason}{exp_reason}"))
    all_pass = all_pass and r5

    # --- Determine action ---
    shares = round(stake / ask, 4) if ask > 0 else 0.0

    if all_pass:
        action = "BET"
        reason = f"All rules pass. Edge={edge_pct:.1f}pt, prob={ensemble_prob:.1%}, ask={ask:.3f}"
    elif edge_pct >= near_miss_min * 100 and r2 and r3:
        # Edge 5-10pt (or near miss): log but don't bet
        action = "NEAR_MISS"
        reason = f"Near-miss: edge={edge_pct:.1f}pt (need {edge_threshold*100:.0f}pt). Logged."
        if not r4:
            action = "SKIP"
            reason = f"In mean buffer (edge {edge_pct:.1f}pt would qualify but bucket straddles mean)"
        elif not r5:
            action = "SKIP"
            reason = f"Bankroll/dup rule blocked (edge {edge_pct:.1f}pt)"
    else:
        failed = [name for name, passed, _ in rules if not passed]
        reason = f"Skip: failed rules = {', '.join(failed)}"
        action = "SKIP"

    return {
        "action": action,
        "reason": reason,
        "edge_pct": round(edge_pct, 2),
        "ensemble_prob": round(ensemble_prob, 4),
        "ask_price": ask,
        "gfs_mean_f": round(gfs_m, 1),
        "ecmwf_mean_f": round(ecmwf_m, 1),
        "combined_mean_f": round(combined_mean, 1),
        "n_members": len(all_highs),
        "all_rules": rules,
        "shares": shares,
        "stake": stake,
    }


def simulate_fill(market, evaluation, cfg):
    """
    Build a paper-bet record from a BET evaluation.
    Returns a dict ready to append to bets.csv.
    """
    fee_pct = cfg.get("fee_on_winnings_pct", 2.0) / 100.0
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    ask = evaluation["ask_price"]
    stake = evaluation["stake"]
    shares = evaluation["shares"]
    gross_if_win = shares * 1.0
    fee_if_win = gross_if_win * fee_pct
    net_if_win = gross_if_win - fee_if_win - stake  # profit after fee and cost back

    return {
        "bet_id": f"{market['slug']}__{now[:16].replace(':', '')}",
        "timestamp": now,
        "city": market["city"],
        "station": market["station"],
        "question": market["question"],
        "slug": market["slug"],
        "market_id": market.get("market_id", ""),
        "yes_token": market["yes_token"],
        "end_date": market["end_date"],
        "bucket_low_f": market["bucket_low_f"],
        "bucket_high_f": market["bucket_high_f"],
        "is_open_ended_low": market.get("is_open_ended_low", False),
        "is_open_ended_high": market.get("is_open_ended_high", False),
        "ask_price": ask,
        "stake": stake,
        "shares": shares,
        "gross_if_win": round(gross_if_win, 4),
        "fee_if_win": round(fee_if_win, 4),
        "net_profit_if_win": round(net_if_win, 4),
        "net_loss_if_lose": round(-stake, 4),
        "ensemble_prob": evaluation["ensemble_prob"],
        "edge_pct": evaluation["edge_pct"],
        "gfs_mean_f": evaluation["gfs_mean_f"],
        "ecmwf_mean_f": evaluation["ecmwf_mean_f"],
        "n_members": evaluation["n_members"],
        "status": "open",
        "result": "",
        "actual_high_f": "",
        "settled_at": "",
        "pnl": "",
        "is_test": "N",
    }
