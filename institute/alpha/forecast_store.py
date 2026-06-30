"""Forecast OPEN market rows in a JSONL store, attaching forecasts to meta (A6).

Point-in-time honesty is STRUCTURAL here:
  - Only rows with status == "open" are touched.
  - Rows that already carry meta.p_final are SKIPPED (idempotent; the first,
    point-in-time forecast is the honest one — never re-forecast a market).
  - Settled rows (status != "open") are NEVER touched.
  - y is never read (it may be None on open rows; assert status is open).

Token budget: max_forecasts caps the number of NEW forecasts per call so
context/cost cannot overflow in the cron.
"""
import datetime

from institute.corpus.store import load_jsonl, overwrite_jsonl
from institute.alpha.engine import forecast_market


def forecast_open(
    store_path,
    fetch_forecaster=None,
    now=None,
    max_forecasts=25,
    mock=True,
):
    """Forecast open rows that have not yet been forecast.

    Args:
        store_path:      Path to the JSONL store.
        fetch_forecaster: Callable(row, mock=mock) -> forecast dict.
                          Defaults to alpha.engine.forecast_market.
        now:             UTC datetime (injectable for tests).
        max_forecasts:   Hard cap on new forecasts this call (token budget).
        mock:            Passed through to the forecaster.

    Returns:
        List of rows that were forecast this call (newly updated rows only).
    """
    if fetch_forecaster is None:
        fetch_forecaster = forecast_market

    if now is None:
        now = datetime.datetime.utcnow()

    rows = load_jsonl(store_path)
    newly_forecast = []

    for row in rows:
        if len(newly_forecast) >= max_forecasts:
            break

        # NEVER touch settled rows
        if row.get("status") != "open":
            continue

        # Idempotency: skip if already forecast
        meta = row.get("meta")
        if meta is None:
            row["meta"] = {}
            meta = row["meta"]
        if meta.get("p_final") is not None:
            continue

        # Safety assertion: must be an open row (y should be None)
        assert row.get("status") == "open", (
            f"forecast_open: row {row.get('market_id')} is not open"
        )

        # Call the forecaster (mock=True by default in all tests)
        result = fetch_forecaster(row, mock=mock)

        # Write forecast fields into meta (point-in-time freeze)
        meta["p_model"] = result["p_model"]
        meta["p_std"] = result["p_std"]
        meta["p_final"] = result["p_final"]
        meta["n_agents"] = result["n_agents"]
        meta["forecast_ts"] = now.strftime("%Y-%m-%dT%H:%M:%SZ")

        newly_forecast.append(row)

    # Persist all rows (including unchanged ones)
    overwrite_jsonl(store_path, rows)

    return newly_forecast
