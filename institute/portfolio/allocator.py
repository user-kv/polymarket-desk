"""Fractional-Kelly allocation with correlation caps (CONSTITUTION Gate 5/6 + §7).

Turns a list of graduated cells into a risk-managed book. Nothing gets capital
unless the evidence earns it; dominated correlated exposure is blocked at Gate 5.
"""
import math

from institute.scoring import clip
from institute.portfolio.factor import cell_vector, correlation

# Changeable params per CONSTITUTION §10 table.
KELLY_FRACTION = 0.25          # start ~0.25, tune
CELL_CAP = 0.10                # max bankroll fraction in one cell
ARCHETYPE_CAP = 0.25           # max per archetype
CLUSTER_CAP = 0.25             # max per correlated cluster
TOTAL_CAP = 0.60               # max deployed; remainder is RESERVE (§7)
CLUSTER_CORR = 0.50            # cells with corr >= this share a cluster
DEFAULT_CELL_DD = -0.20        # default per-cell drawdown halt (§7)
DEFAULT_BOOK_DD = -0.15        # default book drawdown halt (§7)
CALIB_TARGET = 0.05            # mean_S at which calibration_quality = 1.0
MARGINAL_FLOOR_FRAC = 0.5      # non-anchor must have ev_net >= this * anchor.ev_net


def kelly_fraction(win_prob, payoff_b, calib):
    """Fractional Kelly bet size as fraction of bankroll.

    Returns 0.0 for no-edge or negative-edge situations.
    Clipped to [0, CELL_CAP].
    """
    if payoff_b <= 0:
        return 0.0
    f_star = win_prob - (1.0 - win_prob) / payoff_b
    if f_star <= 0:
        return 0.0
    f = f_star * KELLY_FRACTION * calib
    return max(0.0, min(CELL_CAP, f))


def calibration_quality(cell):
    """Monotone map of mean_S into [0, 1].

    A cell scoring our proven +0.063 weather skill earns ~full weight.
    Zero or negative mean_S -> 0 (gets cut, not merely trusted less, per §7).
    """
    mean_s = cell["metrics"].get("mean_S", 0.0)
    return min(1.0, max(0.0, mean_s / CALIB_TARGET))


def cluster(cells):
    """Union-find transitive grouping: cells with corr >= CLUSTER_CORR share a cluster.

    Returns list of index-groups (each group is a sorted list of indices).
    Same-archetype cells always cluster (corr 1.0).
    """
    n = len(cells)
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py

    for i in range(n):
        for j in range(i + 1, n):
            va = cell_vector(cells[i]["archetype"])
            vb = cell_vector(cells[j]["archetype"])
            c = correlation(va, vb)
            if c >= CLUSTER_CORR:
                union(i, j)

    groups = {}
    for i in range(n):
        root = find(i)
        groups.setdefault(root, []).append(i)
    return [sorted(g) for g in groups.values()]


