"""Corpus dataclasses (CONSTITUTION §1, A1_PLAN schemas)."""
from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class ResolvedMarket:
    """A market with known outcome — the atomic row of the predictability map.

    q_yes: market-implied P(YES) at decision time (executable price, not mid).
    y:     1 if YES resolved, else 0.
    realized_pnl/stake: actual ledger result when this row came from real paper
                        trades (used as ground-truth anchor); else None → simulate.
    """
    market_id: str
    archetype: str
    t0: str
    q_yes: float
    y: int
    realized_pnl: Optional[float] = None
    realized_side: Optional[str] = None  # 'YES' | 'NO'
    stake: float = 1.0
    meta: dict = field(default_factory=dict)

    def dict(self):
        return asdict(self)


@dataclass
class MapCell:
    archetype: str
    baseline: str
    n: int
    win_pct: float
    mean_S: float
    ev_net: float
    naive_roi: float
    status: str  # green | grey | red

    def dict(self):
        return asdict(self)


@dataclass
class Trial:
    """Trial-registry skeleton (CONSTITUTION §5). Populated for real in A2."""
    id: str
    archetype: str
    strategy_id: str
    params: dict = field(default_factory=dict)
    search_context: dict = field(default_factory=dict)
    metrics: dict = field(default_factory=dict)
    verdict: str = "pending"
    ts: str = ""

    def dict(self):
        return asdict(self)
