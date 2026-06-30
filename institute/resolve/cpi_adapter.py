"""CPI store -> ResolvedMarket rows (B1 resolve adapter).

Mirrors crypto_adapter.load_rows() in spirit: reads the settled JSONL store
and emits ResolvedMarket dicts. No network -- pure read.
"""
from institute.corpus.schema import ResolvedMarket
from institute.verticals.cpi.sensor import CPI_STORE


def load_rows(store_path=CPI_STORE):
    """Load settled econ-cpi rows as ResolvedMarket dicts.

    Keeps only rows with status=="settled" and integer y.
    The frozen p_model rides in meta (point-in-time honest).
    Returns [] if the store does not exist or is empty.
    """
    from institute.corpus.store import load_jsonl
    rows_raw = load_jsonl(store_path)
    rows = []
    for row in rows_raw:
        if row.get("status") != "settled":
            continue
        y = row.get("y")
        if not isinstance(y, int):
            continue
        rows.append(ResolvedMarket(
            market_id=row["market_id"],
            archetype="econ-cpi",
            t0=row["t0"],
            q_yes=row["q_yes"],
            y=y,
            realized_pnl=None,
            realized_side=None,
            stake=1.0,
            meta=row.get("meta", {}),
        ).dict())
    return rows
