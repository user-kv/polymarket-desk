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
    # Favorite-longshot guard (added 2026-06-20). 0 = disabled.
    min_prob = cfg.get("min_ensemble_prob_pct", 0.0) / 100.0
    # M4: NO-side betting (buy NO on cheap overpriced longshots).
    allow_no_side = cfg.get("allow_no_side", False)
    no_longshot_max = cfg.get("no_longshot_max_ask", 0.15)

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
    # RMSE-weighted by MODEL (M2): models with lower historical RMSE get more
    # weight. Falls back to equal-weight when no calibration weights exist yet.
    from lib.forecasts import bucket_probability_by_model, models_agree, near_mean_buffer
    all_highs = forecast.get("all_highs_f", [])
    ensemble_prob = bucket_probability_by_model(
        forecast,
        market["bucket_low_f"],
        market["bucket_high_f"],
        model_weights=forecast.get("model_weights"),
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

    # Rule 6: Favorite-longshot guard. A 5pt "edge" over a 0.1% ask is still a bet
    # the MODEL ITSELF thinks is a longshot. All 5 of the first paper losses were
    # exactly this (ensemble_prob 0.05-0.14 on deep-tail buckets) — Gemini's autopsies
    # all converged on "don't bet extreme tails without a physical driver." This rule
    # enforces that lesson: require a minimum absolute probability before betting.
    r6 = ensemble_prob >= min_prob
    rules.append(("min_ensemble_prob", r6,
                  f"prob={ensemble_prob:.3f} min={min_prob:.3f}"))
    all_pass = all_pass and r6

    # --- M4: NO-side evaluation (favorite-longshot, buy NO on cheap overpriced buckets) ---
    # YES and NO cannot both qualify on the same market bucket for the same threshold
    # (YES needs prob > ask+thr; NO needs ask > prob+thr — mutually exclusive). So we
    # check NO only when YES failed rule 1 (edge) — or when YES never had edge at all.
    # Rules 2-6 (time, model agreement, buffer, exposure, min-prob) still apply to NO.
    no_side_result = None
    if allow_no_side and not all_pass and r2 and r3:
        # NO edge: market overprices YES relative to ensemble — we buy NO at (1 - ask)
        no_edge = ask - ensemble_prob           # positive when market > model
        no_edge_pct = no_edge * 100.0
        no_qualifies = (
            no_edge >= edge_threshold           # same edge threshold as YES
            and ask <= no_longshot_max          # only cheap longshots (ask ≤ 15¢)
            and r4                              # not in coin-flip buffer
            and r5                              # bankroll/dup ok
        )
        if no_qualifies:
            # Kelly for NO: f* = (ask - ensemble_prob) / ask  (NO payoff = 1/(1-ask)-1 = ask/(1-ask))
            no_stake = stake
            if cfg.get("use_kelly_staking", False) and no_edge > 0 and ask > 0:
                f_star_no = no_edge / ask
                no_stake = bankroll * cfg.get("kelly_fraction", 0.25) * f_star_no
                no_stake = max(cfg.get("min_stake", 1.0),
                               min(no_stake, cfg.get("max_stake", 100.0)))
            no_entry = 1.0 - ask
            no_shares = round(no_stake / no_entry, 4) if no_entry > 0 else 0.0
            no_side_result = {
                "qualifies": True,
                "no_edge_pct": round(no_edge_pct, 2),
                "no_stake": no_stake,
                "no_shares": no_shares,
                "no_entry_price": round(no_entry, 4),
            }

    # --- Brain sizing (M3): only called when all engine rules pass ---
    brain_result = None
    is_no_bet = no_side_result is not None and no_side_result.get("qualifies") and not all_pass
    if (all_pass or is_no_bet) and cfg.get("use_brain", False):
        from lib import brain as _brain
        _eval_for_brain = {
            "ensemble_prob": ensemble_prob, "ask_price": ask,
            "edge_pct": no_side_result["no_edge_pct"] if is_no_bet else edge_pct,
            "gfs_mean_f": round(gfs_m, 1), "ecmwf_mean_f": round(ecmwf_m, 1),
            "combined_mean_f": round(combined_mean, 1), "n_members": len(all_highs),
        }
        brain_result = _brain.evaluate_bet(market, forecast, _eval_for_brain, cfg)
        if brain_result.get("vetoed"):
            all_pass = False
            is_no_bet = False

    # Apply brain size multiplier to Kelly stake (YES side)
    if all_pass and brain_result and brain_result["multiplier"] != 1.0:
        mult = brain_result["multiplier"]
        stake = max(cfg.get("min_stake", 1.0),
                    min(stake * mult, cfg.get("max_stake", 100.0)))
    # Apply brain multiplier to NO stake if it's a NO bet
    if is_no_bet and brain_result and brain_result["multiplier"] != 1.0:
        mult = brain_result["multiplier"]
        no_side_result["no_stake"] = max(
            cfg.get("min_stake", 1.0),
            min(no_side_result["no_stake"] * mult, cfg.get("max_stake", 100.0))
        )

    # --- Determine action ---
    shares = round(stake / ask, 4) if ask > 0 else 0.0

    if all_pass:
        brain_note = ""
        if brain_result:
            brain_note = (f" | brain={brain_result['backend']} "
                          f"x{brain_result['multiplier']:.1f} '{brain_result['rationale']}'")
        action = "BET"
        reason = f"All rules pass. Edge={edge_pct:.1f}pt, prob={ensemble_prob:.1%}, ask={ask:.3f}{brain_note}"
        return {
            "action": action, "reason": reason,
            "edge_pct": round(edge_pct, 2), "ensemble_prob": round(ensemble_prob, 4),
            "ask_price": ask, "gfs_mean_f": round(gfs_m, 1), "ecmwf_mean_f": round(ecmwf_m, 1),
            "combined_mean_f": round(combined_mean, 1), "n_members": len(all_highs),
            "all_rules": rules, "shares": shares, "stake": stake, "side": "YES", "brain": brain_result,
        }

    if is_no_bet:
        # M4: return a NO-side BET result
        ns = no_side_result
        brain_note = ""
        if brain_result:
            brain_note = (f" | brain={brain_result['backend']} "
                          f"x{brain_result['multiplier']:.1f} '{brain_result['rationale']}'")
        return {
            "action": "BET",
            "reason": (f"NO-side: ask={ask:.3f} > prob={ensemble_prob:.3f}+thr "
                       f"(no_edge={ns['no_edge_pct']:.1f}pt, cheap longshot){brain_note}"),
            "edge_pct": ns["no_edge_pct"],
            "ensemble_prob": round(ensemble_prob, 4),
            "ask_price": ask,
            "gfs_mean_f": round(gfs_m, 1), "ecmwf_mean_f": round(ecmwf_m, 1),
            "combined_mean_f": round(combined_mean, 1), "n_members": len(all_highs),
            "all_rules": rules,
            "shares": ns["no_shares"],
            "stake": ns["no_stake"],
            "side": "NO",
            "no_entry_price": ns["no_entry_price"],
            "brain": brain_result,
        }

    if brain_result and brain_result.get("vetoed"):
        action = "SKIP"
        reason = f"Brain VETO: {brain_result['rationale']}"
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
        elif not r6:
            action = "SKIP"
            reason = (f"Favorite-longshot guard: model prob {ensemble_prob:.1%} < "
                      f"{min_prob:.0%} floor (edge {edge_pct:.1f}pt is illusory on a tail bucket)")
    else:
        failed = [name for name, passed, _ in rules if not passed]
        reason = f"Skip: failed rules = {', '.join(failed)}"
        action = "SKIP"

    return {
        "action": action, "reason": reason,
        "edge_pct": round(edge_pct, 2), "ensemble_prob": round(ensemble_prob, 4),
        "ask_price": ask, "gfs_mean_f": round(gfs_m, 1), "ecmwf_mean_f": round(ecmwf_m, 1),
        "combined_mean_f": round(combined_mean, 1), "n_members": len(all_highs),
        "all_rules": rules, "shares": shares, "stake": stake, "side": "YES", "brain": brain_result,
    }


def simulate_fill(market, evaluation, cfg):
    """
    Build a paper-bet record from a BET evaluation.
    Returns a dict ready to append to bets.csv.

    For YES bets: entry price = ask, wins when bucket resolves YES.
    For NO bets:  entry price = 1 - ask, wins when bucket does NOT resolve.
    """
    fee_pct = cfg.get("fee_on_winnings_pct", 2.0) / 100.0
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    side = evaluation.get("side", "YES")
    ask = evaluation["ask_price"]
    stake = evaluation["stake"]
    shares = evaluation["shares"]

    if side == "NO":
        # NO entry price = 1 - ask; shares already set to stake / (1 - ask) by engine
        gross_if_win = shares * 1.0
    else:
        gross_if_win = shares * 1.0  # same formula; entry price baked into shares count

    fee_if_win = gross_if_win * fee_pct
    net_if_win = gross_if_win - fee_if_win - stake

    brain = evaluation.get("brain") or {}
    brain_mult = brain.get("multiplier", 1.0) if brain else 1.0
    brain_rationale = brain.get("rationale", "") if brain else ""

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
        "side": side,
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
        "brain_multiplier": round(brain_mult, 2),
        "brain_rationale": brain_rationale,
        "status": "open",
        "result": "",
        "actual_high_f": "",
        "settled_at": "",
        "pnl": "",
        "is_test": "N",
    }
