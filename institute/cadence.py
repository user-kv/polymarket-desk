"""Cadence loop: one perceive->reason->plan->act->verify->critique->improve pass (A6).

Pure orchestration.  All heavy lifting is in modules that already have their
own tests.  The cadence does NOT place network calls itself (mock=True default);
mock=False enables the real LLM/forecaster path.

PERCEIVE+VERIFY: the cron already runs snapshot/settle before this; cadence
  does not trigger network calls (that is the sensor's job).
REASON:    forecast_open() over each wired store.
PLAN+GATE+ACT: build_book() runs rows through Gates 1-7 + the allocator;
  the new ``research`` baseline cell flows through unchanged.
CRITIQUE: gate4/decay summary is already embedded in the book.
"""
import os

from institute.alpha.forecast_store import forecast_open
from institute.resolve import load_all_rows
from institute.portfolio import book as _book
from institute.sensor.crypto import CRYPTO_STORE

# Wired stores: {label: store_path}. Weather store added here when present.
_DEFAULT_STORES = {
    "crypto": CRYPTO_STORE,
}


def run_cycle(stores=None, bankroll=10000.0, mock=True, log=False, forecast=True):
    """Run one full cadence pass.

    Args:
        stores:   dict {label: store_path} to forecast. Defaults to the crypto store.
        bankroll: total capital for book construction.
        mock:     passed through to forecast_open / build_book.
        log:      passed through to build_book.
        forecast: when False, SKIP the forecast step entirely (build the book
                  over existing rows only). The CLI sets this False unless a
                  real model is wired, so placeholder forecasts are never frozen
                  onto live markets.

    Returns:
        {"forecast": {label: n_newly_forecast}, "book": book_dict}
    """
    if stores is None:
        stores = _DEFAULT_STORES

    # REASON: form point-in-time forecasts for all OPEN, un-forecast rows
    forecast_counts = {}
    for label, path in stores.items():
        if not forecast or not os.path.exists(path):
            forecast_counts[label] = 0
            continue
        newly = forecast_open(path, mock=mock)
        forecast_counts[label] = len(newly)

    # PLAN + GATE + ACT: build the risk-managed book
    rows = load_all_rows()
    b = _book.build_book(rows=rows, bankroll=bankroll, log=log)

    return {"forecast": forecast_counts, "book": b}