def allocate(cells, bankroll, **overrides):
    """Compute risk-managed allocation for a list of graduated cells.

    cells: list of dicts with keys id, archetype, baseline, metrics, mean_price,
           and optionally max_drawdown_live.
    bankroll: total capital available.
    overrides: not currently used; reserved for future param overrides.

    Returns allocation dict per spec section 3d.
    """
    if not cells:
        return {
            "bankroll": bankroll,
            "deployed": 0.0,
            "reserve": round(bankroll, 2),
            "book_drawdown_halt": DEFAULT_BOOK_DD,
            "clusters": [],
            "allocations": [],
        }

    # Step 1: compute raw Kelly and calib per cell
    raws = []
    calibs = []
    statuses = []
    reasons = []
    for cell in cells:
        metrics = cell["metrics"]
        mean_price = cell.get("mean_price", 0.5)
        win_prob = metrics.get("win_pct", 0.0) / 100.0
        payoff_b = 1.0 / clip(mean_price) - 1.0
        calib = calibration_quality(cell)
        raw = kelly_fraction(win_prob, payoff_b, calib)
        raws.append(raw)
        calibs.append(calib)
        if raw == 0.0:
            statuses.append("no_edge")
            reasons.append("Kelly raw = 0 (no edge or zero calibration)")
        else:
            statuses.append("allocated")
            reasons.append("")

    # Step 2: build clusters; apply marginal-contribution gate (Gate 5)
    clusters = cluster(cells)
    cluster_idx = [0] * len(cells)  # which cluster each cell belongs to
    for ci, grp in enumerate(clusters):
        for idx in grp:
            cluster_idx[idx] = ci

    weights = list(raws)  # working copy

    for grp in clusters:
        # Only consider cells that still have positive raw Kelly
        active = [i for i in grp if weights[i] > 0]
        if len(active) <= 1:
            continue
        # Sort by ev_net desc to find anchor
        active.sort(key=lambda i: cells[i]["metrics"].get("ev_net", 0.0), reverse=True)
        anchor_ev = cells[active[0]]["metrics"].get("ev_net", 0.0)
        marginal_floor = MARGINAL_FLOOR_FRAC * anchor_ev if anchor_ev > 0 else 0.0
        for i in active[1:]:
            cell_ev = cells[i]["metrics"].get("ev_net", 0.0)
            if cell_ev < marginal_floor:
                weights[i] = 0.0
                statuses[i] = "gate5_wait"
                reasons[i] = "dominated within cluster"

    # Step 3: apply caps in order
    capped_by = ["none"] * len(cells)

    # Per-cell cap already applied in kelly_fraction (clips to CELL_CAP).
    # Record cells that hit the cell cap.
    for i in range(len(cells)):
        if raws[i] >= CELL_CAP and weights[i] > 0:
            capped_by[i] = "cell"

    # Cluster cap: scale cluster sums down to CLUSTER_CAP
    for grp in clusters:
        cluster_sum = sum(weights[i] for i in grp)
        if cluster_sum > CLUSTER_CAP:
            scale = CLUSTER_CAP / cluster_sum
            for i in grp:
                if weights[i] > 0:
                    weights[i] *= scale
                    if capped_by[i] == "none":
                        capped_by[i] = "cluster"

    # Archetype cap: scale per-archetype sums down to ARCHETYPE_CAP
    archetypes = list({cell["archetype"] for cell in cells})
    for arch in archetypes:
        idxs = [i for i, cell in enumerate(cells) if cell["archetype"] == arch]
        arch_sum = sum(weights[i] for i in idxs)
        if arch_sum > ARCHETYPE_CAP:
            scale = ARCHETYPE_CAP / arch_sum
            for i in idxs:
                if weights[i] > 0:
                    weights[i] *= scale
                    if capped_by[i] in ("none", "cell"):
                        capped_by[i] = "archetype"

    # Total cap: scale all down to TOTAL_CAP
    total = sum(weights)
    if total > TOTAL_CAP:
        scale = TOTAL_CAP / total
        for i in range(len(cells)):
            if weights[i] > 0:
                weights[i] *= scale
                if capped_by[i] == "none":
                    capped_by[i] = "total"

    # Step 4: reserve fraction
    total_deployed = sum(weights)
    reserve_frac = 1.0 - total_deployed

    # Step 5: build allocation records
    alloc_records = []
    for i, cell in enumerate(cells):
        w = weights[i]
        dollars = round(w * bankroll, 2)
        status = statuses[i]
        # If weight rounded away but not explicitly gate5_wait/no_edge, treat as allocated
        # (weight 0 due to caps still shows allocated but 0 dollars)
        alloc_records.append({
            "id": cell["id"],
            "archetype": cell["archetype"],
            "baseline": cell["baseline"],
            "weight": round(w, 4),
            "dollars": dollars,
            "calib": round(calibs[i], 3),
            "kelly_raw": round(raws[i], 4),
            "cluster": cluster_idx[i],
            "capped_by": capped_by[i],
            "status": status,
            "reason": reasons[i],
        })

    # Sort by weight desc
    alloc_records.sort(key=lambda r: r["weight"], reverse=True)

    return {
        "bankroll": bankroll,
        "deployed": round(total_deployed * bankroll, 2),
        "reserve": round(reserve_frac * bankroll, 2),
        "book_drawdown_halt": DEFAULT_BOOK_DD,
        "clusters": [[cells[i]["id"] for i in grp] for grp in clusters],
        "allocations": alloc_records,
    }
