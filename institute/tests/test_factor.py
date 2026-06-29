"""A4 portfolio/factor.py: structural factor correlation tests."""
from institute.portfolio.factor import cell_vector, correlation, corr_matrix, CELL_FACTORS


def test_weather_weather_corr_is_one():
    va = cell_vector("weather-daily")
    vb = cell_vector("weather-daily")
    assert correlation(va, vb) == 1.0


def test_weather_crypto_corr_is_zero():
    va = cell_vector("weather-daily")
    vb = cell_vector("crypto-daily")
    # weather has only "weather" key; crypto has "crypto_beta" + "macro" -- no overlap
    assert correlation(va, vb) == 0.0


def test_crypto_econ_share_macro_partial_corr():
    va = cell_vector("crypto-daily")   # crypto_beta=1.0, macro=0.3
    vb = cell_vector("econ-release")   # macro=1.0
    c = correlation(va, vb)
    assert 0.0 < c < 1.0, f"expected partial correlation, got {c}"


def test_corr_matrix_diagonal_all_one():
    archetypes = ["weather-daily", "crypto-daily", "sports-game", "econ-release"]
    mat = corr_matrix(archetypes)
    for i in range(len(archetypes)):
        assert mat[i][i] == 1.0, f"diagonal [{i}][{i}] != 1.0"


def test_corr_matrix_symmetric():
    archetypes = ["weather-daily", "crypto-daily", "sports-game", "econ-release"]
    mat = corr_matrix(archetypes)
    n = len(archetypes)
    for i in range(n):
        for j in range(n):
            assert abs(mat[i][j] - mat[j][i]) < 1e-9, f"matrix not symmetric at [{i}][{j}]"


def test_cell_vector_does_not_mutate():
    v1 = cell_vector("weather-daily")
    v1["injected"] = 99.0
    v2 = cell_vector("weather-daily")
    assert "injected" not in v2, "cell_vector returned a mutable reference to CELL_FACTORS"


def test_unknown_archetype_returns_empty():
    v = cell_vector("unknown-type")
    assert v == {}


def test_unknown_archetype_corr_zero():
    va = cell_vector("unknown-type")
    vb = cell_vector("weather-daily")
    assert correlation(va, vb) == 0.0
