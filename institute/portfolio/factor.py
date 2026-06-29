"""Gate 5 structural factor correlation between cells (CONSTITUTION §11 Seam 2).

Correlation is computed from shared factor loadings (Barra-style), never from
sparse pairwise pnl history. Stable numeric betas only -- categorical keys
(region_day, underlying, league, event) are intra-cluster concentration signals,
not cross-cell co-movement, so they are excluded here.
"""
import math

# Structural betas per archetype for Gate-5 correlation (numeric, history-free).
# These are the only factors used for cross-cell correlation; categorical meta
# keys from classify.factors.loadings() are intentionally excluded.
CELL_FACTORS = {
    "weather-daily": {"weather": 1.0},
    "crypto-daily":  {"crypto_beta": 1.0, "macro": 0.3},
    "sports-game":   {"sports": 1.0},
    "econ-release":  {"macro": 1.0},
}


def cell_vector(archetype):
    """Return a copy of the structural factor loadings for this archetype.

    Returns {} for unknown archetypes (-> correlation 0 with everything).
    Never mutates CELL_FACTORS.
    """
    return dict(CELL_FACTORS.get(archetype, {}))


def correlation(va, vb):
    """Cosine similarity over the union of factor keys.

    dot / (||va|| * ||vb||). Returns 0.0 if either norm is zero.
    All weights are >= 0 so result is in [0, 1]. Rounded to 4 dp.
    """
    keys = set(va) | set(vb)
    dot = sum(va.get(k, 0.0) * vb.get(k, 0.0) for k in keys)
    norm_a = math.sqrt(sum(v * v for v in va.values()))
    norm_b = math.sqrt(sum(v * v for v in vb.values()))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return round(dot / (norm_a * norm_b), 4)


def corr_matrix(archetypes):
    """Square correlation matrix in the given order. Diagonal = 1.0."""
    n = len(archetypes)
    vectors = [cell_vector(a) for a in archetypes]
    matrix = []
    for i in range(n):
        row = []
        for j in range(n):
            if i == j:
                row.append(1.0)
            else:
                row.append(correlation(vectors[i], vectors[j]))
        matrix.append(row)
    return matrix
