"""Per-model walk-forward RMSE weights for the CPI ensemble (B1).

Analogous to the weather bot's per-station model weights:
  - Walk-forward over history; for each month t (after min_train),
    build each model on data[:t], record error vs actual mom at t.
  - Return {model_name: rmse} + {"bias": mean signed error of ensemble mean}.

Pure, deterministic, no network.
"""
import math

from institute.verticals.cpi.models import all_models


def fit_weights(mom_hist, build_models=None, min_train=24):
    """Walk-forward RMSE fitting.

    mom_hist: list of {"mom": float, ...} sorted OLD->NEW (each entry is one month).
    build_models: callable(history, cleveland_mom=None) -> list[{"name","mu","sigma"}].
                  Defaults to all_models from models.py.
    min_train: minimum number of obs before we start scoring (default 24 = 2 yrs).

    Returns:
        {model_name: rmse_float, ..., "bias": float}

    If history too short (< min_train + 1): returns uniform {name: 1.0} per model
    and bias 0.0.
    """
    if build_models is None:
        build_models = all_models

    n = len(mom_hist)
    if n < min_train + 1:
        # Not enough history: return uniform weights and zero bias
        sample_models = build_models([{"mom": 0.0}])
        names = [m["name"] for m in sample_models]
        result = {name: 1.0 for name in names}
        result["bias"] = 0.0
        return result

    # Accumulate squared errors per model and ensemble signed errors
    sq_errors = {}   # model_name -> list of squared errors
    ens_errors = []  # signed error of ensemble mean per step

    for t in range(min_train, n):
        history = mom_hist[:t]
        actual = mom_hist[t]["mom"]

        try:
            models = build_models(history)
        except Exception:
            continue

        if not models:
            continue

        # Ensemble mean (equal weight for the signed error)
        ens_mean = sum(m["mu"] for m in models) / len(models)
        ens_errors.append(ens_mean - actual)

        for m in models:
            name = m["name"]
            err = m["mu"] - actual
            sq_errors.setdefault(name, []).append(err * err)

    if not sq_errors:
        # All steps failed -- return uniform
        sample_models = build_models(mom_hist[:min_train])
        names = [m["name"] for m in sample_models]
        result = {name: 1.0 for name in names}
        result["bias"] = 0.0
        return result

    result = {}
    for name, sq_list in sq_errors.items():
        result[name] = math.sqrt(sum(sq_list) / len(sq_list))

    result["bias"] = sum(ens_errors) / len(ens_errors) if ens_errors else 0.0
    return result


def inverse_rmse_weights(rmse_map):
    """Convert {model_name: rmse} -> {model_name: weight} summing to 1.

    Lower RMSE -> higher weight.
    Guards against rmse <= 0 with a small floor (0.001).
    Skips the "bias" key if present.
    """
    _FLOOR = 0.001
    inv = {}
    for name, rmse in rmse_map.items():
        if name == "bias":
            continue
        inv[name] = 1.0 / max(float(rmse), _FLOOR)

    total = sum(inv.values())
    if total == 0:
        n = len(inv)
        return {name: 1.0 / n for name in inv} if n else {}

    return {name: v / total for name, v in inv.items()}
