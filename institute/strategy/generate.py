"""Strategy proposal engine (CONSTITUTION §11C strategy-gen, budgeted).

Converts a predictability map into candidate Strategy proposals, each with a
stated causal mechanism. Budget-caps search intensity so the trial count stays
deflation-honest.
"""
import datetime
import uuid

from institute.corpus.schema import Strategy
from institute.map import baselines as B
from institute.map import predictability
from institute.resolve import weather_adapter
from institute.corpus import registry

# Causal mechanism seeded per baseline — the "why" claim Gate 2 must verify.
BASELINE_MECHANISM = {
    "longshot_fade": (
        "favorite_longshot_bias",
        "cheap longshots are systematically overpriced; fade (bet NO)",
    ),
    "price_follow": (
        "",
        "null: copies the price, no claimed edge",
    ),
    "odds_follow": (
        "market_consensus",
        "sharp sportsbook odds beat thin PM price",
    ),
    "power_rating_fade": (
        "model_vs_crowd",
        "power-rating model disagrees with crowd-driven PM price",
    ),
    "research": (
        "model_vs_crowd",
        "independent ensemble forecast diverges from the PM price; bet the edge",
    ),
}


def _utcnow_iso():
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve_baseline(name):
    """Look up a baseline function by name across weather + sports registries.

    Weather baselines live in B.BASELINES; sports baselines are registered in
    classify.sports.SPORTS_BASELINES. Keeping resolution here avoids circular
    imports between strategy and classify.
    """
    if name in B.BASELINES:
        fn, kw, _ = B.BASELINES[name]
        return fn, kw

    # Lazy import to avoid circular dependency at module load time.
    from institute.classify.sports import SPORTS_BASELINES
    if name in SPORTS_BASELINES:
        return SPORTS_BASELINES[name], {}

    raise ValueError(f"unknown baseline '{name}'")


def propose_from_map(cells, budget=10) -> list:
    """Emit one Strategy per promising MapCell, capped at budget.

    Skips the price_follow null baseline (no edge claimed) and cells where
    mean_S <= 0 (no skill signal). One proposal per archetype+baseline pair
    so duplicates are structurally impossible.
    """
    proposals = []
    for cell in cells:
        if len(proposals) >= budget:
            break
        if cell.baseline == "price_follow":
            continue
        if cell.mean_S <= 0:
            continue
        mech, hyp = BASELINE_MECHANISM.get(cell.baseline, ("", ""))
        s = Strategy(
            id=uuid.uuid4().hex[:12],
            archetype=cell.archetype,
            baseline=cell.baseline,
            params={},
            mechanism=mech,
            hypothesis=hyp,
            status="proposed",
            metrics={
                "mean_S": cell.mean_S,
                "ev_net": cell.ev_net,
                "n": cell.n,
            },
            ts=_utcnow_iso(),
        )
        proposals.append(s)
    return proposals


def propose(rows=None, budget=10) -> list:
    """Load weather rows (if not provided), build map, propose strategies."""
    if rows is None:
        rows = weather_adapter.load_rows()
    cells = predictability.build(rows)
    return propose_from_map(cells, budget=budget)


def log_proposals(strategies, registry_path):
    """Write each proposal as a Trial so the deflation counter stays honest."""
    from institute.corpus.schema import Trial
    for s in strategies:
        trial = Trial(
            id=uuid.uuid4().hex,
            archetype=s.archetype,
            strategy_id=s.id,
            params={"baseline": s.baseline},
            metrics=s.metrics,
            verdict="proposed",
            ts=s.ts,
        )
        registry.log_trial(registry_path, trial)
