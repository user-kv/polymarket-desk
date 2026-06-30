"""Tests for institute/verticals/cpi/parse.py (B1).

Offline and deterministic -- no network.
"""
import math

from institute.verticals.cpi.parse import parse_market


# ---------------------------------------------------------------------------
# US CPI MoM -- positive cases
# ---------------------------------------------------------------------------

def test_parse_by_x_percent_bucket():
    """'Will monthly inflation increase by 0.3% in June?' -> bucket [0.25, 0.35)."""
    result = parse_market(
        "Will monthly inflation increase by 0.3% in June?",
        "cpi-increase-0-3-june"
    )
    assert result is not None
    assert result["indicator"] == "us_cpi_mom"
    assert result["period"].endswith("-06")
    assert abs(result["lo"] - 0.25) < 1e-9, f"lo={result['lo']}"
    assert abs(result["hi"] - 0.35) < 1e-9, f"hi={result['hi']}"


def test_parse_more_than():
    """'Will US CPI increase more than 0.4% in July?' -> lo=0.4, hi=+inf."""
    result = parse_market(
        "Will US CPI increase more than 0.4% in July?",
        "us-cpi-more-than-0-4-july"
    )
    assert result is not None
    assert result["indicator"] == "us_cpi_mom"
    assert abs(result["lo"] - 0.4) < 1e-9
    assert result["hi"] == float("inf")


def test_parse_less_than():
    """'Will monthly CPI rise less than 0.2% in August?' -> lo=-inf, hi=0.2."""
    result = parse_market(
        "Will monthly CPI rise less than 0.2% in August?",
        "monthly-cpi-less-than-0-2-august"
    )
    assert result is not None
    assert result["lo"] == float("-inf")
    assert abs(result["hi"] - 0.2) < 1e-9


def test_parse_between():
    """'Will inflation be between 0.2% and 0.4% in May?' -> lo=0.2, hi=0.4."""
    result = parse_market(
        "Will inflation be between 0.2% and 0.4% in May?",
        "inflation-between-may"
    )
    assert result is not None
    assert abs(result["lo"] - 0.2) < 1e-9
    assert abs(result["hi"] - 0.4) < 1e-9


def test_parse_with_explicit_year():
    """'Will US CPI MoM be more than 0.3% in June 2026?' -> period 2026-06."""
    result = parse_market(
        "Will US CPI MoM be more than 0.3% in June 2026?",
        "cpi-mom-june-2026"
    )
    assert result is not None
    assert result["period"] == "2026-06"


def test_parse_zero_point_three_bucket_bounds():
    """0.3% bucket must be exactly [0.25, 0.35) within float tolerance."""
    result = parse_market(
        "Will monthly inflation increase by 0.3% in March?",
        "cpi-0-3-march"
    )
    assert result is not None
    assert abs(result["lo"] - 0.25) < 1e-9
    assert abs(result["hi"] - 0.35) < 1e-9


# ---------------------------------------------------------------------------
# Non-US / ambiguous -> None
# ---------------------------------------------------------------------------

def test_parse_uk_cpi_returns_none():
    """UK CPI market -> None (abstain)."""
    assert parse_market(
        "Will UK CPI increase by 0.3% in June?",
        "uk-cpi-june"
    ) is None


def test_parse_china_cpi_returns_none():
    """China CPI market -> None."""
    assert parse_market(
        "Will China CPI be more than 0.2% in May?",
        "china-cpi-may"
    ) is None


def test_parse_gdp_returns_none():
    """GDP market -> None."""
    assert parse_market(
        "Will US GDP growth in Q2 2026 be between 2.5% and 3.0%?",
        "us-gdp-q2-2026"
    ) is None


def test_parse_yoy_returns_none():
    """Year-over-year CPI -> None."""
    assert parse_market(
        "Will US CPI year-over-year exceed 3.0% in June?",
        "us-cpi-yoy-june"
    ) is None


def test_parse_annual_returns_none():
    """Annual CPI reference -> None."""
    assert parse_market(
        "Will the annual CPI be above 2.5% for 2026?",
        "annual-cpi-2026"
    ) is None


def test_parse_non_cpi_returns_none():
    """Non-inflation question -> None."""
    assert parse_market(
        "Will Bitcoin be above $100,000 by end of June?",
        "btc-100k-june"
    ) is None


def test_parse_empty_returns_none():
    """Empty question -> None."""
    assert parse_market("", "") is None


def test_parse_no_bounds_returns_none():
    """CPI market without parseable bounds -> None."""
    assert parse_market(
        "Will US CPI increase in June?",
        "cpi-increase-june"
    ) is None
